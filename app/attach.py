"""첨부파일(PDF·그림) 읽기와 인쇄.

지출결의서(A5 양식) 인쇄가 끝난 뒤, 같은 프린터에 별도 인쇄 작업으로 보낸다.
첨부 용지는 항상 A4 세로, 쪽마다 용지에 맞춰 축소·회전한다.
"""
import os

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter

PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
SUPPORTED = PDF_EXT | IMG_EXT
FILTER = "PDF · 그림 파일 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif)"
RENDER_DPI = 300  # PDF 쪽을 그림으로 바꿀 때 해상도 (글자가 선명한 정도)



class _Pdf:
    """QPdfDocument 는 읽는 동안 버퍼가 살아 있어야 해서 함께 들고 다닌다."""

    def __init__(self, data: bytes):
        from PySide6.QtPdf import QPdfDocument
        self.buf = QBuffer()
        self.buf.setData(QByteArray(data))
        self.buf.open(QIODevice.OpenModeFlag.ReadOnly)
        self.doc = QPdfDocument()
        self.doc.load(self.buf)
        if self.doc.status() != QPdfDocument.Status.Ready:
            raise ValueError("PDF 파일을 읽을 수 없습니다 (암호가 걸렸거나 손상된 파일).")

    def pages(self):
        return self.doc.pageCount()

    def size_pt(self, i) -> QSizeF:
        return self.doc.pagePointSize(i)

    def render(self, i, dpi=RENDER_DPI) -> QImage:
        s = self.size_pt(i)
        px = QSize(max(1, int(s.width() / 72 * dpi)), max(1, int(s.height() / 72 * dpi)))
        img = self.doc.render(i, px)
        # 투명 배경은 흰색으로
        out = QImage(img.size(), QImage.Format.Format_RGB32)
        out.fill(0xFFFFFFFF)
        p = QPainter(out); p.drawImage(0, 0, img); p.end()
        return out


def read_file(path):
    """(이름, 확장자, 데이터, 쪽수). 지원하지 않거나 못 읽으면 ValueError."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED:
        raise ValueError("PDF 와 그림 파일(PNG·JPG·BMP·GIF)만 첨부할 수 있습니다.\n"
                         "엑셀·한글·워드 파일은 [PDF로 저장]한 뒤 첨부하세요.")
    with open(path, "rb") as f:
        data = f.read()
    return os.path.splitext(os.path.basename(path))[0], ext, data, count_pages(ext, data)


def count_pages(ext, data) -> int:
    if ext in PDF_EXT:
        return _Pdf(data).pages()
    img = QImage()
    if not img.loadFromData(QByteArray(data)):
        raise ValueError("그림 파일을 읽을 수 없습니다.")
    return 1


def page_images(ext, data, dpi=RENDER_DPI):
    """쪽마다 QImage 를 하나씩 돌려준다 (큰 PDF 도 한 쪽씩만 메모리에)."""
    if ext in PDF_EXT:
        pdf = _Pdf(data)
        for i in range(pdf.pages()):
            yield pdf.render(i, dpi)
    else:
        img = QImage()
        img.loadFromData(QByteArray(data))
        yield img


def thumbnail(ext, data, height=160) -> QImage:
    """첫 쪽 미리보기."""
    if ext in PDF_EXT:
        pdf = _Pdf(data)
        s = pdf.size_pt(0)
        img = pdf.render(0, dpi=max(20, int(height / max(s.height(), 1) * 72)))
    else:
        img = QImage(); img.loadFromData(QByteArray(data))
    return img.scaledToHeight(height) if not img.isNull() else img


def make_printer(printer_name):
    """첨부 인쇄용: 항상 A4 세로."""
    pr = QPrinter(QPrinter.PrinterMode.HighResolution)
    if printer_name:
        pr.setPrinterName(printer_name)
    if not pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4)) or \
            pr.pageLayout().pageSize().id() != QPageSize.PageSizeId.A4:
        pr.setPageSize(QPageSize(QSizeF(210, 297), QPageSize.Unit.Millimeter, "A4",
                                 QPageSize.SizeMatchPolicy.FuzzyMatch))
    pr.setPageOrientation(QPageLayout.Orientation.Portrait)
    pr.setFullPage(False)  # 프린터가 못 찍는 가장자리는 피해서
    pr.setDocName("지출결의서 첨부")
    return pr


def print_files(pr: QPrinter, files, load, progress=None):
    """files: [{"hash","name","ext"}], load(hash) → bytes. progress(i, n, 이름) 를 쪽마다 부른다.
    성공하면 (보낸 쪽 수, None), 실패하면 (0, 오류 문구)."""
    total = 0
    p = QPainter()
    if not p.begin(pr):
        return 0, "프린터를 열 수 없습니다."
    try:
        first = True
        for fi, f in enumerate(files):
            data = load(f["hash"])
            if not data:
                continue
            for img in page_images(f["ext"], data):
                if img.isNull():
                    continue
                if not first:
                    pr.newPage()
                first = False
                total += 1
                if progress:
                    progress(fi, len(files), f["name"])
                area = QRectF(pr.pageLayout().paintRectPixels(pr.resolution()))
                area.moveTo(0, 0)
                _draw_fit(p, img, area)
    finally:
        p.end()
    return total, None


def _draw_fit(p: QPainter, img: QImage, area: QRectF):
    """용지(세로)에 맞춰 축소해 가운데 정렬. 가로로 긴 쪽은 90° 돌려 더 크게."""
    rotate = img.width() > img.height() * 1.05 and area.height() > area.width()
    w, h = (img.height(), img.width()) if rotate else (img.width(), img.height())
    k = min(area.width() / w, area.height() / h)
    tw, th = w * k, h * k
    x = area.x() + (area.width() - tw) / 2
    y = area.y() + (area.height() - th) / 2
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if rotate:
        p.translate(x + tw, y)
        p.rotate(90)
        p.drawImage(QRectF(0, 0, th, tw), img)
    else:
        p.drawImage(QRectF(x, y, tw, th), img)
    p.restore()
