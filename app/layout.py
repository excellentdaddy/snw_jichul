"""지출결의서 용지 좌표 정의.

모든 좌표는 '지출결의서.pdf' 스캔(200dpi 렌더링)의 픽셀 위치에서 측정하고,
아래 변환식으로 실제 A5 용지 위의 mm 좌표로 바꾼다.

  용지 x(mm) = MX_A * px + MX_B
  용지 y(mm) = MY_A * py + MY_B

[2차 확정 2026-11-17] 첫 실제 출력물(Canon MB2700, 5칸 용지)을 스캔해 양식을 빼고
인쇄된 글자 11곳의 위치를 측정한 뒤 다시 맞춤 (잔차 x 0.49mm, y 0.38mm 이내).
배율이 0.127mm/px(=200dpi)로 나와 스캔 PDF 가 실물 크기임이 확인됨.
[3차 확정 2026-11-17] 양식 선을 함께 찍은 시험 인쇄(5칸)를 스캔해 비교:
  - 옅은 안내선이 실제 양식 선보다 좌·우 테두리 모두 약 0.8mm 오른쪽
  - 인쇄 글자 9곳도 평균 1.0mm 오른쪽, 세로는 ±0.2mm 이내, 배율 오차 없음
  → 가로 기준만 0.9mm 왼쪽으로 옮김.
이후 미세 조정은 프로그램의 [좌표 설정] 화면에서 칸별로 한다.
"""
from dataclasses import dataclass, field

MX_A, MX_B = 0.12682, -131.799  # 3차: 시험인쇄 스캔 결과 가로 +0.9mm 밀림 보정 (-130.899 → -131.799)
MY_A, MY_B = 0.12751, -0.612

PAPER_W, PAPER_H = 148.0, 210.0  # A5 세로


def mx(px: float) -> float:
    return MX_A * px + MX_B


def my(py: float) -> float:
    return MY_A * py + MY_B


