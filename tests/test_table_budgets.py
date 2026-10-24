"""Table budgets reject work before reconstruction or word-by-cell scans."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import markerlite
from markerlite import tables


@pytest.mark.parametrize(
    "constant,limit",
    [
        ("TABLE_MAX_CELLS", "table_cells"),
        ("TABLE_MAX_TOKENS", "table_tokens"),
        ("TABLE_MAX_COORDINATE_SPAN", "table_coordinate_span"),
    ],
)
def test_low_budget_keeps_source_prose(tmp_path, monkeypatch, constant, limit):
    monkeypatch.setattr(tables, constant, 1)
    source = Path(__file__).parent / "fixtures" / "hard.pdf"
    md, info = markerlite.convert(source, tmp_path, grids=True)
    assert any(r["limit"] == limit for r in info["stats"].get("resource_limits", []))
    assert "resource limit" in markerlite.summarize(info["stats"])
    assert info["stats"]["words"] > 0 and md.read_text()


def test_geometric_scan_guard_precedes_cell_allocation(monkeypatch):
    monkeypatch.setattr(tables, "TABLE_MAX_CELLS", 2)
    tbl = SimpleNamespace(rows=[SimpleNamespace(cells=[None] * 3)])
    with pytest.raises(ValueError, match="budget"):
        tables._grid_from_members(tbl, [])


def test_absolute_span_guard_is_independent_of_enormous_page():
    line = SimpleNamespace(spans=[SimpleNamespace(text="kept", bbox=(0, 0, 20000, 10))])
    member = SimpleNamespace(lines=[line])
    assert not tables._table_work_ok([member])
