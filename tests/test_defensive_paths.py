import pymupdf

from markerlite.extraction import _ocr_page, _page_raster_covered
from markerlite.tables import _page_graphics


class BrokenRasterPage:
    rect = pymupdf.Rect(0, 0, 100, 100)

    def get_image_info(self):
        raise RuntimeError("broken image inventory")


class BrokenDrawingPage:
    def get_drawings(self):
        raise RuntimeError("broken drawing inventory")


class BrokenOcrPage:
    class Pixmap:
        def save(self, _path):
            pass

    def get_pixmap(self, dpi):
        assert dpi > 0
        return self.Pixmap()


def test_pdf_api_failures_degrade_without_losing_the_conversion():
    assert _page_raster_covered(BrokenRasterPage()) is False
    assert _page_graphics(BrokenDrawingPage()) == ([], [])


def test_ocr_process_failure_returns_none(monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        raise TimeoutError("tesseract timeout")

    monkeypatch.setattr("subprocess.run", fail)
    assert _ocr_page(BrokenOcrPage(), 2) is None
    assert "OCR failed on page 3" in capsys.readouterr().err
