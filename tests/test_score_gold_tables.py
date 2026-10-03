"""The gold-table scorer, on a fixture: no third-party content needed."""
import hashlib
import json
import pathlib

import score_gold_tables as s

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = [["Variable", "Hybrid A", "Business", "Hybrid B", "Charity"],
          ["Intent", "5.16", "4.91", "5.19", "5.40"],
          ["Cognitive", "4.64", "4.66", "4.43", "4.41"],
          ["Moral", "5.64", "5.35", "5.62", "5.89"]]


def _items(tmp_path):
    pdf = ROOT / "tests" / "fixtures" / "caption_inside_table.pdf"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    merged = [row[:] for row in MATRIX]
    merged[1][1], merged[1][2] = "5.16 4.91", ""
    items = {
        "exact": {"id": "exact", "kind": "table", "doc": pdf.stem, "sha256": sha, "pages": [1], "matrix": MATRIX},
        "merged": {"id": "merged", "kind": "table", "doc": pdf.stem, "sha256": sha, "pages": [1], "matrix": merged},
        "control": {"id": "control", "kind": "control", "doc": pdf.stem, "sha256": sha, "pages": [1],
                    "bbox": [72, 160, 540, 275]},
    }
    for name, item in items.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(item), encoding="utf-8")


def test_scorer_outcomes_on_a_fixture(tmp_path):
    _items(tmp_path)
    out = tmp_path / "result.json"
    assert s.main(["--gold", str(tmp_path), "--corpus-root", str(ROOT / "tests" / "fixtures"),
                   "--json", str(out)]) == 0
    res = {r["id"]: r for r in json.loads(out.read_text(encoding="utf-8"))}
    assert res["exact"]["outcome"] == "EXACT" and res["exact"]["cell_assoc"] == 1.0
    assert res["merged"]["outcome"] == "GRID-WRONG" and res["merged"]["adj_f1"] < 0.9
    assert res["control"]["outcome"] == "CLEAN"


def test_normalisation_unifies_dashes_ligatures_and_bullets():
    assert s.norm("\u2212 0.5\u2013\ufb01rm \u25cfLaws") == "- 0.5-firm Laws"
    assert s.trim([["a", "", ""], ["", "", ""], ["b", "", "c"]]) == [["a", ""], ["b", "c"]]
