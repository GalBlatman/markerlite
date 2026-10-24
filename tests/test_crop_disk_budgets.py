"""Crop limits bound the whole conversion before writing bytes."""

from pathlib import Path

import markerlite
from markerlite import raster_budget as budget

PDF = Path(__file__).parent / "fixtures" / "repro.pdf"


def test_crop_count_shared_by_images_figures_and_math(tmp_path, monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_MAX_CROPS", 1)
    md, info = markerlite.convert(
        PDF, tmp_path, do_flag_math=True, do_flag_figures=True, images=True
    )
    assert len(list(tmp_path.rglob("*.png"))) == 1
    assert any(
        e["limit"] == "document_crop_count" for e in info["stats"]["resource_limits"]
    )
    assert md.read_text() and info["stats"]["words"] > 0


def test_crop_bytes_checked_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(budget, "DOCUMENT_MAX_CROP_BYTES", 1)
    md, info = markerlite.convert(
        PDF, tmp_path, do_flag_math=True, do_flag_figures=True, images=True
    )
    assert not list(tmp_path.rglob("*.png"))
    assert any(
        e["limit"] == "document_crop_bytes" for e in info["stats"]["resource_limits"]
    )
    assert "resource limit" in markerlite.summarize(info["stats"])
    assert md.read_text()
