"""밝은 구글(Material) 느낌 테마 + Pretendard 글꼴 + 한글 대화상자."""
import os

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

PRIMARY = "#1a73e8"
PRIMARY_DARK = "#1765cc"
PRIMARY_LIGHT = "#e8f0fe"
DANGER = "#d93025"
TEXT = "#202124"
TEXT2 = "#5f6368"
BORDER = "#dadce0"
BG = "#f1f3f4"
SURFACE = "#ffffff"
UI_FONT = "Pretendard"

QSS = """
* { font-family: 'UI_FONT', '맑은 고딕'; font-size: 10pt; color: TEXT; }
QMainWindow, QDialog, QStackedWidget#Pages { background: BG; }
QStackedWidget#HeadActions { background: transparent; }
QWidget#Card { background: SURFACE; border: 1px solid BORDER; border-radius: 10px; }
QWidget#CardHeader {
    background: #e8f0fe; border: none; border-bottom: 1px solid #d2e3fc;
    border-top-left-radius: 9px; border-top-right-radius: 9px;
}
QLabel#CardTitle { font-size: 10pt; font-weight: 700; color: #174ea6; }
QWidget#CardHeader QComboBox { padding: 0px 6px; min-height: 16px; font-size: 9pt; border-radius: 4px; }
QWidget#CardHeader QComboBox:focus { padding: 0px 5px; }
QWidget#CardHeader QPushButton { padding: 0px 10px; min-height: 18px; font-size: 9pt; border-radius: 10px; }
QWidget#CardHeader QLabel#Hint { color: #4a6fa5; }
QWidget#CardHeader[tone="red"] { background: #fce8e6; border-bottom: 1px solid #fad2cf; }
QWidget#CardHeader[tone="red"] QLabel#CardTitle { color: #a50e0e; }
QWidget#CardHeader[tone="red"] QLabel#Hint { color: #b3625a; }
QWidget#CardHeader[tone="yellow"] { background: #fef7e0; border-bottom: 1px solid #feefc3; }
QWidget#CardHeader[tone="yellow"] QLabel#CardTitle { color: #8d5a00; }
QWidget#CardHeader[tone="yellow"] QLabel#Hint { color: #9a7322; }
QWidget#CardHeader[tone="green"] { background: #e6f4ea; border-bottom: 1px solid #ceead6; }
QWidget#CardHeader[tone="green"] QLabel#CardTitle { color: #0d652d; }
QWidget#CardHeader[tone="green"] QLabel#Hint { color: #3d7a52; }
QLabel { background: transparent; }
QLabel#SectionTitle { font-size: 11.5pt; font-weight: 700; color: TEXT; }
QLabel#FieldLabel { color: TEXT2; font-weight: 600; min-width: 52px; }
QLabel#Hint { color: TEXT2; font-size: 9pt; }
QLabel#HintError { color: DANGER; font-size: 9pt; font-weight: 600; }
QLabel#Kor { color: PRIMARY; font-size: 9.5pt; font-weight: 600; }
QLabel#ColHead { color: TEXT; font-weight: 700; background: BG; border-radius: 6px; padding: 5px 2px; }
QLabel#Summary { color: TEXT; font-weight: 600; }
QLabel#BarLabel { color: TEXT2; font-weight: 600; padding-left: 6px; }

/* ---------- 상단 바 ---------- */
QWidget#HeaderBar { background: SURFACE; border-bottom: 1px solid BORDER; min-height: 60px; max-height: 60px; }
QLabel#AppTitle { font-size: 15pt; font-weight: 700; color: TEXT; }
QPushButton#NavTab {
    background: transparent; border: none; border-radius: 0; color: TEXT2;
    font-size: 11pt; font-weight: 600; padding: 18px 18px 15px 18px; border-bottom: 3px solid transparent;
}
QPushButton#NavTab:hover { color: TEXT; background: #f8f9fa; }
QPushButton#NavTab:checked { color: PRIMARY; border-bottom: 3px solid PRIMARY; }
QPushButton#HeadBtn {
    background: SURFACE; border: 1px solid BORDER; border-radius: 15px; padding: 6px 16px;
    color: TEXT; font-weight: 600;
}
QPushButton#HeadBtn:hover { background: #f8f9fa; }
QPushButton#HeadBtn::menu-indicator { image: none; width: 0; }
QPushButton#HeadPrimary {
    background: PRIMARY; border: none; border-radius: 15px; padding: 7px 26px; color: white;
    font-weight: 700; font-size: 10.5pt;
}
QPushButton#HeadPrimary:hover { background: PRIMARY_DARK; }

/* ---------- 입력 ---------- */
QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background: SURFACE; border: 1px solid BORDER; border-radius: 6px; padding: 5px 8px; min-height: 20px;
    selection-background-color: #c6dafc; selection-color: TEXT;
}
QPlainTextEdit { padding: 6px 8px; font-size: 10.5pt; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid PRIMARY; padding: 4px 7px; }
QPlainTextEdit:focus { padding: 5px 7px; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled { background: #f8f9fa; color: #bdc1c6; }
QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 24px; }
QComboBox::down-arrow, QDateEdit::down-arrow { image: url(DOWN_ICON); width: 10px; height: 6px; }
QComboBox QAbstractItemView {
    background: SURFACE; border: 1px solid BORDER; outline: 0; padding: 4px;
    selection-background-color: PRIMARY_LIGHT; selection-color: TEXT;
}
QSpinBox, QDoubleSpinBox { padding-right: 22px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; background: transparent;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; background: transparent;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: BG; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(UP_ICON); width: 9px; height: 5px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(DOWN_ICON); width: 9px; height: 5px; }

/* ---------- 버튼 ---------- */
QPushButton {
    background: SURFACE; border: 1px solid BORDER; border-radius: 15px; padding: 6px 18px;
    color: PRIMARY; font-weight: 600;
}
QPushButton:hover { background: #f6f9fe; border-color: #c6dafc; }
QPushButton:pressed { background: PRIMARY_LIGHT; }
QPushButton:disabled { color: #bdc1c6; background: #f8f9fa; border-color: #e8eaed; }
QPushButton#Primary { background: PRIMARY; color: white; border: none; padding: 8px 22px; }
QPushButton#Primary:hover { background: PRIMARY_DARK; }
QPushButton#Primary:disabled { background: #c6dafc; color: white; }
QPushButton#Danger { color: DANGER; }
QPushButton#Danger:hover { background: #fce8e6; border-color: #f6aea9; }
QPushButton#Small { padding: 4px 12px; border-radius: 12px; font-weight: 600; }
QPushButton#SmallDanger { padding: 4px 12px; border-radius: 12px; font-weight: 600; color: DANGER; }
QPushButton#SmallDanger:hover { background: #fce8e6; border-color: #f6aea9; }
QPushButton#Pad { border-radius: 10px; font-size: 14pt; color: PRIMARY; padding: 0; }
QPushButton#Pad:pressed { background: PRIMARY; color: white; }
QLabel#PadValue { background: PRIMARY_LIGHT; border-radius: 10px; color: PRIMARY; font-weight: 700; font-size: 9pt; }
QPushButton#Chip { padding: 4px 12px; border-radius: 12px; color: TEXT2; font-weight: 600; }
QPushButton#Chip:checked { background: PRIMARY_LIGHT; color: PRIMARY; border-color: #a8c7fa; }
QPushButton#Zero { padding: 5px 12px; border-radius: 13px; color: TEXT; font-weight: 600; }
QPushButton#Zero:hover { border-color: PRIMARY; color: PRIMARY; }

/* ---------- 표 ---------- */
QTableWidget {
    background: SURFACE; alternate-background-color: #fafbfc; border: 1px solid #e8eaed; border-radius: 8px;
    selection-background-color: PRIMARY_LIGHT; selection-color: TEXT; outline: 0;
}
QTableWidget::item { padding: 0 6px; border-bottom: 1px solid #f1f3f4; }
QHeaderView::section {
    background: #f8f9fa; border: none; border-bottom: 1px solid BORDER;
    padding: 7px 6px; font-weight: 700; color: TEXT2;
}
QTableCornerButton::section { background: #f8f9fa; border: none; }

/* ---------- 설정 왼쪽 메뉴 ---------- */
QListWidget#SideNav { background: transparent; border: none; outline: 0; }
QListWidget#SideNav::item {
    padding: 11px 16px; margin: 2px 0; border-radius: 20px; color: TEXT; font-weight: 600;
}
QListWidget#SideNav::item:hover { background: #e8eaed; }
QListWidget#SideNav::item:selected { background: #d3e3fd; color: #041e49; }

/* ---------- 기타 ---------- */
QCheckBox { spacing: 6px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #80868b; border-radius: 3px; background: white; }
QCheckBox::indicator:hover { border-color: PRIMARY; }
QCheckBox::indicator:checked { background: PRIMARY; border-color: PRIMARY; image: url(CHECK_ICON); }
QCheckBox::indicator:disabled { border-color: #dadce0; background: #f1f3f4; }
QCheckBox::indicator:checked:disabled { background: #a8c7fa; border-color: #a8c7fa; }
QCheckBox:disabled { color: #9aa0a6; }

QMenu { background: SURFACE; border: 1px solid BORDER; border-radius: 8px; padding: 6px 0; }
QMenu::item { padding: 8px 28px 8px 18px; }
QMenu::item:selected { background: PRIMARY_LIGHT; }
QMenu::separator { height: 1px; background: BORDER; margin: 4px 0; }
QStatusBar { background: SURFACE; border-top: 1px solid BORDER; color: TEXT2; min-height: 26px; }
QStatusBar QLabel { color: TEXT2; padding: 0 10px; font-size: 9pt; }
QStatusBar::item { border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c4c7c5; border-radius: 4px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c4c7c5; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QWidget#PrintCard { background: SURFACE; border: 1px solid BORDER; border-radius: 12px; }
QLabel#PrintTitle { font-size: 12pt; font-weight: 700; color: TEXT; }
QLabel#PrintDone { font-size: 12pt; font-weight: 700; color: #188038; }
QProgressBar { background: #e8eaed; border: none; border-radius: 4px; }
QProgressBar::chunk { background: PRIMARY; border-radius: 4px; }
QToolTip { background: #3c4043; color: white; border: none; padding: 8px; border-radius: 4px; }
QMessageBox QLabel { font-size: 10pt; }
QMessageBox QPushButton { min-width: 72px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: SURFACE; }
QCalendarWidget QToolButton { color: TEXT; background: transparent; font-weight: 700; padding: 4px 8px; }
QCalendarWidget QAbstractItemView { selection-background-color: PRIMARY; selection-color: white; }
"""


