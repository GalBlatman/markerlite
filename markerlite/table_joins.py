"""Conservative vertical continuation links, with source text left on its page."""

import re
import unicodedata

from .model import TABLE_LABEL
from .render import _TableParser
from .thresholds import TABLE_CONTINUATION_X_TOL

_CONTINUED = re.compile(
    r"^\s*[.:–—-]?\s*(?:\(\s*continued\s*\)|\[\s*continued\s*\]|continued\b)",
    re.I,
)


def _caption_identity(block):
    text = " ".join(block.text.split())
    match = TABLE_LABEL.match(text)
    if not match:
        return None
    key = re.sub(r"^\s*(?:table|tbl\.?)\s*", "", match.group(), flags=re.I).casefold()
    return key, bool(_CONTINUED.match(text[match.end() :]))


def _is_caption(block):
    # A bare "Table N (continued)" can be classified as a heading. Its
    # explicit table identity/continuation marker still supplies the link.
    return (
        block.btype in ("Caption", "SectionHeader")
        and _caption_identity(block) is not None
    )


def _leading_captions(table, preceding):
    return [c for c in table.children if c.leads] + preceding


def _grid(table):
    parser = _TableParser()
    parser.feed(table.html or "")
    if (
        not parser.header
        or not any(c.strip() for c in parser.header)
        or not parser.rows
        or any(len(row) != len(parser.header) for row in parser.rows)
    ):
        return None
    header = tuple(
        unicodedata.normalize("NFKC", " ".join(c.split())) for c in parser.header
    )
    return header, parser.rows


def _row_key(text):
    return unicodedata.normalize("NFKC", " ".join(text.split())).casefold()


def link_continued_tables(pages):
    """Link already-kept row continuations; never admit or reconstruct a grid.

    Require consecutive pages, no intervening body blocks, an explicit
    continuation caption with the same table identity, identical headers,
    and matching normalized horizontal bounds. Different-column continuations
    and missing fragments are intentionally ineligible.
    """
    for page in pages:
        for block in page.blocks:
            block.table_join_prev = block.table_join_next = False
            block.table_join_id = None
            block.table_join_caption_columns = 0
    next_id = 1
    keys_by_join = {}
    for left, right in zip(pages, pages[1:]):
        if right.page_idx != left.page_idx + 1:
            continue
        before = [
            b
            for b in left.blocks
            if not b.ignore_for_output and (b.lines or b.btype == "Table")
        ]
        after = [
            b
            for b in right.blocks
            if not b.ignore_for_output and (b.lines or b.btype == "Table")
        ]
        if not before or not after:
            continue
        a = before[-1]
        prefix = []
        for b in after:
            if not _is_caption(b):
                break
            prefix.append(b)
        b = after[len(prefix)] if len(prefix) < len(after) else None
        if a.btype != "Table" or b is None or b.btype != "Table":
            continue
        if a.fallback_paragraphs or b.fallback_paragraphs:
            continue
        preceding = [before[-2]] if len(before) > 1 and _is_caption(before[-2]) else []
        acaps = _leading_captions(a, preceding)
        bcaps = _leading_captions(b, prefix)
        akeys = {_caption_identity(c)[0] for c in acaps if _caption_identity(c)}
        bkeys = [_caption_identity(c) for c in bcaps]
        if (
            len(akeys) != 1
            or not bkeys
            or any(k is None or k[0] not in akeys or not k[1] for k in bkeys)
        ):
            continue
        ga, gb = _grid(a), _grid(b)
        if ga is None or gb is None or ga[0] != gb[0]:
            continue
        header, ar = ga
        _, br = gb
        if any(not row[0].strip() for row in (ar[0], ar[-1], br[0], br[-1])):
            continue  # a boundary row may continue a cell across the page
        akeys_data = {_row_key(row[0]) for row in ar if row[0].strip()}
        bkeys_data = {_row_key(row[0]) for row in br if row[0].strip()}
        previous_keys = keys_by_join.get(a.table_join_id, akeys_data)
        if not previous_keys or not bkeys_data or previous_keys & bkeys_data:
            continue  # repeated keys can be a column-wise continuation
        if any(
            abs(x / max(left.width, 1) - y / max(right.width, 1))
            > TABLE_CONTINUATION_X_TOL
            for x, y in ((a.x_start, b.x_start), (a.x_end, b.x_end))
        ):
            continue
        if a.table_join_id is None:
            a.table_join_id = next_id
            next_id += 1
        b.table_join_id = a.table_join_id
        keys_by_join[a.table_join_id] = previous_keys | bkeys_data
        a.table_join_next = True
        b.table_join_prev = True
        for caption in prefix:
            caption.table_join_caption_columns = len(header)
