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


def test_token_rejection_never_calls_vendor_even_after_member_preflight(
    tmp_path, monkeypatch
):
    dense = [([("x", 2, 3)] * (tables.TABLE_MAX_TOKENS + 1), 10, 20)]
    monkeypatch.setattr(tables, "_tokens_for_recon", lambda *a, **k: dense)
    monkeypatch.setattr(
        tables, "reconstruct_table_html", lambda *a: pytest.fail("vendor must not run")
    )
    md, info = markerlite.convert(
        Path(__file__).parent / "fixtures" / "hard.pdf", tmp_path, grids=True
    )
    assert md.read_text()
    assert any(e["limit"] == "table_tokens" for e in info["stats"]["resource_limits"])


def test_cell_bound_precedes_vendor_call(monkeypatch):
    from markerlite.model import Page

    monkeypatch.setattr(tables, "TABLE_MAX_RECON_CELLS", 1)
    monkeypatch.setattr(
        tables, "reconstruct_table_html", lambda *a: pytest.fail("vendor must not run")
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    with pytest.raises(tables._TableBudgetExceeded):
        tables._bounded_reconstruct([([("x", 1, 2)], 1, 2)], page)
    assert page.limit_events[0]["limit"] == "table_recon_cells"


def test_oversized_vendor_result_refused_before_owned_cell_scans(monkeypatch):
    from markerlite.model import Page

    monkeypatch.setattr(tables, "TABLE_MAX_CELLS", 16)
    monkeypatch.setattr(
        tables,
        "reconstruct_table_html",
        lambda *a: ("<table><tr>" + "<td>x</td>" * 20 + "</tr></table>", 1.0),
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    with pytest.raises(tables._TableBudgetExceeded):
        tables._bounded_reconstruct([([("x", 1, 2)], 1, 2)], page)
    assert page.limit_events[0]["observed"] == 17


def test_returned_cell_cap_precedes_owned_recovery_scans(tmp_path, monkeypatch):
    monkeypatch.setattr(tables, "TABLE_MAX_CELLS", 16)
    monkeypatch.setattr(
        tables,
        "reconstruct_table_html",
        lambda *a: ("<table><tr>" + "<td>x</td>" * 20 + "</tr></table>", 1.0),
    )
    monkeypatch.setattr(
        tables,
        "recover_ruled_header",
        lambda *a: pytest.fail("must not scan oversized cells"),
    )
    monkeypatch.setattr(
        tables,
        "recover_wrapped_lines",
        lambda *a: pytest.fail("must not scan oversized cells"),
    )
    md, info = markerlite.convert(
        Path(__file__).parent / "fixtures" / "hard.pdf", tmp_path, grids=True
    )
    assert md.read_text()
    assert any(e["limit"] == "table_cells" for e in info["stats"]["resource_limits"])


def test_finite_endpoints_with_overflowing_span_are_refused():
    from markerlite import tables

    lines = [([("x", -1e308, 1e308)], 0, 10)]
    assert tables._recon_cell_bound(lines) > tables.TABLE_MAX_RECON_CELLS
