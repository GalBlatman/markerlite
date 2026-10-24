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
