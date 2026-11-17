"""공용 위젯·한글 메시지 상자."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from store import resource_path
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QSizePolicy, QVBoxLayout, QWidget


def _box(parent, icon, title, text, buttons):
    mb = QMessageBox(parent)
    mb.setIcon(icon)
    mb.setWindowTitle(title)
    mb.setText(text)
    out = {}
    for key, label, role in buttons:
        out[mb.addButton(label, role)] = key
    mb.exec()
    return out.get(mb.clickedButton())


def info(parent, title, text):
    _box(parent, QMessageBox.Icon.Information, title, text,
         [(True, "확인", QMessageBox.ButtonRole.AcceptRole)])


def warn(parent, title, text):
    _box(parent, QMessageBox.Icon.Warning, title, text,
         [(True, "확인", QMessageBox.ButtonRole.AcceptRole)])


def ask(parent, title, text, yes="예", no="아니요", danger=False) -> bool:
    return bool(_box(parent, QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question, title, text,
                     [(True, yes, QMessageBox.ButtonRole.YesRole), (False, no, QMessageBox.ButtonRole.NoRole)]))


def card(inner=None, title=None, subtitle=None, margins=(16, 12, 16, 14), fixed=False, extra=None):
    """흰 카드 패널. title 이 있으면 색 있는 제목줄(오른쪽에 extra 위젯들)을 붙인다."""
    c = QWidget()
    c.setObjectName("Card")
    c.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    outer = QVBoxLayout(c)
    outer.setContentsMargins(1, 1, 1, 1)
    outer.setSpacing(0)
    if title:
        head = QWidget(); head.setObjectName("CardHeader")
        head.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hl = QHBoxLayout(head); hl.setContentsMargins(12, 2, 8, 2); hl.setSpacing(6)
        ic = QLabel(); ic.setPixmap(QIcon(resource_path("assets", "chevron.svg")).pixmap(12, 12))
        t = QLabel(title); t.setObjectName("CardTitle")
        hl.addWidget(ic); hl.addWidget(t)
        hl.addStretch()
        for wdg in extra or []:
            hl.addWidget(wdg)
        head.setFixedHeight(28)
        outer.addWidget(head)
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(*margins)
    v.setSpacing(10)
    outer.addWidget(body, 1)
    if subtitle:
        s = QLabel(subtitle); s.setObjectName("Hint"); s.setWordWrap(True); v.addWidget(s)
    if inner is not None:
        v.addWidget(inner, 1)
    if fixed:
        c.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    return c