@dataclass
class Box:
    """용지 위 사각형 (mm)."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @classmethod
    def px(cls, x0, y0, x1, y1, dx=0.0, dy=0.0):
        return cls(mx(x0 + dx), my(y0 + dy), mx(x1 + dx), my(y1 + dy))


@dataclass
class FormLayout:
    key: str
    title: str
    cols: list                 # 결재란 직급명 (왼쪽→오른쪽, 마지막 칸 = 최종결재)
    jeon_cols: list            # 전결 가능한 칸 인덱스
    fields: dict               # 이름 -> Box
    col_x: list                # 결재칸 세로선 x (mm), len = 칸수+1
    header: tuple              # 결재 직급명 행 (y0, y1)
    sign: tuple                # 서명(도장) 영역 (y0, y1)
    date: tuple                # 결재일 행 (y0, y1)
    guide_lines: list = field(default_factory=list)  # 시험인쇄용 양식 선 [(x0,y0,x1,y1) mm]
    background: str = ""       # 배경 이미지 파일명 (assets)
    bg_box: Box = None         # 배경 이미지가 놓일 용지 위 위치


def _build(key, title, cols, jeon_cols, col_px, dx=0.0, dy=0.0, bg="", enabled=True):
    """5칸 양식에서 측정한 픽셀 좌표를 기준으로 레이아웃을 만든다.

    6칸 양식은 결재란을 뺀 나머지 칸이 같은 위치이므로 dx, dy(스캔상 위치 차이)만 준다.
    """
    B = lambda *a: Box.px(*a, dx=dx, dy=dy)
    fields = {
        # 科目 칸 (왼쪽 칸)
        "account": B(1349.5, 265, 1688, 336),
        # 支給處
        "payee": B(1349.5, 336, 2042, 407),
        # 一金 ~ 원整 앞까지 (한글 금액 + 채움선)
        "amount_kor": B(1349.5, 407, 1692, 478),
        # (₩ 와 ) 사이, 오른쪽 정렬
        "amount_num": B(1830, 407, 2004, 478),
        # 적요 아래 본문 (20 년 월 일 줄 위까지)
        "detail": B(1222, 676, 2042, 1052),
        # "20 __ 년 __ 월 __ 일"
        "year": B(1661, 1060, 1724, 1095),
        "month": B(1746, 1060, 1824, 1095),
        "day": B(1848, 1060, 1927, 1095),
        # 수령인 ______ (인)
        "name": B(1697, 1148, 1903, 1183),
        # 비고(계좌 등): 날짜 줄과 수령인 줄 사이
        "note": B(1215, 1096, 2042, 1147),
    }
    col_x = [mx(x + dx) for x in col_px]
    hy = lambda y: my(y + dy)
    L, R, T, Bm = 1177.5, 2052.5, 265, 1439
    lines = [
        (L, T, R, T), (L, Bm, R, Bm), (L, T, L, Bm), (R, T, R, Bm),
        (L, 336, R, 336), (L, 407, R, 407), (L, 478, R, 478),
        # 科目·支給處·一金 이름표 칸 선 (1318.5) — 아래 '출납' 칸 선(1340)과 다른 선이다
        (1318.5, T, 1318.5, 478), (1694, T, 1694, 336),
        # 출납 칸
        (1340, 1243, 1340, Bm), (L, 1243, 1340, 1243), (L, 1292.5, 1340, 1292.5),
        (col_px[0] - 42.5, 1243, R, 1243), (col_px[0], 1292.5, R, 1292.5),
        (col_px[0], 1395, R, 1395), (col_px[0] - 42.5, 1243, col_px[0] - 42.5, Bm),
    ] + [(x, 1243, x, Bm) for x in col_px]
    guide = [(mx(a + dx), my(b + dy), mx(c + dx), my(d + dy)) for a, b, c, d in lines]
    lay = FormLayout(
        key=key, title=title, cols=cols, jeon_cols=jeon_cols, fields=fields,
        col_x=col_x, header=(hy(1243), hy(1292.5)), sign=(hy(1292.5), hy(1395)),
        date=(hy(1395), hy(1439)), guide_lines=guide, background=bg,
        bg_box=Box.px(1150, 150, 2080, 1500, dx=dx, dy=dy),  # 배경도 양식과 같이 옮긴다
    )
    lay.enabled = enabled
    return lay


# 5칸 (기존 용지): 담당 | 팀장 | 부서장 | 이사 | 대표이사
LAYOUT_5 = _build(
    "5", "5칸 (기존 용지)",
    ["담당", "팀장", "부서장", "이사", "대표이사"], [2, 3],
    [1539.5, 1642, 1744.5, 1847.5, 1950.5, 2052],
    bg="form5.png",
)

# 6칸 (신규 용지): 담당 | 팀장 | 부서장 | 이사 | 사장 | 회장
# 스캔 왼쪽 양식에서 측정 (결재칸 세로선 474.5~1027px). 결재란 외 영역은 5칸과 같은 모양.
# [2026-11-17] 6칸 시험 인쇄 스캔: 안내선이 실제 양식보다 테두리 4변·결재란 세로선 8개·가로선 모두
#   왼쪽 약 2.0mm, 위쪽 약 2.05mm → 6칸 용지는 양식이 종이 위에서 그만큼 오른쪽·아래에 인쇄돼 있음.
#   dx/dy(기준 스캔 px) = 2.0/MX_A, 2.05/MY_A
LAYOUT_6 = _build(
    "6", "6칸 (신규 용지)",
    ["담당", "팀장", "부서장", "이사", "사장", "회장"], [2, 3, 4],
    [1497.5, 1589, 1681, 1773, 1865, 1958, 2050],
    dx=2.0 / MX_A, dy=2.05 / MY_A,
    bg="form6.png", enabled=True,
)

LAYOUTS = {"5": LAYOUT_5, "6": LAYOUT_6}
