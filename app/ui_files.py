"""첨부파일: 작성 화면의 첨부 카드(AttachPanel) + 설정 > 첨부파일 보관함 관리(FilesPanel)."""
import os
import tempfile

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import attach
from ui_common import ask, card, info, warn

KIND = {".pdf": "PDF"}


def kind(ext):
    return KIND.get(ext, "그림")


def size_text(n):
    n = n or 0
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(1, round(n / 1e3))} KB"


def add_paths(parent, store, paths):
    """파일들을 보관함에 넣고 [{hash,name,ext,pages}] 를 돌려준다. 못 읽은 파일은 알려 준다."""
    out, bad = [], []
    for p in paths:
        try:
            name, ext, data, pages = attach.read_file(p)
        except Exception as e:  # noqa
            bad.append(f"· {os.path.basename(p)}\n  {e}")
            continue
        h = store.add_file(name, ext, data, pages)
        out.append(store.file_info(h))
    if bad:
        warn(parent, "첨부할 수 없는 파일", "\n".join(bad))
    return out


def open_file(store, f):
    """임시 폴더에 꺼내서 Windows 연결 프로그램으로 연다 (보기 전용)."""
    data = store.file_data(f["hash"])
    if not data:
        return
    d = os.path.join(tempfile.gettempdir(), "지출이_첨부")
    os.makedirs(d, exist_ok=True)
    safe = "".join(c for c in f["name"] if c not in '\\/:*?"<>|').strip() or "첨부"
    p = os.path.join(d, safe + f["ext"])
    try:
        with open(p, "wb") as fp:
            fp.write(data)
    except OSError:  # 이미 열려 있으면 그 파일을 다시 연다
        pass
    os.startfile(p)


class _DropList(QListWidget):
    filesDropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            e.acceptProposedAction()
            self.filesDropped.emit(paths)


