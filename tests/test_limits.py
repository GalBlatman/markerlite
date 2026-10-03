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


def test_code_with_implausibly_small_glyphs_keeps_its_text_unindented(made):
    md, info = convert(fixtures.code_tiny_glyphs(made), made)
    text = md.read_text(encoding="utf-8")
    assert _limits(info, "code_char_width")
    assert max(len(line) for line in text.splitlines()) < 40
    for word in ("def f(x):", "return x", "return 0"):
        assert word in text


def test_code_indent_is_cut_at_the_cap(made):
    md, info = convert(fixtures.code_deep_indent(made), made)
    [record] = _limits(info, "code_indent")
    assert record["observed"] > record["cap"] == 120
    longest = max(len(line) for line in md.read_text(encoding="utf-8").splitlines())
    assert longest <= 120 + len("    return 0")


def test_provenance_pieces_over_the_cap_warn_and_keep_exact_matching(made):
    md, info = convert(fixtures.provenance_pieces(made), made)
    text = md.read_text(encoding="utf-8")
    [record] = _limits(info, "provenance_pieces")
    assert record["observed"] > record["cap"] == 80
    assert text.count("Body text of page") == 100
    assert "Downloaded from" not in text  # every exact stamp line still dropped


def test_provenance_matcher_joins_pieces_below_the_cap_only():
    from markerlite.extraction import ProvenanceMatcher

    pieces = {"Downloaded from ", "fixture.sagepub.com", "at Library 1 on May 2, 2020"}
    joined = "Downloaded from fixture.sagepub.com at Library 1 on May 2, 2020"
    small = ProvenanceMatcher(pieces)
    assert not small.capped and small(joined) and small("fixture.sagepub.com")
    assert not small("Downloaded from the archive")  # not complete pieces
    many = ProvenanceMatcher(
        pieces | {f"at Library {n} on May 2, 2020" for n in range(100)}
    )
    assert many.capped
    assert many("fixture.sagepub.com")  # exact lines still match
    assert not many(joined)  # the run-together form is not attempted


def _old_clusters(rects):
    """The clustering loop before the limit commit, kept as the reference."""
    import pymupdf

    clusters = []
    for r in rects:
        placed = False
        for cl in clusters:
            merged = pymupdf.Rect(cl[0])
            for other in cl:
                merged |= other
            if merged.intersects(r + (-14, -14, 14, 14)):
                cl.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])
    return [[tuple(r) for r in cl] for cl in clusters]


def test_vector_clustering_is_identical_with_incremental_bounds():
    import random

    import pymupdf

    from markerlite.figures import _cluster_rects

    rng = random.Random(7)
    for _trial in range(300):
        rects = []
        for _ in range(rng.randint(0, 80)):
            x, y = rng.uniform(0, 600), rng.uniform(0, 780)
            w = rng.choice((0, 0, 1, 5, 30, 200))
            h = rng.choice((0, 0, 1, 5, 30, 200))
            rects.append(pymupdf.Rect(x, y, x + w, y + h))
        new = [[tuple(r) for r in cl] for cl in _cluster_rects(rects)]
        assert new == _old_clusters(rects)


def test_vector_drawings_over_the_cap_keep_text_and_caption(made):
    md, info = convert(fixtures.vector_drawings(made), made)
    text = md.read_text(encoding="utf-8")
    [record] = _limits(info, "vector_drawings")
    assert record["observed"] == 4500 and record["cap"] == 4000
    assert "A paragraph before the chart." in text
    assert "A paragraph after the chart." in text
    assert "<!-- figure: p. 1; caption: Figure 1. A dense chart. -->" in text


def test_oversized_image_is_located_without_decoding_and_exported_as_a_crop(made):
    import pymupdf

    pdf = fixtures.huge_image(made)
    md, info = convert(pdf, made / "img", images=True)
    text = md.read_text(encoding="utf-8")
    [record] = _limits(info, "image_pixels")
    assert record["observed"] == 400_000_000 > record["cap"]
    assert "A paragraph before the figure." in text
    assert "<!-- figure: p. 1; caption: Figure 1. A very large raster. -->" in text
    [png] = sorted((made / "img").rglob("*.png"))
    pix = pymupdf.Pixmap(str(png))
    assert pix.width <= 900 and pix.height <= 900  # 300 pt at 200 dpi, not 20000 px


@pytest.mark.skipif(
    __import__("sys").platform == "win32", reason="peak RSS via resource is POSIX"
)
def test_oversized_image_does_not_cost_its_decoded_size(made):
    import subprocess
    import sys

    pdf = fixtures.huge_image(made)
    script = (
        "import pathlib, resource, sys, tempfile\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from markerlite import convert\n"
        f"convert(pathlib.Path({str(pdf)!r}), pathlib.Path(tempfile.mkdtemp()), images=True)\n"
        "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)\n"
    )
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    peak_mb = int(out.stdout.strip().splitlines()[-1])
    assert peak_mb < 400, peak_mb  # decoded, the image alone is 400 MB
