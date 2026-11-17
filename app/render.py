"""지출결의서 그리기 (미리보기·인쇄 공용).

좌표 단위: 1 = 0.01mm. 호출하는 쪽에서 painter 를 그 단위로 맞춰 둔다.
글자 크기는 실제 인쇄 pt 기준.
adjust: {항목: {"dx": mm, "dy": mm, "size": pt}} — [좌표 설정] 화면에서 저장한 칸별 보정값.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen

from layout import Box, FormLayout
from numkor import numberstring

U = 100.0                 # mm → 논리 단위
PT_MM = 25.4 / 72.0
FONT_FAMILY = "맑은 고딕"
BLUE = QColor(0, 0, 255)

# 조정 가능한 항목: 키 -> (화면 이름, 기본 글자크기 pt)
ITEMS = {
    "account": ("계정과목", 9.5),
    "payee": ("지출처", 9.5),
    "amount_kor": ("금액(한글)", 9.5),
    "amount_num": ("금액(숫자)", 9.5),
    "detail": ("내역(적요)", 9.5),
    "year": ("작성일 - 년", 9.5),
    "month": ("작성일 - 월", 9.5),
    "day": ("작성일 - 일", 9.5),
    "name": ("수령인", 9.5),
    "ap_month": ("결재일 - 월", 7.5),
    "ap_day": ("결재일 - 일", 7.5),
    "ap_jeon": ("전결 표시", 10.0),
}
# 내역 글자크기 스핀(8~15, 기존 엑셀 기준)을 실제 pt 로 바꾸는 비율
DETAIL_SCALE = 9.5 / 11.0


def R(b: Box) -> QRectF:
    return QRectF(b.x0 * U, b.y0 * U, b.w * U, b.h * U)


def font(pt: float, bold=False) -> QFont:
    f = QFont(FONT_FAMILY)
    f.setPixelSize(max(1, round(pt * PT_MM * U)))
    f.setBold(bold)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    f.setKerning(False)
    return f


def fit_font(text: str, pt: float, width: float, min_pt=6.0, bold=False) -> QFont:
    """한 줄 글자가 칸 너비를 넘으면 글자 크기를 줄인다."""
    while pt > min_pt:
        f = font(pt, bold)
        if QFontMetricsF(f).horizontalAdvance(text) <= width:
            return f
        pt -= 0.25
    return font(min_pt, bold)


def compute_approvals(n: int, dates, manual_slash, jeon_idx, owner_only):
    """결재칸별 표시 상태를 계산한다.

    - 마지막 칸(최종결재)은 항상 도장 칸: 사선·전결 없음, 날짜만 찍음
    - i 칸 전결: i 칸에 '전결'(날짜 없음), i+1 ~ 마지막 앞 칸은 사선
    - 최종결재자 본인 건: 마지막 칸 앞은 모두 사선
    - 그 외 칸은 사용자가 직접 '사선' 체크 가능
    """
    out = []
    for i in range(n):
        last = i == n - 1
        st = {"date": dates[i], "slash": False, "jeon": False}
        if last:
            pass
        elif owner_only:
            st["slash"] = True
        elif jeon_idx is not None and i == jeon_idx:
            st["jeon"] = True
        elif jeon_idx is not None and i > jeon_idx:
            st["slash"] = True
        elif manual_slash[i]:
            st["slash"] = True
        if st["slash"] or st["jeon"]:
            st["date"] = None
        out.append(st)
    return out


class _Adj:
    def __init__(self, adjust):
        self.a = adjust or {}

    def off(self, key):
        v = self.a.get(key, {})
        return float(v.get("dx", 0.0)), float(v.get("dy", 0.0))

    def size(self, key):
        v = self.a.get(key, {})
        return float(v.get("size") or ITEMS[key][1])

    def box(self, b: Box, key):
        dx, dy = self.off(key)
        return Box(b.x0 + dx, b.y0 + dy, b.x1 + dx, b.y1 + dy)


def _text(p, box: Box, text: str, f: QFont, align, color=Qt.GlobalColor.black):
    p.setFont(f)
    p.setPen(QColor(color))
    return p.drawText(R(box), int(align), text)


def render(p, doc: dict, lay: FormLayout, guides=False, adjust=None, highlight=None):
    """highlight: 좌표 설정 화면에서 선택한 항목 키 → 칸 테두리를 표시."""
    F = lay.fields
    A = _Adj(adjust)
    L, VC, C = Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter, Qt.AlignmentFlag.AlignCenter
    RA = Qt.AlignmentFlag.AlignRight

    if guides:
        p.setPen(QPen(QColor(160, 160, 160), 0.15 * U))
        for x0, y0, x1, y1 in lay.guide_lines:
            p.drawLine(QPointF(x0 * U, y0 * U), QPointF(x1 * U, y1 * U))
        for i in range(len(lay.cols)):
            p.drawLine(QPointF(lay.col_x[i] * U, lay.date[1] * U),
                       QPointF(lay.col_x[i + 1] * U, lay.date[0] * U))

    def simple(key, text, align, fit=True):
        if not text:
            return
        b = A.box(F[key], key)
        f = fit_font(text, A.size(key), b.w * U) if fit else font(A.size(key))
        _text(p, b, text, f, align)

    simple("account", doc.get("account"), L | VC)
    simple("payee", doc.get("payee"), L | VC)

    amt = int(doc.get("amount") or 0)
    if amt:
        kor = numberstring(amt)
        b = A.box(F["amount_kor"], "amount_kor")
        f = fit_font(kor, A.size("amount_kor"), b.w * U * 0.85)
        br = _text(p, b, kor, f, L | VC)
        # 위·변조 방지 채움선: 글자 끝 ~ 칸 끝(원整 앞)
        x_start, x_end = br.right() + 0.8 * U, b.x1 * U - 0.5 * U
        if x_end > x_start:
            p.setPen(QPen(Qt.GlobalColor.black, 0.2 * U))
            p.drawLine(QPointF(x_start, br.center().y()), QPointF(x_end, br.center().y()))
        simple("amount_num", f"{amt:,}", RA | VC)

    if doc.get("detail"):
        b = A.box(F["detail"], "detail")
        pt = float(doc.get("detail_size") or 11) * DETAIL_SCALE
        dpt = A.size("detail") - ITEMS["detail"][1]  # 좌표설정의 내역 크기 보정분
        p.setFont(font(pt + dpt))
        p.setPen(Qt.GlobalColor.black)
        p.drawText(R(b), int(L | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), doc["detail"])

    d = doc.get("date")
    if d is not None and doc.get("print_date", True):
        simple("year", d.strftime("%y"), C, fit=False)
        simple("month", str(d.month), C, fit=False)
        simple("day", str(d.day), C, fit=False)

    simple("name", doc.get("name"), C)
    if doc.get("note"):  # 예전 데이터 호환용 (현재 화면에는 비고란 없음)
        b = F["note"]
        _text(p, b, doc["note"], fit_font(doc["note"], 9.0, b.w * U), L | VC)

    # ---------- 결재란 ----------
    for i, st in enumerate(doc.get("approvals") or []):
        if i >= len(lay.cols):
            break
        x0, x1 = lay.col_x[i], lay.col_x[i + 1]
        w = x1 - x0
        if st.get("jeon"):
            b = A.box(Box(x0, lay.sign[0], x1, lay.sign[1]), "ap_jeon")
            _text(p, b, "전결", font(A.size("ap_jeon"), bold=True), C, BLUE)
        if st.get("slash"):
            pen = QPen(Qt.GlobalColor.black, 0.25 * U)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(QPointF(x0 * U, lay.sign[1] * U), QPointF(x1 * U, lay.sign[0] * U))
        dd = st.get("date")
        if dd is not None:
            y0, y1 = lay.date
            h = y1 - y0
            # 결재일 칸은 왼쪽아래→오른쪽위 대각선: 월은 왼쪽 위, 일은 오른쪽 아래
            mbox = A.box(Box(x0 + 0.04 * w, y0 + 0.02 * h, x0 + 0.52 * w, y0 + 0.58 * h), "ap_month")
            dbox = A.box(Box(x0 + 0.50 * w, y0 + 0.36 * h, x1 - 0.06 * w, y1 - 0.10 * h), "ap_day")
            _text(p, mbox, str(dd.month), font(A.size("ap_month")), C)
            _text(p, dbox, str(dd.day), font(A.size("ap_day")), C)

    if highlight:
        p.setPen(QPen(QColor(26, 115, 232), 0.3 * U, Qt.PenStyle.DashLine))
        p.setBrush(QColor(26, 115, 232, 30))
        for b in _boxes_for(highlight, lay, A):
            p.drawRect(R(b))
        p.setBrush(Qt.BrushStyle.NoBrush)


def _boxes_for(key, lay, A):
    if key in lay.fields:
        return [A.box(lay.fields[key], key)]
    out = []
    y0, y1 = lay.date
    h = y1 - y0
    for i in range(len(lay.cols)):
        x0, x1 = lay.col_x[i], lay.col_x[i + 1]
        w = x1 - x0
        if key == "ap_month":
            out.append(A.box(Box(x0 + 0.04 * w, y0 + 0.02 * h, x0 + 0.52 * w, y0 + 0.58 * h), key))
        elif key == "ap_day":
            out.append(A.box(Box(x0 + 0.50 * w, y0 + 0.36 * h, x1 - 0.06 * w, y1 - 0.10 * h), key))
        elif key == "ap_jeon":
            out.append(A.box(Box(x0, lay.sign[0], x1, lay.sign[1]), key))
    return out