class AttachPanel(QWidget):
    """작성 화면의 첨부파일 카드. 체크한 파일은 지출결의서 인쇄 뒤 같이 인쇄된다."""
    changed = Signal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.store = main.store
        self.items = []
        # 한 줄짜리 작은 칸: [파일 목록(최대 2줄) 또는 안내]  [추가][보기][빼기]
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        self.setAcceptDrops(True)
        self.lst = _DropList()
        self.lst.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lst.setToolTip("체크: 지출결의서 다음에 A4로 같이 인쇄 · 더블클릭: 보기\n파일을 여기로 끌어다 놓아도 첨부됩니다.")
        self.lst.itemChanged.connect(self._checked)
        self.lst.itemDoubleClicked.connect(lambda it: open_file(self.store, self.items[self.lst.row(it)]))
        self.lst.filesDropped.connect(self.add_paths)
        self.empty = QLabel("매번 같이 출력하는 서류(PDF·그림)를 붙여 두면 인쇄할 때 A4로 같이 나옵니다.")
        self.empty.setObjectName("Hint")
        h.addWidget(self.lst, 1, Qt.AlignmentFlag.AlignTop); h.addWidget(self.empty, 1)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().Policy.Maximum)

        self.b_add = QPushButton("추가"); self.b_add.setObjectName("Small")
        self.menu = QMenu(self); self.menu.aboutToShow.connect(self._fill_menu)
        self.b_add.setMenu(self.menu)
        self.b_view = QPushButton("보기"); self.b_view.setObjectName("Small"); self.b_view.clicked.connect(self.view)
        self.b_del = QPushButton("삭제"); self.b_del.setObjectName("SmallDanger"); self.b_del.clicked.connect(self.remove)
        self.b_del.setToolTip("고른 파일을 이 지출결의서에서 삭제합니다 (보관함에는 남아 다시 붙일 수 있음)")
        for b in (self.b_add, self.b_view, self.b_del):
            h.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
        self.count_label = QLabel(""); self.count_label.setObjectName("Hint")  # 카드 제목줄 오른쪽
        self._refresh()

    # ---------- 바깥에서 쓰는 것 ----------
    def set_items(self, items):
        self.items = [dict(f, print=f.get("print", True)) for f in items]
        self._refresh()

    def payload(self):
        return [{"hash": f["hash"], "print": f["print"]} for f in self.items]

    def to_print(self):
        return [f for f in self.items if f["print"]]

    # ---------- 화면 ----------
    def _refresh(self):
        self.lst.blockSignals(True)
        self.lst.clear()
        for f in self.items:
            it = QListWidgetItem(f"{f['name']}   ·  {kind(f['ext'])} {f['pages']}쪽")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if f["print"] else Qt.CheckState.Unchecked)
            it.setToolTip("체크: 같이 인쇄 · 더블클릭: 보기")
            self.lst.addItem(it)
        self.lst.blockSignals(False)
        has = bool(self.items)
        self.lst.setVisible(has); self.empty.setVisible(not has)
        self.b_view.setVisible(has); self.b_del.setVisible(has)
        if has:  # 1개면 1줄, 2개 이상이면 2줄 높이 (더 많으면 스크롤)
            rh = max(self.lst.sizeHintForRow(0), 20)
            self.lst.setFixedHeight(rh * min(len(self.items), 2) + 2 * self.lst.frameWidth() + 2)
        pages = sum(f["pages"] for f in self.to_print())
        self.count_label.setText(f"{len(self.items)}개 · 인쇄 {pages}쪽" if has else "")

    def dragEnterEvent(self, e):  # 안내 문구 위(빈 상태)에 놓아도 첨부
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            e.acceptProposedAction()
            self.add_paths(paths)

    def _checked(self, it):
        r = self.lst.row(it)
        if 0 <= r < len(self.items):
            self.items[r]["print"] = it.checkState() == Qt.CheckState.Checked
            self._refresh(); self.changed.emit()

    def _fill_menu(self):
        m = self.menu
        m.clear()
        m.addAction("파일에서 찾아 추가…", self.pick)
        have = {f["hash"] for f in self.items}
        lib = [f for f in self.store.file_list() if f["hash"] not in have]
        if lib:
            m.addSeparator()
            t = m.addAction("보관함에서 추가"); t.setEnabled(False)
            for f in lib[:20]:
                m.addAction(f"   {f['name']}  ({kind(f['ext'])} {f['pages']}쪽)",
                            lambda ff=f: self._add([ff]))
        m.addSeparator()
        m.addAction("첨부파일 관리…", self.main.open_files_settings)

    def pick(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "첨부파일 선택", self.store.get("attach_dir", ""), attach.FILTER)
        if paths:
            self.store.set("attach_dir", os.path.dirname(paths[0]))
            self.add_paths(paths)

    def add_paths(self, paths):
        self._add(add_paths(self, self.store, paths))

    def _add(self, files):
        have = {f["hash"] for f in self.items}
        new = [dict(f, print=True) for f in files if f and f["hash"] not in have]
        if new:
            self.items += new
            self._refresh(); self.changed.emit()
            self.main.toast(f"첨부파일 {len(new)}개를 붙였습니다. 인쇄할 때 지출결의서 다음에 같이 나옵니다.")

    def _selected_rows(self):
        rows = sorted({self.lst.row(i) for i in self.lst.selectedItems()})
        if not rows and self.lst.currentRow() >= 0:
            rows = [self.lst.currentRow()]
        return rows

    def view(self):
        # [보기]: 붙어 있는 파일을 모두 연다 (하나만 볼 때는 그 파일을 더블클릭)
        for r in range(len(self.items)):
            open_file(self.store, self.items[r])

    def remove(self):
        rows = self._selected_rows()
        if not rows and len(self.items) == 1:  # 하나뿐이면 고르지 않아도 그 파일
            rows = [0]
        if not rows:
            info(self, "첨부파일 삭제", "삭제할 파일 이름을 목록에서 한 번 클릭해 고른 뒤 [삭제]를 누르세요.\n"
                                       "(앞의 체크는 '같이 인쇄' 여부입니다)")
            return
        names = "\n".join("· " + self.items[r]["name"] for r in rows)
        if not ask(self, "첨부파일 삭제", f"이 지출결의서에서 첨부파일을 삭제할까요?\n\n{names}\n\n"
                   "(설정 > 첨부파일 관리의 보관함에는 남아 있어 다시 붙일 수 있습니다)"):
            return
        for r in reversed(rows):
            del self.items[r]
        self._refresh(); self.changed.emit()


