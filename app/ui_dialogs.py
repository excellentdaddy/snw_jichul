"""설정 > 프린터·기본값 / 데이터 관리, 엑셀 가져오기 대화상자."""
import os
import shutil
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import importer
from store import FIELD_LABELS, FIELDS
from ui_common import card, info, warn


def fill_printers(cb):
    """프린터 목록 채우기 (첫 항목 = Windows 기본 프린터)."""
    cb.blockSignals(True)
    cb.clear()
    default = QPrinterInfo.defaultPrinterName()
    cb.addItem(f"Windows 기본 ({default})" if default else "Windows 기본 프린터", "")
    for n in sorted(QPrinterInfo.availablePrinterNames()):
        cb.addItem(n, n)
    cb.blockSignals(False)


class SettingsPanel(QWidget):
    """프린터·기본값."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.store = main.store
        self.setMaximumWidth(860)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)

        w1 = QWidget(); f1 = QFormLayout(w1); f1.setContentsMargins(0, 0, 0, 0); f1.setSpacing(10)
        self.cb_printer = QComboBox(); self.cb_printer.setMinimumWidth(360); self.cb_printer.setMaximumWidth(520)
        self.chk_dialog = QCheckBox("인쇄할 때마다 인쇄 대화상자 띄우기 (용지함·매수 선택)")
        f1.addRow("사용할 프린터", self.cb_printer)
        f1.addRow("", self.chk_dialog)
        v.addWidget(card(w1, "프린터", "기본으로 쓸 프린터입니다. 작성 화면의 미리보기 위에서도 바로 바꿀 수 있습니다. "
                                      "용지는 A5로 자동 설정됩니다.", fixed=True))

        w2 = QWidget(); f2 = QFormLayout(w2); f2.setContentsMargins(0, 0, 0, 0); f2.setSpacing(10)
        self.ed_name = QLineEdit(); self.ed_name.setMaximumWidth(240)
        self.ed_owner = QLineEdit(); self.ed_owner.setMaximumWidth(240)
        self.chk_auto = QCheckBox("이력을 불러올 때 20만원 이하면 부서장 전결 자동 체크")
        f2.addRow("기본 수령인(성명)", self.ed_name)
        f2.addRow("최종결재자 성명", self.ed_owner)
        f2.addRow("", self.chk_auto)
        v.addWidget(card(w2, "기본값", "새로 작성할 때 자동으로 채워지는 값입니다.", fixed=True))

        h = QHBoxLayout(); h.addStretch()
        b = QPushButton("저장"); b.setObjectName("Primary"); b.clicked.connect(self.save)
        h.addWidget(b)
        v.addLayout(h)
        v.addStretch()
        self.load()

    def load(self):
        s = self.store
        fill_printers(self.cb_printer)
        self.cb_printer.setCurrentIndex(max(self.cb_printer.findData(s.get("printer", "")), 0))
        self.chk_dialog.setChecked(s.get("show_dialog", False))
        self.ed_name.setText(s.get("default_name", ""))
        self.ed_owner.setText(s.get("owner_name", ""))
        self.chk_auto.setChecked(s.get("auto_jeon_200k", False))

    def save(self):
        s = self.store
        s.set("printer", self.cb_printer.currentData())
        s.set("show_dialog", self.chk_dialog.isChecked())
        s.set("default_name", self.ed_name.text().strip())
        s.set("owner_name", self.ed_owner.text().strip())
        s.set("auto_jeon_200k", self.chk_auto.isChecked())
        self.main.settings_changed()
        self.main.toast("출력 설정을 저장했습니다.")


class DataPanel(QWidget):
    """데이터 파일 위치·백업."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.store = main.store
        self.setMaximumWidth(860)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)
        w = QWidget(); g = QGridLayout(w); g.setContentsMargins(0, 0, 0, 0); g.setHorizontalSpacing(12); g.setVerticalSpacing(10)
        self.lbl_path = QLabel(); self.lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_count = QLabel()
        for r, (k, wdg) in enumerate((("데이터 파일", self.lbl_path), ("작성이력", self.lbl_count))):
            lb = QLabel(k); lb.setObjectName("FieldLabel"); g.addWidget(lb, r, 0); g.addWidget(wdg, r, 1)
        g.setColumnStretch(1, 1)
        h = QHBoxLayout()
        b1 = QPushButton("폴더 열기"); b1.clicked.connect(main.open_data_dir)
        b2 = QPushButton("백업 만들기"); b2.clicked.connect(self.backup)
        h.addWidget(b1); h.addWidget(b2); h.addStretch()
        g.addLayout(h, 2, 1)
        v.addWidget(card(w, "데이터",
                         "작성이력과 설정은 이 파일 하나에 저장됩니다. 파일만 복사해 두면 그대로 백업됩니다.", fixed=True))

        w2 = QWidget(); h2 = QHBoxLayout(w2); h2.setContentsMargins(0, 0, 0, 0)
        b3 = QPushButton("엑셀 가져오기"); b3.clicked.connect(lambda: main.do_import())
        b4 = QPushButton("엑셀 내보내기"); b4.clicked.connect(lambda: main.do_export())
        h2.addWidget(b3); h2.addWidget(b4); h2.addStretch()
        v.addWidget(card(w2, "엑셀 가져오기 · 내보내기",
                         "다른 부서나 기존 엑셀의 작성이력을 불러오거나(중복은 자동으로 건너뜀), "
                         "전체 작성이력을 엑셀 파일로 저장합니다.", fixed=True))
        v.addStretch()

    def refresh(self):
        self.lbl_path.setText(self.store.path)
        self.lbl_count.setText(f"{self.store.count():,}건")

    def backup(self):
        name = f"지출결의서_백업_{datetime.now():%Y%m%d_%H%M}.db"
        p, _ = QFileDialog.getSaveFileName(self, "백업 파일 저장", name, "데이터 파일 (*.db)")
        if not p:
            return
        self.store.con.commit()
        shutil.copy2(self.store.path, p)
        info(self, "백업", f"백업 파일을 저장했습니다.\n{p}")


