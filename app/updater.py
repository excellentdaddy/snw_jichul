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
TIMEOUT = 15  # 초 (느린 회사망 대비)
UA = {"User-Agent": "JichulUpdater"}


# ---------------------------------------------------------------- 네트워크
# PC마다 막히는 이유가 달라서 두 길로 시도한다.
#  1) 파이썬 urllib: Windows 인증서 + 내장 인증서 묶음(certifi) 을 함께 써서
#     'Windows 에 루트 인증서가 아직 안 깔린 PC' 에서도 HTTPS 가 되게 한다.
#  2) 그래도 안 되면 PowerShell(Windows 자체 인터넷 기능): 회사 프록시·보안 프로그램 설정을 그대로 따른다.
def _ssl_context():
    import ssl
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:  # noqa
        pass
    return ctx


def _ps_quote(x: str) -> str:
    return "'" + x.replace("'", "''") + "'"


def _powershell_get(url: str, dst: str, headers=None, timeout=TIMEOUT):
    """Windows PowerShell 로 내려받는다 (프록시·인증서를 브라우저처럼 처리)."""
    h = "; ".join(f"{_ps_quote(k)}={_ps_quote(v)}" for k, v in (headers or {}).items())
    script = (
        "$ProgressPreference='SilentlyContinue'; "
        "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
        "[Net.WebRequest]::DefaultWebProxy.Credentials=[Net.CredentialCache]::DefaultNetworkCredentials; "
        f"Invoke-WebRequest -UseBasicParsing -Uri {_ps_quote(url)} -OutFile {_ps_quote(dst)} "
        f"-Headers @{{{h}}} -TimeoutSec {int(timeout)}"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-Command", script], capture_output=True, text=True, timeout=timeout + 30,
                       creationflags=0x08000000)  # CREATE_NO_WINDOW
    if r.returncode != 0 or not os.path.exists(dst):
        msg = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError(msg[0] if msg else "PowerShell 다운로드 실패")


def http_get(url: str, headers=None, timeout=TIMEOUT) -> bytes:
    """작은 응답(JSON·글)을 받는다. 404 같은 HTTP 오류는 그대로 올린다."""
    hd = dict(UA, **(headers or {}))
    try:
        req = urllib.request.Request(url, headers=hd)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            return r.read()
    except urllib.error.HTTPError:
        raise
    except Exception as first:  # noqa  인증서·프록시·시간 초과 → Windows 방식으로 다시
        fd, tmp = tempfile.mkstemp(prefix="jichul_get_"); os.close(fd); os.remove(tmp)
        try:
            _powershell_get(url, tmp, hd, timeout)
            with open(tmp, "rb") as f:
                return f.read()
        except Exception as second:  # noqa
            raise RuntimeError(explain(first) + f"\n(다른 방법도 실패: {second})")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def explain(e) -> str:
    """사용자에게 보여 줄 실패 이유 (짧게)."""
    if isinstance(e, RuntimeError):  # 이미 사용자용 문구
        return str(e)
    t = f"{type(e).__name__}: {e}"
    low = t.lower()
    if isinstance(e, urllib.error.HTTPError) and e.code in (403, 429):
        return "업데이트 서버가 잠시 요청을 막았습니다 (같은 회사 인터넷에서 확인이 몰림). 잠시 뒤 다시 시도하세요."
    if "certificate" in low or "ssl" in low:
        return "보안 인증서 확인에 실패했습니다 (회사 보안 프로그램·인증서 문제)."
    if "timed out" in low or "timeout" in low:
        return "응답이 너무 늦습니다 (인터넷이 느리거나 막혀 있음)."
    if "getaddrinfo" in low or "name or service" in low or "11001" in low:
        return "서버 주소를 찾지 못했습니다 (인터넷 연결 끊김)."
    if "proxy" in low or "407" in low:
        return "회사 프록시(인터넷 관문) 설정 때문에 연결하지 못했습니다."
    return t[:200]


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


