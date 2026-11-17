"""업데이트 확인 · 설치.

업데이트 위치 (설정 > 업데이트)
  - GitHub (권장):  owner/repo  또는  https://github.com/owner/repo
      최신 Release 의 태그(v1.3.1)와 첨부된 설치파일(.exe)을 사용한다.
  - 공유폴더/웹주소: 아래 version.json 과 설치파일을 둔 곳

공유폴더 구성 (tools/publish.py 가 자동으로 만든다)
    version.json                      {"version": "1.3.0", "installer": "지출결의서_설치_1.3.0.exe",
                                       "date": "2026-11-17", "notes": "바뀐 내용"}
    지출결의서_설치_1.3.0.exe

업데이트 위치 예)  \\\\192.168.0.10\\공유\\지출결의서   또는   http://server/jichul/
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QThread, Signal

from version import APP_VERSION, parse

MANIFEST = "version.json"
TIMEOUT = 6  # 초


def is_url(src: str) -> bool:
    return src.lower().startswith(("http://", "https://"))


def github_repo(src: str):
    """'github:owner/repo', 'owner/repo', 'https://github.com/owner/repo' → 'owner/repo' (아니면 None)."""
    s = src.strip().rstrip("/")
    if s.lower().startswith("github:"):
        s = s[7:]
    elif "github.com/" in s.lower():
        s = s[s.lower().index("github.com/") + 11:]
    elif is_url(s) or "\\" in s or ":" in s:
        return None
    parts = [p for p in s.split("/") if p]
    if len(parts) >= 2 and not parts[1].lower().endswith(".json"):
        name = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
        return f"{parts[0]}/{name}"
    return None


def read_github(repo: str) -> dict:
    """GitHub 최신 Release → manifest. 태그 v1.3.0, 첨부파일 중 .exe 를 설치파일로 사용."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "JichulUpdater",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError("공개된 새 버전 정보가 없습니다.")
        raise
    exe = [a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".exe")]
    if not exe:
        raise RuntimeError("최신 Release 에 설치파일(.exe)이 첨부되어 있지 않습니다.")
    return {"version": rel.get("tag_name", "0").lstrip("vV"), "installer": exe[0]["name"],
            "url": exe[0]["browser_download_url"], "size": exe[0].get("size", 0),
            "notes": clean_notes(rel.get("body") or ""), "date": (rel.get("published_at") or "")[:10],
            "_base": "github"}


def clean_notes(text: str) -> str:
    """사용자에게 보여 줄 변경 내용: 주소·링크·저장소 정보가 든 줄은 뺀다."""
    out = []
    for line in (text or "").replace("\r", "").split("\n"):
        low = line.lower()
        if any(k in low for k in ("http", "github", "full changelog", "@", "what's changed", "new contributors")):
            continue
        line = line.strip().lstrip("#").strip()
        if line.startswith(("* ", "- ")):
            line = "· " + line[2:]
        out.append(line)
    s = "\n".join(out).strip()
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s


def read_history(src: str, limit=30) -> list:
    """서버의 버전 이력 [{version, date, notes}] (최신 순)."""
    repo = github_repo((src or "").strip())
    if not repo:
        m = read_manifest(src)
        return m.get("history") or [{"version": m["version"], "date": m.get("date", ""), "notes": m.get("notes", "")}]
    url = f"https://api.github.com/repos/{repo}/releases?per_page={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "JichulUpdater",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        rels = json.loads(r.read().decode("utf-8"))
    out = []
    for rel in rels:
        if rel.get("draft"):
            continue
        out.append({"version": rel.get("tag_name", "").lstrip("vV"),
                    "date": (rel.get("published_at") or "")[:10],
                    "notes": clean_notes(rel.get("body") or "")})
    out.sort(key=lambda h: parse(h["version"]), reverse=True)
    return out


class HistoryThread(QThread):
    done = Signal(object, str)  # (이력 목록 또는 None, 오류)

    def __init__(self, src, parent=None):
        super().__init__(parent)
        self.src = src

    def run(self):
        try:
            self.done.emit(read_history(self.src), "")
        except Exception as e:  # noqa
            self.done.emit(None, str(e))


def read_manifest(src: str) -> dict:
    src = (src or "").strip()
    if not src:
        raise RuntimeError("업데이트 위치가 설정되지 않았습니다.")
    repo = github_repo(src)
    if repo:
        return read_github(repo)
    if is_url(src):
        url = src if src.lower().endswith(".json") else urllib.parse.urljoin(src.rstrip("/") + "/", MANIFEST)
        req = urllib.request.Request(url, headers={"User-Agent": "JichulUpdater"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            m = json.loads(r.read().decode("utf-8-sig"))
        m["_base"] = url.rsplit("/", 1)[0] + "/"
    else:
        path = src if src.lower().endswith(".json") else os.path.join(src, MANIFEST)
        with open(path, encoding="utf-8-sig") as f:
            m = json.load(f)
        m["_base"] = os.path.dirname(path)
    if "version" not in m or "installer" not in m:
        raise RuntimeError("version.json 형식이 올바르지 않습니다.")
    return m


def is_newer(m: dict) -> bool:
    return parse(m["version"]) > parse(APP_VERSION)


def fetch_installer(m: dict, progress=None) -> str:
    """설치파일을 임시 폴더로 가져온다. progress(받은바이트, 전체바이트)"""
    name = os.path.basename(m["installer"])
    dst = os.path.join(tempfile.mkdtemp(prefix="jichul_upd_"), name)
    base = m["_base"]
    if base == "github" or is_url(base):
        url = m["url"] if base == "github" else urllib.parse.urljoin(base, urllib.parse.quote(m["installer"]))
        req = urllib.request.Request(url, headers={"User-Agent": "JichulUpdater"})
        with urllib.request.urlopen(req, timeout=TIMEOUT * 5) as r, open(dst, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if progress:
                    progress(got, total)
    else:
        src = os.path.join(base, m["installer"])
        total = os.path.getsize(src)
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            got = 0
            while True:
                chunk = fi.read(1024 * 1024)
                if not chunk:
                    break
                fo.write(chunk)
                got += len(chunk)
                if progress:
                    progress(got, total)
    return dst


def carry_portable_data():
    """휴대용(exe 옆 db)으로 쓰던 경우, 설치형이 쓸 문서 폴더로 데이터를 복사해 둔다 (없을 때만)."""
    from store import DB_NAME, base_dir, documents_dir
    from version import APP_DIR_NAME
    if not getattr(sys, "frozen", False):
        return None
    src = os.path.join(base_dir(), DB_NAME)
    dst_dir = os.path.join(documents_dir(), APP_DIR_NAME)
    dst = os.path.join(dst_dir, DB_NAME)
    if os.path.exists(src) and not os.path.exists(dst):
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        return dst
    return None


def run_installer(path: str):
    """조용히 설치 → 설치가 끝나면 설치 프로그램이 새 버전을 다시 실행한다."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     close_fds=True, creationflags=flags)


class CheckThread(QThread):
    """네트워크가 느려도 화면이 멈추지 않게 따로 확인."""
    done = Signal(object, str)  # (manifest 또는 None, 오류메시지)

    def __init__(self, src, parent=None):
        super().__init__(parent)
        self.src = src

    def run(self):
        try:
            self.done.emit(read_manifest(self.src), "")
        except Exception as e:  # noqa
            self.done.emit(None, str(e))
