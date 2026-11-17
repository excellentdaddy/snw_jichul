"""지출이 — 시작점."""
import os
import sys
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from store import Store, data_dir, resource_path
from version import APP_NAME


def excepthook(et, ev, tb):
    msg = "".join(traceback.format_exception(et, ev, tb))
    try:
        with open(os.path.join(data_dir(), "오류기록.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass
    from ui_common import warn
    warn(None, "오류", f"예상치 못한 오류가 발생했습니다.\n\n{ev}\n\n(자세한 내용은 오류기록.txt 에 저장됨)")


def set_app_id():
    """Windows 작업표시줄이 이 프로그램 고유 아이콘을 쓰도록 앱 ID 를 지정."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SnW.JichulGyeoluiseo.Writer")
        except Exception:
            pass


def main():
    sys.excepthook = excepthook
    set_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    import theme
    theme.apply(app)
    app.setWindowIcon(QIcon(resource_path("assets", "icon.ico")))  # 16~256px 포함
    store = Store()

    from ui_main import MainWindow
    from ui_common import ask
    w = MainWindow(store)
    w.place_window()
    w.show()

    if store.count() == 0:
        if ask(w, "처음 실행", "작성이력이 비어 있습니다.\n기존 엑셀(지출결의서 .xlsm 등)의 작성이력을 지금 불러올까요?"):
            w.do_import()
    w.start_update_check()  # 서버에 새 버전이 있는지 조용히 확인
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
