"""Conservative wrapped-cell recovery owned by markerlite, not the vendor.

Keep the vendored winner (columns, assignment convention, and score). Rebuild
its cells from source line identities only when logical rows are unambiguous.
Numeric tables, incomplete recoveries, and uncertain row layouts keep the
original reconstruction and its existing downstream fallback decision.
"""

from bisect import bisect_right
from collections import Counter
from html import unescape
import re
from statistics import median


def _words(text):
    return Counter(unescape(text).split())


def _html_words(text):
    return _words(re.sub(r"<[^>]*>", " ", text))


def _ruled_bounds(table, columns):
    """Only a complete rectangular grid can provide trusted row intervals."""
    if table is None or table.col_count != columns:
        return None
    bounds = []
    for row in table.rows:
        cells = row.cells
        if len(cells) != columns or any(cell is None for cell in cells):
            return None  # spanning/partial cells need a different row model
        top, bottom = cells[0][1], cells[0][3]
        if any(abs(cell[1] - top) > 0.5 or abs(cell[3] - bottom) > 0.5
               for cell in cells):
            return None
        if bottom <= top or (bounds and abs(top - bounds[-1][1]) > 0.5):
            return None
        bounds.append((top, bottom))
    return bounds


def recover_wrapped_lines(lines, original, table=None):
    """Return an improved ``(html, score)`` or the unmodified original.

    The vendor's public result has discarded source-row identity. Reuse its
    pure candidate/selection helpers, without modifying or monkey-patching it,
    to retain that identity and the winner's x intervals before serialization.
    """
    if not original:
        return original
    source_words = _words(" ".join(t for spans, _, _ in lines for t, _, _ in spans))
    old_words = _html_words(original[0])
    if not source_words - old_words:
        return original  # no wrapped words to recover
    try:
        import table_recon as vendor
    except ImportError:
        return original  # retain the installed-Marker fallback if used
    if vendor._find_header_band(lines) is not None:
        return original  # leave the existing numeric-table path untouched

    data_ids = [i for i, (spans, _, _) in enumerate(lines)
                if len(spans) >= vendor.MIN_CELLS_PER_ROW]
    if not data_ids:
        return original
    first_y = min(lines[i][1] for i in data_ids)
    band = [(spans, y0) for spans, y0, _ in lines if y0 < first_y]
    n_header = (sum(x1 - x0 < 200 for spans, _ in band for _, x0, x1 in spans)
                or None) if band else None
    name, best, _ = vendor._pick_winner(
        vendor._candidates([lines[i][0] for i in data_ids]), n_header)
    if not best:
        return original
    columns, cuts, winning_grid, _ = best
    if len(winning_grid) != len(data_ids):
        return original  # never zip a truncated grid to a guessed row suffix

    def assign(spans):
        cells = [""] * columns
        for text, x0, x1 in spans:
            # A span-x0 winner defines intervals for start anchors; center
            # winners define them for centers. Using centers unconditionally
            # sends long wrapped text into its neighbor's column.
            anchor = x0 if name == "span-x0" else (x0 + x1) / 2
            col = bisect_right(cuts, anchor)
            cells[col] = f"{cells[col]} {text}".strip()
        return cells

    # Projection candidates use overlap with occupied x bands. Accept the cut
    # intervals only if they reproduce EVERY original data-row assignment.
    if any(assign(lines[i][0]) != row for i, row in zip(data_ids, winning_grid)):
        return original

    body_ids = [i for i, (_, y0, _) in enumerate(lines) if y0 >= first_y]
    bounds = _ruled_bounds(table, columns)
    if bounds is not None and not band:
        groups = [[] for _ in bounds]
        for i in body_ids:
            _, y0, y1 = lines[i]
            cy = (y0 + y1) / 2
            matches = [j for j, (top, bottom) in enumerate(bounds) if top <= cy < bottom]
            if len(matches) != 1:
                return original
            groups[matches[0]].append(i)
        if any(not group for group in groups):
            return original
    else:
        # Without trustworthy rules, require short first-column record keys
        # and complete row starts. Lines lacking that key are continuations;
        # a partial new record is ambiguous and must keep the old fallback.
        groups = []
        line_height = median(max(y1 - y0, 1) for _, y0, y1 in lines)
        for i in body_ids:
            cells = assign(lines[i][0])
            if cells[0]:
                if not all(cells) or len(cells[0].split()) > 6:
                    return original
                groups.append([])
            if not groups:
                return original
            if (not cells[0] and groups[-1]
                    and lines[i][1] - lines[groups[-1][-1]][2] > line_height):
                return original  # distant prose is not a soft cell wrap
            groups[-1].append(i)
        if len(groups) < vendor.MIN_TABLE_ROWS:
            return original

    grid = []
    for group in groups:
        cells = [""] * columns
        for i in sorted(group, key=lambda i: lines[i][1]):
            for j, text in enumerate(assign(lines[i][0])):
                if text:
                    cells[j] = f"{cells[j]} {text}".strip()
        grid.append(cells)
    if band:
        names, _ = vendor._stitch_band_headers(band, cuts, columns)
    else:
        names, grid = grid[0], grid[1:]
    if not grid:
        return original
    names, grid = vendor._merge_marker_columns(names, grid)
    html = vendor._build_html(names, grid, True)
    new_words = _html_words(html)
    if new_words != source_words or old_words - new_words:
        return original  # all source tokens exactly once; no lost old content
    return html, original[1]
