"""The gold-table scorer, on a fixture: no third-party content needed."""

import hashlib
import json
import pathlib

import score_gold_tables as s

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = [
    ["Variable", "Hybrid A", "Business", "Hybrid B", "Charity"],
    ["Intent", "5.16", "4.91", "5.19", "5.40"],
    ["Cognitive", "4.64", "4.66", "4.43", "4.41"],
    ["Moral", "5.64", "5.35", "5.62", "5.89"],
]


def _items(tmp_path):
    pdf = ROOT / "tests" / "fixtures" / "caption_inside_table.pdf"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    merged = [row[:] for row in MATRIX]
    merged[1][1], merged[1][2] = "5.16 4.91", ""
    items = {
        "exact": {
            "id": "exact",
            "kind": "table",
            "doc": pdf.stem,
            "sha256": sha,
            "pages": [1],
            "matrix": MATRIX,
        },
        "merged": {
            "id": "merged",
            "kind": "table",
            "doc": pdf.stem,
            "sha256": sha,
            "pages": [1],
            "matrix": merged,
        },
        "control": {
            "id": "control",
            "kind": "control",
            "doc": pdf.stem,
            "sha256": sha,
            "pages": [1],
            "bbox": [72, 160, 540, 275],
        },
        "ambiguous": {
            "id": "ambiguous",
            "kind": "ambiguous",
            "doc": pdf.stem,
            "sha256": sha,
            "pages": [1],
            "bbox": [72, 160, 540, 275],
        },
    }
    for name, item in items.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(item), encoding="utf-8")


def test_scorer_outcomes_on_a_fixture(tmp_path):
    _items(tmp_path)
    out = tmp_path / "result.json"
    assert (
        s.main(
            [
                "--gold",
                str(tmp_path),
                "--corpus-root",
                str(ROOT / "tests" / "fixtures"),
                "--json",
                str(out),
            ]
        )
        == 0
    )
    res = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))}
    assert res["exact"]["outcome"] == "EXACT" and res["exact"]["cell_assoc"] == 1.0
    assert res["merged"]["outcome"] == "GRID-WRONG" and res["merged"]["adj_f1"] < 0.9
    assert res["control"]["outcome"] == "CLEAN"
    assert res["ambiguous"]["kind"] == "ambiguous"
    assert res["ambiguous"]["outcome"] == res["control"]["outcome"]


def test_segmented_table_is_scored_per_page():
    """A table whose columns continue on the next page: each page's columns
    against that page only; joining the halves is neither needed nor
    credited."""
    gold = {
        "id": "seg",
        "kind": "table",
        "doc": "d",
        "pages": [1, 2],
        "matrix": MATRIX,
        "segments": [{"page": 1, "cols": [0, 1, 2]}, {"page": 2, "cols": [3, 4]}],
    }
    left = [row[:3] for row in MATRIX]
    right = [row[3:] for row in MATRIX]
    regions = [
        {"page": 1, "kind": "grid", "bbox": [0, 0, 1, 1], "matrix": left},
        {"page": 2, "kind": "grid", "bbox": [0, 0, 1, 1], "matrix": right},
    ]
    pages = {
        1: " ".join(c for r in left for c in r),
        2: " ".join(c for r in right for c in r),
    }
    res = s.score_table(gold, regions, pages)
    assert res["outcome"] == "EXACT" and res["cell_assoc"] == 1.0
    assert [seg["outcome"] for seg in res["segments"]] == ["EXACT", "EXACT"]
    assert not any(k.startswith("_") for k in res)
    # the right half missing on page 2: prose there, the table is not exact
    res = s.score_table(gold, regions[:1], pages)
    assert res["outcome"] == "GRID-WRONG" and res["segments"][1]["outcome"] == "PROSE"


def test_normalisation_unifies_dashes_ligatures_and_bullets():
    assert s.norm("\u2212 0.5\u2013\ufb01rm \u25cfLaws") == "- 0.5-firm Laws"
    assert s.trim([["a", "", ""], ["", "", ""], ["b", "", "c"]]) == [
        ["a", ""],
        ["b", "c"],
    ]
