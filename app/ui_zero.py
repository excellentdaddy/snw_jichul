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
    txt = ("  ".join(parts) + " mm") if parts else ""
    k = c.get("sx", 100.0)
    if abs(k - 100.0) >= 0.05:
        txt = (txt + "  " if txt else "") + f"{k:g}%"
    return txt or "0점"


def describe_pos(c) -> str:
    """위치만 (방향 패드 가운데 표시용)."""
    return describe({"dx": c.get("dx", 0.0), "dy": c.get("dy", 0.0)})


TIP = ("이 프린터로 찍을 때 인쇄 내용 전체를 옮깁니다. 프린터마다 따로 저장됩니다.\n"
       "예) 출력물이 양식보다 오른쪽으로 1mm 밀렸으면 ◀ 를 1mm 만큼 누르세요.\n"
       "배율: 글자·칸이 양식보다 작게(축소) 찍히면 100% 보다 크게, 크게 찍히면 작게 하세요.")


class ZeroPad(QWidget):
    """방향 패드 + 이동량 칩 + 숫자 칸. 값이 바뀌면 바로 main.set_calib(key) 로 저장한다.
    영점조정 창과 설정 > 좌표 설정에서 같이 쓴다."""

    def __init__(self, main, key=None, on_change=None):
        super().__init__()
        self.main = main
        self.on_change = on_change
        self.step = 0.5
        g = QGridLayout(); g.setSpacing(6); g.setContentsMargins(0, 0, 0, 0)

        def arrow(t, dx, dy, r, c):
            b = QPushButton(t); b.setObjectName("Pad"); b.setFixedSize(64, 48)
            b.setAutoRepeat(True); b.setAutoRepeatDelay(400); b.setAutoRepeatInterval(120)
            b.clicked.connect(lambda _=False: self.nudge(dx, dy))
            g.addWidget(b, r, c)
        arrow("▲", 0, -1, 0, 1); arrow("◀", -1, 0, 1, 0); arrow("▶", 1, 0, 1, 2); arrow("▼", 0, 1, 2, 1)
        self.lbl_now = QLabel(); self.lbl_now.setObjectName("PadValue"); self.lbl_now.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_now.setFixedSize(64, 48)
        g.addWidget(self.lbl_now, 1, 1)
        pad = QWidget(); pad.setLayout(g)

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
        hs.addStretch()
        rv.addLayout(hs)
        gg = QGridLayout(); gg.setHorizontalSpacing(8); gg.setVerticalSpacing(6)
        self.sx = QDoubleSpinBox(); self.sy = QDoubleSpinBox()
        for sp in (self.sx, self.sy):
            sp.setRange(-20, 20); sp.setDecimals(1); sp.setSingleStep(0.1); sp.setSuffix(" mm")
            sp.valueChanged.connect(self._typed)
        l1 = QLabel("좌우 (+ 오른쪽)"); l1.setObjectName("FieldLabel")
        l2 = QLabel("상하 (+ 아래)"); l2.setObjectName("FieldLabel")
        gg.addWidget(l1, 0, 0); gg.addWidget(self.sx, 0, 1); gg.addWidget(l2, 1, 0); gg.addWidget(self.sy, 1, 1)
        # 배율: 인쇄 내용 전체 크기 (가로·세로 같이, 왼쪽 위 기준)
        self.sk = QDoubleSpinBox()
        self.sk.setRange(50, 150); self.sk.setDecimals(1); self.sk.setSingleStep(0.5); self.sk.setSuffix(" %")
        self.sk.setToolTip("인쇄 내용 전체 크기. 축소돼 찍히면 키우고, 크게 찍히면 줄이세요. (기본 100%)")
        self.sk.valueChanged.connect(self._typed)
        l3 = QLabel("배율 (기본 100)"); l3.setObjectName("FieldLabel")
        gg.addWidget(l3, 2, 0); gg.addWidget(self.sk, 2, 1)
        rv.addLayout(gg)
        rv.addStretch()

        hb = QHBoxLayout(self); hb.setContentsMargins(0, 0, 0, 0); hb.setSpacing(20)
        hb.addWidget(pad); hb.addWidget(right, 1)
        self.set_key(key or main.calib_key())

    def set_key(self, key):
        """다른 프린터로 바꾸면 그 프린터의 저장값을 불러온다."""
        self.key = key
        self.c = dict(self.main.get_calib(key))
        self._sync(save=False)

    def _sync(self, save=True):
        for sp, k, d in ((self.sx, "dx", 0.0), (self.sy, "dy", 0.0), (self.sk, "sx", 100.0)):
            sp.blockSignals(True); sp.setValue(self.c.get(k, d)); sp.blockSignals(False)
        self.lbl_now.setText(describe_pos(self.c).replace(" mm", "").replace("  ", "\n"))
        if save:
            self.main.set_calib(self.key, self.c)  # 바로 저장
            if self.on_change:
                self.on_change()

    def nudge(self, dx, dy):
        self.c["dx"] = round(self.c.get("dx", 0.0) + dx * self.step, 2)
        self.c["dy"] = round(self.c.get("dy", 0.0) + dy * self.step, 2)
        self._sync()

    def _typed(self):
        self.c["dx"] = round(self.sx.value(), 2)
        self.c["dy"] = round(self.sy.value(), 2)
        self.c["sx"] = self.c["sy"] = round(self.sk.value(), 2)
        self._sync()

    def zero(self):
        self.c["dx"] = self.c["dy"] = 0.0
        self.c["sx"] = self.c["sy"] = 100.0
        self._sync()


class ZeroDialog(QDialog):
    def __init__(self, main, key):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("영점 보정")
        self.setFixedWidth(520)
        v = QVBoxLayout(self); v.setContentsMargins(18, 18, 18, 18); v.setSpacing(14)

        head = QLabel(f"프린터: {key}"); head.setObjectName("SectionTitle"); head.setWordWrap(True)
        v.addWidget(head)
        tip = QLabel(TIP); tip.setObjectName("Hint"); tip.setWordWrap(True)
        v.addWidget(tip)
        self.key = key
        self.orig = dict(main.get_calib(key))  # [취소]·Esc·창 닫기 → 이 값으로 되돌림
        self.pad = ZeroPad(main, key)
        v.addWidget(card(self.pad))

        h = QHBoxLayout()
        bz = QPushButton("0점으로"); bz.clicked.connect(self.pad.zero)
        bt = QPushButton("시험 인쇄"); bt.clicked.connect(main.test_print)
        bt.setToolTip("빈 A5 용지에 양식 선과 내용을 함께 인쇄 → 실제 용지와 겹쳐 비교")
        bc = QPushButton("취소"); bc.clicked.connect(self.reject)
        bc.setToolTip("바꾼 값을 버리고 창을 열기 전 값으로 되돌립니다 (Esc)")
        bo = QPushButton("확인"); bo.setObjectName("Primary"); bo.clicked.connect(self.accept)
        bo.setDefault(True)
        h.addWidget(bz); h.addWidget(bt); h.addStretch(); h.addWidget(bc); h.addWidget(bo)
        v.addLayout(h)

    def reject(self):
        """[취소]·Esc·창 닫기(X): 바꾼 값은 버린다 (시험 인쇄는 바꾼 값으로 미리 찍어 볼 수 있음)."""
        self.main.set_calib(self.key, self.orig)
        super().reject()
