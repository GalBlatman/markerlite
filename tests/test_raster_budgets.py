"""Raster guards are checked before allocation and keep source text."""

import math
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

import markerlite
from markerlite import extraction
from markerlite import raster_budget as budget
from markerlite.model import Page


@pytest.mark.parametrize("width,height", [(0.001, 1000000), (1000000, 0.001)])
def test_subpixel_side_cannot_zero_pixel_estimate(width, height):
    page = SimpleNamespace(rect=SimpleNamespace(width=width, height=height))
    dpi, pixels = extraction.ocr_dpi(page)
    assert pixels > 1_000_000
    w, h = budget.device_size(page.rect, dpi)
    assert w * h <= extraction.OCR_MAX_PIXELS


@pytest.mark.parametrize("value", [math.nan, math.inf, -1, 0])
def test_invalid_dimensions_rejected_before_render(value):
    page = SimpleNamespace(rect=SimpleNamespace(width=value, height=100))
    with pytest.raises(ValueError, match="raster dimensions"):
        extraction.ocr_dpi(page)


def test_crop_long_side_limit_is_checked_before_render(monkeypatch):
    monkeypatch.setattr(budget, "CROP_MAX_DEVICE_SIDE", 10)
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    pm = SimpleNamespace(get_pixmap=lambda **kw: pytest.fail("must not allocate"))
    assert budget.crop_pixmap(pm, page, pymupdf.Rect(0, 0, 1000000, 1), 200) is None
    assert page.limit_events[0]["limit"] == "crop_device_side"


def test_cumulative_decode_limit_records_visible_degradation(tmp_path, monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_DECODED_BYTES", 1)
    source = Path(__file__).parent / "fixtures" / "repro.pdf"
    md, info = markerlite.convert(source, tmp_path, images=True)
    limits = info["stats"].get("resource_limits", [])
    assert any(item["limit"] == "document_decoded_bytes" for item in limits)
    assert "resource limits reached" in markerlite.summarize(info["stats"])
    assert md.read_text() and info["stats"]["words"] > 0


def test_reservation_counts_repeated_decode_attempts(monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_DECODED_BYTES", 20)
    pm = SimpleNamespace(number=0)
    with budget.document_raster_budget() as state:
        assert budget.reserve_decode(pm, 10)
        assert budget.reserve_decode(pm, 10)
        assert not budget.reserve_decode(pm, 1)
        assert state["decoded"] == 20
        assert len(state["limits"]) == 1


def test_decode_budget_blocks_ocr_renderer_before_allocation(monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_DECODED_BYTES", 1)
    monkeypatch.setattr(extraction, "discover_tesseract", lambda: "tesseract")
    pm = SimpleNamespace(
        number=3,
        rect=SimpleNamespace(width=100, height=100),
        get_images=lambda **kw: [(1, 0, 100, 100)],
        get_image_info=lambda: [],
        get_pixmap=lambda **kw: pytest.fail("must not decode source"),
    )
    page = Page(page_idx=7, width=100, height=100, blocks=[])
    with budget.document_raster_budget() as state:
        assert extraction._ocr_page(pm, 7) is None
        budget.flush_limits(state, [page])
    assert page.limit_events[0]["page"] == 8
    assert page.limit_events[0]["limit"] == "document_decoded_bytes"


def test_decode_budget_blocks_crop_renderer_before_allocation(monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_DECODED_BYTES", 1)
    pm = SimpleNamespace(
        number=0,
        get_images=lambda **kw: [(1, 0, 100, 100)],
        get_image_info=lambda: [],
        get_pixmap=lambda **kw: pytest.fail("must not decode source"),
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    with budget.document_raster_budget() as state:
        assert budget.crop_pixmap(pm, page, pymupdf.Rect(0, 0, 100, 100), 200) is None
        budget.flush_limits(state, [page])
    assert page.limit_events[0]["limit"] == "document_decoded_bytes"


def test_lowered_ocr_limit_is_recorded_even_when_renderer_fails(monkeypatch):
    monkeypatch.setattr(extraction, "OCR_MAX_PIXELS", 100)
    monkeypatch.setattr(extraction, "discover_tesseract", lambda: "tesseract")

    def fail(**kwargs):
        raise RuntimeError("renderer rejected")

    pm = SimpleNamespace(
        number=0,
        rect=SimpleNamespace(width=100, height=100),
        get_images=lambda **kw: [],
        get_image_info=lambda: [],
        get_pixmap=fail,
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    with budget.document_raster_budget() as state:
        assert extraction._ocr_page(pm, 0) is None
        budget.flush_limits(state, [page])
    assert page.limit_events[0]["limit"] == "ocr_pixels"


def test_inline_images_are_charged_before_render(monkeypatch):
    doc = pymupdf.open()
    pm = doc.new_page(width=100, height=100)
    stream = doc.get_new_xref()
    doc.update_object(stream, "<<>>")
    doc.update_stream(
        stream,
        b"q 10 0 0 10 0 0 cm BI /W 2 /H 2 /BPC 8 /CS /G ID \x00\xff\x00\xff EI Q",
    )
    pm.set_contents(stream)
    assert pm.get_images(full=True) == []
    assert budget.image_bytes(pm) == 16
    monkeypatch.setattr(budget, "DOCUMENT_DECODED_BYTES", 1)
    with budget.document_raster_budget() as state:
        assert not budget.reserve_render(pm)
    assert state["decoded"] == 0
    assert state["limits"][0][1] == "document_decoded_bytes"
    doc.close()


def test_repeated_placements_are_charged_when_resource_list_is_smaller():
    pm = SimpleNamespace(
        get_images=lambda **kw: [(1, 0, 10, 10)],
        get_image_info=lambda: [dict(width=10, height=10, colorspace=3)] * 3,
    )
    assert budget.image_bytes(pm) == 1200
