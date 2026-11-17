"""설정 > 좌표 설정: 칸별 위치·글자크기 + 프린터 전체 보정(이동·배율)."""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import render
from ui_common import ask, card, info

STEP = 0.5  # 방향 버튼 1회 이동량(mm)


class CoordPanel(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.store = main.store
        self.dirty = False

        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(12)
        leftw = QWidget(); leftw.setFixedWidth(520)
        left = QVBoxLayout(leftw); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(12)
        root.addWidget(leftw)

        # ---- 전체 보정 ----
        gw = QWidget(); gl = QGridLayout(gw); gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(10); gl.setVerticalSpacing(8)
        from ui_dialogs import fill_printers
        self.cb_pr = QComboBox()
        fill_printers(self.cb_pr)
        self.cb_pr.currentIndexChanged.connect(self._printer_pick)
        lb = QLabel("프린터"); lb.setObjectName("FieldLabel")
        gl.addWidget(lb, 0, 0); gl.addWidget(self.cb_pr, 0, 1, 1, 3)
        self.sp = {}
        for i, (k, label, lo, hi, step, suf) in enumerate((
            ("dx", "좌우 이동", -20, 20, 0.5, " mm"),
            ("dy", "상하 이동", -20, 20, 0.5, " mm"),
            ("sx", "가로 배율", 90, 110, 0.1, " %"),
            ("sy", "세로 배율", 90, 110, 0.1, " %"),
        )):
            s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(1); s.setSuffix(suf)
            s.valueChanged.connect(lambda v, kk=k: self._glob(kk, v))
            self.sp[k] = s
            lb = QLabel(label); lb.setObjectName("FieldLabel")
            gl.addWidget(lb, 1 + i // 2, (i % 2) * 2); gl.addWidget(s, 1 + i // 2, (i % 2) * 2 + 1)
        left.addWidget(card(gw, "프린터별 영점 · 배율",
                            "고른 프린터에만 적용됩니다. 전체가 한쪽으로 밀리면 '이동'(+는 오른쪽·아래), "
                            "아래로 갈수록 점점 어긋나면 '배율'을 조정하세요."))

        # ---- 칸별 보정 ----
        tw = QWidget(); tv = QVBoxLayout(tw); tv.setContentsMargins(0, 0, 0, 0); tv.setSpacing(8)
        self.tbl = QTableWidget(len(render.ITEMS), 4)
        self.tbl.setHorizontalHeaderLabels(["항목", "좌우(mm)", "상하(mm)", "글자(pt)"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setDefaultSectionSize(36)
        self.tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, w in ((1, 104), (2, 104), (3, 92)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            self.tbl.setColumnWidth(c, w)
        self.keys = list(render.ITEMS)
        self.cells = {}
        for r, k in enumerate(self.keys):
            it = QTableWidgetItem(render.ITEMS[k][0]); it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl.setItem(r, 0, it)
            sx = self._spin(-15, 15, 0.1, lambda v, kk=k: self._set(kk, "dx", v))
            sy = self._spin(-15, 15, 0.1, lambda v, kk=k: self._set(kk, "dy", v))
            sz = self._spin(5, 16, 0.5, lambda v, kk=k: self._set(kk, "size", v))
            self.tbl.setCellWidget(r, 1, sx); self.tbl.setCellWidget(r, 2, sy); self.tbl.setCellWidget(r, 3, sz)
            self.cells[k] = (sx, sy, sz)
        self.tbl.itemSelectionChanged.connect(self._refresh)
        tv.addWidget(self.tbl, 1)

        h = QHBoxLayout(); h.setSpacing(4)
        for txt, dx, dy, tip in (("◀", -STEP, 0, "왼쪽"), ("▲", 0, -STEP, "위"), ("▼", 0, STEP, "아래"), ("▶", STEP, 0, "오른쪽")):
            b = QPushButton(txt); b.setObjectName("Small"); b.setFixedWidth(44)
            b.setToolTip(f"선택한 항목을 {tip}으로 {STEP}mm 이동")
            b.clicked.connect(lambda _=False, a=dx, bb=dy: self._nudge(a, bb))
            h.addWidget(b)
        lbl = QLabel(f"{STEP}mm씩 이동"); lbl.setObjectName("Hint")
        h.addWidget(lbl); h.addStretch()
        b1 = QPushButton("선택 초기화"); b1.setObjectName("Small"); b1.clicked.connect(self._reset_sel)
        b2 = QPushButton("전체 초기화"); b2.setObjectName("Small"); b2.clicked.connect(self._reset_all)
        h.addWidget(b1); h.addWidget(b2)
        tv.addLayout(h)
        left.addWidget(card(tw, "칸별 위치 · 글자크기", "항목을 고르면 오른쪽 미리보기에 파란 테두리로 표시됩니다."), 1)

        h = QHBoxLayout()
        bt = QPushButton("시험 인쇄"); bt.clicked.connect(self._test)
        bt.setToolTip("빈 A5 용지에 양식 선과 내용을 함께 인쇄 → 실제 용지와 겹쳐 비교")
        self.b_revert = QPushButton("되돌리기"); self.b_revert.clicked.connect(self.load)
        self.b_save = QPushButton("저장"); self.b_save.setObjectName("Primary"); self.b_save.clicked.connect(self.save)
        h.addWidget(bt); h.addStretch(); h.addWidget(self.b_revert); h.addWidget(self.b_save)
        left.addLayout(h)

        # ---- 미리보기 ----
        from ui_main import Preview
        self.title = QLabel(); self.title.setObjectName("Hint")
        self.preview = Preview()
        root.addWidget(card(self.preview, "미리보기", margins=(10, 10, 10, 10), extra=[self.title]), 1)
        self.load()

    # ---------- 값 ----------
    def _spin(self, lo, hi, step, cb):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(1)
        s.valueChanged.connect(cb)
        return s

    def load(self):
        """현재 양식의 저장값을 화면에 불러온다 (양식 바꿀 때·되돌리기)."""
        self.lay = self.main.lay
        self.adj = copy.deepcopy(self.store.get(f"adjust_{self.lay.key}", {}) or {})
        self._loading = True
        cur = self.store.get("printer", "")
        self.cb_pr.blockSignals(True)
        self.cb_pr.setCurrentIndex(max(self.cb_pr.findData(cur), 0))
        self.cb_pr.blockSignals(False)
        self.pkey = self.main.calib_key(self.cb_pr.currentData())
        self.glob = self.main.get_calib(self.pkey)
        for k, s in self.sp.items():
            s.setValue(self.glob[k])
        for k, (sx, sy, sz) in self.cells.items():
            a = self.adj.get(k, {})
            sx.setValue(a.get("dx", 0.0)); sy.setValue(a.get("dy", 0.0)); sz.setValue(a.get("size", render.ITEMS[k][1]))
        self._loading = False
        self.title.setText(f"{self.lay.title}  ·  파란 테두리 = 선택한 항목")
        if self.tbl.currentRow() < 0:
            self.tbl.selectRow(1)
        self._mark(False)
        self._refresh()

    def _mark(self, dirty):
        self.dirty = dirty
        self.b_save.setEnabled(dirty); self.b_revert.setEnabled(dirty)
        self.b_save.setText("저장" if dirty else "저장됨")

    def current(self):
        r = self.tbl.currentRow()
        return self.keys[r] if 0 <= r < len(self.keys) else None

    def _set(self, k, field, v):
        if self._loading:
            return
        self.adj.setdefault(k, {})[field] = round(float(v), 2)
        self._mark(True); self._refresh()

    def _printer_pick(self, _):
        if self.dirty and not ask(self, "좌표 설정", "저장하지 않은 변경이 있습니다.\n프린터를 바꾸기 전에 저장할까요?"):
            pass
        elif self.dirty:
            self.save()
        self.pkey = self.main.calib_key(self.cb_pr.currentData())
        self.glob = self.main.get_calib(self.pkey)
        self._loading = True
        for k, s in self.sp.items():
            s.setValue(self.glob[k])
        self._loading = False
        self._mark(False)

    def _glob(self, k, v):
        if self._loading:
            return
        self.glob[k] = float(v)
        self._mark(True); self._refresh()

    def _nudge(self, dx, dy):
        k = self.current()
        if k:
            sx, sy, _ = self.cells[k]
            sx.setValue(sx.value() + dx); sy.setValue(sy.value() + dy)

    def _reset_sel(self):
        k = self.current()
        if k:
            sx, sy, sz = self.cells[k]
            sx.setValue(0); sy.setValue(0); sz.setValue(render.ITEMS[k][1])

    def _reset_all(self):
        if not ask(self, "전체 초기화", "모든 칸의 위치·글자크기를 기본값으로 되돌릴까요?\n"
                   "(프린터 전체 보정 값은 그대로 둡니다)"):
            return
        for k, (sx, sy, sz) in self.cells.items():
            sx.setValue(0); sy.setValue(0); sz.setValue(render.ITEMS[k][1])

    def _clean(self):
        out = {}
        for k, v in self.adj.items():
            base = render.ITEMS[k][1]
            vv = {f: x for f, x in v.items()
                  if not (f in ("dx", "dy") and abs(x) < 1e-6) and not (f == "size" and abs(x - base) < 1e-6)}
            if vv:
                out[k] = vv
        return out

    def _refresh(self):
        self.preview.set(self.main.sample_doc(), self.lay, self._clean(), self.current())

    def save(self):
        self.store.set(f"adjust_{self.lay.key}", self._clean())
        self.main.set_calib(self.pkey, self.glob)
        self._mark(False)
        self.main.refresh_preview()
        self.main.toast("좌표 설정을 저장했습니다.")

    def _test(self):
        if self.dirty:
            self.save()
        self.main.test_print()

    def confirm_leave(self) -> bool:
        if not self.dirty:
            return True
        if ask(self, "좌표 설정", "저장하지 않은 좌표 변경이 있습니다. 저장할까요?"):
            self.save()
        else:
            self.load()
        return True
