"""메인 창: 상단 메뉴 [작성 | 작성이력 | 설정] 으로 화면을 나눈다."""
import ast
import operator
import os
import re
from datetime import date

from PySide6.QtCore import QBuffer, QByteArray, QDate, QEvent, QIODevice, QMarginsF, QObject, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QFontMetrics, QIcon, QImage, QKeySequence, QPageLayout, QPageSize, QPainter, QPen, QShortcut
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QSplitter, QCheckBox, QComboBox, QCompleter, QDateEdit, QFileDialog, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QStyle, QStyledItemDelegate, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

import render
from layout import LAYOUTS
from numkor import numberstring
from store import FIELD_LABELS, FIELDS, resource_path
from ui_common import ask, card, info, warn
from ui_zero import describe

from version import APP_NAME, APP_VERSION, UPDATE_SOURCE

AMT_VAT_RE = re.compile(r"\d{1,3}(,\d{3})*\s?원(\s?\(VAT 포함\)|\s?\(VAT포함\))?")
VAT_RE = re.compile(r"\(?(VAT\s*포함)\)?", re.I)
# 내역의 '금액 :' 줄 — 기본 틀처럼 숫자가 빈 '2) 금액 : 원' 도 잡는다
AMT_LINE_RE = re.compile(r"(금\s*액\s*:\s*)(?:\d{1,3}(?:,\d{3})*|\d+)?\s?원(?:\s?\(VAT\s*포함\))?", re.I)

PAGE_WRITE, PAGE_SETTINGS = 0, 1


def qd(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def pyd(q: QDate) -> date:
    return date(q.year(), q.month(), q.day())


# ---------------------------------------------------------------- 계산기
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def safe_eval(expr: str):
    expr = expr.replace(",", "").replace("×", "*").replace("x", "*").replace("X", "*").replace("÷", "/")
    if not expr.strip():
        return None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        raise ValueError

    try:
        return ev(ast.parse(expr, mode="eval"))
    except Exception:
        return None


def local_shortcut(key, widget, fn):
    """그 위젯에 커서가 있을 때만 동작하는 단축키."""
    sc = QShortcut(QKeySequence(key), widget, activated=fn)
    sc.setContext(Qt.ShortcutContext.WidgetShortcut)
    return sc


class FitLabel(QLabel):
    """칸이 모자라면 글자를 작게 줄여서 끝까지 다 보이게 하는 한 줄 라벨."""

    def minimumSizeHint(self):
        return QSize(10, super().minimumSizeHint().height())

    def paintEvent(self, ev):
        p = QPainter(self)
        f = QFont(self.font())
        size = f.pointSizeF() if f.pointSizeF() > 0 else 10.0
        while size > 6:
            f.setPointSizeF(size)
            if QFontMetrics(f).horizontalAdvance(self.text()) <= self.width():
                break
            size -= 0.5
        p.setFont(f)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), self.text())