class FilesPanel(QWidget):
    """설정 > 첨부파일 관리: 보관함 목록, 추가(끌어다 놓기 가능)·이름 바꾸기·보기·삭제."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.store = main.store
        self.setAcceptDrops(True)  # 탐색기에서 파일을 끌어다 놓으면 등록
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(12)

        tw = QWidget(); tv = QVBoxLayout(tw); tv.setContentsMargins(0, 0, 0, 0); tv.setSpacing(8)
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["이름", "종류", "쪽수", "크기", "쓰는 이력", "최근 사용"])
        self.tbl.verticalHeader().setVisible(False); self.tbl.setShowGrid(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setDefaultSectionSize(32)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, w in ((1, 70), (2, 60), (3, 80), (4, 80), (5, 110)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed); self.tbl.setColumnWidth(c, w)
        self.tbl.cellDoubleClicked.connect(lambda r, c: self.view())
        tv.addWidget(self.tbl, 1)
        h = QHBoxLayout(); h.setSpacing(6)
        for text, fn, obj in (("추가", self.add, "Small"), ("이름 바꾸기", self.rename, "Small"),
                              ("보기", self.view, "Small"), ("작성 중인 결의서에 붙이기", self.attach_now, "Small")):
            b = QPushButton(text); b.setObjectName(obj); b.clicked.connect(fn); h.addWidget(b)
        h.addStretch()
        bd = QPushButton("삭제"); bd.setObjectName("SmallDanger"); bd.clicked.connect(self.delete); h.addWidget(bd)
        tv.addLayout(h)
        self.lbl = QLabel(""); self.lbl.setObjectName("Hint")
        root.addWidget(card(tw, "첨부파일 관리", "PDF·그림 파일을 이 화면으로 끌어다 놓거나 [추가]로 등록합니다. "
                            "등록한 파일은 작성 화면 [추가]에서 바로 골라 붙입니다. "
                            "인쇄는 지출결의서(A5) 다음에 같은 프린터로 A4 용지에 맞춰 이어서 나옵니다.",
                            extra=[self.lbl]), 1)
        self.files = []

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            e.acceptProposedAction()
            got = add_paths(self, self.store, paths)
            self.refresh()
            if got:
                self.main.toast(f"첨부파일 {len(got)}개를 등록했습니다.")

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    def refresh(self):
        self.files = self.store.file_list()
        self.tbl.setRowCount(len(self.files))
        for r, f in enumerate(self.files):
            vals = [f["name"], kind(f["ext"]), f"{f['pages']}", size_text(f["size"]),
                    f"{f['used']:,}건", f["last"] or "-"]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c in (2, 3, 4):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tbl.setItem(r, c, it)
        total = sum(f["size"] or 0 for f in self.files)
        self.lbl.setText(f"{len(self.files)}개 · {size_text(total)}" if self.files else "")

    def current(self):
        r = self.tbl.currentRow()
        return self.files[r] if 0 <= r < len(self.files) else None

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "첨부파일 등록", self.store.get("attach_dir", ""), attach.FILTER)
        if paths:
            self.store.set("attach_dir", os.path.dirname(paths[0]))
            add_paths(self, self.store, paths)
            self.refresh()

    def rename(self):
        f = self.current()
        if not f:
            return
        name, ok = QInputDialog.getText(self, "이름 바꾸기", "첨부파일 이름", text=f["name"])
        if ok and name.strip():
            self.store.rename_file(f["hash"], name.strip())
            for it in self.main.attach_panel.items:
                if it["hash"] == f["hash"]:
                    it["name"] = name.strip()
            self.main.attach_panel._refresh()
            self.refresh()

    def view(self):
        f = self.current()
        if f:
            open_file(self.store, f)

    def attach_now(self):
        f = self.current()
        if f:
            self.main.attach_panel._add([f])

    def delete(self):
        f = self.current()
        if not f:
            return
        msg = f"'{f['name']}'을(를) 보관함에서 삭제할까요?"
        if f["used"]:
            msg += f"\n\n이 파일을 쓰는 작성이력 {f['used']:,}건에서도 첨부가 빠집니다."
        if not ask(self, "첨부파일 삭제", msg, danger=True):
            return
        self.store.delete_file(f["hash"])
        ap = self.main.attach_panel
        ap.set_items([it for it in ap.items if it["hash"] != f["hash"]])
        self.main.load_history()
        self.refresh()
