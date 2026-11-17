"""여러 부서의 엑셀 작성이력을 읽어 들이는 기능.

- .xlsx / .xlsm : openpyxl
- .xls          : xlrd 가 설치돼 있으면 읽고, 없으면 xlsx 로 저장해 달라고 안내
- .csv          : utf-8 / cp949 자동 판별
열 이름이 달라도 아래 동의어로 자동 매칭하고, 화면에서 직접 바꿀 수 있다.
"""
import csv
import os
import re
from datetime import date, datetime, timedelta

SYNONYMS = {
    "date": ["날짜", "일자", "작성일", "작성일자", "지출일", "지출일자", "결의일", "결의일자", "date"],
    "payee": ["지출처", "거래처", "지급처", "업체", "업체명", "상호", "거래처명", "사용처"],
    "amount": ["금액", "지출금액", "합계", "합계금액", "지급액", "결의금액", "amount"],
    "name": ["성명", "작성자", "수령인", "담당자", "이름", "기안자"],
    "detail": ["내역", "적요", "내용", "지출내역", "사유", "용도"],
    "note": ["비고", "계좌", "계좌번호", "메모", "참고"],
    "account": ["계정과목", "계정", "과목"],
}


def _clean(s) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower()


def read_book(path):
    """{시트이름: [[셀값...], ...]} 반환 (최대 2만 행)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = {}
        for ws in wb.worksheets:
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i > 20000:
                    break
                rows.append(list(row))
            out[ws.title] = rows
        wb.close()
        return out
    if ext == ".xls":
        try:
            import xlrd
        except ImportError:
            raise RuntimeError(".xls(엑셀 97-2003) 파일은 엑셀에서 '다른 이름으로 저장 → .xlsx' 후 불러와 주세요.")
        wb = xlrd.open_workbook(path)
        out = {}
        for sh in wb.sheets():
            rows = []
            for r in range(min(sh.nrows, 20000)):
                vals = []
                for c in range(sh.ncols):
                    cell = sh.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        vals.append(xlrd.xldate.xldate_as_datetime(cell.value, wb.datemode))
                    else:
                        vals.append(cell.value)
                rows.append(vals)
            out[sh.name] = rows
        return out
    if ext == ".csv":
        for enc in ("utf-8-sig", "cp949"):
            try:
                with open(path, newline="", encoding=enc) as f:
                    return {"CSV": [row for row in csv.reader(f)]}
            except UnicodeDecodeError:
                continue
        raise RuntimeError("CSV 인코딩을 알 수 없습니다.")
    raise RuntimeError(f"지원하지 않는 파일 형식입니다: {ext}")


def detect(rows):
    """헤더 행 번호와 {필드: 열번호} 자동 추정."""
    best = (0, -1, {})
    for ri, row in enumerate(rows[:30]):
        mapping = {}
        for ci, v in enumerate(row):
            cv = _clean(v)
            if not cv:
                continue
            for f, words in SYNONYMS.items():
                if f in mapping:
                    continue
                if any(cv == _clean(w) for w in words):
                    mapping[f] = ci
                    break
        score = len(mapping)
        if score > best[0]:
            best = (score, ri, mapping)
    return best[1], best[2]


def parse_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):
        if 20000 < v < 80000:  # 엑셀 날짜 일련번호
            return (datetime(1899, 12, 30) + timedelta(days=float(v))).date()
        return None
    s = str(v).strip()
    m = re.match(r"^(\d{2,4})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        try:
            return date(*(int(x) for x in m.groups()))
        except ValueError:
            return None
    return None


def parse_amount(v):
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(round(v))
    s = re.sub(r"[^\d\-.]", "", str(v))
    try:
        return int(round(float(s))) if s not in ("", "-", ".") else 0
    except ValueError:
        return 0


def extract(rows, header_row, mapping):
    """매핑대로 레코드 목록과 건너뛴 행 수를 반환."""
    out, bad = [], 0
    for row in rows[header_row + 1:]:
        get = lambda f: (row[mapping[f]] if f in mapping and mapping[f] is not None
                         and mapping[f] < len(row) else None)
        if all(c in (None, "") for c in row):
            continue
        d = parse_date(get("date"))
        amt = parse_amount(get("amount"))
        payee = get("payee")
        detail = get("detail")
        if d is None or (not amt and not payee and not detail):
            bad += 1
            continue
        out.append({
            "date": d, "payee": payee or "", "amount": amt, "name": get("name") or "",
            "detail": detail or "", "note": get("note") or "", "account": get("account") or "",
        })
    return out, bad
