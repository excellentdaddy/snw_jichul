"""프린터별 영점(출력 위치) 보정 창."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ui_common import card


def describe(c) -> str:
    """보정값을 짧은 글로: 예) ◀ 1.0  ▲ 0.5 mm"""
    dx, dy = c.get("dx", 0.0), c.get("dy", 0.0)
    parts = []
    if abs(dx) >= 0.05:
        parts.append(f"{'▶' if dx > 0 else '◀'} {abs(dx):.1f}")
    if abs(dy) >= 0.05:
        parts.append(f"{'▼' if dy > 0 else '▲'} {abs(dy):.1f}")
    return ("  ".join(parts) + " mm") if parts else "0점"


class ZeroDialog(QDialog):
    def __init__(self, main, key):
        super().__init__(main)
        self.main = main
        self.key = key
        self.c = dict(main.get_calib(key))
        self.step = 0.5
        self.setWindowTitle("영점 보정")
        self.setFixedWidth(520)
        v = QVBoxLayout(self); v.setContentsMargins(18, 18, 18, 18); v.setSpacing(14)

        head = QLabel(f"프린터: {key}"); head.setObjectName("SectionTitle"); head.setWordWrap(True)
        v.addWidget(head)
        tip = QLabel("이 프린터로 찍을 때 인쇄 내용 전체를 옮깁니다. 프린터마다 따로 저장됩니다.\n"
                     "예) 출력물이 양식보다 오른쪽으로 1mm 밀렸으면 ◀ 를 1mm 만큼 누르세요.")
        tip.setObjectName("Hint"); tip.setWordWrap(True)
        v.addWidget(tip)

        # 방향 패드
        pad = QWidget(); g = QGridLayout(pad); g.setSpacing(6); g.setContentsMargins(0, 0, 0, 0)
        def arrow(t, dx, dy, r, c):
            b = QPushButton(t); b.setObjectName("Pad"); b.setFixedSize(64, 48)
            b.setAutoRepeat(True); b.setAutoRepeatDelay(400); b.setAutoRepeatInterval(120)
            b.clicked.connect(lambda _=False: self.move(dx, dy))
            g.addWidget(b, r, c)
        arrow("▲", 0, -1, 0, 1); arrow("◀", -1, 0, 1, 0); arrow("▶", 1, 0, 1, 2); arrow("▼", 0, 1, 2, 1)
        self.lbl_now = QLabel(); self.lbl_now.setObjectName("PadValue"); self.lbl_now.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_now.setFixedSize(64, 48)
        g.addWidget(self.lbl_now, 1, 1)

        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(10)
        lb = QLabel("한 번에 이동"); lb.setObjectName("FieldLabel"); rv.addWidget(lb)
        hs = QHBoxLayout(); hs.setSpacing(6)
        self.steps = QButtonGroup(self)
        for i, s in enumerate((0.1, 0.5, 1.0)):
            b = QPushButton(f"{s:g}mm"); b.setObjectName("Chip"); b.setCheckable(True)
            b.setChecked(s == self.step)
            self.steps.addButton(b, i)
            b.clicked.connect(lambda _=False, ss=s: setattr(self, "step", ss))
            hs.addWidget(b)
        rv.addLayout(hs)
        gg = QGridLayout(); gg.setHorizontalSpacing(8); gg.setVerticalSpacing(6)
        self.sx = QDoubleSpinBox(); self.sy = QDoubleSpinBox()
        for sp in (self.sx, self.sy):
            sp.setRange(-20, 20); sp.setDecimals(1); sp.setSingleStep(0.1); sp.setSuffix(" mm")
            sp.valueChanged.connect(self._typed)
        l1 = QLabel("좌우 (+ 오른쪽)"); l1.setObjectName("FieldLabel")
        l2 = QLabel("상하 (+ 아래)"); l2.setObjectName("FieldLabel")
        gg.addWidget(l1, 0, 0); gg.addWidget(self.sx, 0, 1); gg.addWidget(l2, 1, 0); gg.addWidget(self.sy, 1, 1)
        rv.addLayout(gg)
        rv.addStretch()

        body = QWidget(); hb = QHBoxLayout(body); hb.setContentsMargins(0, 0, 0, 0); hb.setSpacing(20)
        hb.addWidget(pad); hb.addWidget(right, 1)
        v.addWidget(card(body))

        h = QHBoxLayout()
        bz = QPushButton("0점으로"); bz.clicked.connect(self.zero)
        bt = QPushButton("시험 인쇄"); bt.clicked.connect(self.test)
        bt.setToolTip("빈 A5 용지에 양식 선과 내용을 함께 인쇄 → 실제 용지와 겹쳐 비교")
        bo = QPushButton("확인"); bo.setObjectName("Primary"); bo.clicked.connect(self.accept)
        h.addWidget(bz); h.addWidget(bt); h.addStretch(); h.addWidget(bo)
        v.addLayout(h)
        self._sync()

    def _sync(self):
        for sp, k in ((self.sx, "dx"), (self.sy, "dy")):
            sp.blockSignals(True); sp.setValue(self.c.get(k, 0.0)); sp.blockSignals(False)
        self.lbl_now.setText(describe(self.c).replace(" mm", "").replace("  ", "\n"))
        self.main.set_calib(self.key, self.c)  # 바로 저장

    def move(self, dx, dy):
        self.c["dx"] = round(self.c.get("dx", 0.0) + dx * self.step, 2)
        self.c["dy"] = round(self.c.get("dy", 0.0) + dy * self.step, 2)
        self._sync()

    def _typed(self):
        self.c["dx"] = round(self.sx.value(), 2)
        self.c["dy"] = round(self.sy.value(), 2)
        self._sync()

    def zero(self):
        self.c["dx"] = self.c["dy"] = 0.0
        self._sync()

    def test(self):
        self.main.test_print()
