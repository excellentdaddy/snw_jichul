"""CHANGELOG.md 에서 해당 버전 부분만 뽑아 Release 설명으로 쓴다.

    python tools/notes.py 1.3.1 > dist/release_notes.md
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def section(version: str) -> str:
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(rf"^##\s*v?{re.escape(version)}\b.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else "변경 내용 없음"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(section(sys.argv[1].lstrip("vV")))
