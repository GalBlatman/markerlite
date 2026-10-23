"""Put rule-bounded spanning labels in their own leftmost grid cell."""

from collections import Counter
from html import escape
from statistics import median

from .gate import GATE_RULE_PAD, _merge
from .render import _TableParser
from .thresholds import RULE_MIN_COVER, WRAP_RULE_COORD_TOL


def _spanning_labels(lines, graphics, region):
    x0, y0, x1, y1 = region
    rules = [
        (y, a, b)
        for y, a, b in _merge(graphics["h"])
        if y0 - GATE_RULE_PAD <= y <= y1 + GATE_RULE_PAD
        and min(b, x1) - max(a, x0) >= RULE_MIN_COVER * (x1 - x0)
    ]
    if len(rules) < 2:
        return []
    left = median(a for _, a, _ in rules)
    right = median(b for _, _, b in rules)
    result = []
    for spans, top, bottom in lines:
        if len(spans) != 1:
            continue
        text, a, b = spans[0]
        mid = (top + bottom) / 2
        above = [y for y, _, _ in rules if y < mid]
        below = [y for y, _, _ in rules if y > mid]
        if not above or not below:
            continue
        lo, hi = max(above), min(below)
        if sum(lo < (u + v) / 2 < hi for _, u, v in lines) != 1:
            continue
        if abs((a + b) / 2 - (left + right) / 2) > (bottom - top) / 2:
            continue
        if any(
            left + WRAP_RULE_COORD_TOL < x < right - WRAP_RULE_COORD_TOL
            and min(v1, hi) > max(v0, lo)
            for x, v0, v1 in graphics["v"]
        ):
            continue  # a drawn cell divider contradicts a full-width span
        result.append((mid, text.split()))
    return sorted(result)


def recover_spanning_columns(lines, html, graphics, region):
    """Relocate only unique complete labels at an existing cell's edge.

    The caller restricts this to already-kept grids. Non-label body cells
    retain their words and order; ambiguous duplicate or embedded matches
    keep the original. The source's ruling lines, not vocabulary, identify
    a spanning row. No new table is admitted by this repair.
    """
    labels = _spanning_labels(lines, graphics, region)
    if not labels:
        return html
    parser = _TableParser()
    parser.feed(html)
    rows = [list(parser.header), *[list(row) for row in parser.rows]]
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        return html
    columns = len(rows[0])
    before = Counter(word for row in rows for cell in row for word in cell.split())
    changed = False
    for _y, words in labels:
        matches = []
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                tokens = cell.split()
                for pos in range(len(tokens) - len(words) + 1):
                    if tokens[pos : pos + len(words)] == words:
                        matches.append((i, j, pos, tokens))
        if len(matches) != 1:
            continue
        i, j, pos, tokens = matches[0]
        label = " ".join(words)
        span = [label] + [""] * (columns - 1)
        if len(tokens) == len(words):
            if any(cell.strip() for k, cell in enumerate(rows[i]) if k != j):
                continue
            if rows[i] != span:
                rows[i] = span
                changed = True
        elif pos == 0:
            rows[i][j] = " ".join(tokens[len(words) :])
            rows.insert(i, span)
            changed = True
        elif pos + len(words) == len(tokens):
            rows[i][j] = " ".join(tokens[:pos])
            rows.insert(i + 1, span)
            changed = True
    after = Counter(word for row in rows for cell in row for word in cell.split())
    if not changed or before != after:
        return html
    head = "".join(f"<th>{escape(cell)}</th>" for cell in rows[0])
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows[1:]
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
