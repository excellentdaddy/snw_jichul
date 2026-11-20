"""공용 위젯·한글 메시지 상자."""
from PySide6.QtCore import Qt
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

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


# 카드 제목줄 색 (구글 색: 파랑·빨강·노랑·초록) — 제목줄 화살표 색. 배경·글자색은 theme.py 의 [tone=…]
TONES = {"blue": "#1a73e8", "red": "#d93025", "yellow": "#f9ab00", "green": "#1e8e3e"}


def _chevron(color):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14">'
           f'<path d="M4.5 2.2 L9.6 7 L4.5 11.8" fill="none" stroke="{color}" stroke-width="2.6" '
           f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    pm = QPixmap(); pm.loadFromData(QByteArray(svg.encode()), "SVG")
    return QIcon(pm).pixmap(12, 12)


def card(inner=None, title=None, subtitle=None, margins=(16, 12, 16, 14), fixed=False, extra=None, tone="blue"):
    """흰 카드 패널. title 이 있으면 색 있는 제목줄(오른쪽에 extra 위젯들)을 붙인다.
    tone: 제목줄 색 blue / red / yellow / green."""
    c = QWidget()
    c.setObjectName("Card")
    c.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    outer = QVBoxLayout(c)
    outer.setContentsMargins(1, 1, 1, 1)
    outer.setSpacing(0)
    if title:
        head = QWidget(); head.setObjectName("CardHeader"); head.setProperty("tone", tone)
        head.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hl = QHBoxLayout(head); hl.setContentsMargins(12, 2, 8, 2); hl.setSpacing(6)
        ic = QLabel(); ic.setPixmap(_chevron(TONES.get(tone, TONES["blue"])))
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
