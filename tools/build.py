"""exe(폴더형) 빌드 → 설치파일 생성.

사용법 (프로젝트 폴더에서)
    python tools/build.py                 # app/version.py 의 버전으로 빌드
    python tools/build.py --version 1.3.1 # 버전을 지정 (version.py 도 그 값으로 바꾼다; GitHub 자동 빌드용)

결과: dist/SnW_Jichul_Setup_<버전>.exe
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
DIST = os.path.join(ROOT, "dist")
WORK = os.path.join(ROOT, "build")
VERSION_PY = os.path.join(APP, "version.py")


def read_version():
    m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', open(VERSION_PY, encoding="utf-8").read())
    return m.group(1)


def write_version(v):
    s = open(VERSION_PY, encoding="utf-8").read()
    s = re.sub(r'APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{v}"', s)
    open(VERSION_PY, "w", encoding="utf-8").write(s)


def find_iscc():
    cands = [shutil.which("ISCC"), shutil.which("iscc"),
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
             r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("Inno Setup(ISCC.exe)을 찾을 수 없습니다. https://jrsoftware.org/isdl.php 에서 설치하세요.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="빌드할 버전 (예: 1.3.1). 생략하면 app/version.py 값")
    a = ap.parse_args()
    if a.version:
        write_version(a.version.lstrip("vV"))
    ver = read_version()
    print(f"== 버전 {ver} 빌드 ==")

    out_app = os.path.join(DIST, "지출결의서")
    shutil.rmtree(out_app, ignore_errors=True)
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "지출결의서",
        "--icon", os.path.join(APP, "assets", "icon.ico"),
        "--add-data", f"{os.path.join(APP, 'assets')}{os.pathsep}assets",
        "--exclude-module", "PyQt5", "--exclude-module", "PyQt6", "--exclude-module", "tkinter",
        "--exclude-module", "numpy", "--exclude-module", "pandas", "--exclude-module", "matplotlib",
        "--distpath", DIST, "--workpath", WORK, "--specpath", WORK,
        os.path.join(APP, "main.py"),
    ], cwd=APP)

    iscc = find_iscc()
    subprocess.check_call([iscc, f"/DAppVersion={ver}", f"/DSourceDir={out_app}", f"/DOutputDir={DIST}",
                           os.path.join(ROOT, "installer", "setup.iss")])
    setup = os.path.join(DIST, f"SnW_Jichul_Setup_{ver}.exe")
    print(f"\n완료: {setup}  ({os.path.getsize(setup) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
