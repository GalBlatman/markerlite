"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import bisect
import math
import re
import warnings
from collections import Counter, defaultdict
from html import unescape
from statistics import median
from typing import List, Tuple

import pymupdf

from .extraction import _bbox_of
from .model import *
from .render import _TableParser
from .table_wrap import recover_wrapped_lines

try:
    from table_recon import reconstruct_table_html
except ImportError:
    try:
        from marker.processors.table_recon import reconstruct_table_html
    except ImportError:
        reconstruct_table_html = None
        warnings.warn(
            "table_recon.py not found beside markerlite.py; borderless table reconstruction is disabled",
            RuntimeWarning,
        )


def _overlap_frac(inner, outer) -> float:
    ix0 = max(inner[0], outer[0])
    iy0 = max(inner[1], outer[1])
    ix1 = min(inner[2], outer[2])
    iy1 = min(inner[3], outer[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area = max((inner[2] - inner[0]) * (inner[3] - inner[1]), 1e-6)
    return inter / area


def _tokens_for_recon(blocks: List[Block], bbox) -> list:
    """Build marker's ``[(tokens, y0, y1)]`` shape from PyMuPDF char data.

    Mirrors table_recon._line_tokens: re-split each line's characters at gaps
    wider than half the char height, because a single PDF span routinely spans
    several table cells.
    """
    bx0, by0, bx1, by1 = bbox
    out = []
    for blk in blocks:
        for ln in blk.lines:
            tokens = []
            cur = None
            if not any(sp.chars for sp in ln.spans):
                # No char layer (OCR spans are already word-level) - marker's
                # _line_tokens has the same span-level fallback. Words are then
                # re-joined across ordinary word spaces: only a gap wide enough
                # to be a column separator may split a cell. Without this, every
                # word of justified prose looks like its own cell and the grid
                # judge happily "reconstructs" a paragraph as a table.
                words = []
                for sp in ln.spans:
                    t = sp.text.strip()
                    sx0, sy0, sx1, sy1 = sp.bbox
                    if (
                        t
                        and bx0 <= (sx0 + sx1) / 2 <= bx1
                        and by0 <= (sy0 + sy1) / 2 <= by1
                    ):
                        words.append([t, sx0, sx1, sy1 - sy0])
                if words:
                    gap_thresh = TABLE_TOKEN_GAP_HEIGHT * median([w[3] for w in words])
                    for t, x0, x1, _h in words:
                        if tokens and x0 - tokens[-1][2] < gap_thresh:
                            tokens[-1][0] += " " + t
                            tokens[-1][2] = x1
                        else:
                            tokens.append([t, x0, x1])
            for sp in ln.spans:
                for c in sp.chars or []:
                    cx0, cy0, cx1, cy1 = c["bbox"]
                    if not (
                        bx0 <= (cx0 + cx1) / 2 <= bx1 and by0 <= (cy0 + cy1) / 2 <= by1
                    ):
                        continue
                    ch = c.get("c", "")
                    gap = TABLE_ROW_TOLERANCE_HEIGHT * max(cy1 - cy0, 1.0)
                    if cur is None:
                        cur = [ch, cx0, cx1]
                    elif cx0 - cur[2] > gap:
                        tokens.append(cur)
                        cur = [ch, cx0, cx1]
                    else:
                        cur[0] += ch
                        cur[2] = cx1
            if cur is not None:
                tokens.append(cur)
            toks = [
                (t.strip(), round(x0, 1), round(x1, 1))
                for t, x0, x1 in tokens
                if t.strip() and not re.match(r"^[.·•…_\-\s]+$", t.strip())
            ]
            if toks:
                out.append((toks, round(ln.bbox[1], 1), round(ln.bbox[3], 1)))

    # PyMuPDF emits one "line" per cell inside a table, so a row arrives as
    # several same-y entries. table_recon expects one entry per ROW (its whole
    # grid inference keys off tokens-per-row), so merge by vertical band first.
    if not out:
        return out
    heights = [y1 - y0 for _, y0, y1 in out if y1 > y0]
    tol = (median(heights) / 2) if heights else 3.0
    out.sort(key=lambda e: (e[1], e[0][0][1]))
    rows = []
    for toks, y0, y1 in out:
        if rows and abs(y0 - rows[-1][1]) <= tol:
            rows[-1][0].extend(toks)
            rows[-1][2] = max(rows[-1][2], y1)
        else:
            rows.append([list(toks), y0, y1])
    return [(sorted(t, key=lambda x: x[1]), y0, y1) for t, y0, y1 in rows]


def _grid_from_members(tbl, members: List[Block]) -> List[List[str]]:
    """PyMuPDF's cell geometry filled with OUR text.

    ``tbl.extract()`` reads the page's own text layer, so it duplicates words
    shared with an overlapping table candidate and carries rotated watermark
    glyphs that extract_page already dropped. Assigning the member blocks'
    words to the cells by position keeps the geometric truth of the grid
    (each word in the cell the ruling lines put it in) with only the text the
    converter has already accepted.
    """
    cells = [[c for c in row.cells] for row in tbl.rows]
    grid = [["" for _ in row] for row in cells]

    def place(word: str, cx: float, cy: float) -> None:
        for ri, row in enumerate(cells):
            for ci, c in enumerate(row):
                if c and c[0] <= cx <= c[2] and c[1] <= cy <= c[3]:
                    grid[ri][ci] = (grid[ri][ci] + " " + word).strip()
                    return

    for blk in members:
        for ln in blk.lines:
            cy = (ln.bbox[1] + ln.bbox[3]) / 2
            word, wx0, wx1 = "", 0.0, 0.0
            for sp in ln.spans:
                if not sp.chars:
                    t = sp.text.strip()
                    if t:
                        place(t, (sp.bbox[0] + sp.bbox[2]) / 2, cy)
                    continue
                for c in sp.chars:
                    ch = c.get("c", "")
                    cx0, _y0, cx1, _y1 = c["bbox"]
                    if ch.isspace():
                        if word:
                            place(word, (wx0 + wx1) / 2, cy)
                        word = ""
                        continue
                    if not word:
                        wx0 = cx0
                    word += ch
                    wx1 = cx1
            if word:
                place(word, (wx0 + wx1) / 2, cy)
    return grid


def _grid_to_html(rows: List[List[str]]) -> str:
    rows = [
        [(c or "").strip() for c in r]
        for r in rows
        if any((c or "").strip() for c in r)
    ]
    if len(rows) < 2:
        return ""
    head, body = rows[0], rows[1:]
    parts = ["<table><thead><tr>"]
    parts += [f"<th>{c}</th>" for c in head]
    parts.append("</tr></thead><tbody>")
    for r in body:
        parts.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _html_word_count(html: str) -> int:
    """Words of visible text in a table's HTML (tags stripped)."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(unescape(text).split())


def _table_sane(
    html: str,
    max_header_ratio=TABLE_MAX_HEADER_RATIO,
    max_empty_frac=TABLE_MAX_EMPTY_FRAC,
) -> bool:
    """Reject a reconstruction that cannot be the table on the page.

    The grid sweep sometimes wins with far too many columns - a nine-column
    header over what is plainly a three-column table - because a wrapped header
    fragments into extra tokens and the judge rewards one-token cells. Two
    checks catch it: a header much wider than the body, and a grid mostly made
    of holes.
    """
    if not html:
        return False
    p = _TableParser()
    try:
        p.feed(html)
    except Exception:
        return False
    header, rows = p.header, p.rows
    if not rows:
        return False
    body_widths = [len([c for c in r if c.strip()]) for r in rows]
    body_widths = [w for w in body_widths if w]
    if not body_widths:
        return False
    modal = Counter(body_widths).most_common(1)[0][0]
    if header and modal and len(header) > max_header_ratio * modal:
        return False
    total = sum(len(r) for r in rows)
    empty = sum(1 for r in rows for c in r if not c.strip())
    if total and empty / total > max_empty_frac:
        return False
    return True


def _page_graphics(pmpage) -> Tuple[list, list]:
    """Horizontal rule segments ``(y, x0, x1)`` and the boxes of every other
    drawing on the page.

    A rule is a drawing made of horizontal strokes only. The top and bottom
    edge of a frame are horizontal too, but they belong to a box, and a box
    under a table is a diagram, not the table's last row.
    """
    rules, others = [], []
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        return rules, others
    for d in drawings:
        segs, plain = [], True
        for it in d.get("items", []):
            if it[0] == "l":
                p0, p1 = it[1], it[2]
                if abs(p0.y - p1.y) <= 0.5 and abs(p0.x - p1.x) > 2:
                    segs.append(((p0.y + p1.y) / 2, min(p0.x, p1.x), max(p0.x, p1.x)))
                else:
                    plain = False
            elif it[0] == "re":
                r = it[1]
                if r.height <= 1.5 and r.width > 2:
                    segs.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                else:
                    plain = False
            else:
                plain = False
        if plain and segs:
            rules.extend(segs)
        else:
            others.append(tuple(d["rect"]))
    return rules, others


def _rules_in(rules: list, bbox, min_cover: float = RULE_MIN_COVER) -> List[float]:
    """y of every horizontal rule that spans the candidate, top to bottom."""
    x0, y0, x1, y1 = bbox
    width = max(x1 - x0, 1.0)
    bands: List[list] = []  # [y, covered length]
    for y, a, b in sorted(rules):
        if y < y0 - 1 or y > y1 + 1:
            continue
        a, b = max(a, x0), min(b, x1)
        if b <= a:
            continue
        if bands and abs(y - bands[-1][0]) <= 1.0:
            bands[-1][1] += b - a
        else:
            bands.append([y, b - a])
    return [y for y, covered in bands if covered >= min_cover * width]


def _one_run(ln: Line) -> bool:
    """True when the line is one run of text, not several cells: no gap in it
    is wide enough to separate columns."""
    probe = Block(lines=[ln], bbox=ln.bbox, page_idx=0, char_pos=0)
    rows = _tokens_for_recon([probe], (-1e9, -1e9, 1e9, 1e9))
    return len(rows) == 1 and len(rows[0][0]) == 1


def _line_size(ln: Line) -> float:
    sizes = [sp.size for sp in ln.spans if sp.text.strip()]
    return max(sizes) if sizes else 0.0


def _isolate_table(
    members: List[Block], bbox, rules: list, others: list, bound_rows: bool = True
):
    """Split a candidate's source lines into caption, grid and what stands
    below the grid, BEFORE reconstruction.

    Returns ``(caption_lines, excluded_lines, extent)`` where ``extent`` is
    the vertical span ``(top, bottom)`` the grid may occupy, or None when the
    candidate is left as it was.

    Caption: the leading line carries a table label, stands alone in its row
    and is one run of text. Lines that follow it in the same size, close
    under it, alone in their row and not split into cells are its
    continuation. A rule between two lines ends the caption.

    Row extent: when the candidate holds at least two rules, the last one is
    the table's bottom rule. Lines under it are kept out of the grid when
    the first of them is a note, or when a drawing that is not a rule (a
    frame, a curve: a diagram) stands under the rule.
    """
    entries = sorted(
        ((ln, blk) for blk in members for ln in blk.lines if ln.text.strip()),
        key=lambda e: (e[0].bbox[1], e[0].bbox[0]),
    )
    if len(entries) < 3:
        return [], [], None
    ys = _rules_in(rules, bbox)

    def alone(i: int) -> bool:
        ln = entries[i][0]
        mid = (ln.bbox[1] + ln.bbox[3]) / 2
        return not any(
            j != i and o.bbox[1] <= mid <= o.bbox[3]
            for j, (o, _b) in enumerate(entries)
        )

    def rule_between(upper: Line, lower: Line) -> bool:
        return any(upper.bbox[3] - 1.5 <= y <= lower.bbox[1] + 1.5 for y in ys)

    caption: List[Line] = []
    first = entries[0][0]
    if TABLE_LABEL.match(first.text) and alone(0) and _one_run(first):
        caption = [first]
        for i in range(1, min(len(entries), 5)):
            ln, prev = entries[i][0], caption[-1]
            if rule_between(prev, ln):
                break
            if not alone(i) or not _one_run(ln):
                break
            if abs(_line_size(ln) - _line_size(first)) > TABLE_CAPTION_MAX_SIZE_DELTA:
                break
            if ln.bbox[1] - prev.bbox[3] > TABLE_CAPTION_MAX_GAP_HEIGHT * max(
                prev.height, 1.0
            ):
                break
            if (
                abs(ln.bbox[0] - first.bbox[0]) > 3.0
                and abs((ln.bbox[0] + ln.bbox[2]) - (first.bbox[0] + first.bbox[2]))
                > 10.0
            ):
                break
            caption.append(ln)
        rest = [e for e in entries if not any(e[0] is c for c in caption)]
        bands = {round(e[0].bbox[1] / 4) for e in rest}
        if len(bands) < 2:
            caption = []  # nothing like a grid is left: not a caption split
    top = bbox[1]
    if caption:
        top = max(c.bbox[3] for c in caption)
        ys = [y for y in ys if y >= top - 1.5]

    excluded: List[Line] = []
    bottom = bbox[3]
    if bound_rows and len(ys) >= 2:
        last = ys[-1]
        below = [
            e[0]
            for e in entries
            if (e[0].bbox[1] + e[0].bbox[3]) / 2 > last + 0.5
            and not any(e[0] is c for c in caption)
        ]
        # Strokes that are not rules inside the grid - cell borders, a frame
        # around the rows - mean the table is boxed after all: it is closed
        # by its frame, and what stands under an inner rule is a row.
        framed = any(
            o[1] < last - 1
            and o[3] > top + 1
            and min(o[2], bbox[2]) - max(o[0], bbox[0]) > 0
            and min(o[3], bbox[3]) - max(o[1], bbox[1]) >= 0
            for o in others
        )
        if below and not framed:
            diagram = any(
                o[1] >= last - 1
                and o[3] <= bbox[3] + 2
                and (o[3] - o[1]) > 3
                and min(o[2], bbox[2]) - max(o[0], bbox[0]) > 0
                for o in others
            )
            if TABLE_NOTE.match(below[0].text) or diagram:
                excluded = below
                bottom = last
    if not caption and not excluded:
        return [], [], None
    return caption, excluded, (top, bottom)


def _split_members(members: List[Block], caption: List[Line], excluded: List[Line]):
    """Rebuild the member blocks without the caption and the excluded lines.

    Returns ``(grid_members, caption_block, leftovers, touched)``: the blocks
    that feed the grid, the caption as a block of its own, the blocks made of
    lines that stand below the grid, and the original blocks that were taken
    apart or used (these leave the page; an original made only of excluded
    lines is not touched and stays where it is).
    """

    def among(ln: Line, group: List[Line]) -> bool:
        return any(ln is g for g in group)

    def block_of(lines: List[Line], src: Block, btype: str = "Text") -> Block:
        return Block(
            lines=lines,
            bbox=_bbox_of([ln.bbox for ln in lines]),
            page_idx=src.page_idx,
            char_pos=lines[0].char_pos,
            btype=btype,
        )

    grid_members, leftovers, touched, cap_lines, cap_src = [], [], [], [], None
    for blk in members:
        cap = [ln for ln in blk.lines if among(ln, caption)]
        out = [ln for ln in blk.lines if among(ln, excluded)]
        grid = [
            ln for ln in blk.lines if not among(ln, caption) and not among(ln, excluded)
        ]
        if not cap and not out:
            grid_members.append(blk)
            touched.append(blk)
            continue
        if not cap and not grid:
            continue  # wholly below the grid: stays on the page
        touched.append(blk)
        if cap:
            cap_lines.extend(cap)
            cap_src = cap_src or blk
        if grid:
            grid_members.append(block_of(grid, blk))
        if out:
            leftovers.append(block_of(out, blk))
    caption_block = None
    if cap_lines:
        cap_lines.sort(key=lambda ln: ln.bbox[1])
        caption_block = block_of(cap_lines, cap_src, "Caption")
        caption_block.leads = True
    return grid_members, caption_block, leftovers, touched


def _journal_front_matter(members: List[Block], context: List[Block]) -> bool:
    """Require abstract prose, a distinct title, and publication metadata.

    Page position is not evidence: an ordinary first-page data table, or a
    submission cover's isolated key/value metadata, fails this conjunction.
    Spaced-out publisher labels ("a b s t r a c t") count as labels too.
    """
    lines = [ln for b in members for ln in b.lines if ln.text.strip()]
    labels = {re.sub(r"\s+", "", ln.text).rstrip(":").lower() for ln in lines}
    if "abstract" not in labels:
        return False
    prose = [b for b in members if len(b.text.split()) >= FRONT_MATTER_MIN_PROSE_WORDS]
    if not prose:
        return False
    sizes = [sp.size for b in prose for sp in b.spans if sp.text.strip()]
    if not sizes:
        return False
    body_size = median(sizes)
    abstract_top = min(
        ln.bbox[1]
        for ln in lines
        if re.sub(r"\s+", "", ln.text).rstrip(":").lower() == "abstract"
    )
    title = any(
        FRONT_MATTER_TITLE_MIN_WORDS
        <= len(b.text.split())
        <= FRONT_MATTER_TITLE_MAX_WORDS
        and b.y_end <= abstract_top
        and b.max_size() >= FRONT_MATTER_TITLE_SCALE * body_size
        for b in context
    )
    if not title:
        return False
    text = "\n".join(b.text for b in members)
    metadata = re.search(
        r"doi\s*[:.]|doi\.org/|journal(?:s| homepage)?|"
        r"article history|received.*\d{4}|corresponding author",
        text,
        re.I,
    )
    return bool(metadata or "keywords" in labels)


def _projection_ok(lines: list, page: Page) -> Tuple[bool, float]:
    """(acceptable, worst distance outside the page in page sides).

    table_recon projects token coordinates onto grids whose size follows the
    coordinates' span. A crafted PDF can place glyphs at non-finite or absurd
    positions; such a candidate is not reconstructed. The page box is widened
    by TABLE_PROJECTION_MARGIN page sides, because real tables do carry
    glyphs a little outside the page.
    """
    side = max(page.width, page.height, 1.0)
    worst = 0.0
    for toks, y0, y1 in lines:
        for value in (y0, y1):
            if not math.isfinite(value):
                return False, math.inf
            worst = max(worst, -value / side, (value - page.height) / side)
        for _t, x0, x1 in toks:
            for value in (x0, x1):
                if not math.isfinite(value):
                    return False, math.inf
                worst = max(worst, -value / side, (value - page.width) / side)
    return worst <= TABLE_PROJECTION_MARGIN, worst


def _rule_rows(physical_rules: list, page: Page) -> list:
    """(y, x0, x1) of each row of horizontal rules that can bound a table,
    in first-seen order: the segments of one row (y rounded to 0.1 pt) are
    coalesced into their full extent."""
    # Publisher edge rules are not table boundaries. An actual admitted
    # table remains protected independently; a table caption can also
    # establish a genuine top rule inside the header band. The caption ends
    # are found once per page, not once per rule.
    caption_ends = [b.y_end for b in page.blocks if TABLE_LABEL.match(b.text.strip())]
    rows = defaultdict(list)
    for y, x0, x1 in physical_rules:
        caption_above = any(0 <= y - end <= 30 for end in caption_ends)
        if y > TABLE_PHYSICAL_EDGE_Y * page.height or (
            y < TABLE_TOP_EDGE_Y * page.height and not caption_above
        ):
            continue
        rows[round(y, 1)].append((x0, x1))
    return [(y, min(a for a, b in xs), max(b for a, b in xs)) for y, xs in rows.items()]


def _rule_zones(physical_rules: list, page: Page) -> list:
    """Table zones delimited by matching horizontal rules.

    Two rule rows with the same left and right edges, a plausible height
    apart, and a third matching row between them bound a zone. Broken or
    segmented booktabs strokes may not form a find_tables candidate; the
    zone still protects their content from furniture suppression. It does
    not admit a table.

    The search used to try every middle row for every pair of rows, cubic in
    the number of rows. For each row the matching rows' heights are now
    sorted once, and a pair qualifies when a matching height lies strictly
    between them (a binary search). The zones and their order are the same.
    Above TABLE_RULES_MAX rule segments or TABLE_RULE_ROWS_MAX rows the
    search is skipped and the page records the limit.
    """
    if len(physical_rules) > TABLE_RULES_MAX:
        note_limit(
            page,
            "table_rules",
            len(physical_rules),
            TABLE_RULES_MAX,
            "rule-bounded table zones not searched",
        )
        return []
    extents = _rule_rows(physical_rules, page)
    if len(extents) > TABLE_RULE_ROWS_MAX:
        note_limit(
            page,
            "table_rule_rows",
            len(extents),
            TABLE_RULE_ROWS_MAX,
            "rule-bounded table zones not searched",
        )
        return []
    tol = TABLE_RULE_EDGE_TOL
    matching = [
        sorted(
            mid
            for mid, left, right in extents
            if abs(left - x0) < tol and abs(right - x1) < tol
        )
        for _y, x0, x1 in extents
    ]
    zones = []
    for i, (y0, x0, x1) in enumerate(extents):
        if not x1 - x0 > TABLE_RULE_MIN_WIDTH_FRAC * page.width:
            continue
        mids = matching[i]
        first_above = bisect.bisect_right(mids, y0)
        for y1, a, b in extents:
            if (
                TABLE_RULE_MIN_HEIGHT
                < y1 - y0
                < TABLE_RULE_MAX_HEIGHT_FRAC * page.height
                and abs(x0 - a) < tol
                and abs(x1 - b) < tol
                and first_above < len(mids)
                and mids[first_above] < y1
            ):
                zones.append((x0, y0, x1, y1))
    return zones


def _recurring_columns(members: List[Block], region) -> int:
    """Column starts (within MARKER_COLUMN_TOL pt) that recur in at least
    half of the region's multi-cell rows."""
    rows = [
        sorted(x0 for _t, x0, _x1 in toks)
        for toks, _y0, _y1 in _tokens_for_recon(members, region)
        if len(toks) >= 2
    ]
    if not rows:
        return 0
    clusters: List[list] = []
    for x in sorted(x for row in rows for x in row):
        if clusters and x - clusters[-1][-1] <= MARKER_COLUMN_TOL:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    recurring = 0
    for cl in clusters:
        lo, hi = cl[0] - MARKER_COLUMN_TOL, cl[-1] + MARKER_COLUMN_TOL
        if sum(1 for row in rows if any(lo <= x <= hi for x in row)) >= 0.5 * len(rows):
            recurring += 1
    return recurring


def _looks_like_a_table(pmpage, region, members: List[Block]) -> bool:
    """Whether a failed table candidate is a table at all.

    The "reconstruction failed" marker asserts that a table stood here. A
    find_tables candidate is also made over body prose, reference lists and
    figures (R00023 p. 3: no ruling at all, a 45 x 8 candidate over
    double-spaced prose). The marker stays only where the page shows table
    evidence: a horizontal or vertical rule touching the region, or at least
    two column starts that recur across its rows, and no curve, which is a
    figure's sign.
    """
    x0, y0, x1, y1 = region
    box = pymupdf.Rect(x0 - 6, y0 - 6, x1 + 6, y1 + 6)
    w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    ruled = False
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        drawings = []
    for d in drawings:
        r = pymupdf.Rect(d["rect"])
        if not r.intersects(box) and not (r.is_empty and box.contains(r.tl)):
            continue
        if any(item[0] == "c" for item in d.get("items", [])):
            return False
        if (r.height < 1.6 and r.width > 0.5 * w) or (
            r.width < 1.6 and r.height > 0.3 * h
        ):
            ruled = True
    return ruled or _recurring_columns(members, region) >= 2


def detect_tables(pmpage: pymupdf.Page, page: Page) -> None:
    """Find table regions with PyMuPDF, then rebuild the grid.

    PyMuPDF's find_tables replaces surya's table-detection head (it uses ruling
    lines and whitespace projection). Marker's own table_recon then does the
    structure work - it is already weight-free, sweeping several grid
    parameterizations and picking a winner with a deterministic judge.
    """
    page_area = max(pmpage.rect.width * pmpage.rect.height, 1.0)
    found = []
    seen_bboxes = []
    # Candidates of the second pass: horizontal rules only, columns from
    # whitespace. Only these may be cut at their bottom rule. A boxed table
    # is closed by its own frame, and its inner rules say nothing about
    # where it ends (the SBTi criteria tables lost rows to that mistake).
    ruled_only: set = set()
    # Strategy cascade. Ruling-line detection finds fully boxed tables; booktabs
    # tables have only three horizontal rules and no verticals, so a second pass
    # derives the columns from whitespace. The whole-page "text/text" strategy is
    # deliberately excluded - it matches any page and swallows body text.
    for kw in ({}, {"vertical_strategy": "text", "horizontal_strategy": "lines"}):
        try:
            cands = list(pmpage.find_tables(**kw).tables)
        except Exception:
            continue
        for tbl in cands:
            bb = tuple(tbl.bbox)
            area = max((bb[2] - bb[0]) * (bb[3] - bb[1]), 0.0)
            if (
                area > TABLE_CANDIDATE_MAX_PAGE_FRAC * page_area
                or area < TABLE_CANDIDATE_MIN_AREA
            ):
                continue  # a "table" covering the page is the page, not a table
            if any(
                _overlap_frac(bb, prev) > TABLE_CANDIDATE_MAX_OVERLAP
                for prev in seen_bboxes
            ):
                continue
            seen_bboxes.append(bb)
            found.append(tbl)
            if kw:
                ruled_only.add(id(tbl))
    # Broken/segmented booktabs strokes may not form a find_tables candidate.
    # Two matching horizontal rules with intervening text still delimit table
    # content for furniture protection; this does not admit a new table.
    physical_rules, _ = _page_graphics(pmpage)
    page.table_zones.extend(_rule_zones(physical_rules, page))
    if not found:
        return

    consumed: set = set()
    new_blocks: List[Block] = []
    rules, others = _page_graphics(pmpage)
    for tbl in found:
        bbox = tuple(tbl.bbox)
        members = [
            b
            for i, b in enumerate(page.blocks)
            if i not in consumed
            and not b.fill_backed_banner
            and _overlap_frac(b.bbox, bbox) > TABLE_MEMBER_OVERLAP
        ]
        if not members:
            continue
        if _journal_front_matter(members, page.blocks):
            abstract_top = min(
                ln.bbox[1]
                for b in members
                for ln in b.lines
                if re.sub(r"\s+", "", ln.text).rstrip(":").lower() == "abstract"
            )
            preceding = [b for b in page.blocks if b.y_end <= abstract_top]
            title_size = max(
                b.max_size()
                for b in preceding
                if FRONT_MATTER_TITLE_MIN_WORDS
                <= len(b.text.split())
                <= FRONT_MATTER_TITLE_MAX_WORDS
            )
            for block in members + preceding:
                block.journal_front_matter = True
                block.journal_title = (
                    FRONT_MATTER_TITLE_MIN_WORDS
                    <= len(block.text.split())
                    <= FRONT_MATTER_TITLE_MAX_WORDS
                    and block.max_size()
                    >= FRONT_MATTER_JOURNAL_TITLE_SCALE * title_size
                )
            continue  # original blocks remain for heading/paragraph classification

        # The caption and whatever stands under the bottom rule leave the
        # candidate before anything is reconstructed or counted. ``members``
        # is from here on the grid's own source: the text-loss guard and the
        # audit compare table words with table words, so a caption that
        # survived cannot make up for a number that did not.
        caption_block, leftovers, caption_tokens, lines_excluded = None, [], 0, 0
        touched = members
        try:
            cap_lines, out_lines, extent = _isolate_table(
                members, bbox, rules, others, bound_rows=id(tbl) in ruled_only
            )
        except Exception:
            cap_lines, out_lines, extent = [], [], None
        if extent is not None:
            grid_members, caption_block, leftovers, touched = _split_members(
                members, cap_lines, out_lines
            )
            if len(grid_members) == 0:
                caption_block, leftovers, touched, extent = None, [], members, None
            else:
                members = grid_members
                bbox = (
                    bbox[0],
                    max(bbox[1], extent[0]),
                    bbox[2],
                    min(bbox[3], extent[1] + 1.0),
                )
                lines_excluded = len(out_lines)
                if caption_block is not None:
                    caption_tokens = len(caption_block.text.split())

        # find_tables' bbox hugs the ruling lines and can clip the first and
        # last character of each row ("Condition" -> "ndition"). Reconstruct
        # from the union of the member blocks instead, padded slightly.
        region = _bbox_of([m.bbox for m in members] + [bbox])
        region = (region[0] - 4, region[1] - 3, region[2] + 4, region[3] + 3)

        html = ""
        rejected = False
        if reconstruct_table_html is not None:
            lines = _tokens_for_recon(members, region)
            ok, worst = _projection_ok(lines, page)
            if not ok:
                rejected = True
                note_limit(
                    page,
                    "table_projection",
                    round(worst, 3) if math.isfinite(worst) else "non-finite",
                    TABLE_PROJECTION_MARGIN,
                    "candidate kept as prose",
                )
            else:
                try:
                    res = reconstruct_table_html(lines)
                    res = recover_wrapped_lines(lines, res, tbl)
                except Exception:
                    res = None
                if res:
                    html = res[0]

        # PyMuPDF's geometric cells: text assigned by cell bbox, so wrapped
        # lines stay in their cell. Used when the reconstruction is unusable,
        # and also when it is "sane" but has lost words (TABLE_FALLBACK_MIN_KEEP).
        try:
            fallback = (
                "" if rejected else _grid_to_html(_grid_from_members(tbl, members))
            )
        except Exception:
            fallback = ""
        fell_back = False
        if rejected:
            # Neither the reconstruction nor PyMuPDF's cell grid is trusted
            # with these coordinates: the source text stays, as prose.
            html, fell_back = "<rejected>", True
        elif not html or not _table_sane(html):
            # The geometric grid is only the admission oracle here. If it
            # passes the same sanity check, the admitted region renders from
            # its ordered source prose below.
            html = fallback if _table_sane(fallback) else ""
            fell_back = bool(html)
        elif fallback:
            # A usable reconstruction still becomes a prose fallback when it
            # has dropped words. The geometric grid is not required to be
            # "sane" here: a sparse criteria table has many genuinely empty
            # cells, which is what _table_sane rejects. Its word count is the
            # baseline because each source word is assigned by cell geometry.
            kept, cells = _html_word_count(html), _html_word_count(fallback)
            if kept < TABLE_FALLBACK_MIN_KEEP * cells:
                html, fell_back = fallback, True
        if not html:
            continue
        if (
            fell_back
            and not rejected
            and not _looks_like_a_table(pmpage, region, members)
        ):
            # Not a table: the candidate is dropped and its blocks stay on the
            # page, to be classified like any other text, with no marker.
            page.table_candidates_released += 1
            continue
        page.tables_emitted += 1
        page.tables_fell_back += int(fell_back)
        page.table_captions_isolated += int(caption_block is not None)
        page.table_caption_words += caption_tokens
        page.table_lines_excluded += lines_excluded

        for i, b in enumerate(page.blocks):
            if any(b is t for t in touched):
                consumed.add(i)
        if caption_block is not None:
            new_blocks.append(caption_block)
        new_blocks.extend(leftovers)
        tb = Block(
            lines=[ln for m in members for ln in m.lines],
            bbox=bbox,
            page_idx=page.page_idx,
            char_pos=min(m.char_pos for m in members),
            btype="Table",
            html=html if not fell_back else None,
            # Preserve original block/line stream order. In particular, do
            # not dehyphenate: conservation is a source-token multiset check.
            fallback_paragraphs=[
                "\n".join(ln.text.strip() for ln in m.lines if ln.text.strip())
                for m in members
                if m.text.strip()
            ]
            if fell_back
            else [],
        )
        new_blocks.append(tb)

    if new_blocks:
        page.blocks = [b for i, b in enumerate(page.blocks) if i not in consumed]
        page.blocks.extend(new_blocks)
        page.blocks.sort(key=lambda b: b.char_pos)


def _columns_align(
    rows, tol=PROPOSAL_ALIGN_TOL, min_share=PROPOSAL_ALIGN_MIN_SHARE
) -> bool:
    """True when token starts recur at the same x across rows.

    This is the test that separates a table from justified prose. Both can show
    wide inter-word gaps and a steady token count per line, but only a table
    puts its tokens at the *same* x positions row after row - prose word starts
    scatter. Requires at least two such shared columns beyond the left margin.
    """
    if len(rows) < PROPOSAL_MIN_ROWS:
        return False
    starts = [sorted(round(x0, 1) for _t, x0, _x1 in r[0]) for r in rows]
    positions = sorted({x for row in starts for x in row})
    clusters = []
    for x in positions:
        if clusters and x - clusters[-1][-1] <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    shared = 0
    for cl in clusters:
        lo, hi = cl[0] - tol, cl[-1] + tol
        hits = sum(1 for row in starts if any(lo <= x <= hi for x in row))
        if hits >= min_share * len(starts):
            shared += 1
    return shared >= 2


def propose_tables_from_text(pages: List[Page], min_score=PROPOSAL_MIN_SCORE) -> None:
    """Second-chance table detection for pages with no ruling lines.

    find_tables needs vectors or a clean whitespace signal; a scanned page has
    neither (its rules are pixels, not vectors). Marker's layout model supplies
    the region there. The stand-in: offer each remaining multi-line block to
    table_recon and keep the result only when its own deterministic judge scores
    it well - the judge is doing the discrimination that the model would.
    """
    if reconstruct_table_html is None:
        return
    for page in pages:
        for blk in page.blocks:
            if (
                blk.btype == "Table"
                or blk.journal_front_matter
                or len(blk.lines) < 3
                or blk.ignore_for_output
            ):
                continue
            lines = _tokens_for_recon([blk], blk.bbox)
            ok, worst = _projection_ok(lines, page)
            if not ok:
                note_limit(
                    page,
                    "table_projection",
                    round(worst, 3) if math.isfinite(worst) else "non-finite",
                    TABLE_PROJECTION_MARGIN,
                    "proposal kept as prose",
                )
                continue
            multi = [ln for ln in lines if len(ln[0]) >= 2]
            if len(multi) < PROPOSAL_MIN_ROWS:
                continue
            if not _columns_align(multi):
                continue
            try:
                res = reconstruct_table_html(lines)
                res = recover_wrapped_lines(lines, res)
            except Exception:
                continue
            if not res:
                continue
            html, score = res
            ncols = html.count("<th>") or html.split("</tr>")[0].count("<td>")
            if (
                score < min_score
                or not (PROPOSAL_MIN_COLUMNS <= ncols <= PROPOSAL_MAX_COLUMNS)
                or not _table_sane(html)
            ):
                continue
            # Text-loss guard, the proposal path's counterpart of the one in
            # detect_tables. The proposal consumes this block, so the block's
            # own words are the baseline: a grid that keeps fewer than
            # TABLE_FALLBACK_MIN_KEEP of them has dropped rows (justified OCR
            # prose on a two-column scan loses half its lines this way) and
            # the block stays prose. This rejects proposals only; it does not
            # change what is admitted (PLAN-tables items 4 and 5 still stand).
            src_words = len(blk.text.split())
            if (
                src_words
                and _html_word_count(html) < TABLE_FALLBACK_MIN_KEEP * src_words
            ):
                page.proposals_kept_prose += 1
                continue
            page.tables_emitted += 1
            page.proposals_emitted += 1
            blk.btype = "Table"
            blk.html = html