def _load_fonts():
    from store import resource_path
    d = resource_path("assets", "fonts")
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(d, f))
    return UI_FONT in QFontDatabase.families()


def _load_korean(app):
    """Qt 기본 대화상자(파일 선택·인쇄·달력·확인 버튼)를 한글로."""
    QLocale.setDefault(QLocale(QLocale.Language.Korean, QLocale.Country.SouthKorea))
    app._translators = []
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in ("qtbase_ko", "qt_ko"):
        t = QTranslator(app)
        if t.load(name, path):
            app.installTranslator(t)
            app._translators.append(t)
    return len(app._translators)


def _no_wheel_spin(app):
    """마우스 휠로 숫자·날짜 칸(스핀 단추) 값이 바뀌지 않게 한다. 휠은 바깥(목록·화면 스크롤)으로 넘긴다."""
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QAbstractSpinBox, QApplication

    class _Filter(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Type.Wheel and isinstance(obj, QAbstractSpinBox):
                par = obj.parentWidget()
                if par is not None:
                    QApplication.sendEvent(par, ev)
                return True
            return False

    app._no_wheel = _Filter(app)
    app.installEventFilter(app._no_wheel)


def apply(app):
    """Windows 다크 모드여도 항상 밝게 보이도록 팔레트를 고정한다."""
    from store import resource_path
    _no_wheel_spin(app)
    app.setStyle("Fusion")
    has_font = _load_fonts()
    _load_korean(app)
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG, QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: SURFACE, QPalette.ColorRole.AlternateBase: "#fafbfc",
        QPalette.ColorRole.Text: TEXT, QPalette.ColorRole.Button: SURFACE,
        QPalette.ColorRole.ButtonText: TEXT, QPalette.ColorRole.Highlight: PRIMARY,
        QPalette.ColorRole.HighlightedText: "#ffffff", QPalette.ColorRole.ToolTipBase: "#3c4043",
        QPalette.ColorRole.ToolTipText: "#ffffff", QPalette.ColorRole.PlaceholderText: "#9aa0a6",
        QPalette.ColorRole.Link: PRIMARY, QPalette.ColorRole.Light: "#ffffff",
        QPalette.ColorRole.Mid: BORDER, QPalette.ColorRole.Dark: "#bdc1c6",
    }
    for r, c in roles.items():
        pal.setColor(r, QColor(c))
    for r in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, r, QColor("#9aa0a6"))
    app.setPalette(pal)
    family = UI_FONT if has_font else "맑은 고딕"
    f = QFont(family, 10)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(f)
    a = lambda n: resource_path("assets", n).replace("\\", "/")
    qss = QSS
    for k, v in (("UI_FONT", family), ("PRIMARY_LIGHT", PRIMARY_LIGHT), ("PRIMARY_DARK", PRIMARY_DARK),
                 ("PRIMARY", PRIMARY), ("DANGER", DANGER), ("TEXT2", TEXT2), ("TEXT", TEXT),
                 ("BORDER", BORDER), ("SURFACE", SURFACE), ("BG", BG),
                 ("CHECK_ICON", a("check.svg")), ("UP_ICON", a("up.svg")), ("DOWN_ICON", a("down.svg"))):
        qss = qss.replace(k, v)
    app.setStyleSheet(qss)
    try:  # Qt 6.5+: 다크 모드 무시
        from PySide6.QtCore import Qt
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass
