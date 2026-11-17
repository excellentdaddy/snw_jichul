"""버전 정보. 새로 배포할 때 APP_VERSION 만 올리면 된다 (tools/publish.py 가 읽음)."""
APP_VERSION = "1.3.5"
APP_NAME = "지출이"
APP_DIR_NAME = "S&W 지출결의서"          # 문서 폴더 아래 데이터 폴더 이름
APP_EXE = "지출결의서.exe"
APP_ID = "{6E3A4F7C-2B9D-4C1E-9A57-5D0F3B8C21A4}"  # 설치 프로그램 고유 ID (바꾸지 말 것)
# 기본 업데이트 위치: GitHub 'owner/repo' (설정 > 업데이트에서 바꿀 수 있음)
UPDATE_SOURCE = "excellentdaddy/snw_jichul"


def parse(v: str):
    """'1.3.0' → (1, 3, 0). 비교용."""
    out = []
    for p in str(v).strip().split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        out.append(int(num) if num else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)
