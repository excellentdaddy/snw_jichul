"""작성이력·설정 저장소 (SQLite 파일 1개)."""
import json
import os
import sqlite3
import sys
from datetime import date, datetime

DB_NAME = "지출결의서.db"

FIELDS = ["date", "payee", "amount", "name", "detail", "note", "account"]
FIELD_LABELS = {
    "date": "날짜", "payee": "지출처", "amount": "금액", "name": "성명",
    "detail": "내역", "note": "비고", "account": "계정과목",
}


def base_dir() -> str:
    """exe 로 실행하면 exe 가 있는 폴더, 스크립트로 실행하면 app 폴더."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def documents_dir() -> str:
    """내 문서 폴더 (OneDrive 로 옮겨진 경우도 Windows 에 물어서 찾는다)."""
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def data_dir() -> str:
    """데이터 폴더.

    - exe 옆에 지출결의서.db 가 이미 있으면 그 폴더 (설치 없이 쓰는 '휴대용' 방식, 기존 배포 폴더 호환)
    - 아니면 내 문서 / S&W 지출결의서  (설치형: Program Files 등은 쓰기 불가)
    """
    here = base_dir()
    if os.path.exists(os.path.join(here, DB_NAME)) or not getattr(sys, "frozen", False):
        return here
    from version import APP_DIR_NAME
    d = os.path.join(documents_dir(), APP_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def resource_path(*parts) -> str:
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, *parts)


def to_iso(d) -> str:
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    return str(d or "")


class Store:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), DB_NAME)
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, payee TEXT, amount INTEGER, name TEXT,
                detail TEXT, note TEXT, account TEXT,
                source TEXT, created TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_records_date ON records(date);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            -- 첨부 이미지(엑셀 표 등): 내용 해시로 한 번만 저장
            CREATE TABLE IF NOT EXISTS images (hash TEXT PRIMARY KEY, png BLOB);
            """
        )
        cols = [r[1] for r in self.con.execute("PRAGMA table_info(records)")]
        if "attach" not in cols:  # 예전 데이터 파일에 첨부 칸 추가
            self.con.execute("ALTER TABLE records ADD COLUMN attach TEXT")
        self.con.commit()

    # ---------- 작성이력 ----------
    @staticmethod
    def _norm(rec: dict) -> dict:
        r = {k: rec.get(k) for k in FIELDS}
        r["date"] = to_iso(r["date"])
        r["amount"] = int(r["amount"] or 0)
        for k in ("payee", "name", "detail", "note", "account"):
            r[k] = (str(r[k]).replace("\r\n", "\n").replace("\r", "\n").strip()
                    if r[k] is not None else "")
        return r

    def exists(self, r: dict) -> bool:
        """기존 엑셀과 같은 기준(날짜·지출처·금액·성명·내역)으로 중복 판단."""
        cur = self.con.execute(
            "SELECT 1 FROM records WHERE date=? AND payee=? AND amount=? AND name=? AND detail=? LIMIT 1",
            (r["date"], r["payee"], r["amount"], r["name"], r["detail"]),
        )
        return cur.fetchone() is not None

    def _attach_json(self, images):
        """images: [{"png": bytes, "x","y","w","h": mm}] → 이미지 표에 저장하고 위치 정보 JSON 반환."""
        if not images:
            return None
        import hashlib
        out = []
        for im in images:
            h = hashlib.sha1(im["png"]).hexdigest()
            self.con.execute("INSERT OR IGNORE INTO images(hash, png) VALUES(?, ?)", (h, im["png"]))
            out.append({"hash": h, **{k: round(float(im[k]), 2) for k in ("x", "y", "w", "h")}})
        return json.dumps(out)

    def add(self, rec: dict, source="직접작성", commit=True, images=None) -> bool:
        """새로 추가하면 True. 같은 내용이 이미 있으면 False (이미지가 있으면 그 이력의 이미지만 갱신)."""
        r = self._norm(rec)
        attach = self._attach_json(images)
        if self.exists(r):
            if attach:
                self.con.execute(
                    "UPDATE records SET attach=? WHERE date=? AND payee=? AND amount=? AND name=? AND detail=?",
                    (attach, r["date"], r["payee"], r["amount"], r["name"], r["detail"]))
                if commit:
                    self.con.commit()
            return False
        self.con.execute(
            "INSERT INTO records(date,payee,amount,name,detail,note,account,source,created,attach)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (r["date"], r["payee"], r["amount"], r["name"], r["detail"], r["note"],
             r["account"], source, datetime.now().isoformat(timespec="seconds"), attach),
        )
        if commit:
            self.con.commit()
        return True

    def images_of(self, rec: dict):
        """이력의 첨부 이미지 [{"png": bytes, x, y, w, h}] (불러올 때만 읽는다)."""
        try:
            items = json.loads(rec.get("attach") or "[]")
        except ValueError:
            return []
        out = []
        for it in items:
            row = self.con.execute("SELECT png FROM images WHERE hash=?", (it.get("hash"),)).fetchone()
            if row:
                out.append({"png": bytes(row[0]), **{k: it[k] for k in ("x", "y", "w", "h")}})
        return out

    def add_many(self, recs, source):
        added = skipped = 0
        for rec in recs:
            if self.add(rec, source, commit=False):
                added += 1
            else:
                skipped += 1
        self.con.commit()
        return added, skipped

    def delete(self, rid: int):
        self.con.execute("DELETE FROM records WHERE id=?", (rid,))
        self._clean_images()
        self.con.commit()

    def _clean_images(self):
        """어느 이력에서도 쓰지 않는 이미지는 지운다."""
        used = set()
        for (a,) in self.con.execute("SELECT attach FROM records WHERE attach IS NOT NULL AND attach<>''"):
            try:
                used.update(it.get("hash") for it in json.loads(a))
            except ValueError:
                pass
        for (h,) in self.con.execute("SELECT hash FROM images").fetchall():
            if h not in used:
                self.con.execute("DELETE FROM images WHERE hash=?", (h,))

    def all(self):
        return [dict(r) for r in self.con.execute(
            "SELECT * FROM records ORDER BY date DESC, id DESC")]

    def count(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    def payees(self):
        return [r[0] for r in self.con.execute(
            "SELECT payee FROM records WHERE payee<>'' GROUP BY payee ORDER BY MAX(date) DESC")]

    def names(self):
        return [r[0] for r in self.con.execute(
            "SELECT name FROM records WHERE name<>'' GROUP BY name ORDER BY COUNT(*) DESC")]

    def latest_for_payee(self, payee: str):
        r = self.con.execute(
            "SELECT * FROM records WHERE payee=? ORDER BY date DESC, id DESC LIMIT 1", (payee,)
        ).fetchone()
        return dict(r) if r else None

    # ---------- 설정 ----------
    def get(self, key, default=None):
        r = self.con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(r[0]) if r else default

    def set(self, key, value):
        self.con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                         (key, json.dumps(value, ensure_ascii=False)))
        self.con.commit()
