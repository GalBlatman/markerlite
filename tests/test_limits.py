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


def _old_rule_zones(extents, page):
    """The pairing search before the limit commit, kept as the reference."""
    from markerlite.thresholds import (
        TABLE_RULE_EDGE_TOL,
        TABLE_RULE_MAX_HEIGHT_FRAC,
        TABLE_RULE_MIN_HEIGHT,
        TABLE_RULE_MIN_WIDTH_FRAC,
    )

    zones = []
    for y0, x0, x1 in extents:
        for y1, a, b in extents:
            if (
                TABLE_RULE_MIN_HEIGHT
                < y1 - y0
                < TABLE_RULE_MAX_HEIGHT_FRAC * page.height
                and x1 - x0 > TABLE_RULE_MIN_WIDTH_FRAC * page.width
                and abs(x0 - a) < TABLE_RULE_EDGE_TOL
                and abs(x1 - b) < TABLE_RULE_EDGE_TOL
                and any(
                    y0 < mid < y1
                    and abs(left - x0) < TABLE_RULE_EDGE_TOL
                    and abs(right - x1) < TABLE_RULE_EDGE_TOL
                    for mid, left, right in extents
                )
            ):
                zones.append((x0, y0, x1, y1))
    return zones


def test_rule_pairing_is_identical_to_the_cubic_search():
    import random

    from markerlite.tables import _rule_rows, _rule_zones

    rng = random.Random(20261002)
    page = Page(page_idx=0, width=612, height=792, blocks=[])
    for _trial in range(300):
        rules = []
        for _ in range(rng.randint(0, 40)):
            y = round(rng.uniform(60, 760), rng.choice((0, 1, 2)))
            x0 = rng.choice((72, 72.5, 74, 90, 300))
            x1 = rng.choice((540, 539, 536, 450, 320))
            for _ in range(rng.randint(1, 3)):
                rules.append(
                    (y, x0 + rng.choice((0, 1, 5)), x1 - rng.choice((0, 1, 5)))
                )
        extents = _rule_rows(rules, page)
        assert _rule_zones(rules, page) == _old_rule_zones(extents, page)


@pytest.mark.parametrize(
    "make,limit",
    [("rule_rows", "table_rule_rows"), ("rule_segments", "table_rules")],
)
def test_rule_limits_degrade_with_a_warning(made, make, limit):
    pdf = getattr(fixtures, make)(made)
    md, info = convert(pdf, made)
    [record] = _limits(info, limit)
    assert record["observed"] > record["cap"]
    assert f"{limit} p1" in summarize(info["stats"])
    assert "Ruled page" in md.read_text(encoding="utf-8")
