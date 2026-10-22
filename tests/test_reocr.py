"""Re-OCR of sideways scans whose text layer is fragments
(extraction._reocr_fragments), without needing Tesseract."""

import pathlib
import subprocess

import pymupdf

from markerlite import extraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "fixtures" / "sideways_scan.pdf"


def test_orientation_is_parsed_from_tesseract(monkeypatch, tmp_path):
    monkeypatch.setattr(extraction, "discover_tesseract", lambda: "tesseract")

    def fake_run(args, stdout, **kwargs):
        stdout.write(
            b"Page number: 0\nOrientation in degrees: 270\nRotate: 90\n"
            b"Orientation confidence: 12.5\nScript: Latin\n"
        )
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)
    doc = pymupdf.open(PDF)
    assert extraction.ocr_orientation(doc[0]) == (90, 12.5)


def test_unavailable_orientation_leaves_the_page(monkeypatch):
    monkeypatch.setattr(extraction, "discover_tesseract", lambda: None)
    doc = pymupdf.open(PDF)
    page, original = doc[0], doc[0].get_text()
    ocr, page = extraction._reocr_fragments(page, 0)
    assert ocr is None and page.get_text() == original


def test_turned_back_when_ocr_is_still_fragments(monkeypatch):
    doc = pymupdf.open(PDF)
    original = doc[0].get_text()
    width = doc[0].rect.width
    monkeypatch.setattr(
        extraction, "ocr_orientation", lambda page, cancel=None: (90, 10.0)
    )
    seen = {}

    def still_pieces(page, idx, dpi=300, cancel=None):
        seen["turned_width"] = page.rect.width
        return extraction.extract_page(page, idx, ocr_if_empty=False)

    monkeypatch.setattr(extraction, "_ocr_page", still_pieces)
    ocr, page = extraction._reocr_fragments(doc[0], 0)
    assert ocr is None
    assert seen["turned_width"] != width  # the attempt ran on a turned copy
    assert page.rect.width == width and page.get_text() == original  # untouched


def test_low_confidence_is_not_trusted(monkeypatch):
    monkeypatch.setattr(
        extraction, "ocr_orientation", lambda page, cancel=None: (90, 0.5)
    )
    monkeypatch.setattr(extraction, "_ocr_page", lambda *a, **k: 1 / 0)
    doc = pymupdf.open(PDF)
    ocr, _page = extraction._reocr_fragments(doc[0], 0)
    assert ocr is None


def test_fragment_measure_matches_stats():
    assert extraction.is_fragments(" ".join(["o 0 t I in C m ur b"] * 10))
    assert not extraction.is_fragments("Regression results for fixture adoption " * 10)