class UpdatePanel(QWidget):
    """설정 > 업데이트."""

    def __init__(self, main):
        super().__init__()
        from version import APP_VERSION
        self.main = main
        self.store = main.store
        self.setMaximumWidth(860)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)
        w = QWidget(); f = QFormLayout(w); f.setContentsMargins(0, 0, 0, 0); f.setSpacing(10)
        self.lbl_ver = QLabel(APP_VERSION)
        self.ed_src = QLineEdit()
        self.ed_src.setPlaceholderText("예) excellentdaddy/jichul   또는   \\\\서버\\공유\\지출결의서")
        self.ed_src.setText(main.update_source())
        self.chk_auto = QCheckBox("프로그램을 켤 때 자동으로 확인")
        self.chk_auto.setChecked(self.store.get("auto_update_check", True))
        self.lbl_res = QLabel(""); self.lbl_res.setObjectName("Hint"); self.lbl_res.setWordWrap(True)
        f.addRow("지금 버전", self.lbl_ver)
        f.addRow("업데이트 위치", self.ed_src)
        f.addRow("", self.chk_auto)
        h = QHBoxLayout()
        b1 = QPushButton("저장"); b1.clicked.connect(self.save)
        b2 = QPushButton("지금 확인"); b2.setObjectName("Primary"); b2.clicked.connect(self.check)
        h.addWidget(b1); h.addWidget(b2); h.addStretch()
        f.addRow("", h)
        f.addRow("", self.lbl_res)
        v.addWidget(card(w, "업데이트",
                         "GitHub 저장소(owner/repo)를 적으면 최신 Release 를 확인합니다. "
                         "새 버전이 있으면 알려 주고, 설치까지 자동으로 진행합니다.", fixed=True))
        v.addStretch()

    def save(self):
        self.store.set("update_source", self.ed_src.text().strip())
        self.store.set("auto_update_check", self.chk_auto.isChecked())
        self.main.toast("업데이트 설정을 저장했습니다.")

    def check(self):
        self.save()
        self.lbl_res.setText("확인 중…")
        self.main.check_update_now()

    def show_result(self, m, err):
        from version import APP_VERSION
        import updater
        if err:
            self.lbl_res.setText(f"확인 실패: {err}")
        elif updater.is_newer(m):
            self.lbl_res.setText(f"새 버전 {m['version']} 이 있습니다. ({m.get('date', '')})")
        else:
            self.lbl_res.setText(f"최신 버전입니다. (서버 {m['version']} / 지금 {APP_VERSION})")


