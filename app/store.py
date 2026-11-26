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
            -- 첨부파일 보관함(PDF·그림): 지출결의서 뒤에 같이 인쇄. 내용 해시로 한 번만 저장
            CREATE TABLE IF NOT EXISTS files (
                hash TEXT PRIMARY KEY, name TEXT, ext TEXT, data BLOB, pages INTEGER, added TEXT
            );
            """
        )
        cols = [r[1] for r in self.con.execute("PRAGMA table_info(records)")]
        if "attach" not in cols:  # 예전 데이터 파일에 첨부 칸 추가
            self.con.execute("ALTER TABLE records ADD COLUMN attach TEXT")
        if "files" not in cols:  # 첨부파일 목록 [{"hash", "print"}]
            self.con.execute("ALTER TABLE records ADD COLUMN files TEXT")
        if "appr" not in cols:  # 결재란 표시 {"n", "slash": [..], "jeon": 칸|None, "owner": bool}
            self.con.execute("ALTER TABLE records ADD COLUMN appr TEXT")
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

    def add(self, rec: dict, source="직접작성", commit=True, images=None, files=None, appr=None) -> bool:
        """새로 추가하면 True. 같은 내용이 이미 있으면 False.
        직접 작성한 것이면 그 이력의 이미지·첨부파일을 지금 것으로 갱신한다 (가져오기는 건드리지 않음)."""
        r = self._norm(rec)
        attach = self._attach_json(images)
        fj = self._files_json(files)
        direct = source == "직접작성"
        if direct:
            self._unhide(r["name"]); self._unhide(r["account"], "hidden_accounts")
        if self.exists(r):
            if direct:
                self.con.execute(
                    "UPDATE records SET attach=?, files=?, note=?, appr=? "
                    "WHERE date=? AND payee=? AND amount=? AND name=? AND detail=?",
                    (attach, fj, r["note"], appr, r["date"], r["payee"], r["amount"], r["name"], r["detail"]))
                self._clean_images()
                if commit:
                    self.con.commit()
            return False
        self.con.execute(
            "INSERT INTO records(date,payee,amount,name,detail,note,account,source,created,attach,files,appr)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["date"], r["payee"], r["amount"], r["name"], r["detail"], r["note"],
             r["account"], source, datetime.now().isoformat(timespec="seconds"), attach, fj, appr),
        )
        if commit:
            self.con.commit()
        return True

    def find_id(self, rec: dict):
        r = self._norm(rec)
        row = self.con.execute(
            "SELECT id FROM records WHERE date=? AND payee=? AND amount=? AND name=? AND detail=?"
            " ORDER BY id DESC LIMIT 1",
            (r["date"], r["payee"], r["amount"], r["name"], r["detail"])).fetchone()
        return row[0] if row else None

    def update(self, rid: int, rec: dict, images=None, files=None, appr=None) -> bool:
        """그 이력을 지금 내용(이미지 포함, 없으면 이미지 지움)으로 덮어쓴다. 이력이 없으면 False."""
        r = self._norm(rec)
        self._unhide(r["name"]); self._unhide(r["account"], "hidden_accounts")
        cur = self.con.execute(
            "UPDATE records SET date=?, payee=?, amount=?, name=?, detail=?, note=?, account=?, attach=?, files=?,"
            " appr=? WHERE id=?",
            (r["date"], r["payee"], r["amount"], r["name"], r["detail"], r["note"], r["account"],
             self._attach_json(images), self._files_json(files), appr, rid))
        self._clean_images()
        self.con.commit()
        return cur.rowcount > 0

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

    # ---------- 첨부파일 보관함 ----------
    @staticmethod
    def _files_json(files):
        """files: [{"hash", "print"}] → 이력에 저장할 JSON (없으면 None)."""
        if not files:
            return None
        return json.dumps([{"hash": f["hash"], "print": bool(f.get("print", True))} for f in files])

    def add_file(self, name, ext, data: bytes, pages: int) -> str:
        """보관함에 넣고 해시를 돌려준다. 같은 내용이 이미 있으면 그대로 쓴다."""
        import hashlib
        h = hashlib.sha1(data).hexdigest()
        self.con.execute("INSERT OR IGNORE INTO files(hash,name,ext,data,pages,added) VALUES(?,?,?,?,?,?)",
                         (h, name, ext.lower(), data, int(pages), datetime.now().isoformat(timespec="seconds")))
        self.con.commit()
        return h

    def file_info(self, h):
        r = self.con.execute("SELECT hash,name,ext,pages,length(data) AS size,added FROM files WHERE hash=?",
                             (h,)).fetchone()
        return dict(r) if r else None

    def file_data(self, h):
        r = self.con.execute("SELECT data FROM files WHERE hash=?", (h,)).fetchone()
        return bytes(r[0]) if r else None

    def file_list(self):
        """보관함 전체 + 쓰는 이력 수 (최근 쓴 것 먼저)."""
        used, last = {}, {}
        for (fj, d) in self.con.execute("SELECT files, date FROM records WHERE files IS NOT NULL AND files<>''"):
            try:
                for it in json.loads(fj):
                    used[it["hash"]] = used.get(it["hash"], 0) + 1
                    last[it["hash"]] = max(last.get(it["hash"], ""), d or "")
            except (ValueError, KeyError, TypeError):
                pass
        out = [dict(r) for r in self.con.execute(
            "SELECT hash,name,ext,pages,length(data) AS size,added FROM files")]
        for f in out:
            f["used"] = used.get(f["hash"], 0)
            f["last"] = last.get(f["hash"], "")
        out.sort(key=lambda f: (f["last"] or f["added"] or ""), reverse=True)
        return out

    def rename_file(self, h, name):
        self.con.execute("UPDATE files SET name=? WHERE hash=?", (name, h))
        self.con.commit()

    def delete_file(self, h):
        """보관함에서 지우고, 그 파일을 쓰던 이력에서도 뺀다."""
        rows = self.con.execute("SELECT id, files FROM records WHERE files LIKE ?", ("%" + h + "%",)).fetchall()
        for (rid, fj) in rows:
            try:
                items = [it for it in json.loads(fj) if it.get("hash") != h]
            except ValueError:
                continue
            self.con.execute("UPDATE records SET files=? WHERE id=?", (json.dumps(items) if items else None, rid))
        self.con.execute("DELETE FROM files WHERE hash=?", (h,))
        self.con.commit()

    def files_of(self, rec: dict):
        """이력의 첨부파일 [{"hash","name","ext","pages","print"}] (보관함에서 지워진 것은 뺌)."""
        try:
            items = json.loads(rec.get("files") or "[]")
        except ValueError:
            return []
        out = []
        for it in items:
            f = self.file_info(it.get("hash"))
            if f:
                f["print"] = bool(it.get("print", True))
                out.append(f)
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

    def accounts(self):
        """작성이력에 쓴 계정과목 (많이 쓴 순)."""
        return [r[0] for r in self.con.execute(
            "SELECT account FROM records WHERE account<>'' GROUP BY account ORDER BY COUNT(*) DESC, MAX(date) DESC")
            if r[0] not in set(self.get("hidden_accounts", []) or [])]

    def hide_account(self, account):
        """계정과목 목록에서만 뺀다 (이력은 그대로). 그 계정과목으로 다시 저장하면 목록에 다시 나온다."""
        self.hide_name(account, "hidden_accounts")

    def names(self):
        hidden = set(self.get("hidden_names", []) or [])
        return [r[0] for r in self.con.execute(
            "SELECT name FROM records WHERE name<>'' GROUP BY name ORDER BY COUNT(*) DESC") if r[0] not in hidden]

    def hide_name(self, name, key="hidden_names"):
        """수령인 목록에서만 뺀다 (이력은 그대로). 그 이름으로 다시 저장하면 목록에 다시 나온다."""
        h = list(self.get(key, []) or [])
        if name and name not in h:
            self.set(key, h + [name])

    def _unhide(self, name, key="hidden_names"):
        h = list(self.get(key, []) or [])
        if name in h:
            h.remove(name); self.set(key, h)

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
