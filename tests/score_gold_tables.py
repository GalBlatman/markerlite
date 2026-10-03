"""Score the converter against the gold tables set.

The gold set is third-party content and is never committed: it lives in the
git-ignored ``tests/gold-tables/`` beside ``tests/real/``. Each JSON file there
describes one item:

    {"id": "york2018-t1", "kind": "table" | "control",
     "doc": "york2018", "sha256": "<source pdf sha256>",
     "pages": [12], "layout": ["ruled", "wrapped", ...],
     "matrix": [["", "Mean", ...], ...],      # tables: every printed cell
     "bbox": [x0, y0, x1, y1],                # controls: the region, PDF points
     "description": "..."}

A gold matrix is written by reading the rendered page, then re-checked
independently; see tests/PLAN-tables.md, block 2.

Metrics, per table:

- exact: the emitted grid equals the gold matrix after normalisation
  (NFKC, dashes and minus signs unified, white space collapsed) and after
  dropping rows and columns that are empty in the matrix compared;
- cell association: the mean, over the gold matrix's non-empty cells, of
  the token Jaccard between the gold cell and the best-matching emitted
  cell. A cell reproduced whole and alone scores 1; a cell merged with its
  neighbour or split in two scores less; prose scores 0;
- adjacency F1: ICDAR-2013 style. Every non-empty cell is related to the
  next non-empty cell to its right and below it; precision and recall are
  over those relations, matched by cell text;
- tokens kept: the share of the gold table's tokens present in the
  Markdown of its pages, whatever the form.

Each table gets one outcome: EXACT; GRID-NEAR (adjacency F1 >= 0.9); GRID-WRONG
(a grid below that); PROSE (no grid, >= 0.95 of the tokens kept); LOST (fewer
tokens kept). A control gets FALSE-GRID when a grid region intersects its
bbox, FALSE-MARKER when a fallback region does, else CLEAN.

usage:
    python tests/score_gold_tables.py [--gold DIR] [--corpus-root DIR ...]
                                      [--json OUT] [--regions DIR]

``--regions`` reads region dumps written by an instrumented run instead of
converting (one ``<stem>.tables.json`` and ``<stem>.md`` per document).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import tempfile
import unicodedata
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLD = ROOT / "tests" / "gold-tables"
NEAR_F1 = 0.9
PROSE_KEEP = 0.95
MATCH_MIN = 0.5

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—−﹣－"), "-")


# Bullet glyphs: a converter may glue one to its word ("●Laws") or extract it
# as another glyph. They are layout, not cell content.
_BULLETS = dict.fromkeys(map(ord, "•●▪◦‣⁃■○"), " ")


def norm(text: str) -> str:
    text = (
        unicodedata.normalize("NFKC", text or "").translate(_DASHES).translate(_BULLETS)
    )
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return norm(text).split()


def trim(matrix: list[list[str]]) -> list[list[str]]:
    """Normalise cells and drop rows and columns that are empty."""
    rows = [[norm(c) for c in r] for r in matrix]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    keep = [j for j in range(width) if any(r[j] for r in rows)]
    return [[r[j] for j in keep] for r in rows]


def relations(matrix: list[list[str]]) -> Counter:
    m = trim(matrix)
    rel: Counter = Counter()
    for i, row in enumerate(m):
        for j, cell in enumerate(row):
            if not cell:
                continue
            for jj in range(j + 1, len(row)):
                if row[jj]:
                    rel[(cell, row[jj], "h")] += 1
                    break
            for ii in range(i + 1, len(m)):
                if m[ii][j]:
                    rel[(cell, m[ii][j], "v")] += 1
                    break
    return rel


def jaccard(a: list[str], b: list[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    union = sum((ca | cb).values())
    return sum((ca & cb).values()) / union if union else 0.0


def score_table(gold: dict, regions: list[dict], page_text: str) -> dict:
    gm = trim(gold["matrix"])
    gold_cells = [c for r in gm for c in r if c]
    gold_tokens = [t for c in gold_cells for t in c.split()]
    kept = Counter(gold_tokens) & Counter(tokens(page_text))
    keep_share = sum(kept.values()) / max(1, len(gold_tokens))
    gset = Counter(gold_tokens)
    mine = []
    for r in regions:
        rtok = Counter(tokens(" ".join(r.get("lines") or [])))
        if r.get("matrix"):
            rtok = Counter(t for row in r["matrix"] for c in row for t in tokens(c))
        overlap = sum((rtok & gset).values())
        # Most of a region's words must belong to this table: a neighbouring
        # table on the same page shares common words, never most of them.
        if rtok and overlap / sum(rtok.values()) >= MATCH_MIN:
            mine.append(r)
    grids = [r for r in mine if r["kind"] == "grid"]
    result = {
        "id": gold["id"],
        "kind": "table",
        "doc": gold["doc"],
        "pages": gold["pages"],
        "layout": gold.get("layout", []),
        "gold_cells": len(gold_cells),
        "tokens_kept": round(keep_share, 3),
        "grid_regions": len(grids),
        "fallback_regions": sum(1 for r in mine if r["kind"] == "fallback"),
    }
    if not grids:
        result.update(
            exact=False,
            cell_assoc=0.0,
            adj_p=0.0,
            adj_r=0.0,
            adj_f1=0.0,
            outcome="PROSE" if keep_share >= PROSE_KEEP else "LOST",
        )
        return result
    pred: list[list[str]] = []
    for r in sorted(grids, key=lambda r: (r["page"], r["bbox"][1])):
        pred.extend(r["matrix"])
    pm = trim(pred)
    pred_cells = [c.split() for r in pm for c in r if c]
    assoc = [
        max((jaccard(c.split(), p) for p in pred_cells), default=0.0)
        for c in gold_cells
    ]
    gr, pr = relations(gm), relations(pm)
    hit = sum((gr & pr).values())
    p = hit / max(1, sum(pr.values()))
    rc = hit / max(1, sum(gr.values()))
    f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
    exact = pm == gm
    result.update(
        exact=exact,
        cell_assoc=round(sum(assoc) / max(1, len(assoc)), 3),
        adj_p=round(p, 3),
        adj_r=round(rc, 3),
        adj_f1=round(f1, 3),
        outcome="EXACT" if exact else ("GRID-NEAR" if f1 >= NEAR_F1 else "GRID-WRONG"),
    )
    return result


def intersects(a, b) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def score_control(gold: dict, regions: list[dict]) -> dict:
    hits = [
        r
        for r in regions
        if r["page"] in gold["pages"] and intersects(r["bbox"], gold["bbox"])
    ]
    outcome = (
        "FALSE-GRID"
        if any(r["kind"] == "grid" for r in hits)
        else "FALSE-MARKER"
        if hits
        else "CLEAN"
    )
    return {
        "id": gold["id"],
        "kind": "control",
        "doc": gold["doc"],
        "pages": gold["pages"],
        "outcome": outcome,
        "grid_regions": sum(r["kind"] == "grid" for r in hits),
        "fallback_regions": sum(r["kind"] == "fallback" for r in hits),
    }


def page_slices(md: str) -> dict[int, str]:
    out: dict[int, list[str]] = {}
    page = 0
    for line in md.splitlines():
        m = re.match(r"<!-- page (\d+) -->", line)
        if m:
            page = int(m.group(1))
            continue
        out.setdefault(page, []).append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def plain(md: str) -> str:
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    md = re.sub(r"</?[A-Za-z][^<>]*>", " ", md)
    return md.replace("|", " ").replace("*", " ").replace("\\", "")


def convert_with_regions(pdf: pathlib.Path) -> tuple[str, list[dict]]:
    """Convert with page markers and capture every emitted table region."""
    sys.path.insert(0, str(ROOT))
    import importlib

    api = importlib.import_module("markerlite.api")
    render_mod = importlib.import_module("markerlite.render")

    found: list[dict] = []
    original = api.render

    def spy(pages, **kw):
        for page in pages:
            for b in page.blocks:
                if b.btype != "Table" or b.ignore_for_output:
                    continue
                fallback = bool(b.fallback_paragraphs)
                matrix = None
                if not fallback:
                    parser = render_mod._TableParser()
                    parser.feed(b.html or "")
                    matrix = [list(parser.header), *[list(r) for r in parser.rows]]
                found.append(
                    {
                        "page": page.page_idx + 1,
                        "bbox": list(b.bbox),
                        "kind": "fallback" if fallback else "grid",
                        "matrix": matrix,
                        "lines": [ln.text for ln in b.lines],
                    }
                )
        return original(pages, **kw)

    api.render = spy
    try:
        with tempfile.TemporaryDirectory() as tmp:
            md, _info = api.convert(pdf, pathlib.Path(tmp), page_markers=True)
            return md.read_text(encoding="utf-8"), found
    finally:
        api.render = original


def resolve(sha: str, doc: str, roots: list[pathlib.Path]) -> pathlib.Path | None:
    for root in roots:
        for path in root.rglob(f"{doc}.pdf"):
            if hashlib.sha256(path.read_bytes()).hexdigest() == sha:
                return path
    for root in roots:
        for path in root.rglob("*.pdf"):
            if hashlib.sha256(path.read_bytes()).hexdigest() == sha:
                return path
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gold", type=pathlib.Path, default=GOLD)
    ap.add_argument("--corpus-root", type=pathlib.Path, action="append", default=[])
    ap.add_argument(
        "--regions",
        type=pathlib.Path,
        help="read <stem>.tables.json and <stem>.md instead of converting",
    )
    ap.add_argument("--json", type=pathlib.Path, help="write the per-item results here")
    args = ap.parse_args(argv)
    items = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(args.gold.glob("*.json"))
    ]
    if not items:
        print(f"no gold items under {args.gold}")
        return 2
    roots = [ROOT / "tests" / "real", *args.corpus_root]
    cache: dict[str, tuple[str, list[dict]]] = {}
    results = []
    for item in items:
        key = item["sha256"]
        if key not in cache:
            if args.regions:
                data = json.loads(
                    (args.regions / f"{item['doc']}.tables.json").read_text(
                        encoding="utf-8"
                    )
                )
                md = (args.regions / f"{item['doc']}.md").read_text(encoding="utf-8")
                cache[key] = (md, data["regions"])
            else:
                pdf = resolve(key, item["doc"], roots)
                if pdf is None:
                    print(
                        f"SKIP  {item['id']}: source not found under the corpus roots"
                    )
                    continue
                cache[key] = convert_with_regions(pdf)
        md, regions = cache[key]
        if item["kind"] == "control":
            res = score_control(item, regions)
        else:
            pages = page_slices(md)
            text = plain(" ".join(pages.get(p, "") for p in item["pages"]))
            res = score_table(
                item, [r for r in regions if r["page"] in item["pages"]], text
            )
        results.append(res)
        if res["kind"] == "table":
            print(
                f"{res['outcome']:11s} {res['id']:28s} cells={res['gold_cells']:4d} "
                f"assoc={res['cell_assoc']:.3f} adjF1={res['adj_f1']:.3f} kept={res['tokens_kept']:.3f}"
            )
        else:
            print(f"{res['outcome']:11s} {res['id']:28s} control")
    tables = [r for r in results if r["kind"] == "table"]
    controls = [r for r in results if r["kind"] == "control"]
    if tables:
        outcomes = Counter(r["outcome"] for r in tables)
        print(
            f"\ntables {len(tables)}: "
            + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
        )
        print(
            f"exact-match rate {sum(r['exact'] for r in tables) / len(tables):.3f}; "
            f"mean cell association {sum(r['cell_assoc'] for r in tables) / len(tables):.3f}; "
            f"mean adjacency F1 {sum(r['adj_f1'] for r in tables) / len(tables):.3f}"
        )
    if controls:
        outcomes = Counter(r["outcome"] for r in controls)
        print(
            f"controls {len(controls)}: "
            + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
        )
    if args.json:
        args.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
