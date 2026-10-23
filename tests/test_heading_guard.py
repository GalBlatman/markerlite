"""Heading-density guard: a page where more than a third of the lines
became headings is judged again by weight and shape only."""

import pathlib
from unittest.mock import patch

import markerlite
from markerlite import classification

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "fixtures" / "mixed_body_sizes.pdf"


def _headings(md):
    return [
        ln for ln in md.read_text(encoding="utf-8").splitlines() if ln.startswith("#")
    ]


def test_guard_alone_catches_size_only_headings(tmp_path):
    # Without per-page body sizes the 12 pt manuscript lines are all
    # "bigger" than the 9.5 pt mode; the guard must catch both pages.
    def document_size_only(pages, doc_body):
        return [doc_body] * len(pages)

    with patch.object(classification, "local_body_sizes", document_size_only):
        md, info = markerlite.convert(PDF, tmp_path, grids=True)
    assert info["stats"]["heading_guard_pages"] == [1, 2]
    assert _headings(md) == ["## Introduction", "## Response to the reviewers"]
    assert any(
        "size-only headings" in w for w in markerlite.stat_warnings(info["stats"])
    )


def test_guard_is_quiet_on_an_ordinary_document(tmp_path):
    md, info = markerlite.convert(PDF, tmp_path, grids=True)
    assert "heading_guard_pages" not in info["stats"]


def test_short_pages_are_not_judged(tmp_path):
    title = ROOT / "tests" / "fixtures" / "all_text_wrapped.pdf"
    md, info = markerlite.convert(title, tmp_path, grids=True)
    assert "heading_guard_pages" not in info["stats"]
