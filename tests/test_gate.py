"""The table-confidence gate (markerlite/gate.py): each of its six tests
on its own, and the two ways a stopped grid is kept as prose."""

import pathlib
from unittest.mock import patch

import markerlite
from markerlite import gate

ROOT = pathlib.Path(__file__).resolve().parents[1]
NONE = {"h": [], "v": [], "curves": []}
REGION = (100.0, 100.0, 400.0, 300.0)
ROWS_X = [[100, 200, 300]] * 4  # three recurring column starts
GRID = (
    "<table><tr><th>a</th><th>b</th><th>c</th></tr>"
    "<tr><td>1</td><td>2</td><td>3</td></tr><tr><td>4</td><td>5</td><td>6</td></tr></table>"
)
LINES = ["a b c", "1 2 3", "4 5 6"]


def judge(graphics=NONE, rows_x=ROWS_X, lines=LINES, html=GRID):
    return gate.evaluate(graphics, REGION, rows_x, lines, html)


def test_a_clean_grid_passes():
    assert judge()["passed"]


def test_evidence_rules_or_recurring_columns():
    assert "evidence" in judge(rows_x=[[100], [150], [230]])["failed"]
    ruled = {"h": [(98, 100, 400), (302, 100, 400)], "v": [], "curves": []}
    assert judge(graphics=ruled, rows_x=[[100], [150], [230]])["passed"]


def test_shape_two_rows_and_two_columns():
    one_col = "<table><tr><th>a</th></tr><tr><td>1</td></tr><tr><td>4</td></tr></table>"
    assert "shape" in judge(html=one_col, lines=["a", "1", "4"])["failed"]
    two_rows = (
        "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    assert judge(html=two_rows, lines=["a b", "1 2"])["passed"]


def test_a_curve_marks_a_figure():
    assert (
        "figure"
        in judge(graphics={"h": [], "v": [], "curves": [(150, 150, 200, 200)]})[
            "failed"
        ]
    )


def test_prose_share():
    sentences = ["The method was tested.", "It worked well.", "a b c"]
    assert "prose" in judge(lines=sentences + ["1 2 3"])["failed"]


def test_token_identity():
    assert "identity" in judge(lines=LINES + ["7 8 9 10 11 12"])["failed"]


def test_continuation_rows():
    html = (
        "<table><tr><th>a</th><th>b</th></tr><tr><td>x</td><td>one</td></tr>"
        "<tr><td></td><td>two lines</td></tr><tr><td>y</td><td>three</td></tr></table>"
    )
    assert (
        "continuation"
        in judge(html=html, lines=["a b", "x one", "two lines", "y three"])["failed"]
    )


def test_stopped_find_tables_grid_is_marked_prose(tmp_path):
    pdf = ROOT / "tests" / "fixtures" / "caption_inside_table.pdf"
    with patch.object(gate, "GATE_MIN_ROWS", 99):
        md, info = markerlite.convert(pdf, tmp_path)
    text = md.read_text(encoding="utf-8")
    assert "reconstruction failed; text kept as prose" in text
    assert info["stats"]["tables_gated"][0]["failed"] == ["shape"]
    assert "5.16" in text and "Moral" in text


def test_stopped_proposal_stays_a_paragraph(tmp_path):
    pdf = ROOT / "tests" / "fixtures" / "all_text_wrapped.pdf"
    with patch.object(gate, "GATE_MIN_ROWS", 99):
        md, info = markerlite.convert(pdf, tmp_path)
    gated = info["stats"]["tables_gated"]
    assert any(g["path"] == "proposal" for g in gated)
    assert info["stats"]["proposals"] == 0


def test_every_grid_names_its_evidence(tmp_path):
    ruled = ROOT / "tests" / "fixtures" / "hard.pdf"  # one stroked box per cell
    md, _info = markerlite.convert(ruled, tmp_path)
    text = md.read_text(encoding="utf-8")
    assert "<!-- table p. 2: grid from ruling lines -->\n\n|" in text
    assert gate.evidence_kind({"hrules": 0, "vrules": 0}) == "text"
    assert gate.evidence_kind({"hrules": 0, "vrules": 0, "hrules_joined": 3}) == "rules"


def test_cell_edges_join_into_rules():
    edges = [
        (100.0, 72.0, 160.0),
        (100.0, 160.0, 206.0),
        (100.2, 206.0, 282.0),
        (140.0, 72.0, 100.0),
    ]
    assert gate._merge(edges) == [(100.0, 72.0, 282.0), (140.0, 72.0, 100.0)]