class ImportDialog(QDialog):
    """엑셀 작성이력 가져오기: 파일 → 시트 → 열 매칭 → 미리보기 → 가져오기."""

    def __init__(self, store, parent=None, path=None):
        super().__init__(parent)
        self.store = store
        self.book = {}
        self.path = ""
        self.recs = []
        self.setWindowTitle("엑셀 작성이력 가져오기")
        self.resize(1080, 680)
        v = QVBoxLayout(self); v.setContentsMargins(16, 16, 16, 16); v.setSpacing(12)

        w = QWidget(); g = QGridLayout(w); g.setContentsMargins(0, 0, 0, 0); g.setHorizontalSpacing(10); g.setVerticalSpacing(8)
        self.ed_path = QLineEdit(); self.ed_path.setReadOnly(True); self.ed_path.setPlaceholderText("가져올 엑셀 파일을 선택하세요")
        b = QPushButton("파일 선택"); b.clicked.connect(self.pick)
        self.cb_sheet = QComboBox(); self.cb_sheet.currentIndexChanged.connect(self.sheet_changed)
        self.sp_header = QSpinBox(); self.sp_header.setRange(1, 30); self.sp_header.setSuffix(" 행")
        self.sp_header.valueChanged.connect(self.header_changed)
        g.addWidget(QLabel("파일"), 0, 0); g.addWidget(self.ed_path, 0, 1, 1, 3); g.addWidget(b, 0, 4)
        g.addWidget(QLabel("시트"), 1, 0); g.addWidget(self.cb_sheet, 1, 1)
        g.addWidget(QLabel("제목(헤더) 행"), 1, 2); g.addWidget(self.sp_header, 1, 3)
        g.setColumnStretch(1, 1)
        v.addWidget(card(w, "1. 파일 선택", "엑셀(.xlsx, .xlsm), CSV 파일을 읽을 수 있습니다. "
                                            ".xls 파일은 엑셀에서 .xlsx 로 저장한 뒤 불러오세요."))

        mw = QWidget(); grid = QGridLayout(mw); grid.setContentsMargins(0, 0, 0, 0); grid.setHorizontalSpacing(10)
        self.map_cb = {}
        for i, f in enumerate(FIELDS):
            cb = QComboBox(); cb.currentIndexChanged.connect(self.refresh_preview)
            self.map_cb[f] = cb
            lb = QLabel(FIELD_LABELS[f] + (" *" if f in ("date", "amount") else "")); lb.setObjectName("FieldLabel")
            grid.addWidget(lb, i // 4 * 2, i % 4)
            grid.addWidget(cb, i // 4 * 2 + 1, i % 4)
        v.addWidget(card(mw, "2. 열 매칭", "열 이름으로 자동으로 찾았습니다. 다르게 잡힌 곳이 있으면 바꿔 주세요. (* 필수)"))

        pw = QWidget(); pv = QVBoxLayout(pw); pv.setContentsMargins(0, 0, 0, 0)
        self.tbl = QTableWidget(); self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setShowGrid(False)
        pv.addWidget(self.tbl, 1)
        self.lbl = QLabel(""); self.lbl.setObjectName("Hint"); pv.addWidget(self.lbl)
        v.addWidget(card(pw, "3. 미리보기"), 1)

        h = QHBoxLayout(); h.addStretch()
        bc = QPushButton("닫기"); bc.clicked.connect(self.reject)
        self.btn_ok = QPushButton("가져오기"); self.btn_ok.setObjectName("Primary"); self.btn_ok.clicked.connect(self.do_import)
        self.btn_ok.setEnabled(False)
        h.addWidget(bc); h.addWidget(self.btn_ok)
        v.addLayout(h)
        self.imported = 0
        if path:
            self.load(path)

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "엑셀 파일 선택", "", "엑셀/CSV 파일 (*.xlsx *.xlsm *.xls *.csv)")
        if p:
            self.load(p)

    def load(self, p):
        try:
            self.book = importer.read_book(p)
        except Exception as e:  # noqa
            warn(self, "파일을 열 수 없음", str(e))
            return
        self.path = p
        self.ed_path.setText(p)
        self.cb_sheet.blockSignals(True)
        self.cb_sheet.clear()
        best, best_score = 0, -1
        for i, (name, rows) in enumerate(self.book.items()):
            self.cb_sheet.addItem(f"{name}  ({len(rows):,}행)", name)
            _, m = importer.detect(rows)
            if len(m) > best_score:
                best, best_score = i, len(m)
        self.cb_sheet.blockSignals(False)
        self.cb_sheet.setCurrentIndex(best)
        self.sheet_changed()

    def rows(self):
        return self.book.get(self.cb_sheet.currentData(), [])

    def sheet_changed(self):
        hr, m = importer.detect(self.rows())
        self.sp_header.blockSignals(True)
        self.sp_header.setValue(max(hr, 0) + 1)
        self.sp_header.blockSignals(False)
        self.fill_columns(m)

    def header_changed(self):
        self.fill_columns({})

    def fill_columns(self, auto):
        rows = self.rows()
        hr = self.sp_header.value() - 1
        header = rows[hr] if 0 <= hr < len(rows) else []
        if not auto:
            _, auto = importer.detect([header])
        ncol = max((len(r) for r in rows[:50]), default=0)
        for f, cb in self.map_cb.items():
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("(없음)", None)
            for c in range(ncol):
                name = header[c] if c < len(header) and header[c] not in (None, "") else ""
                cb.addItem(f"{_col_letter(c)}열  {name}", c)
            if f in auto:
                cb.setCurrentIndex(auto[f] + 1)
            cb.blockSignals(False)
        self.refresh_preview()

    def mapping(self):
        return {f: cb.currentData() for f, cb in self.map_cb.items() if cb.currentData() is not None}

    def refresh_preview(self):
        rows = self.rows()
        m = self.mapping()
        hr = self.sp_header.value() - 1
        recs, bad = importer.extract(rows, hr, m) if "date" in m else ([], 0)
        self.tbl.clear()
        self.tbl.setColumnCount(len(FIELDS))
        self.tbl.setHorizontalHeaderLabels([FIELD_LABELS[f] for f in FIELDS])
        show = recs[:200]
        self.tbl.setRowCount(len(show))
        for r, rec in enumerate(show):
            for c, f in enumerate(FIELDS):
                val = rec[f]
                if f == "amount":
                    val = f"{val:,}"
                elif f == "detail":
                    val = str(val).split("\n")[0]
                self.tbl.setItem(r, c, QTableWidgetItem(str(val)))
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.recs = recs
        if not self.path:
            self.lbl.setText("")
        elif "date" not in m:
            self.lbl.setText("날짜 열을 지정해 주세요.")
        else:
            self.lbl.setText(f"가져올 수 있는 행 {len(recs):,}건  ·  날짜/금액을 읽을 수 없어 제외 {bad:,}건"
                             + ("  ·  미리보기는 200건까지만 표시" if len(recs) > 200 else ""))
        self.btn_ok.setEnabled(bool(recs))

    def do_import(self):
        src = os.path.basename(self.path) + " / " + str(self.cb_sheet.currentData())
        added, skipped = self.store.add_many(self.recs, src)
        self.imported += added
        info(self, "가져오기 완료", f"새로 추가: {added:,}건\n이미 있어서 건너뜀(중복): {skipped:,}건")
        self.btn_ok.setEnabled(False)


def _col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
