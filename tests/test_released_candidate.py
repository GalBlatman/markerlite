"""A failed table candidate released as text is not proposed again.

Released blocks were already a find_tables candidate whose reconstruction
failed and which showed no table evidence. Without the guard the
second-chance proposal pass rebuilt a partial grid from the same text
(Peng 2009 p. 2: PROSE became GRID-WRONG in the gold set).
"""

import pathlib
from unittest.mock import patch

import markerlite
from markerlite import tables

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "fixtures" / "caption_inside_table.pdf"


def test_released_candidate_is_not_proposed_again(tmp_path):
    real = tables.reconstruct_table_html
    calls = []

    def first_call_fails(lines):
        # detect_tables reconstructs first; make that one fail so the
        # candidate falls back, and leave the proposal pass the real thing.
        calls.append(1)
        return None if len(calls) == 1 else real(lines)

    with (
        patch.object(tables, "reconstruct_table_html", first_call_fails),
        patch.object(tables, "_looks_like_a_table", lambda *a: False),
    ):
        out, info = markerlite.convert(PDF, tmp_path)
    md = out.read_text(encoding="utf-8")
    assert info["stats"]["table_candidates_released"] == 1
    assert info["stats"]["tables"] == 0
    assert "reconstruction failed" not in md
    assert not any(line.startswith("|") for line in md.splitlines())
    for word in ("Intent", "Cognitive", "Moral", "5.16", "5.89"):
        assert word in md
