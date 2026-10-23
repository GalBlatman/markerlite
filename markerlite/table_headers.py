"""Recover a ruled header band before its wrapped labels become body rows."""

import re
from bisect import bisect_right
from collections import Counter
from html import unescape
from statistics import median

from .thresholds import WRAP_RULE_COORD_TOL


def _words(text):
    return Counter(unescape(re.sub(r"<[^>]*>", " ", text)).split())


def _header_rows(band, cuts, columns):
    """Keep spanning levels, then stitch the remaining wrapped leaf labels."""

    def column(span):
        return bisect_right(cuts, (span[1] + span[2]) / 2)

    levels = []
    leaf = [""] * columns
    for i, (spans, _y0, _y1) in enumerate(band):
        later = {column(span) for row, _, _ in band[i + 1 :] for span in row}
        spans_columns = []
        spanning = False
        for text, x0, x1 in spans:
            lo, hi = bisect_right(cuts, x0), bisect_right(cuts, x1)
            covers = set(range(lo, hi + 1))
            wide = hi > lo and covers <= later
            spans_columns.append(
                (
                    text,
                    lo if wide else column((text, x0, x1)),
                    covers if wide else set(),
                )
            )
            spanning |= wide
        if spanning:
            if any(leaf):
                return None  # hierarchical levels must precede leaf wrapping
            row, occupied = [""] * columns, set()
            for text, col, covers in spans_columns:
                covers = covers or {col}
                if occupied & covers:
                    return None
                row[col] = text
                occupied |= covers
            levels.append(row)
        else:
            for text, col, _ in spans_columns:
                leaf[col] = f"{leaf[col]} {text}".strip()
    if not any(leaf):
        return None
    return levels + [leaf]


def recover_ruled_header(lines, original, rule_ys):
    """Three full-width rules identify top, header divider and table bottom.

    Only a multi-line band wholly above the divider is eligible. Rebuild
    columns from the body, preserve every source token, and retain the
    original score. Other geometries keep their current reconstruction.
    """
    if not original or len(rule_ys) != 3:
        return original
    if any(
        not rule_ys[0] - WRAP_RULE_COORD_TOL
        <= (y0 + y1) / 2
        <= rule_ys[-1] + WRAP_RULE_COORD_TOL
        for _, y0, y1 in lines
    ):
        return original  # a caption/note outside the frame is not a header
    divider = rule_ys[1]
    band = [ln for ln in lines if ln[2] <= divider + WRAP_RULE_COORD_TOL]
    body = [ln for ln in lines if ln[1] >= divider - WRAP_RULE_COORD_TOL]
    if len(band) < 2 or not body or len(band) + len(body) != len(lines):
        return original
    try:
        import table_recon as vendor
    except ImportError:
        return original
    data = [ln for ln in body if len(ln[0]) >= vendor.MIN_CELLS_PER_ROW]
    if len(data) < vendor.MIN_TABLE_ROWS:
        return original
    name, best, _score = vendor._pick_winner(
        vendor._candidates([spans for spans, _, _ in data]), None
    )
    if not best:
        return original
    columns, cuts, grid, _ = best
    if len(grid) != len(data):
        return original
    # A span-x0 winner's cuts separate START anchors, not physical cells.
    # Centred header labels need intervals between the body's cell centres.
    centers = [[] for _ in range(columns)]
    for (spans, _, _), expected in zip(data, grid):
        assigned = [""] * columns
        for text, x0, x1 in spans:
            anchor = x0 if name == "span-x0" else (x0 + x1) / 2
            col = bisect_right(cuts, anchor)
            assigned[col] = f"{assigned[col]} {text}".strip()
            centers[col].append((x0 + x1) / 2)
        if assigned != expected:
            return original
    if any(not values for values in centers):
        return original
    midpoints = [median(values) for values in centers]
    if any(a >= b for a, b in zip(midpoints, midpoints[1:])):
        return original
    header_cuts = [(a + b) / 2 for a, b in zip(midpoints, midpoints[1:])]
    headers = _header_rows(band, header_cuts, columns)
    if headers is None:
        return original
    grid_y = [(list(row), ln[1]) for row, ln in zip(grid, data)]
    vendor._attach_wrapped_lines(lines, body[0][1], grid_y, cuts)
    rows = [row for row, _ in grid_y]
    html = vendor._build_html(headers[0], headers[1:] + rows, True)
    source = Counter(text for spans, _, _ in lines for text, _, _ in spans)
    source_words = Counter(" ".join(source.elements()).split())
    if _words(html) != source_words or _words(original[0]) - _words(html):
        return original
    return html, original[1]
