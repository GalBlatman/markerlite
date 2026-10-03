"""Resource limits: a crafted PDF trips each limit, which degrades visibly
(warning + stats["resource_limits"] + text kept). Fixtures are generated at
test time by tests/generators/make_limit_fixtures.py; nothing third-party."""

from __future__ import annotations

import importlib.util
import math
import pathlib

import pytest

from markerlite import convert
from markerlite.model import Page
from markerlite.stats import content_words, summarize
from markerlite.tables import _projection_ok

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "make_limit_fixtures", ROOT / "tests" / "generators" / "make_limit_fixtures.py"
)
fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixtures)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    return tmp_path_factory.mktemp("limits")


def _limits(info, name):
    return [r for r in info["stats"].get("resource_limits", []) if r["limit"] == name]


def test_projection_rejects_non_finite_and_absurd_coordinates():
    page = Page(page_idx=0, width=612, height=792, blocks=[])
    ok_lines = [([("a", 72.0, 90.0), ("b", 650.0, 700.0)], 100.0, 110.0)]
    assert _projection_ok(ok_lines, page)[0]  # 88 pt off the page is normal
    for bad in (math.nan, math.inf, -math.inf, 1e19, -1e19):
        assert not _projection_ok([([("a", bad, 90.0)], 100.0, 110.0)], page)[0]
        assert not _projection_ok([([("a", 72.0, 90.0)], bad, 110.0)], page)[0]


def test_projection_fixture_degrades_to_prose_with_a_warning(made):
    pdf = fixtures.projection(made)
    md, info = convert(pdf, made)
    text = md.read_text(encoding="utf-8")
    [record] = _limits(info, "table_projection")
    assert record["page"] == 1 and record["action"] == "proposal kept as prose"
    assert "resource limit reached (table_projection p1)" in summarize(info["stats"])
    assert "|" not in text  # no grid built from the absurd coordinates
    for word in ("Group", "Alpha", "Beta", "3.7", "1.2X", "Delta", "1.1"):
        assert word in text
    assert content_words(text) == 18  # 3 heading words + 15 cells


def test_no_limit_record_on_an_ordinary_document(made):
    _md, info = convert(ROOT / "tests" / "fixtures" / "caption_inside_table.pdf", made)
    assert "resource_limits" not in info["stats"]