class CalcEdit(QPlainTextEdit):
    """두 줄 높이 계산식 칸. Enter = 금액에 넣기, Shift+Enter = 줄바꿈.
    줄을 바꿔 쓰면 줄끼리 더한다 (줄 끝·줄 앞에 + - * / 가 있으면 그대로 이어서 계산)."""
    returnPressed = Signal()
    textEdited = Signal(str)

    def __init__(self):
        super().__init__()
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.textChanged.connect(lambda: self.textEdited.emit(self.text()))

    def showEvent(self, ev):
        super().showEvent(ev)
        m = self.contentsMargins(); d = self.document().documentMargin()
        self.setFixedHeight(int(self.fontMetrics().lineSpacing() * 2 + d * 2 + m.top() + m.bottom() + 6))

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (ev.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.returnPressed.emit()
            return
        super().keyPressEvent(ev)

    def text(self) -> str:
        out = ""
        for line in (x.strip() for x in self.toPlainText().splitlines()):
            if not line:
                continue
            if out and not (out[-1] in "+-*/×÷xX(" or line[0] in "+-*/×÷xX)"):
                out += "+"
            out += line
        return out


def field_label(text):
    lb = QLabel(text)
    lb.setObjectName("FieldLabel")
    return lb


# ---------------------------------------------------------------- 미리보기
class Preview(QWidget):
    """양식 부분만 잘라 크게 보여 준다 (용지 위·아래 빈 여백 생략).

    editable=True 이면 doc["images"] 의 이미지를 마우스로 옮기고(드래그) 크기를 바꾼다(오른쪽 아래 모서리).
    """
    imagesChanged = Signal()
    HANDLE_MM = 2.5

    def __init__(self, editable=False):
        super().__init__()
        self.doc, self.lay = {}, None
        self.adjust, self.highlight = {}, None
        self.show_bg = True
        self.bg = {}
        self.editable = editable
        self.sel = -1
        self._drag = None
        self._view = None  # (ox, oy, s, vx0, vy0)
        self.setMinimumWidth(380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if editable:
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set(self, doc, lay, adjust=None, highlight=None):
        self.doc, self.lay = doc, lay
        self.adjust, self.highlight = adjust or {}, highlight
        if self.sel >= len(self.images()):
            self.sel = -1
        self.update()

    def images(self):
        return self.doc.get("images") or []

    def _bg(self, name):
        if name not in self.bg:
            self.bg[name] = QImage(resource_path("assets", name))
        return self.bg[name]

    # ---------- 좌표 변환 ----------
    def _to_mm(self, pos):
        if not self._view:
            return None
        ox, oy, sc, vx0, vy0 = self._view
        return (pos.x() - ox) / sc + vx0, (pos.y() - oy) / sc + vy0

    @staticmethod
    def _handles(im):
        """손잡이 8개: 모서리(nw,ne,sw,se)=비율 유지, 변 중간(n,s,w,e)=세로만·가로만."""
        x0, y0 = im["x"], im["y"]
        x1, y1 = x0 + im["w"], y0 + im["h"]
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        return {"nw": (x0, y0), "n": (xm, y0), "ne": (x1, y0), "e": (x1, ym),
                "se": (x1, y1), "s": (xm, y1), "sw": (x0, y1), "w": (x0, ym)}

    _CURSORS = {"nw": Qt.CursorShape.SizeFDiagCursor, "se": Qt.CursorShape.SizeFDiagCursor,
                "ne": Qt.CursorShape.SizeBDiagCursor, "sw": Qt.CursorShape.SizeBDiagCursor,
                "n": Qt.CursorShape.SizeVerCursor, "s": Qt.CursorShape.SizeVerCursor,
                "e": Qt.CursorShape.SizeHorCursor, "w": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.SizeAllCursor}

    def _hit(self, mm):
        """(이미지 번호, 손잡이 이름|'move') 또는 (-1, None)."""
        x, y = mm
        ims = self.images()
        if 0 <= self.sel < len(ims):
            for name, (hx, hy) in self._handles(ims[self.sel]).items():
                if abs(x - hx) <= self.HANDLE_MM and abs(y - hy) <= self.HANDLE_MM:
                    return self.sel, name
        for i in range(len(ims) - 1, -1, -1):
            im = ims[i]
            if im["x"] <= x <= im["x"] + im["w"] and im["y"] <= y <= im["y"] + im["h"]:
                return i, "move"
        return -1, None

    # ---------- 마우스 ----------
    def mousePressEvent(self, e):
        if not self.editable or e.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(e)
        mm = self._to_mm(e.position())
        if mm is None:
            return
        i, mode = self._hit(mm)
        self.sel = i
        if i >= 0:
            im = self.images()[i]
            self._drag = (mode, mm, dict(im))
        else:
            self._drag = None
        self.update()

    def mouseMoveEvent(self, e):
        if not self.editable:
            return super().mouseMoveEvent(e)
        mm = self._to_mm(e.position())
        if mm is None:
            return
        if self._drag:
            mode, start, orig = self._drag
            im = self.images()[self.sel]
            dx, dy = mm[0] - start[0], mm[1] - start[1]
            if mode == "move":
                im["x"], im["y"] = orig["x"] + dx, orig["y"] + dy
            else:
                self._resize(im, orig, mode, dx, dy, bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            self.update()
        else:
            i, mode = self._hit(mm)
            self.setCursor(self._CURSORS.get(mode, Qt.CursorShape.ArrowCursor))

    @staticmethod
    def _resize(im, orig, h, dx, dy, free):
        """손잡이 h 를 (dx, dy) 만큼 끌었을 때. 반대쪽 변·모서리는 고정.

        변(e/w/n/s): 가로만 또는 세로만. 모서리: 비율 유지 (Shift 를 누르면 자유롭게).
        """
        MIN = 3.0
        x0, y0 = orig["x"], orig["y"]
        x1, y1 = x0 + orig["w"], y0 + orig["h"]
        if "e" in h:
            x1 = max(x0 + MIN, x1 + dx)
        if "w" in h:
            x0 = min(x1 - MIN, x0 + dx)
        if "s" in h:
            y1 = max(y0 + MIN, y1 + dy)
        if "n" in h:
            y0 = min(y1 - MIN, y0 + dy)
        if len(h) == 2 and not free:  # 모서리: 가로 변화에 맞춰 세로를 비율대로
            w = x1 - x0
            nh = w * orig["h"] / orig["w"]
            if "n" in h:
                y0 = y1 - nh
            else:
                y1 = y0 + nh
        im["x"], im["y"], im["w"], im["h"] = x0, y0, x1 - x0, y1 - y0

    def mouseReleaseEvent(self, e):
        if self.editable and self._drag:
            self._drag = None
            self.imagesChanged.emit()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if self.editable and e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and 0 <= self.sel < len(self.images()):
            del self.images()[self.sel]
            self.sel = -1
            self.imagesChanged.emit()
            self.update()
            return
        super().keyPressEvent(e)

    # ---------- 그리기 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#f1f3f4"))
        if not self.lay:
            return
        b = self.lay.bg_box
        vx0, vy0, vx1, vy1 = b.x0 - 2, b.y0 - 2, b.x1 + 2, b.y1 + 2
        vw, vh = vx1 - vx0, vy1 - vy0
        m = 10
        s = min((self.width() - 2 * m) / vw, (self.height() - 2 * m) / vh)  # px/mm
        ox = (self.width() - vw * s) / 2
        oy = (self.height() - vh * s) / 2
        self._view = (ox, oy, s, vx0, vy0)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(QRectF(ox + 1, oy + 2, vw * s, vh * s), QColor(60, 64, 67, 38))
        p.fillRect(QRectF(ox, oy, vw * s, vh * s), Qt.GlobalColor.white)
        p.setClipRect(QRectF(ox, oy, vw * s, vh * s))
        p.translate(ox - vx0 * s, oy - vy0 * s)
        p.scale(s / render.U, s / render.U)
        if self.show_bg and self.lay.background:
            p.setOpacity(0.5)
            p.drawImage(QRectF(b.x0 * render.U, b.y0 * render.U, b.w * render.U, b.h * render.U),
                        self._bg(self.lay.background))
            p.setOpacity(1.0)
        render.render(p, self.doc, self.lay, guides=not self.show_bg, adjust=self.adjust, highlight=self.highlight)
        ims = self.images()
        if self.editable and 0 <= self.sel < len(ims):
            im = ims[self.sel]
            U = render.U
            p.setPen(QPen(QColor(26, 115, 232), 0.35 * U, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(im["x"] * U, im["y"] * U, im["w"] * U, im["h"] * U))
            hs = self.HANDLE_MM * U
            p.setPen(QPen(QColor(26, 115, 232), 0.25 * U)); p.setBrush(QColor("white"))
            for name, (hx, hy) in self._handles(im).items():
                if len(name) == 2:  # 모서리: 파란 네모 (비율 유지)
                    p.setBrush(QColor(26, 115, 232))
                else:               # 변 중간: 흰 네모 (가로만·세로만)
                    p.setBrush(QColor("white"))
                p.drawRect(QRectF(hx * U - hs / 2, hy * U - hs / 2, hs, hs))
        p.end()


# ---------------------------------------------------------------- 인쇄 진행 표시
class PrintProgress(QWidget):
    """인쇄 버튼을 눌렀을 때 창 가운데에 뜨는 작은 진행 카드. 완료되면 1.5초 뒤 저절로 닫힌다."""

    def __init__(self, parent, printer_name):
        from PySide6.QtWidgets import QProgressBar
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("PrintCard")
        self.setFixedWidth(380)
        v = QVBoxLayout(self); v.setContentsMargins(22, 18, 22, 18); v.setSpacing(10)
        self.title = QLabel("인쇄 중"); self.title.setObjectName("PrintTitle")
        self.msg = QLabel(""); self.msg.setObjectName("Hint")
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setTextVisible(False); self.bar.setFixedHeight(8)
        self.sub = QLabel(f"프린터: {printer_name}"); self.sub.setObjectName("Hint")
        for wd in (self.title, self.msg, self.bar, self.sub):
            v.addWidget(wd)
        self.adjustSize()
        g = parent.geometry()
        self.move(g.x() + (g.width() - self.width()) // 2, g.y() + (g.height() - self.height()) // 2)
        self.show(); self.raise_()
        self._pump()

    def _pump(self):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def step(self, value, text):
        self.bar.setValue(value)
        self.msg.setText(text)
        self._pump()

    def done(self, msg="Windows 인쇄 대기열에 전송을 마쳤습니다."):
        self.bar.setValue(100)
        self.title.setText("✓ 프린터로 보냈습니다")
        self.title.setObjectName("PrintDone"); self.title.style().unpolish(self.title); self.title.style().polish(self.title)
        self.msg.setText(msg)
        self._pump()
        QTimer.singleShot(1500, self.close)


class _XDelegate(QStyledItemDelegate):
    """콤보 목록 항목 오른쪽에 ✕ 를 그린다 (마우스가 올라간 줄은 빨갛게)."""
    W = 28

    def paint(self, p, opt, idx):
        super().paint(p, opt, idx)
        if not idx.data():  # 빈 줄(선택 안 함)에는 ✕ 없음
            return
        r = QRect(opt.rect.right() - self.W, opt.rect.top(), self.W, opt.rect.height())
        hover = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        p.save()
        p.setPen(QColor("#d93025" if hover else "#9aa0a6"))
        f = QFont(opt.font); f.setPixelSize(13); f.setBold(hover); p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "✕")
        p.restore()


class _XFilter(QObject):
    """✕ 위를 누르면 그 항목을 지우고, 목록은 닫지 않는다."""

    def __init__(self, combo, on_delete):
        super().__init__(combo)
        self.combo, self.on_delete = combo, on_delete

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                         QEvent.Type.MouseButtonDblClick):
            view = self.combo.view()
            pos = ev.position().toPoint()
            idx = view.indexAt(pos)
            if idx.isValid() and idx.data() and pos.x() >= view.visualRect(idx).right() - _XDelegate.W:
                if ev.type() == QEvent.Type.MouseButtonRelease:
                    text = idx.data()
                    cur = self.combo.currentText()
                    self.combo.blockSignals(True)
                    self.combo.removeItem(idx.row())
                    self.combo.setCurrentText(cur)
                    self.combo.blockSignals(False)
                    self.on_delete(text)
                    if self.combo.count() == 0:
                        self.combo.hidePopup()
                return True
        return False


def deletable_combo(combo, on_delete):
    """편집 가능한 콤보의 목록 항목마다 ✕ 삭제 단추를 단다."""
    view = combo.view()  # 팝업을 먼저 만들어 두어야 우리 필터가 먼저 불린다
    view.setItemDelegate(_XDelegate(view))
    view.setMouseTracking(True)
    view.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    view.viewport().installEventFilter(_XFilter(combo, on_delete))
    combo.setToolTip("목록의 ✕ 를 누르면 그 이름을 목록에서 뺍니다 (작성이력은 그대로)")


class Notice(QWidget):
    """저장 같은 동작 뒤 창 가운데에 잠깐 뜨는 안내 카드 (1.6초 뒤 저절로 닫힘)."""

    def __init__(self, parent, title, msg="", ok=True, ms=1600):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setObjectName("PrintCard")
        self.setFixedWidth(360)
        v = QVBoxLayout(self); v.setContentsMargins(22, 18, 22, 18); v.setSpacing(8)
        t = QLabel(title); t.setObjectName("PrintDone" if ok else "PrintTitle")
        v.addWidget(t)
        if msg:
            m = QLabel(msg); m.setObjectName("Hint"); m.setWordWrap(True); v.addWidget(m)
        self.adjustSize()
        g = parent.geometry()
        self.move(g.x() + (g.width() - self.width()) // 2, g.y() + (g.height() - self.height()) // 2)
        self.show(); self.raise_()
        QTimer.singleShot(ms, self.close)


# ---------------------------------------------------------------- 결재란 (실제 양식처럼 가로 배치)
class ApprovalPanel(QWidget):
    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        self.rows = []
        self.lay = None
        self.owner_name = ""
        self._auto = set()
        self.no_dates = False  # '년월일 인쇄 안 함' → 결재일도 인쇄 안 함

    def set_no_dates(self, on):
        self.no_dates = bool(on)
        self._apply_auto()

    def build(self, lay, base: date):
        self.lay = lay
        self._auto = set()
        while self.grid.count():
            it = self.grid.takeAt(0)
            wd = it.widget()
            if wd:
                wd.hide(); wd.setParent(None); wd.deleteLater()  # 양식 전환 시 잔상 방지
        for c in range(12):
            self.grid.setColumnStretch(c, 0)
        self.rows = []
        n = len(lay.cols)
        for r, t in ((1, "결재일"), (2, "사선"), (3, "전결")):
            self.grid.addWidget(field_label(t), r, 0)
        for i, col in enumerate(lay.cols):
            last = i == n - 1
            head = QLabel(col)
            head.setObjectName("ColHead"); head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            de = QDateEdit(qd(base))
            de.setDisplayFormat("M/d")
            de.setCalendarPopup(True)
            de.setAlignment(Qt.AlignmentFlag.AlignCenter)
            de.setMinimumWidth(64)
            de.dateChanged.connect(self.on_change)
            sl = QCheckBox(); sl.toggled.connect(self.on_change)
            jn = QCheckBox(); jn.toggled.connect(lambda on, k=i: self._jeon(k, on))
            if last:
                sl.setEnabled(False); sl.setToolTip("마지막 칸은 항상 도장 칸입니다.")
                jn.setEnabled(False)
            if i not in lay.jeon_cols:
                jn.setEnabled(False)
            c = i + 1
            self.grid.addWidget(head, 0, c)
            self.grid.addWidget(de, 1, c)
            self.grid.addWidget(sl, 2, c, alignment=Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(jn, 3, c, alignment=Qt.AlignmentFlag.AlignCenter)
            self.grid.setColumnStretch(c, 1)
            self.rows.append((de, sl, jn))
        self.chk_owner = QCheckBox()
        self.chk_owner.toggled.connect(self._owner)
        self.set_owner_name(self.owner_name)
        b = QPushButton("결재일 = 작성일"); b.setObjectName("Small")
        b.setToolTip("모든 결재일을 작성일로 되돌립니다.")
        b.clicked.connect(lambda: self.on_change("reset_dates"))
        holder = QWidget(); h = QHBoxLayout(holder); h.setContentsMargins(0, 4, 0, 0)
        h.addWidget(self.chk_owner, 1); h.addWidget(b)
        self.grid.addWidget(holder, 4, 0, 1, n + 1)
        self._apply_auto()

    def set_owner_name(self, name):
        self.owner_name = name
        if hasattr(self, "chk_owner") and self.lay:
            last = self.lay.cols[-1]
            self.chk_owner.setText(f"{last} 전결")
            self.chk_owner.setToolTip(f"{last} 전결: {last} 칸만 도장, 나머지 칸은 모두 사선")

    def set_dates(self, d: date):
        for de, _, _ in self.rows:
            de.blockSignals(True); de.setDate(qd(d)); de.blockSignals(False)

    def _jeon(self, k, on):
        if on:
            for i, (_, _, jn) in enumerate(self.rows):
                if i != k and jn.isChecked():
                    jn.blockSignals(True); jn.setChecked(False); jn.blockSignals(False)
            if self.chk_owner.isChecked():
                self.chk_owner.blockSignals(True); self.chk_owner.setChecked(False); self.chk_owner.blockSignals(False)
        self._apply_auto()
        self.on_change()

    def _owner(self, on):
        if on:
            for _, _, jn in self.rows:
                jn.blockSignals(True); jn.setChecked(False); jn.blockSignals(False)
        self._apply_auto()
        self.on_change("owner")

    def jeon_idx(self):
        for i, (_, _, jn) in enumerate(self.rows):
            if jn.isChecked():
                return i
        return None

    def set_jeon(self, idx):
        for i, (_, _, jn) in enumerate(self.rows):
            jn.blockSignals(True); jn.setChecked(i == idx and jn.isEnabled()); jn.blockSignals(False)
        self._apply_auto()

    def _apply_auto(self):
        """전결/본인 건에 따라 자동으로 정해지는 칸은 화면에도 반영하고 잠근다."""
        n = len(self.rows)
        st = self.states()
        owner = self.chk_owner.isChecked() if hasattr(self, "chk_owner") else False
        j = self.jeon_idx()
        prev_auto = self._auto
        self._auto = set()
        for i, (de, sl, jn) in enumerate(self.rows):
            last = i == n - 1
            auto = (not last) and (owner or (j is not None and i >= j))
            sl.blockSignals(True)
            if auto:
                self._auto.add(i)
                sl.setChecked(st[i]["slash"])
            elif i in prev_auto:
                sl.setChecked(False)  # 자동 사선이 풀리면 체크도 해제
            sl.setEnabled(not last and not auto)
            sl.blockSignals(False)
            de.setEnabled(st[i]["date"] is not None)
            de.setToolTip("'년월일 인쇄 안 함'이 켜져 있어 결재일도 인쇄하지 않습니다." if self.no_dates else "")

    def states(self):
        n = len(self.rows)
        dates = [pyd(de.date()) for de, _, _ in self.rows]
        manual = [sl.isChecked() for _, sl, _ in self.rows]
        owner = self.chk_owner.isChecked() if hasattr(self, "chk_owner") else False
        st = render.compute_approvals(n, dates, manual, self.jeon_idx(), owner)
        if self.no_dates:
            for s in st:
                s["date"] = None
        return st

    def reset(self, base: date):
        for _, sl, jn in self.rows:
            for w in (sl, jn):
                w.blockSignals(True); w.setChecked(False); w.blockSignals(False)
        self.chk_owner.blockSignals(True); self.chk_owner.setChecked(False); self.chk_owner.blockSignals(False)
        self.set_dates(base)
        self._apply_auto()


# ---------------------------------------------------------------- 메인 창
class MainWindow(QMainWindow):
    loaded_id = None  # 불러온(또는 방금 저장·인쇄한) 이력 id

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.records = []
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("assets", "icon.ico")))
        self.setMinimumSize(1360, 780)
        self._loading = False
        self._prev_name = ""
        self.images = []  # 미리보기에 올린 이미지 [{"img": QImage, "x","y","w","h": mm}]

        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(120)
        self.timer.timeout.connect(self.refresh_preview)

        self.setMenuWidget(self._build_header())
        self.lbl_db = QLabel("")
        self.statusBar().addPermanentWidget(self.lbl_db)

        self.pages = QStackedWidget(); self.pages.setObjectName("Pages")
        self.pages.addWidget(self._build_write_page())
        self.pages.addWidget(self._build_settings_page())
        self.setCentralWidget(self.pages)

        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.do_print)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.do_save)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_doc)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        for i, key in enumerate(("Ctrl+1", "Ctrl+2")):
            QShortcut(QKeySequence(key), self, activated=lambda k=i: self.go(k))

        lk = store.get("layout", "5")
        self.cb_layout.setCurrentIndex(max(0, self.cb_layout.findData(lk)))
        self.layout_changed()
        self.new_doc()
        self.load_history()
        self._update_zero_btn()
        self.go(PAGE_WRITE)

    # ================================================================ 창 / 공통
    def place_window(self):
        """저장된 창 위치가 없으면 모니터 작업영역에 맞춰 크게 띄운다."""
        geo = self.store.get("geometry_v2")
        if geo:
            from PySide6.QtCore import QByteArray
            if self.restoreGeometry(QByteArray.fromBase64(geo.encode())):
                return
        scr = self.screen().availableGeometry()
        w = min(scr.width() - 40, 1840)
        h = min(scr.height() - 30, 1060)
        self.resize(w, h)
        self.move(scr.x() + (scr.width() - w) // 2, scr.y() + (scr.height() - h) // 2)

    def closeEvent(self, e):
        if hasattr(self, "coord"):
            self.coord.confirm_leave()
        self.store.set("geometry_v2", bytes(self.saveGeometry().toBase64()).decode())
        self.store.set("write_split", bytes(self.write_split.saveState().toBase64()).decode())
        super().closeEvent(e)

    def toast(self, msg, ms=4000):
        self.statusBar().showMessage(msg, ms)

    def _build_header(self):
        bar = QWidget(); bar.setObjectName("HeaderBar")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        h = QHBoxLayout(bar); h.setContentsMargins(20, 0, 16, 0); h.setSpacing(0)
        ic = QLabel(); ic.setPixmap(QIcon(resource_path("assets", "icon.png")).pixmap(28, 28))
        title = QLabel("지출결의서"); title.setObjectName("AppTitle")
        h.addWidget(ic); h.addSpacing(10); h.addWidget(title); h.addSpacing(36)

        # 메뉴(탭)
        self.nav = QButtonGroup(self); self.nav.setExclusive(True)
        for i, (text, tip) in enumerate((("작성", "지출결의서 작성·인쇄 (Ctrl+1)"),
                                         ("설정", "좌표·프린터·데이터 설정 (Ctrl+2)"))):
            b = QPushButton(text); b.setObjectName("NavTab"); b.setCheckable(True); b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav.addButton(b, i)
            h.addWidget(b)
        self.nav.idClicked.connect(self.go)
        h.addStretch()

        # 화면별 동작 버튼
        self.actions = QStackedWidget(); self.actions.setObjectName("HeadActions")
        self.actions.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        def group(*items):
            w = QWidget(); hl = QHBoxLayout(w); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(8)
            hl.addStretch()
            for it in items:
                hl.addWidget(it)
            return w

        def btn(text, fn, tip="", name="HeadBtn"):
            b = QPushButton(text); b.setObjectName(name); b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, f=fn: f())
            return b

        self.actions.addWidget(group())  # 작성 화면: [새로 작성·저장·인쇄]는 미리보기 위에 있음
        more = QPushButton("도움말"); more.setObjectName("HeadBtn")
        m = QMenu(more)
        for text, fn in (("업데이트 확인", self.check_update_now), ("시험 인쇄", self.test_print),
                         ("데이터 폴더 열기", self.open_data_dir), ("프로그램 정보", self.about)):
            a = QAction(text, self); a.triggered.connect(lambda _=False, f=fn: f()); m.addAction(a)
        more.setMenu(m)
        self.actions.addWidget(group(more))
        h.addWidget(self.actions)
        return bar

    def go(self, idx):
        if self.pages.currentIndex() == PAGE_SETTINGS and idx != PAGE_SETTINGS and hasattr(self, "coord"):
            self.coord.confirm_leave()
        self.pages.setCurrentIndex(idx)
        self.actions.setCurrentIndex(idx)
        self.nav.button(idx).setChecked(True)
        if idx == PAGE_SETTINGS:
            self.coord.load()
            self.data_panel.refresh()

    def _focus_search(self):
        self.go(PAGE_WRITE)
        self.ed_qsearch.setFocus()
        self.ed_qsearch.selectAll()

    def open_data_dir(self):
        import subprocess
        subprocess.Popen(["explorer", "/select,", os.path.normpath(self.store.path)])

    def about(self):
        info(self, "프로그램 정보",
             f"{APP_NAME}  버전 {APP_VERSION}\n\n"
             f"데이터 파일: {self.store.path}\n작성이력: {self.store.count():,}건\n\n"
             "단축키\n  Ctrl+P 인쇄   Ctrl+S 저장   Ctrl+N 새로 작성\n"
             "  Ctrl+1/2 화면 이동   Ctrl+F 이력 검색")

    # ================================================================ 업데이트
    def update_source(self):
        return (UPDATE_SOURCE or "").strip()  # 프로그램 안에 고정 (사용자에게 보이지 않음)

    def start_update_check(self, silent=True):
        """서버(GitHub 등)에 새 버전이 있는지 확인. silent 이면 새 버전이 있을 때만 알린다."""
        import updater
        src = self.update_source()
        if not src:
            if not silent:
                info(self, "업데이트", "업데이트를 확인할 수 없습니다.")
            return
        if silent and not self.store.get("auto_update_check", True):
            return
        t = updater.CheckThread(src, self)
        t.done.connect(lambda m, err, s=silent: self._update_checked(m, err, s))
        t.finished.connect(t.deleteLater)
        self._upd_thread = t
        t.start()
        if not silent:
            self.toast("업데이트 확인 중…")

    def check_update_now(self):
        self.start_update_check(silent=False)

    def _update_checked(self, m, err, silent):
        import updater
        if hasattr(self, "update_panel"):
            self.update_panel.show_result(m, err)
        if err:
            if not silent:
                warn(self, "업데이트 확인 실패", f"업데이트 서버에 연결하지 못했습니다.\n\n이유: {err}\n\n잠시 뒤 다시 시도하세요.")
            return
        if not updater.is_newer(m):
            if not silent:
                info(self, "업데이트", f"최신 버전을 사용하고 있습니다. (버전 {APP_VERSION})")
            return
        if silent and self.store.get("skip_version", "") == m["version"]:
            return
        notes = m.get("notes") or ""
        if len(notes) > 600:
            notes = notes[:600] + "…"
        msg = (f"새 버전이 있습니다.\n\n지금 버전: {APP_VERSION}\n새 버전: {m['version']}"
               + (f"  ({m['date']})" if m.get("date") else "")
               + (f"\n\n바뀐 내용\n{notes}" if notes else "")
               + "\n\n지금 업데이트할까요? (프로그램이 잠시 닫혔다가 다시 열립니다)")
        if ask(self, "업데이트 알림", msg):
            self.do_update(m)
        elif silent:
            self.store.set("skip_version", m["version"])  # 같은 버전은 다음 실행 때 다시 묻지 않음
            self.toast(f"새 버전 {m['version']} 은 도움말 > 업데이트 확인에서 언제든 설치할 수 있습니다.", 8000)

    def do_update(self, m):
        import updater
        from PySide6.QtWidgets import QApplication, QProgressDialog
        dlg = QProgressDialog("새 버전을 내려받는 중…", "취소", 0, 100, self)
        dlg.setWindowTitle("업데이트"); dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0); dlg.setValue(0)
        cancelled = {"v": False}

        def prog(got, total):
            if total:
                dlg.setValue(int(got * 100 / total))
            QApplication.processEvents()
            if dlg.wasCanceled():
                cancelled["v"] = True
                raise RuntimeError("취소됨")
        try:
            path = updater.fetch_installer(m, prog)
        except Exception as e:  # noqa
            dlg.close()
            if not cancelled["v"]:
                why = str(e) if isinstance(e, RuntimeError) else updater.explain(e)
                warn(self, "업데이트 실패", f"새 버전을 내려받지 못했습니다.\n\n이유: {why}\n\n잠시 뒤 다시 시도하세요.")
            return
        dlg.close()
        try:
            moved = updater.carry_portable_data()
        except Exception:
            moved = None
        if moved:
            info(self, "업데이트", f"지금까지의 작성이력을 설치형 데이터 위치로 복사했습니다.\n{moved}")
        self.store.con.commit()
        updater.run_installer(path)
        QApplication.quit()

    # ================================================================ 1. 작성 화면
    def _build_write_page(self):
        page = QWidget()
        h = QHBoxLayout(page); h.setContentsMargins(16, 14, 16, 10); h.setSpacing(14)

        left = QWidget(); left.setFixedWidth(560)
        lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(12)
        lv.addWidget(card(self._build_basic(), "기본 정보"))
        lv.addWidget(card(self._build_detail(), "내역 (적요)"), 1)
        self.approval = ApprovalPanel(self._approval_changed)
        lv.addWidget(card(self.approval, "결재란"))
        h.addWidget(left)

        # 미리보기 카드: 제목줄 오른쪽에 양식 · 프린터 · 영점
        self.cb_layout = QComboBox(); self.cb_layout.setToolTip("인쇄할 용지 양식 (한 번 정하면 거의 바꾸지 않음)")
        for k, l in LAYOUTS.items():
            self.cb_layout.addItem(l.title, k)
        self.cb_layout.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.cb_layout.currentIndexChanged.connect(self.layout_changed)
        from ui_dialogs import fill_printers
        self.cb_printer = QComboBox(); self.cb_printer.setMinimumWidth(110); self.cb_printer.setToolTip("인쇄할 프린터")
        self.cb_printer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fill_printers(self.cb_printer)
        self.cb_printer.setCurrentIndex(max(self.cb_printer.findData(self.store.get("printer", "")), 0))
        self.cb_printer.currentIndexChanged.connect(self._printer_changed)
        self.btn_zero = QPushButton(); self.btn_zero.setObjectName("Zero")
        self.btn_zero.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zero.setToolTip("이 프린터의 출력 위치(영점) 보정 — 프린터마다 따로 저장")
        self.btn_zero.clicked.connect(self.do_zero)
        self.preview = Preview(editable=True)
        self.preview.imagesChanged.connect(self.changed)
        # Ctrl+V: 창 전체 단축키. 입력칸(내역·금액 등)에 커서가 있으면 그 칸이 먼저 받아 글자로 붙고,
        # 그 밖(미리보기 클릭 후, 이력 목록 등)에서는 클립보드 이미지를 미리보기에 올린다.
        QShortcut(QKeySequence(QKeySequence.StandardKey.Paste), self, activated=lambda: self.paste_image(quiet=True))
        self.preview.setToolTip("Ctrl+V: 클립보드 이미지(엑셀 표 등) 올리기\n"
                                "드래그로 이동 · 모서리(파란 점) 비율 유지 · 변 가운데(흰 점) 가로/세로 조절 · Delete 삭제")
        pv_card = card(self.preview, "미리보기", margins=(10, 10, 10, 10),
                       extra=[self.cb_layout, self.cb_printer, self.btn_zero])

        # 미리보기 아래: 첨부파일 (작은 칸, 1~2줄)
        from ui_files import AttachPanel
        self.attach_panel = AttachPanel(self)
        self.attach_panel.changed.connect(self.changed)
        mid = QWidget(); mv = QVBoxLayout(mid); mv.setContentsMargins(0, 0, 0, 0); mv.setSpacing(12)
        # 미리보기 위: 새로 작성 · 저장 · 인쇄
        ab = QHBoxLayout(); ab.setContentsMargins(0, 0, 0, 0); ab.setSpacing(8); ab.addStretch()
        for text, fn, tip, name in (("새로 작성", self.new_doc, "입력칸 비우기 (Ctrl+N)", "HeadBtn"),
                                    ("저장", self.do_save, "인쇄하지 않고 작성이력에만 저장 (Ctrl+S)", "HeadBtn"),
                                    ("인쇄", self.do_print, "인쇄하고 작성이력에 저장 (Ctrl+P)", "HeadPrimary")):
            b = QPushButton(text); b.setObjectName(name); b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, f=fn: f())
            ab.addWidget(b)
        mv.addLayout(ab)
        mv.addWidget(pv_card, 1)
        att_card = card(self.attach_panel, "첨부파일 (A4로 같이 인쇄)", margins=(12, 8, 12, 8),
                        extra=[self.attach_panel.count_label])
        att_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)  # 내용 높이만큼만
        mv.addWidget(att_card)

        split = QSplitter(); split.setChildrenCollapsible(False); split.setHandleWidth(14)
        split.addWidget(mid)
        quick = self._build_quick()
        split.addWidget(card(quick, "작성이력", extra=[self.lbl_qcount]))
        split.setStretchFactor(0, 5); split.setStretchFactor(1, 4)
        split.setSizes([700, 560])
        self.write_split = split
        st = self.store.get("write_split")  # 미리보기 | 작성이력 경계 위치 기억
        if st:
            from PySide6.QtCore import QByteArray
            split.restoreState(QByteArray.fromBase64(st.encode()))
        h.addWidget(split, 1)
        return page

    # ---------- 작성 화면 오른쪽: 작성이력 빠른 검색 ----------
    def _build_quick(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(8)
        self.lbl_qcount = QLabel(""); self.lbl_qcount.setObjectName("Hint")
        self.ed_qsearch = QLineEdit(); self.ed_qsearch.setClearButtonEnabled(True)
        self.ed_qsearch.setPlaceholderText("지출처 · 내역 · 금액으로 검색  (↓ 키로 목록 이동)")
        self.ed_qsearch.textChanged.connect(self.filter_quick)
        # Enter 는 아무 동작 없이 검색칸에 머문다. ↓ 키만 목록으로 (이 칸에서만 동작)
        local_shortcut(Qt.Key.Key_Down, self.ed_qsearch, self._quick_focus_table)
        v.addWidget(self.ed_qsearch)
        self.qtbl = QTableWidget()
        self.qtbl.setColumnCount(4)
        self.qtbl.setHorizontalHeaderLabels(["날짜", "지출처", "금액", "내역"])
        self.qtbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.qtbl.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.qtbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.qtbl.verticalHeader().setVisible(False)
        self.qtbl.setShowGrid(False); self.qtbl.setWordWrap(False)
        self.qtbl.verticalHeader().setDefaultSectionSize(30)
        hh = self.qtbl.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)  # 열 머리는 가운데
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for c, wd in enumerate([96, 130, 92]):
            self.qtbl.setColumnWidth(c, wd)
        hh.setStretchLastSection(True)
        self.qtbl.cellDoubleClicked.connect(lambda r, c: self.quick_load())
        # 표에 커서가 있을 때만 동작 (예전엔 창 전체에서 걸려 검색칸 Enter·내역 Delete 가 오동작)
        local_shortcut(Qt.Key.Key_Return, self.qtbl, self.quick_load)
        local_shortcut(Qt.Key.Key_Enter, self.qtbl, self.quick_load)
        local_shortcut(Qt.Key.Key_Delete, self.qtbl, self.delete_selected)
        v.addWidget(self.qtbl, 1)
        h = QHBoxLayout()
        hint = QLabel("더블클릭·Enter로 불러오기"); hint.setObjectName("Hint")
        bd = QPushButton("삭제"); bd.setObjectName("SmallDanger"); bd.clicked.connect(self.delete_selected)
        bd.setToolTip("선택한 이력 삭제 (Delete 키, Ctrl/Shift로 여러 건 선택)")
        b = QPushButton("불러오기"); b.setObjectName("Small"); b.clicked.connect(self.quick_load)
        h.addWidget(hint, 1); h.addWidget(bd); h.addWidget(b)
        v.addLayout(h)
        return w

    def _match(self, r, q, qn):
        if not q:
            return True
        hay = f"{r['payee']}\n{r['detail']}\n{r['note']}\n{r['account']}".lower()
        return q in hay or bool(qn and qn in str(r["amount"]))

    def filter_quick(self):
        q = self.ed_qsearch.text().strip().lower()
        qn = re.sub(r"[^\d]", "", q)
        rows = [r for r in self.records if self._match(r, q, qn)]
        self.qtbl.setUpdatesEnabled(False)
        self.qtbl.setSortingEnabled(False)
        self.qtbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            tip = (f"<b>{r['date']} · {r['payee']} · {r['amount']:,}원</b><br>"
                   + (r["detail"] or "").replace("\n", "<br>")
                   + (f"<br>비고: {r['note']}" if r["note"] else ""))
            first = (r["detail"] or "").split("\n")[0]
            first = first.split(":", 1)[1].strip() if ":" in first else first
            if r.get("files"):
                first = "[첨부] " + first
            if r.get("attach"):
                first = "[이미지] " + first
            for c, val in enumerate([r["date"], r["payee"], f"{r['amount']:,}", first]):
                it = QTableWidgetItem(val)
                if c == 2:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r)
                it.setToolTip(tip)
                self.qtbl.setItem(i, c, it)
        self.qtbl.setUpdatesEnabled(True)
        self.lbl_qcount.setText(f"{len(rows):,}건")

    def _quick_focus_table(self):
        if self.qtbl.rowCount():
            self.qtbl.setFocus()
            self.qtbl.selectRow(0)

    def quick_load(self):
        r = self.qtbl.currentRow()
        it = self.qtbl.item(r, 0) if r >= 0 else None
        if not it:
            return
        rec = it.data(Qt.ItemDataRole.UserRole)
        self.load_record(rec)
        self.toast(f"불러왔습니다: {rec['payee'] or ''} {rec['amount']:,}원 — 금액·날짜를 확인하세요")

    def _build_basic(self):
        w = QWidget()
        g = QGridLayout(w); g.setContentsMargins(0, 0, 0, 0); g.setHorizontalSpacing(10); g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        # 종이에 써지는 순서대로: 科目 [계정과목 | 비고] → 支給處 → 一金 → 적요(내역) → 작성일 · 수령인
        # (작성일 · 수령인 칸은 _build_detail 에서 내역 아래 [기본 틀] 옆에 놓는다)
        self.de_date = QDateEdit(); self.de_date.setCalendarPopup(True); self.de_date.setDisplayFormat("yyyy-MM-dd")
        self.de_date.dateChanged.connect(self._date_changed)
        self.ed_name = QComboBox(); self.ed_name.setEditable(True)
        self.ed_name.currentTextChanged.connect(self.changed)
        deletable_combo(self.ed_name, self._name_deleted)
        self.chk_nodate = QCheckBox("년월일 인쇄 안 함")
        self.chk_nodate.toggled.connect(self._nodate_toggled)

        # 계정과목: 기본 목록 없이, 저장·인쇄한 계정과목이 쌓여서 목록에 나온다 (load_history 에서 채움)
        self.cb_account = QComboBox(); self.cb_account.setEditable(True)
        self.cb_account.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        deletable_combo(self.cb_account, self._account_deleted)  # 이름마다 ✕: 오타 등을 목록에서 빼기
        self.cb_account.currentTextChanged.connect(self.changed)
        self.ed_note = QLineEdit()
        self.ed_note.textChanged.connect(self.changed)
        g.addWidget(field_label("계정과목"), 1, 0); g.addWidget(self.cb_account, 1, 1)
        lb_note = field_label("비고"); lb_note.setContentsMargins(14, 0, 0, 0)  # 계정과목 상자와 띄우기
        g.addWidget(lb_note, 1, 2); g.addWidget(self.ed_note, 1, 3)

        self.ed_payee = QLineEdit(); self.ed_payee.setPlaceholderText("입력하면 이전 지출처가 자동완성됩니다")
        self.ed_payee.textChanged.connect(self.changed)
        self.payee_completer = QCompleter([]); self.payee_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.payee_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.payee_completer.activated.connect(self._payee_picked)
        self.ed_payee.setCompleter(self.payee_completer)
        g.addWidget(field_label("지출처"), 2, 0); g.addWidget(self.ed_payee, 2, 1, 1, 3)

        hb = QHBoxLayout(); hb.setSpacing(8)
        self.ed_amount = QLineEdit(); self.ed_amount.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ed_amount.setPlaceholderText("0")
        self.ed_amount.textEdited.connect(self._amount_edited)
        self.chk_vat = QCheckBox("VAT 포함"); self.chk_vat.clicked.connect(self._vat_clicked)
        self.ed_amount.setFixedWidth(140)  # 금액 칸은 짧게, 한글 금액은 오른쪽에
        self.lbl_kor = FitLabel(""); self.lbl_kor.setObjectName("Kor")  # 길면 글자를 줄여 다 보이게
        hb.addWidget(self.ed_amount); hb.addWidget(QLabel("원")); hb.addSpacing(6); hb.addWidget(self.chk_vat)
        hb.addSpacing(10); hb.addWidget(self.lbl_kor, 1)
        g.addWidget(field_label("금액"), 3, 0); g.addLayout(hb, 3, 1, 1, 3)

        hc = QHBoxLayout(); hc.setSpacing(8)
        self.ed_calc = CalcEdit(); self.ed_calc.setPlaceholderText("예) 380,000*4  또는  12000+8500  (줄을 바꿔 쓰면 더함)")
        self.ed_calc.textEdited.connect(self._calc)
        self.ed_calc.returnPressed.connect(self._calc_apply)
        self.lbl_calc = QLabel(""); self.lbl_calc.setObjectName("Hint")
        b = QPushButton("금액에 넣기"); b.setObjectName("Small"); b.clicked.connect(self._calc_apply)
        # 오른쪽 고정폭 칸: 위에 계산 결과, 아래 [금액에 넣기] → 결과가 길어져도 입력칸 크기는 그대로
        rc = QVBoxLayout(); rc.setContentsMargins(0, 0, 0, 0); rc.setSpacing(4)
        self.lbl_calc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc.addWidget(self.lbl_calc); rc.addWidget(b)
        rw = QWidget(); rw.setLayout(rc); rw.setFixedWidth(110)
        hc.addWidget(self.ed_calc, 1); hc.addWidget(rw)
        g.addWidget(field_label("계산기"), 5, 0); g.addLayout(hc, 5, 1, 1, 3)

        return w

    def _build_detail(self):
        w = QWidget()
        v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(8)
        self.ed_detail = QPlainTextEdit(); self.ed_detail.setMinimumHeight(120)
        self.ed_detail.setPlaceholderText("[기본 틀]을 누르면 '1) 내역 / 2) 금액 / 3) 첨부' 틀이 들어갑니다.")
        self.ed_detail.textChanged.connect(self._detail_changed)
        v.addWidget(self.ed_detail, 1)
        h = QHBoxLayout(); h.setSpacing(8)
        b = QPushButton("기본 틀"); b.setObjectName("Small"); b.clicked.connect(self._template)
        self.lbl_cnt = QLabel(""); self.lbl_cnt.setObjectName("Hint")
        self.sp_size = QSpinBox(); self.sp_size.setRange(8, 15); self.sp_size.setValue(11)
        self.sp_size.valueChanged.connect(self._detail_changed)  # 글자크기에 따라 들어가는 줄 수가 바뀜
        self.sp_size.setFixedWidth(64); self.sp_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sp_size.setToolTip("내역 글자크기 (8~15, 기본 11)")
        h.addWidget(b); h.addWidget(self.lbl_cnt, 1)
        h.addWidget(field_label("글자크기")); h.addWidget(self.sp_size)
        v.addLayout(h)
        # 종이에서 적요 아래 '20 년 월 일 / 수령인' 자리 순서대로
        h2 = QHBoxLayout(); h2.setSpacing(8)
        h2.addWidget(field_label("작성일")); h2.addWidget(self.de_date); h2.addWidget(self.chk_nodate)
        h2.addSpacing(12)
        h2.addWidget(field_label("수령인")); h2.addWidget(self.ed_name, 1)
        v.addLayout(h2)
        return w

    # ================================================================ 3. 설정 화면
    def _build_settings_page(self):
        from ui_coord import CoordPanel
        from ui_dialogs import DataPanel, SettingsPanel, UpdatePanel
        from ui_files import FilesPanel
        page = QWidget()
        h = QHBoxLayout(page); h.setContentsMargins(16, 14, 16, 10); h.setSpacing(14)
        self.side = QListWidget(); self.side.setObjectName("SideNav"); self.side.setFixedWidth(190)
        for text in ("좌표 설정", "프린터 · 기본값", "첨부파일 관리", "데이터", "업데이트"):
            QListWidgetItem(text, self.side)
        h.addWidget(self.side)
        self.set_stack = QStackedWidget()
        self.coord = CoordPanel(self)
        self.settings_panel = SettingsPanel(self)
        self.files_panel = FilesPanel(self)
        self.data_panel = DataPanel(self)
        self.update_panel = UpdatePanel(self)
        for wdg in (self.coord, self.settings_panel, self.files_panel, self.data_panel, self.update_panel):
            self.set_stack.addWidget(wdg)
        h.addWidget(self.set_stack, 1)
        self.side.currentRowChanged.connect(self._side_changed)
        self.side.setCurrentRow(0)
        return page

    def _side_changed(self, r):
        if self.set_stack.currentIndex() == 0 and r != 0:
            self.coord.confirm_leave()
        self.set_stack.setCurrentIndex(r)
        if self.set_stack.widget(r) is self.data_panel:
            self.data_panel.refresh()

    def open_files_settings(self):
        """작성 화면 [추가 ▾] > 첨부파일 관리… → 설정 > 첨부파일."""
        self.go(PAGE_SETTINGS)
        self.side.setCurrentRow(self.set_stack.indexOf(self.files_panel))

    def _printer_changed(self, _):
        self.store.set("printer", self.cb_printer.currentData())
        self._update_zero_btn()
        c = self.get_calib()
        self.toast(f"프린터: {self.calib_key()}  ·  영점 보정 {describe(c)}")

    # ---------- 프린터별 영점 보정 ----------
    def calib_key(self, name=None):
        """보정값을 저장하는 이름 = 실제 프린터 이름 ('Windows 기본'이면 지금의 기본 프린터)."""
        from PySide6.QtPrintSupport import QPrinterInfo
        return name or self.store.get("printer", "") or QPrinterInfo.defaultPrinterName() or "기본 프린터"

    def get_calib(self, key=None):
        key = key or self.calib_key()
        allc = self.store.get("calib", {}) or {}
        if key in allc:
            c = allc[key]
        elif not allc and not self.store.get("calib_migrated", False):
            # 예전 버전의 전체 보정값(프린터 구분 없음)은 처음 한 번만 지금 프린터로 옮긴다
            c = {"dx": self.store.get("offset_x", 0.0), "dy": self.store.get("offset_y", 0.0),
                 "sx": self.store.get("scale_x", 100.0), "sy": self.store.get("scale_y", 100.0)}
            self.store.set("calib_migrated", True)
            self.store.set("calib", {key: c})
        else:
            c = {}  # 처음 쓰는 프린터는 0점에서 시작
        return {"dx": float(c.get("dx", 0.0)), "dy": float(c.get("dy", 0.0)),
                "sx": float(c.get("sx", 100.0)), "sy": float(c.get("sy", 100.0))}

    def set_calib(self, key, c):
        allc = self.store.get("calib", {}) or {}
        allc[key] = {k: round(float(c.get(k, d)), 2) for k, d in (("dx", 0), ("dy", 0), ("sx", 100), ("sy", 100))}
        self.store.set("calib", allc)
        self._update_zero_btn()

    def _update_zero_btn(self):
        if hasattr(self, "btn_zero"):
            d = describe(self.get_calib())
            self.btn_zero.setText("영점조정" if d == "0점" else f"영점조정  {d}")

    def do_zero(self):
        from ui_zero import ZeroDialog
        ZeroDialog(self, self.calib_key()).exec()
        self._update_zero_btn()

    def settings_changed(self):
        self.cb_printer.blockSignals(True)
        self.cb_printer.setCurrentIndex(max(self.cb_printer.findData(self.store.get("printer", "")), 0))
        self.cb_printer.blockSignals(False)
        self._update_zero_btn()
        self.approval.set_owner_name(self.store.get("owner_name", ""))
        if not self.ed_name.currentText():
            self.ed_name.setCurrentText(self.store.get("default_name", ""))

    # ================================================================ 상태
    @property
    def lay(self):
        return LAYOUTS[self.cb_layout.currentData()]

    def amount(self) -> int:
        s = re.sub(r"[^\d]", "", self.ed_amount.text())
        return int(s) if s else 0

    def doc(self) -> dict:
        return {
            "date": pyd(self.de_date.date()),
            "print_date": not self.chk_nodate.isChecked(),
            "account": self.cb_account.currentText().strip(),
            "payee": self.ed_payee.text().strip(),
            "amount": self.amount(),
            "name": self.ed_name.currentText().strip(),
            "detail": self.ed_detail.toPlainText().rstrip(),
            "note": self.ed_note.text().strip(),  # 비고: 科目 줄 오른쪽 칸
            "detail_size": self.sp_size.value(),
            "approvals": self.approval.states(),
            "images": self.images,
        }

    def changed(self, *_):
        if not self._loading:
            self.timer.start()

    def adjust(self):
        return self.store.get(f"adjust_{self.lay.key}", {}) or {}

    def refresh_preview(self):
        self.preview.set(self.doc(), self.lay, self.adjust())

    def layout_changed(self):
        if hasattr(self, "coord"):
            self.coord.confirm_leave()
        self.store.set("layout", self.cb_layout.currentData())
        self.approval.owner_name = self.store.get("owner_name", "")
        self.approval.build(self.lay, pyd(self.de_date.date()))
        if hasattr(self, "coord") and self.pages.currentIndex() == PAGE_SETTINGS:
            self.coord.load()
        if hasattr(self, "ed_detail"):
            self._detail_changed()
        self.changed()

    def _nodate_toggled(self, on):
        self.approval.set_no_dates(on)
        self.changed()

    def _date_changed(self, q):
        # 작성일을 바꾸면 결재일도 모두 같은 날짜로 (이후 칸별로 직접 조정)
        self.approval.set_dates(pyd(q))
        self.approval._apply_auto()
        self.changed()

    def _approval_changed(self, what=None):
        if what == "reset_dates":
            self.approval.set_dates(pyd(self.de_date.date()))
        elif what == "owner":
            owner = self.store.get("owner_name", "")
            if self.approval.chk_owner.isChecked() and owner:
                self._prev_name = self.ed_name.currentText()
                self.ed_name.setCurrentText(owner)
            elif owner and self.ed_name.currentText() == owner:
                self.ed_name.setCurrentText(self._prev_name or self.store.get("default_name", ""))
        self.approval._apply_auto()
        self.changed()

    # ---------- 금액 / VAT / 내역 ----------
    def _set_amount_text(self, n):
        self.ed_amount.setText(f"{n:,}" if n else "")
        self.lbl_kor.setText(f"금 {numberstring(n)}원정" if n else "")
        self.lbl_kor.setToolTip(self.lbl_kor.text())  # 아주 큰 금액은 칸이 모자라 잘릴 수 있어 전체를 툴팁으로

    def _apply_amount_to_detail(self):
        """위의 금액·VAT 를 내역에 반영.

        - '금액 :' 줄이 있으면 그 줄만 바꾼다 (기본 틀의 빈 '2) 금액 : 원' 포함). 다른 'N원' 은 그대로.
        - '금액 :' 줄이 없으면 예전처럼 내역 안의 'N원' 을 바꾼다.
        - 둘 다 없으면 내역을 건드리지 않는다 (맨 아래에 새 줄을 붙이지 않음).
        반환: 바꿨으면 True
        """
        n = self.amount()
        if not n:
            return False
        t = self.ed_detail.toPlainText()
        new = f"{n:,}원" + ("(VAT 포함)" if self.chk_vat.isChecked() else "")
        if AMT_LINE_RE.search(t):
            t2 = AMT_LINE_RE.sub(lambda m: m.group(1) + new, t)
        elif AMT_VAT_RE.search(t):
            t2 = AMT_VAT_RE.sub(new, t)
        else:
            return False
        if t2 != t:
            self.ed_detail.setPlainText(t2)
        return True

    def _amount_edited(self, _):
        self._set_amount_text(self.amount())
        self._apply_amount_to_detail()
        self.changed()

    def _vat_clicked(self, on):
        if self.amount() and not self._apply_amount_to_detail():
            self.toast("내역에 금액 줄(예: 2) 금액 : …원)이 없어 'VAT 포함' 문구는 넣지 않았습니다.", 5000)

    def _template(self):
        n = self.amount()
        vat = "(VAT 포함)" if self.chk_vat.isChecked() else ""
        amt = f"{n:,}원{vat}" if n else "원"
        self.ed_detail.setPlainText(f"1) 내역 : \n\n2) 금액 : {amt}\n\n3) 첨부 : 관련문서 1매.  끝.")
        c = self.ed_detail.textCursor(); c.setPosition(len("1) 내역 : ")); self.ed_detail.setTextCursor(c)
        self.ed_detail.setFocus()

    # ---------- 이미지(엑셀 표 등) ----------
    def paste_image(self, quiet=False):
        from PySide6.QtWidgets import QApplication
        if self.pages.currentIndex() != PAGE_WRITE:
            return
        cb = QApplication.clipboard()
        md = cb.mimeData()
        img = cb.image() if md is not None and md.hasImage() else QImage()
        if img.isNull():
            msg = "클립보드에 이미지가 없습니다. 엑셀에서 표를 선택해 복사(Ctrl+C)한 뒤 미리보기를 클릭하고 Ctrl+V 하세요."
            if quiet:
                self.toast(msg, 6000)
            else:
                info(self, "이미지 붙여넣기", msg)
            return
        img = img.convertToFormat(QImage.Format.Format_ARGB32)
        # 처음 크기: 화면 해상도 기준 실제 크기, 내역 칸 너비를 넘으면 줄임. 위치: 내역 글 아래
        box = self.lay.fields["detail"]
        dpi_x = img.dotsPerMeterX() * 0.0254 or 96
        w = img.width() * 25.4 / (dpi_x if dpi_x > 30 else 96)
        h = w * img.height() / max(1, img.width())
        if w > box.w:
            h, w = h * box.w / w, box.w
        used, _ = self.detail_fit()
        A = render._Adj(self.adjust())
        first_h, line_h = render._line_metrics(render.detail_font(self.sp_size.value(), A), box)
        y = box.y0 + (used * line_h) / render.U + 1.0 if used else box.y0
        self.images.append({"img": img, "x": box.x0, "y": min(y, box.y1 - 5), "w": w, "h": h})
        self.preview.sel = len(self.images) - 1
        self.preview.setFocus()
        self.changed()
        self.toast("이미지를 올렸습니다. 드래그로 옮기고, 모서리(비율 유지)나 변 가운데(가로·세로 따로)로 크기를 바꾸세요. (Delete: 삭제)", 7000)

    def _images_payload(self):
        out = []
        for im in self.images:
            buf = QBuffer(); buf.open(QIODevice.OpenModeFlag.WriteOnly)
            im["img"].save(buf, "PNG")
            out.append({"png": bytes(buf.data()), **{k: im[k] for k in ("x", "y", "w", "h")}})
        return out

    def _set_images(self, items):
        self.images.clear()
        for it in items:
            img = QImage(); img.loadFromData(QByteArray(it["png"]), "PNG")
            if not img.isNull():
                self.images.append({"img": img, **{k: float(it[k]) for k in ("x", "y", "w", "h")}})
        self.preview.sel = -1

    def detail_fit(self, text=None):
        """(쓴 줄, 최대 줄) — 글자크기와 용지 칸 크기로 계산 (작게 하면 더 많이 들어감)."""
        t = self.ed_detail.toPlainText() if text is None else text
        return render.detail_fit(t, self.lay, self.sp_size.value(), self.adjust())

    def _detail_changed(self, *_):
        if not hasattr(self, "sp_size"):
            return
        used, cap = self.detail_fit()
        over = used > cap
        self.lbl_cnt.setText(f"{used}/{cap}줄" + ("  — 칸을 넘칩니다. 글자크기를 줄이세요" if over else ""))
        self.lbl_cnt.setObjectName("HintError" if over else "Hint")
        self.lbl_cnt.style().unpolish(self.lbl_cnt); self.lbl_cnt.style().polish(self.lbl_cnt)
        self.changed()

    def _calc(self, t):
        r = safe_eval(t)
        self.lbl_calc.setText(f"= {r:,.0f}" if isinstance(r, (int, float)) else "")

    def _calc_apply(self):
        r = safe_eval(self.ed_calc.text())
        if isinstance(r, (int, float)):
            self._set_amount_text(int(round(r)))
            self._amount_edited("")

    def _name_deleted(self, name):
        self.store.hide_name(name)
        self.toast(f"수령인 목록에서 '{name}'을(를) 뺐습니다. (작성이력은 그대로, 이 이름으로 다시 저장하면 목록에 다시 나옵니다)", 6000)

    def _account_deleted(self, account):
        self.store.hide_account(account)
        self.toast(f"계정과목 목록에서 '{account}'을(를) 뺐습니다. (작성이력은 그대로, 이 계정과목으로 다시 저장하면 목록에 다시 나옵니다)", 6000)

    def _payee_picked(self, text):
        rec = self.store.latest_for_payee(text)
        if not rec:
            return
        if not self.cb_account.currentText() and rec.get("account") in self.store.accounts():
            self.cb_account.setCurrentText(rec["account"])

    # ---------- 새 문서 / 불러오기 ----------
    def new_doc(self):
        self.go(PAGE_WRITE) if hasattr(self, "nav") and self.pages.currentIndex() != PAGE_WRITE else None
        self._loading = True
        today = date.today()
        self.de_date.blockSignals(True); self.de_date.setDate(qd(today)); self.de_date.blockSignals(False)
        self.chk_nodate.setChecked(False)
        self.cb_account.setCurrentText("")
        self.ed_note.clear()
        self.ed_payee.clear()
        self._set_amount_text(0)
        self.chk_vat.setChecked(False)
        self.ed_calc.clear()
        self.ed_name.setCurrentText(self.store.get("default_name", ""))
        self.ed_detail.clear()
        self.sp_size.setValue(11)
        self.images.clear(); self.preview.sel = -1
        self.attach_panel.set_items([])
        self.loaded_id = None
        self.approval.reset(today)
        self._loading = False
        self._detail_changed()
        self.ed_payee.setFocus()

    def load_record(self, rec):
        self.loaded_id = rec.get("id")  # 이 상태에서 [저장]하면 이 이력에 덮어쓴다
        self._loading = True
        today = date.today()  # 기존 엑셀처럼 날짜는 오늘로
        self.de_date.blockSignals(True); self.de_date.setDate(qd(today)); self.de_date.blockSignals(False)
        self.cb_account.setCurrentText(rec.get("account") or "")
        self.ed_payee.setText(rec.get("payee") or "")
        self._set_amount_text(int(rec.get("amount") or 0))
        self.ed_name.setCurrentText(rec.get("name") or self.store.get("default_name", ""))
        detail = (rec.get("detail") or "").rstrip()
        note = (rec.get("note") or "").strip()
        if (rec.get("source") or "직접작성") != "직접작성":
            # 엑셀에서 가져온 예전 비고(계좌 등)는 지금처럼 내역 맨 아래 줄로
            if note and note not in detail:
                detail = (detail + "\n" if detail else "") + note
            note = ""
        self.ed_note.setText(note)
        self.ed_detail.setPlainText(detail)
        self._set_images(self.store.images_of(rec))  # 저장해 둔 이미지(엑셀 표 등)도 같은 자리에
        self.attach_panel.set_items(self.store.files_of(rec))  # 첨부파일도 같이
        self.chk_vat.setChecked(bool(re.search(r"vat\s*포함", rec.get("detail") or "", re.I)))
        self.approval.reset(today)
        if self.store.get("auto_jeon_200k", False) and int(rec.get("amount") or 0) <= 200000:
            self.approval.set_jeon(2)
        self._loading = False
        self._detail_changed()
        self.ed_amount.setFocus()
        self.ed_amount.selectAll()

    # ================================================================ 작성이력
    def load_history(self):
        self.records = self.store.all()
        cur = self.ed_name.currentText()
        self.ed_name.blockSignals(True)
        self.ed_name.clear(); self.ed_name.addItems(self.store.names()); self.ed_name.setCurrentText(cur)
        self.ed_name.blockSignals(False)
        cur = self.cb_account.currentText()
        self.cb_account.blockSignals(True)
        self.cb_account.clear(); self.cb_account.addItems([""] + self.store.accounts()); self.cb_account.setCurrentText(cur)
        self.cb_account.blockSignals(False)
        self.payee_completer.model().setStringList(self.store.payees())
        self.filter_quick()
        self.lbl_db.setText(f"작성이력 {len(self.records):,}건  ·  {self.store.path}")

    def selected_all(self):
        out = []
        for idx in self.qtbl.selectionModel().selectedRows():
            it = self.qtbl.item(idx.row(), 0)
            if it:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def delete_selected(self):
        recs = self.selected_all()
        if not recs:
            info(self, "삭제", "삭제할 이력을 선택하세요.")
            return
        if len(recs) == 1:
            r = recs[0]
            msg = (f"선택한 이력을 삭제할까요?\n\n날짜 : {r['date']}\n지출처 : {r['payee']}\n"
                   f"금액 : {r['amount']:,}원\n\n{r['detail']}")
        else:
            msg = f"선택한 {len(recs):,}건을 삭제할까요?\n합계 {sum(r['amount'] for r in recs):,}원"
        if ask(self, "삭제 확인", msg, danger=True):
            for r in recs:
                self.store.delete(r["id"])
            self.load_history()
            self.toast(f"{len(recs):,}건을 삭제했습니다.")

    # ================================================================ 저장 / 인쇄
    def _validate(self, d) -> bool:
        if not d["detail"] and not d["payee"]:
            warn(self, "입력 확인", "지출처나 내역을 입력하세요.")
            return False
        used, cap = self.detail_fit(d["detail"])
        if used > cap:
            return ask(self, "입력 확인", f"내역이 {used}줄로, 지금 글자크기에서 들어가는 {cap}줄을 넘습니다.\n"
                       "글자크기를 줄이면 더 들어갑니다. 그래도 인쇄할까요?")
        return True

    def _record(self, d):
        return {k: d[k] for k in FIELDS}

    def do_save(self):
        d = self.doc()
        if not d["detail"] and not d["payee"]:
            warn(self, "저장", "지출처나 내역을 입력하세요.")
            return
        rec, imgs, files = self._record(d), self._images_payload(), self.attach_panel.payload()
        if self.loaded_id and self.store.update(self.loaded_id, rec, images=imgs, files=files):
            title, msg = "✓ 저장했습니다", "불러온 이력을 지금 내용으로 덮어썼습니다."
        else:
            added = self.store.add(rec, images=imgs, files=files)
            self.loaded_id = self.store.find_id(rec)
            title, msg = ("✓ 저장했습니다", "작성이력에 새로 저장했습니다.") if added else \
                         ("✓ 저장했습니다", "같은 내용의 이력에 덮어썼습니다.")
            if not added and self.loaded_id:
                self.store.update(self.loaded_id, rec, images=imgs, files=files)
        self.load_history()
        self.toast(f"{title} — {msg}")
        Notice(self, title, msg)

    def make_printer(self):
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        name = self.store.get("printer", "")
        if name:
            pr.setPrinterName(name)
        self.force_a5(pr)
        pr.setDocName("지출결의서")
        return pr

    @staticmethod
    def force_a5(pr):
        """용지를 A5 세로로 강제한다 (프린터 기본값이 A4여도). 인쇄 대화상자를 거친 뒤에도 다시 부른다."""
        from PySide6.QtCore import QSizeF
        if not pr.setPageSize(QPageSize(QPageSize.PageSizeId.A5)) or \
                pr.pageLayout().pageSize().id() != QPageSize.PageSizeId.A5:
            pr.setPageSize(QPageSize(QSizeF(148, 210), QPageSize.Unit.Millimeter, "A5",
                                     QPageSize.SizeMatchPolicy.FuzzyMatch))
        pr.setPageOrientation(QPageLayout.Orientation.Portrait)
        pr.setFullPage(True)
        pr.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    @staticmethod
    def open_printer_prefs(name):
        """Windows 의 '인쇄 기본 설정' 창 (용지 크기·맞춤 인쇄 등 드라이버 설정)."""
        import subprocess
        subprocess.Popen(["rundll32", "printui.dll,PrintUIEntry", "/e", "/n", name])

    def print_doc(self, d, guides=False, ask_dialog=None, files=None):
        pr = self.make_printer()
        ask_dialog = self.store.get("show_dialog", False) if ask_dialog is None else ask_dialog
        if ask_dialog:
            dlg = QPrintDialog(pr, self)
            dlg.setWindowTitle("인쇄")
            if dlg.exec() != QPrintDialog.DialogCode.Accepted:
                return False
            self.force_a5(pr)  # 대화상자에서 A4 로 바뀌었어도 A5 로
        prog = PrintProgress(self, pr.printerName() or "기본 프린터")
        prog.step(15, "인쇄 준비 중…")
        p = QPainter()
        if not p.begin(pr):
            prog.close()
            warn(self, "인쇄 실패", "프린터를 열 수 없습니다.\n설정 > 프린터 · 기본값에서 프린터를 확인하세요.")
            return False
        paper = pr.paperRect(QPrinter.Unit.Millimeter)  # 프린터 드라이버가 실제로 받아들인 용지
        if paper.width() > 160 or paper.height() > 222:
            prog.hide()
            name = pr.printerName() or "기본 프린터"
            if ask(self, "용지 크기 확인",
                   f"프린터({name})가 A5가 아닌 {paper.width():.0f}×{paper.height():.0f}mm 용지로 인쇄하려고 합니다.\n"
                   "프린터 설정에서 용지가 A4로 고정돼 있거나 '용지에 맞춤(확대/축소)'이 켜져 있으면 이렇게 됩니다.\n\n"
                   "[예] 인쇄를 취소하고 프린터의 '인쇄 기본 설정' 창을 엽니다. 용지 크기를 A5로 바꿔 주세요.\n"
                   "[아니요] 그대로 인쇄합니다."):
                pr.abort(); p.end(); prog.close()
                self.open_printer_prefs(name)
                return False
            prog.show()
        prog.step(45, "지출결의서를 그리는 중…")
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # fullPage 모드: 원점 = 용지 왼쪽 위 모서리. 0.01mm 단위로 맞춘다.
        k = pr.resolution() / 25.4 / render.U
        p.scale(k, k)
        c = self.get_calib(self.calib_key(pr.printerName()))  # 프린터별 영점·배율
        p.translate(c["dx"] * render.U, c["dy"] * render.U)
        p.scale(c["sx"] / 100.0, c["sy"] / 100.0)
        render.render(p, d, self.lay, guides=guides, adjust=self.adjust())
        prog.step(80 if not files else 50, "프린터로 보내는 중…")
        ok = p.end()
        if not ok:
            prog.close()
            warn(self, "인쇄 실패", "프린터로 보내지 못했습니다.\n프린터가 켜져 있는지, 연결 상태를 확인하세요.")
            return False
        if files:
            import attach
            apr = attach.make_printer(pr.printerName())  # 첨부는 항상 A4
            npages = max(1, sum(f["pages"] for f in files))
            done = [0]

            def step(i, n, name):
                done[0] += 1
                prog.step(50 + int(45 * done[0] / npages), f"첨부파일 인쇄 중… {name} ({done[0]}/{npages}쪽)")
            sent, err = attach.print_files(apr, files, self.store.file_data, step)
            if err:
                prog.close()
                warn(self, "첨부 인쇄 실패", f"지출결의서는 보냈지만 첨부파일을 인쇄하지 못했습니다.\n{err}")
                return True
            prog.done(f"지출결의서(A5) 1장 + 첨부 A4 {sent}쪽을 인쇄 대기열에 보냈습니다.")
            return True
        prog.done()
        return True

    def do_print(self):
        if self.pages.currentIndex() != PAGE_WRITE:
            self.go(PAGE_WRITE)
        d = self.doc()
        if not self._validate(d):
            return
        if self.print_doc(d, files=self.attach_panel.to_print()):
            added = self.store.add(self._record(d), images=self._images_payload(), files=self.attach_panel.payload())
            self.loaded_id = self.store.find_id(self._record(d))  # 이후 저장은 방금 인쇄한 이력에 덮어씀
            self.load_history()
            self.toast("인쇄했습니다." + (" 작성이력에 저장했습니다." if added else ""), 5000)

    def sample_doc(self):
        """입력 중인 내용, 비어 있으면 모든 칸이 채워진 견본."""
        d = self.doc()
        if not d["payee"] and not d["detail"]:
            n = len(self.lay.cols)
            t = date.today()
            d.update(account="복리후생비", payee="견본 지출처 주식회사", amount=1234500, name="홍길동",
                     detail="1) 내역 : 좌표 확인용 견본\n\n2) 금액 : 1,234,500원(VAT 포함)\n\n3) 첨부 : 관련문서 1매.  끝.",
                     approvals=render.compute_approvals(n, [t] * n, [False] * n, 2, False))
        return d

    def test_print(self):
        self.print_doc(self.sample_doc(), guides=True, ask_dialog=True)

    # ================================================================ 가져오기 / 내보내기
    def do_import(self, path=None):
        from ui_dialogs import ImportDialog
        dlg = ImportDialog(self.store, self, path=path if isinstance(path, str) else None)
        dlg.exec()
        self.load_history()
        if hasattr(self, "data_panel"):
            self.data_panel.refresh()

    def do_export(self):
        rows = self.store.all()
        p, _ = QFileDialog.getSaveFileName(self, "엑셀로 내보내기",
                                           f"지출결의서_작성이력_{date.today():%Y%m%d}.xlsx", "엑셀 파일 (*.xlsx)")
        if not p:
            return
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "작성이력"
        ws.append([FIELD_LABELS[f] for f in FIELDS] + ["출처"])
        for r in rows:
            ws.append([date.fromisoformat(r["date"]) if r["date"] else None, r["payee"], r["amount"],
                       r["name"], r["detail"], r["note"], r["account"], r.get("source")])
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="E8F0FE")
        for row in ws.iter_rows(min_row=2):
            row[0].number_format = "yyyy-mm-dd"; row[2].number_format = "#,##0"
            row[4].alignment = Alignment(wrap_text=True, vertical="top")
        for col, wd in zip("ABCDEFGH", [11, 22, 12, 8, 60, 30, 12, 30]):
            ws.column_dimensions[col].width = wd
        ws.freeze_panes = "A2"
        try:
            wb.save(p)
        except PermissionError:
            warn(self, "내보내기 실패", "파일이 다른 프로그램(엑셀 등)에서 열려 있습니다.\n닫은 뒤 다시 시도하세요.")
            return
        info(self, "내보내기", f"{len(rows):,}건을 저장했습니다.\n{p}")
