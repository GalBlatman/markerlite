"""Table-confidence gate (tests/PLAN-tables.md, block 2, item 14).

A reconstructed grid is emitted only when the page and the grid itself give
evidence that it is a table and that its cells hold the source's words.
Below the gate the region is kept as ordered prose with all its text: the
table path that produced the grid decides how (a find_tables candidate
falls back to prose with its marker; a text proposal stays a paragraph).

Each test is measured on the source page or the candidate, never on the
reconstruction it judges, except 2, 5 and 6, which judge the grid against
its own source words:

1. evidence: two horizontal rules across the region or one vertical rule,
   or at least two column starts that recur in half the multi-cell rows;
2. shape: at least two rows and two columns;
3. not a figure: no curve drawn inside the region;
4. not prose: fewer than 40% of printed lines end a sentence;
5. token identity: the grid's tokens equal the members' tokens as a
   multiset, within GATE_IDENTITY_MAX;
6. no continuation rows: fewer than 15% of body rows have an empty first
   cell and lower-case continuation text (wrapped lines emitted as rows);
7. not drawn boxes: three or more stroked boxes inside the region, none
   sharing an edge with another, are a diagram's boxes (a flow chart or
   model figure), not cells. A table drawn cell by cell has boxes that
   touch; a single frame round a table is one box.

Thresholds: owner ruling at block 2 stop 2. Prose 0.40 and two-row grids
held up on held-out documents; looser continuation and proposal-identity
limits did not (they kept more bad grids than good) and were not taken.
A correct grid this gate turns into marked prose is an accepted, listed
cost: a wrong grid is worse than no grid (tests/REPORT-block2-stop2.md).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from html import unescape
from typing import List

from .model import *

GATE_HRULES_MIN = 2
GATE_RULE_SPAN = 0.5  # a horizontal rule must span half the region's width
GATE_VRULE_SPAN = 0.3  # a vertical rule a third of its height
GATE_RULE_PAD = 6.0
GATE_MIN_ROWS = 2
GATE_MIN_COLS = 2
GATE_PROSE_MAX = 0.40
GATE_IDENTITY_MAX = 0.05
GATE_CONTINUATION_MAX = 0.15
GATE_COLUMN_TOL = 4.0
GATE_BOXES_MIN = 3
GATE_BOX_EDGE_TOL = 1.5
GATE_BOX_MAX_WIDTH = 0.9  # a box this wide is a frame or a row band

_SENTENCE_END = re.compile(r"[A-Za-z]{2,}[.!?][\"'”’)\]]*$")


def page_graphics(pmpage) -> dict:
    """Rules and curve boxes of a page, read once for every candidate on it.
    Horizontal: (y, x0, x1); vertical: (x, y0, y1); curves: rect tuples."""
    out = {"h": [], "v": [], "curves": [], "boxes": []}
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        return out
    for d in drawings:
        items = d.get("items", [])
        if any(it[0] == "c" for it in items):
            out["curves"].append(tuple(d["rect"]))
        for it in items:
            if it[0] == "l":
                p0, p1 = it[1], it[2]
                if abs(p0.y - p1.y) <= 0.5 and abs(p0.x - p1.x) > 2:
                    out["h"].append(
                        ((p0.y + p1.y) / 2, min(p0.x, p1.x), max(p0.x, p1.x))
                    )
                elif abs(p0.x - p1.x) <= 0.5 and abs(p0.y - p1.y) > 2:
                    out["v"].append(
                        ((p0.x + p1.x) / 2, min(p0.y, p1.y), max(p0.y, p1.y))
                    )
            elif it[0] == "re":
                r = it[1]
                if r.height <= 1.6 and r.width > 2:
                    out["h"].append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                elif r.width <= 1.6 and r.height > 2:
                    out["v"].append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                elif r.width > 2 and r.height > 2:
                    if d.get("color") is not None:
                        out["boxes"].append((r.x0, r.y0, r.x1, r.y1))
                    # a box: its edges are rules of a ruled table
                    out["h"] += [(r.y0, r.x0, r.x1), (r.y1, r.x0, r.x1)]
                    out["v"] += [(r.x0, r.y0, r.y1), (r.x1, r.y0, r.y1)]
    return out


def _norm(text: str) -> List[str]:
    return unicodedata.normalize("NFKC", unescape(text or "")).split()


def grid_rows(html: str) -> List[List[str]]:
    from .render import _TableParser

    tp = _TableParser()
    tp.feed(html or "")
    rows = [list(tp.header)] if tp.header else []
    rows += [list(r) for r in tp.rows]
    return [r for r in rows if any(c.strip() for c in r)]


def recurring_columns(rows_x: List[List[float]]) -> int:
    rows = [sorted(r) for r in rows_x if len(r) >= 2]
    if not rows:
        return 0
    clusters: List[list] = []
    for x in sorted(x for row in rows for x in row):
        if clusters and x - clusters[-1][-1] <= GATE_COLUMN_TOL:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    count = 0
    for cl in clusters:
        lo, hi = cl[0] - GATE_COLUMN_TOL, cl[-1] + GATE_COLUMN_TOL
        if sum(1 for r in rows if any(lo <= x <= hi for x in r)) >= 0.5 * len(rows):
            count += 1
    return count


def evaluate(
    graphics: dict,
    region,
    rows_x,
    member_lines: List[str],
    html: str,
    path: str = "find_tables",
) -> dict:
    """Run the six tests. Returns {"passed": bool, "failed": [names],
    "measures": {...}} so a stopped grid can say why."""
    x0, y0, x1, y1 = region
    w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    pad = GATE_RULE_PAD
    hr = [
        r
        for r in graphics["h"]
        if y0 - pad <= r[0] <= y1 + pad
        and min(r[2], x1) - max(r[1], x0) >= GATE_RULE_SPAN * w
    ]
    vr = [
        r
        for r in graphics["v"]
        if x0 - pad <= r[0] <= x1 + pad
        and min(r[2], y1) - max(r[1], y0) >= GATE_VRULE_SPAN * h
    ]
    hr_levels = len({round(r[0]) for r in hr})
    # The same counts after joining collinear edges: a table drawn as one
    # stroked rectangle per cell has no single edge across it, though its
    # cell edges line up into full rules. Used for the evidence label only;
    # the gate's own evidence test above is unchanged.
    mh = [
        r
        for r in _merge(graphics["h"])
        if y0 - pad <= r[0] <= y1 + pad
        and min(r[2], x1) - max(r[1], x0) >= GATE_RULE_SPAN * w
    ]
    mv = [
        r
        for r in _merge(graphics["v"])
        if x0 - pad <= r[0] <= x1 + pad
        and min(r[2], y1) - max(r[1], y0) >= GATE_VRULE_SPAN * h
    ]
    cols = recurring_columns(rows_x)
    curves = sum(
        1
        for c in graphics["curves"]
        if min(c[2], x1) > max(c[0], x0) and min(c[3], y1) > max(c[1], y0)
    )
    lines = [ln.strip() for ln in member_lines if ln.strip()]
    prose = sum(1 for ln in lines if _SENTENCE_END.search(ln)) / max(1, len(lines))
    rows = grid_rows(html)
    ncols = max((len(r) for r in rows), default=0)
    src = Counter(t for ln in member_lines for t in _norm(ln))
    grid = Counter(t for r in rows for c in r for t in _norm(c))
    n_src = max(1, sum(src.values()))
    identity = (sum((src - grid).values()) + sum((grid - src).values())) / n_src
    body = rows[1:]
    cont = sum(
        1
        for r in body
        if len(r) >= 2
        and not r[0].strip()
        and any(c.strip()[:1].islower() for c in r[1:] if c.strip())
    ) / max(1, len(body))
    boxes = [
        b
        for b in graphics.get("boxes", [])
        if b[0] >= x0 - pad
        and b[2] <= x1 + pad
        and b[1] >= y0 - pad
        and b[3] <= y1 + pad
        and b[2] - b[0] < GATE_BOX_MAX_WIDTH * w
    ]
    touching = sum(
        1 for i, a in enumerate(boxes) for b in boxes[i + 1 :] if _boxes_touch(a, b)
    )
    measures = {
        "hrules": hr_levels,
        "vrules": len(vr),
        "recurring_cols": cols,
        "rows": len(rows),
        "cols": ncols,
        "curves": curves,
        "prose": round(prose, 3),
        "identity": round(identity, 3),
        "continuation": round(cont, 3),
        "boxes": len(boxes),
        "boxes_touching": touching,
        "hrules_joined": len({round(r[0]) for r in mh}),
        "vrules_joined": len(mv),
    }
    failed = []
    if not (hr_levels >= GATE_HRULES_MIN or vr or cols >= 2):
        failed.append("evidence")
    if len(rows) < GATE_MIN_ROWS or ncols < GATE_MIN_COLS:
        failed.append("shape")
    if curves:
        failed.append("figure")
    if prose >= GATE_PROSE_MAX:
        failed.append("prose")
    if identity > GATE_IDENTITY_MAX:
        failed.append("identity")
    if cont >= GATE_CONTINUATION_MAX:
        failed.append("continuation")
    if len(boxes) >= GATE_BOXES_MIN and not touching:
        failed.append("boxes")
    return {"passed": not failed, "failed": failed, "measures": measures}


def evidence_kind(measures: dict) -> str:
    """What a grid stands on: "rules" (two horizontal rules across it or a
    vertical rule, counting cell edges that line up as one rule) or "text"
    (column starts that recur, nothing drawn)."""
    h = max(measures.get("hrules", 0), measures.get("hrules_joined", 0))
    v = max(measures.get("vrules", 0), measures.get("vrules_joined", 0))
    return "rules" if h >= GATE_HRULES_MIN or v else "text"


def _boxes_touch(a, b, tol: float = GATE_BOX_EDGE_TOL) -> bool:
    """Whether two boxes share part of an edge (cells of one grid do)."""
    xs = min(a[2], b[2]) - max(a[0], b[0])
    ys = min(a[3], b[3]) - max(a[1], b[1])
    if xs > tol and any(abs(p - q) <= tol for p in a[1::2] for q in b[1::2]):
        return True
    return ys > tol and any(abs(p - q) <= tol for p in a[0::2] for q in b[0::2])


def _merge(segments, tol: float = 1.5) -> list:
    """Join collinear segments (same position within 0.5 pt) whose ranges
    touch or overlap within ``tol``: (pos, start, end)."""
    out = []
    for pos, a, b in sorted(segments, key=lambda r: (round(r[0] * 2), r[1])):
        if out and abs(out[-1][0] - pos) <= 0.5 and a <= out[-1][2] + tol:
            out[-1] = (out[-1][0], out[-1][1], max(out[-1][2], b))
        else:
            out.append((pos, a, b))
    return out


def rows_x_of(tokens_for_recon) -> List[List[float]]:
    """Column-start x of every printed row, from table_recon's token rows."""
    return [[x0 for _t, x0, _x1 in toks] for toks, _y0, _y1 in tokens_for_recon]


def record(page: "Page", path: str, region, result: dict) -> None:
    page.gate_events.append(
        {
            "page": page.page_idx + 1,
            "path": path,
            "bbox": [round(v, 1) for v in region],
            "failed": result["failed"],
            **{
                k: v
                for k, v in result["measures"].items()
                if not k.endswith("_joined")  # label-only measures
            },
        }
    )