API = {"Accept": "application/vnd.github+json"}


def read_github(repo: str) -> dict:
    """GitHub 최신 Release → manifest. 태그 v1.3.0, 첨부파일 중 .exe 를 설치파일로 사용.
    API 가 막히면(같은 인터넷에서 시간당 60회 한도 등) 저장소의 원본 파일로 대신 확인한다."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        rel = json.loads(http_get(url, API).decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError("공개된 새 버전 정보가 없습니다.")
        return read_github_raw(repo, e)
    except Exception as e:  # noqa
        return read_github_raw(repo, e)
    exe = [a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".exe")]
    if not exe:
        raise RuntimeError("최신 Release 에 설치파일(.exe)이 첨부되어 있지 않습니다.")
    return {"version": rel.get("tag_name", "0").lstrip("vV"), "installer": exe[0]["name"],
            "url": exe[0]["browser_download_url"], "size": exe[0].get("size", 0),
            "notes": clean_notes(rel.get("body") or ""), "date": (rel.get("published_at") or "")[:10],
            "_base": "github"}


RAW = "https://raw.githubusercontent.com/{repo}/main/{path}"


def _raw(repo, path) -> str:
    return http_get(RAW.format(repo=repo, path=path)).decode("utf-8-sig")


def changelog_entries(text: str) -> list:
    """CHANGELOG.md 의 '## 버전' 묶음 → [{version, date, notes}]."""
    out, cur = [], None
    for line in text.replace("\r", "").split("\n"):
        if line.startswith("## "):
            cur = {"version": line[3:].strip().lstrip("vV"), "date": "", "lines": []}
            out.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    return [{"version": c["version"], "date": c["date"], "notes": clean_notes("\n".join(c["lines"]))} for c in out]


def read_github_raw(repo: str, why=None) -> dict:
    """API 없이 확인: app/version.py 의 버전 + 정해진 이름의 설치파일 주소."""
    try:
        import re
        src = _raw(repo, "app/version.py")
        ver = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src).group(1)
    except Exception as e:  # noqa
        raise RuntimeError(explain(why or e))
    name = f"SnW_Jichul_Setup_{ver}.exe"
    notes = ""
    try:
        for c in changelog_entries(_raw(repo, "CHANGELOG.md")):
            if c["version"] == ver:
                notes = c["notes"]
                break
    except Exception:  # noqa
        pass
    return {"version": ver, "installer": name,
            "url": f"https://github.com/{repo}/releases/download/v{ver}/{name}",
            "size": 0, "notes": notes, "date": "", "_base": "github"}


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
    try:
        rels = json.loads(http_get(url, API).decode("utf-8"))
    except Exception:  # noqa  API 가 막히면 CHANGELOG.md 로
        return changelog_entries(_raw(repo, "CHANGELOG.md"))[:limit]
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
            self.done.emit(None, str(e) if isinstance(e, RuntimeError) else explain(e))


def read_manifest(src: str) -> dict:
    src = (src or "").strip()
    if not src:
        raise RuntimeError("업데이트 위치가 설정되지 않았습니다.")
    repo = github_repo(src)
    if repo:
        return read_github(repo)
    if is_url(src):
        url = src if src.lower().endswith(".json") else urllib.parse.urljoin(src.rstrip("/") + "/", MANIFEST)
        m = json.loads(http_get(url).decode("utf-8-sig"))
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
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=TIMEOUT * 4, context=_ssl_context()) as r, open(dst, "wb") as f:
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
        except urllib.error.HTTPError:
            raise
        except Exception:  # noqa  인증서·프록시 문제면 Windows 방식으로 (진행률 없이)
            if progress:
                progress(1, 100)
            _powershell_get(url, dst, UA, timeout=600)
            if progress:
                progress(100, 100)
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
            self.done.emit(None, str(e) if isinstance(e, RuntimeError) else explain(e))
