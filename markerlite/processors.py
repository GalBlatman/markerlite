"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import math
import re
from statistics import median
from typing import List

import numpy as np
from rapidfuzz import fuzz
from sklearn.cluster import KMeans

from .classification import _symbol_is_notation, footnote_label, note_text_size
from .extraction import _bbox_of
from .model import *
from .tables import _overlap_frac


def _protect_numeric_records(page):
    """Repeated rows of independent numeric cells are table evidence even on
    scans without vector rules. A manuscript number beside prose is not a row
    of numeric cells. Geometry is used for protection, never to reorder text.
    """
    rows = []
    for block in page.blocks:
        for line in block.lines:
            if not re.fullmatch(r"[−-]?\d+(?:[.,]\d+)?", line.text.strip()):
                continue
            mid = (line.bbox[1] + line.bbox[3]) / 2
            row = next((r for y, r in rows if abs(mid - y) < 3), None)
            if row is None:
                row = []
                rows.append((mid, row))
            row.append(line)
    groups = []
    for y, row in rows:
        xs = sorted(ln.bbox[0] for ln in row)
        if len(xs) < 2 or xs[-1] - xs[0] < 30:
            continue
        group = next(
            (
                g
                for cuts, g in groups
                if len(cuts) == len(xs)
                and all(abs(a - b) < 5 for a, b in zip(cuts, xs))
            ),
            None,
        )
        if group is None:
            group = []
            groups.append((xs, group))
        group.append(row)
    for cuts, group in groups:
        if len(group) >= 3:
            page.table_zones.append(_bbox_of([ln.bbox for row in group for ln in row]))


def _furniture_band(page, bbox):
    if bbox[3] <= FURNITURE_HEADER_BAND * page.height:
        return "header"
    if bbox[1] >= FURNITURE_FOOTER_BAND * page.height:
        return "footer"
    return None


def _furniture_protected(page: Page, block: Block) -> bool:
    if block.btype in ("Table", "Figure", "Caption", "Footnote"):
        return True
    if TABLE_LABEL.match(block.text.strip()) or FIGURE_LABEL.match(block.text.strip()):
        return True
    boxes = page.table_zones + [b.bbox for b in page.blocks if b.btype == "Table"]
    for box in boxes:
        for ln in block.lines:
            if _overlap_frac(ln.bbox, box) > 0.5:
                return True
            x0, y0, x1, y1 = ln.bbox
            touching = min(abs(y1 - box[1]), abs(y0 - box[3])) <= FURNITURE_TOUCH_TOL
            # A page-wide running head can have one fragment above a
            # table's top rule. Attachment requires the whole block to align
            # with the table, not just that incidental fragment.
            if (
                touching
                and block.x_start >= box[0] - FURNITURE_X_TOL
                and block.x_end <= box[2] + FURNITURE_X_TOL
            ):
                return True
    return any(
        _overlap_frac(ln.bbox, box) > 0.5
        for box in page.figure_zones
        for ln in block.lines
    )


def _evidence(page, bbox, text, size):
    """One piece of repetition evidence: where a line sits, what it says,
    and how large it is set. ``size`` may be None (a suppressed record keeps
    no type size)."""
    return (page, _furniture_band(page, bbox), bbox[1] / page.height, text, bbox, size)


def _same_place(page, bbox, size, other, other_bbox, other_size) -> bool:
    """Two lines in the same band are the same furniture only if they are
    also aligned alike and set at a similar size. A running head and a
    line of an article's own citation block can share their text and their
    band (R00014 p. 1: the journal name, left-aligned in 6.3 pt, above the
    volume line; the even-page head, centred in 8.3 pt); they are told
    apart by alignment and size. Aligned means the left edges, the right
    edges or the centres agree within FURNITURE_ALIGN_TOL of the page width,
    which tolerates heads whose page number changes length.

    On an OCR page the size is Tesseract's line-box height, not a font
    size: descenders and noise move it by a third (Kitchener 2002 p. 22:
    the same running head measures 8.6 pt there and 6.2 pt on every other
    even page). If either line is on an OCR page only position decides."""
    tol = FURNITURE_ALIGN_TOL * max(page.width, other.width)
    aligned = (
        abs(bbox[0] - other_bbox[0]) <= tol
        or abs(bbox[2] - other_bbox[2]) <= tol
        or abs((bbox[0] + bbox[2]) - (other_bbox[0] + other_bbox[2])) / 2 <= tol
    )
    if not aligned:
        return False
    if size and other_size and not (page.ocr_used or other.ocr_used):
        return max(size, other_size) / min(size, other_size) <= FURNITURE_SIZE_RATIO
    return True


def _line_size(lines) -> float:
    return max(
        (s.size for ln in lines for s in ln.spans if s.text.strip()), default=0.0
    )


def _positional_repeat(page, block, norm, corpus):
    if not norm:
        return False  # numeric fragments must never match the empty string
    band = _furniture_band(page, block.bbox)
    if band is None:
        return False
    y = block.y_start / page.height
    size = _line_size(block.lines)
    return any(
        other.page_idx != page.page_idx
        and other_band == band
        and abs(y - other_y) <= FURNITURE_HEIGHT_TOL
        and text
        and fuzz.ratio(norm, text) > 90
        and _same_place(page, block.bbox, size, other, other_bbox, other_size)
        for other, other_band, other_y, text, other_bbox, other_size in corpus
    )


def _record_suppressed(page: Page, lines, reason: str) -> None:
    """Stable public audit records; PDF page is one-based, bbox is in points.

    Record source lines, not formatted Markdown. Relocation into a caption,
    table, footnote or another paragraph is not suppression.
    """
    for line in lines:
        if line.text.strip():
            page.suppressed.append(
                {
                    "page": page.page_idx + 1,
                    "bbox": list(line.bbox),
                    "text": line.text,
                    "reason": reason,
                }
            )


def _suppress_block(page: Page, block: Block, reason: str) -> None:
    if not block.ignore_for_output:
        _record_suppressed(page, block.lines, reason)
        block.ignore_for_output = True


def proc_line_numbers(
    pages: List[Page],
    margin_frac=LINE_NUMBER_MARGIN_FRAC,
    min_count=LINE_NUMBER_MIN_COUNT,
) -> None:
    """marker/processors/line_numbers.py - manuscript line numbers in the margin.

    Review-copy PDFs number every line down the left edge. Usually each number
    is its own tiny block, so without this they render as a column of one-digit
    paragraphs. A run of many bare integers, all hugging the same margin and
    mostly increasing, is the signature.

    ScholarOne draws the column at single spacing regardless of the text's
    leading, and PyMuPDF then returns all sixty numbers as ONE block. That
    block is caught by the same signature applied to its lines: every line a
    short integer, mostly increasing, the block in the margin.
    """

    def _increasing(vals) -> bool:
        if len(vals) < min_count:
            return False
        inc = sum(1 for a, b in zip(vals, vals[1:]) if 1 <= b - a <= 2)
        return inc >= LINE_NUMBER_MIN_INCREASING * (len(vals) - 1)

    for page in pages:
        body_lines = [
            ln
            for b in page.blocks
            if b.btype in TEXTISH
            and b.width > LINE_NUMBER_MIN_BODY_WIDTH * page.width
            and not b.ignore_for_output
            for ln in b.lines
            if MARGINALIA_HEADER_ZONE * page.height
            < ln.bbox[1]
            < FURNITURE_FOOTER_BAND * page.height
        ]
        body_extent = (
            max(ln.bbox[3] for ln in body_lines) - min(ln.bbox[1] for ln in body_lines)
            if body_lines
            else page.height
        )
        min_extent = min(
            LINE_NUMBER_MIN_PAGE_EXTENT * page.height,
            LINE_NUMBER_MIN_BODY_EXTENT * body_extent,
        )
        cands = []
        for blk in page.blocks:
            if blk.ignore_for_output or _furniture_protected(page, blk):
                continue
            in_left = blk.x_end <= margin_frac * page.width
            in_right = blk.x_start >= (1 - margin_frac) * page.width
            if not (in_left or in_right):
                continue
            t = blk.text.strip()
            if t.isdigit() and len(t) <= 4:
                cands.append((int(t), blk))
                continue
            # one block holding the whole column
            lines = [ln.text.strip() for ln in blk.lines]
            if (
                len(lines) >= min_count
                and all(x.isdigit() and len(x) <= 4 for x in lines)
                and blk.height >= min_extent
                and _increasing([int(x) for x in lines])
            ):
                _suppress_block(page, blk, "proc_line_numbers")
        if len(cands) < min_count:
            continue
        vals = [v for v, _ in sorted(cands, key=lambda c: c[1].y_start)]
        if (
            _increasing(vals)
            and max(b.y_end for _, b in cands) - min(b.y_start for _, b in cands)
            >= min_extent
        ):
            for _v, blk in cands:
                _suppress_block(page, blk, "proc_line_numbers")


def proc_ignore_common(pages: List[Page]) -> None:
    """Repeated boundary blocks require matching edge position and context."""
    candidates = []
    for page in pages:
        blocks = [
            b
            for b in page.blocks
            if b.btype in TEXTISH and b.text.strip() and not b.ignore_for_output
        ]
        for block in [blocks[0], blocks[-1]] if blocks else []:
            if not _furniture_protected(page, block):
                candidates.append((page, block))
    corpus = [
        _evidence(p, b.bbox, _clean_text(b.text), _line_size(b.lines))
        for p, b in candidates
    ]
    for page, block in candidates:
        norm = _clean_text(block.text)
        size = _line_size(block.lines)
        matches = {
            p.page_idx
            for p, band, y, text, other_bbox, other_size in corpus
            if band == _furniture_band(page, block.bbox)
            and abs(y - block.y_start / page.height) <= FURNITURE_HEIGHT_TOL
            and norm
            and fuzz.ratio(norm, text) > 90
            and _same_place(page, block.bbox, size, p, other_bbox, other_size)
        }
        # Retain the original common-boundary pass's four-page minimum.
        # Marginalia below accepts two-page evidence in its narrower bands.
        bare_number = bool(PAGE_NUMBER_ONLY.fullmatch(block.text.strip()))
        # Aggregator margins can put the printed folio above the fixed footer
        # band. A centered bare number below all content is still a folio;
        # provenance stamps have already been removed, and table/figure
        # candidates were excluded above.
        below_content = (
            block.y_start > page.height / 2
            and abs((block.x_start + block.x_end) / 2 - page.width / 2)
            < 0.1 * page.width
            and all(
                other is block
                or other.ignore_for_output
                or not other.text.strip()
                or other.y_end <= block.y_start
                for other in page.blocks
            )
        )
        if (_positional_repeat(page, block, norm, corpus) and len(matches) >= 4) or (
            bare_number and (_furniture_band(page, block.bbox) or below_content)
        ):
            _suppress_block(page, block, "proc_ignore_common")


def _clean_text(text: str) -> str:
    """Furniture text with its page-number tokens removed, for repetition
    matching. A leading or trailing token that merely CONTAINS a digit goes
    too: OCR reads "1995 Suchman 579" on one page and "1995 Suchman $79" on
    the next, and "Suchman $79" missed the fuzzy match against "Suchman"."""
    text = text.replace("\n", " ").strip()
    text = re.sub(r"^\S*\d\S*\s*", "", text)
    text = re.sub(r"\s*\S*\d\S*$", "", text)
    return text


def proc_marginalia(
    pages: List[Page],
    header_zone=MARGINALIA_HEADER_ZONE,
    footer_zone=MARGINALIA_FOOTER_ZONE,
    max_height_frac=MARGINALIA_MAX_HEIGHT_FRAC,
    max_chars=MARGINALIA_MAX_CHARS,
) -> None:
    """Suppress running heads and feet - but only on evidence of repetition.

    The earlier rule deleted anything short sitting in the top 8% of a page.
    On a multi-page document that destroys content: a section heading at the
    top of page 2, or a title on page 1, is short, small, and first in reading
    order, so it matched and vanished silently. Position alone cannot separate
    furniture from content - what makes a running head a running head is that
    it RUNS, i.e. repeats across pages.

    A candidate is now suppressed only when
      * its text, with page numbers stripped, recurs on 2+ pages, or
      * it is nothing but a page number.
    Headings are protected unless they repeat, and page 1 is treated as content
    unless the same text reappears later in the document.
    """
    candidates: List[tuple] = []  # (page_idx, block, normalized_text)

    for page in pages:
        text_blocks = [
            b
            for b in page.blocks
            if b.btype in (*TEXTISH, "Table", "TocEntry")
            and not b.ignore_for_output
            and b.text.strip()
        ]
        if len(text_blocks) < 2:
            continue
        h = page.height or 1

        def yfrac(b):
            return (b.y_start / h, b.y_end / h)

        body = [
            b
            for b in text_blocks
            if not (yfrac(b)[1] <= header_zone or yfrac(b)[0] >= 1 - footer_zone)
        ]
        if not body:
            continue
        body_top = min(yfrac(b)[0] for b in body)
        body_bottom = max(yfrac(b)[1] for b in body)

        for blk in text_blocks:
            if blk.btype == "TocEntry":
                continue
            if _furniture_protected(page, blk):
                continue
            y0, y1 = yfrac(blk)
            if (y1 - y0) > max_height_frac and not PAGE_NUMBER_ONLY.fullmatch(
                blk.text.strip()
            ):
                continue
            t = blk.text.strip()
            if not t or len(t) > max_chars:
                continue
            # Position only, for headers and footers alike. Content is
            # protected by the repetition evidence checked below, not by
            # stream order: a running head is often DRAWN LAST (manuscript
            # templates), and a footer is often drawn FIRST (Acrobat
            # PDFMaker), so ordering guards only ever let furniture through.
            # The foot of a two-column page's left column never repeats
            # across pages, so it needs no order guard either.
            is_header = y1 <= header_zone and y1 <= body_top
            is_footer = y0 >= 1 - footer_zone and y0 >= body_bottom
            if is_header or is_footer:
                candidates.append((page.page_idx, blk, _clean_text(t)))

    if not candidates:
        return

    # A report can use its running head as the only section label. Promote the
    # first head in each repeated contiguous run when the document has at least
    # three such values. Alternating author/title journal heads never form a
    # two-page run and remain furniture.
    header_runs = []
    for idx, blk, norm in candidates:
        page = next(p for p in pages if p.page_idx == idx)
        if blk.y_end / (page.height or 1) > header_zone:
            continue
        if (
            header_runs
            and idx == header_runs[-1][-1][0] + 1
            and norm == header_runs[-1][-1][2]
        ):
            header_runs[-1].append((idx, blk, norm))
        else:
            header_runs.append([(idx, blk, norm)])
    eligible_runs = [
        run for run in header_runs if len(run) >= SECTIONED_HEAD_MIN_RUN_PAGES
    ]
    promoted = set()
    if len({run[0][2] for run in eligible_runs}) >= SECTIONED_HEAD_MIN_DISTINCT:
        lookup = {p.page_idx: p for p in pages}
        for run in eligible_runs:
            idx, blk, _norm = run[0]
            page = lookup[idx]
            blk.btype = "SectionHeader"
            blk.heading_level = 2
            page.blocks.remove(blk)
            page.blocks.insert(0, blk)
            page.section_heads_emitted.append(
                {"page": idx + 1, "text": blk.text.strip()}
            )
            promoted.add(id(blk))

    corpus = []
    lookup = {p.page_idx: p for p in pages}
    for idx, blk, norm in candidates:
        p = lookup[idx]
        corpus.append(_evidence(p, blk.bbox, norm, _line_size(blk.lines)))
    # Earlier furniture removal must not erase the repetition evidence for
    # a split header (year, author and page number in separate blocks).
    for page in pages:
        for record in page.suppressed:
            if record["reason"] == "proc_ignore_common":
                corpus.append(
                    _evidence(page, record["bbox"], _clean_text(record["text"]), None)
                )
    merged = []
    for page in pages:
        for blk in page.blocks:
            if (
                len(blk.lines) < 2
                or blk.ignore_for_output
                or _furniture_protected(page, blk)
            ):
                continue
            first = blk.lines[0]
            if first.bbox[3] > FURNITURE_HEADER_BAND * page.height:
                continue
            probe = Block(
                lines=[first],
                bbox=first.bbox,
                page_idx=page.page_idx,
                char_pos=first.char_pos,
            )
            norm = _clean_text(first.text)
            # the first line of a block is header evidence wherever its band
            entry = _evidence(page, first.bbox, norm, _line_size([first]))
            corpus.append((page, "header", *entry[2:]))
            merged.append((page, blk, probe, norm))
    for idx, blk, norm in candidates:
        page = lookup[idx]
        if id(blk) in promoted:
            continue
        repeats = _positional_repeat(page, blk, norm, corpus)
        bare_number = bool(PAGE_NUMBER_ONLY.fullmatch(blk.text.strip()))
        if repeats or bare_number:
            _suppress_block(page, blk, "proc_marginalia")
    for page, blk, probe, norm in merged:
        bare_number = bool(PAGE_NUMBER_ONLY.fullmatch(probe.text.strip()))
        if not bare_number and not _positional_repeat(page, probe, norm, corpus):
            continue
        head_size = max((s.size for s in blk.lines[0].spans), default=0)
        rest_size = max((s.size for ln in blk.lines[1:] for s in ln.spans), default=0)
        if bare_number or (rest_size and head_size < FOOTNOTE_MAX_SIZE * rest_size):
            _record_suppressed(page, blk.lines[:1], "proc_marginalia")
            blk.lines = blk.lines[1:]
            blk.bbox = _bbox_of([ln.bbox for ln in blk.lines])
            blk.char_pos = blk.lines[0].char_pos


def proc_footnotes(pages: List[Page]) -> None:
    """Relabel stragglers, merge wrapped continuations, push notes to the bottom.

    marker/processors/footnote.py pushes footnotes to the page foot. Two things
    are added here. Blocks the classifier missed (small type, page foot, marker
    at the start) are relabeled - including ones it called ListItem. And a
    Footnote block that does NOT start with a marker is a wrapped continuation
    of the note above it, so it is folded into that note. Without the merge,
    one note wrapped across two blocks became two anonymous definitions.
    """
    for page in pages:
        h = page.height or 1
        body_sizes = [
            b.max_size()
            for b in page.blocks
            if b.btype == "Text" and not b.ignore_for_output
        ]
        body = median(body_sizes) if body_sizes else 0
        for blk in page.blocks:
            if blk.btype not in ("Text", "ListItem") or blk.ignore_for_output:
                continue
            if blk.y_start / h < FOOTNOTE_MIN_Y:
                continue
            if body and note_text_size(blk) >= body * FOOTNOTE_MAX_SIZE:
                continue
            if not FOOTNOTE_MARKER.match(blk.text.strip()):
                continue
            if SIGNIFICANCE_LEGEND.match(blk.text.strip()):
                continue
            if _symbol_is_notation(blk, page):
                continue
            blk.btype = "Footnote"

        # A small-type block in the foot zone with no marker, immediately after
        # a note in reading order, is that note's wrapped continuation.
        prev_was_note = False
        for blk in page.blocks:
            if blk.ignore_for_output:
                continue
            if blk.btype == "Footnote":
                prev_was_note = True
                continue
            if (
                prev_was_note
                and blk.btype in ("Text", "ListItem")
                and blk.y_start / h >= FOOTNOTE_MIN_Y
                and (not body or note_text_size(blk) < body * FOOTNOTE_MAX_SIZE)
                and not FOOTNOTE_MARKER.match(blk.text.strip())
                and not PAGE_NUMBER_ONLY.match(blk.text.strip())
            ):
                blk.btype = "Footnote"
                continue
            prev_was_note = False

        notes = [
            b for b in page.blocks if b.btype == "Footnote" and not b.ignore_for_output
        ]
        if not notes:
            continue

        # Fold continuation blocks into the note above them. A block that opens
        # without a marker, in the same small type, is the tail of a wrapped
        # note, not a new one.
        merged: List[Block] = []
        prev_num = None
        for blk in notes:
            label, _ = footnote_label(blk.text.strip())
            # Notes on a page are numbered upward. A block that opens with a
            # number no larger than the previous note's is a continuation
            # whose first word happens to be a number ("2 of them were ...").
            if label is not None and label.isdigit():
                if prev_num is not None and int(label) <= prev_num:
                    label = None
                else:
                    prev_num = int(label)
            if merged and label is None:
                prev = merged[-1]
                prev.lines.extend(blk.lines)
                prev.bbox = _bbox_of([ln.bbox for ln in prev.lines])
                page.blocks.remove(blk)
                continue
            merged.append(blk)

        for n in merged:
            page.blocks.remove(n)
        page.blocks.extend(merged)


def proc_section_levels(
    pages: List[Page],
    level_count=4,
    merge_threshold=0.25,
    default_level=2,
    height_tolerance=0.99,
) -> None:
    """marker/processors/sectionheader.py - KMeans over heading line heights."""
    headers = [b for p in pages for b in p.blocks if b.btype == "SectionHeader"]
    heights = [b.line_height() for b in headers]
    ranges = _bucket_headings(heights, level_count, merge_threshold)
    for blk, hgt in zip(headers, heights):
        if hgt > 0:
            for idx, (lo, _hi) in enumerate(ranges):
                if hgt >= lo * height_tolerance:
                    blk.heading_level = idx + 1
                    break
        if blk.heading_level is None:
            blk.heading_level = default_level

    _levels_from_numbering(headers)


def _levels_from_numbering(headers: List[Block]) -> None:
    """Prefer section numbering over font size for heading depth.

    Journals often set `1 Introduction` and `3.1 Boundary conditions` in the
    same face at the same size, which leaves the line-height clustering nothing
    to separate - every heading lands on one level and the outline is flat. The
    numbering states the depth outright, so when a document numbers its
    headings, that wins. Unnumbered headings keep their size-derived level, so
    a title above `1 ...` still outranks it.
    """
    numbered = []
    for blk in headers:
        m = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+\S", blk.text.strip())
        if m:
            numbered.append((blk, m.group(1).count(".") + 1))
    if len(numbered) < 2:
        return
    for blk, depth in numbered:
        blk.heading_level = min(depth + 1, 6)


def _bucket_headings(
    line_heights: List[float], level_count: int, merge_threshold: float
):
    if len(line_heights) <= level_count:
        return []
    data = np.asarray(line_heights).reshape(-1, 1)
    labels = KMeans(n_clusters=level_count, random_state=0, n_init="auto").fit_predict(
        data
    )
    data_labels = np.concatenate([data, labels.reshape(-1, 1)], axis=1)
    # Marker sorts this with np.sort(..., axis=0), which sorts the value and
    # label columns independently and so scrambles the value->cluster pairing;
    # heading levels come out permuted. Sort by row instead.
    data_labels = data_labels[np.argsort(data_labels[:, 0], kind="stable")]
    cluster_means = {
        int(lb): float(np.mean(data_labels[data_labels[:, 1] == lb, 0]))
        for lb in np.unique(labels)
    }
    label_max = label_min = None
    ranges, prev = [], None
    for row in data_labels:
        value, label = float(row[0]), int(row[1])
        if prev is not None and label != prev:
            if cluster_means[label] * merge_threshold < cluster_means[prev]:
                ranges.append((label_min, label_max))
                label_min = label_max = None
        label_min = value if label_min is None else min(label_min, value)
        label_max = value if label_max is None else max(label_max, value)
        prev = label
    if label_min is not None:
        ranges.append((label_min, label_max))
    ranges = sorted(ranges, reverse=True)
    # KMeans is asked for level_count clusters even when fewer distinct heading
    # sizes exist, so it splits one size across clusters and invents a level.
    # Collapse ranges that start at the same height.
    deduped, seen = [], set()
    for lo, hi in ranges:
        key = round(lo, 1)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((lo, hi))
    return deduped


def proc_reflow(
    pages: List[Page],
    max_gap_lines=REFLOW_MAX_GAP_LINES,
    ragged_tol=REFLOW_SIZE_DELTA,
    indent_frac=REFLOW_X_TOL,
    margin_frac=REFLOW_COLUMN_MARGIN,
) -> None:
    """Rejoin lines that the extractor split into one block each.

    Double-spaced manuscripts put enough space between lines that PyMuPDF
    returns every line as its own block, and every block then rendered as its
    own paragraph. Two consecutive Text blocks are the same paragraph when they
    sit close enough vertically (double spacing allowed), the first runs to
    the column's right edge (ragged-right tolerated), and the second does not
    open with a first-line indent - the indent is how the document itself
    marks a paragraph boundary.
    """
    for page in pages:
        texts = [
            b
            for b in page.blocks
            if b.btype == "Text" and not b.ignore_for_output and b.lines
        ]
        if len(texts) < 2:
            continue
        # The column edges come from body-sized blocks that are not parked in
        # a margin. A line-number column at x=8 once set ``left`` for the whole
        # page, which made every body line look indented and stopped all
        # joining (the Ragins manuscript case).
        size_med = median([b.max_size() for b in texts])
        body_blocks = [
            b
            for b in texts
            if b.max_size() >= REFLOW_BODY_SCALE * size_med
            and b.x_end > margin_frac * page.width
            and b.x_start < (1 - margin_frac) * page.width
        ] or texts
        left = min(b.x_start for b in body_blocks)
        right = max(b.x_end for b in body_blocks)
        width = max(right - left, 1.0)
        lh = median(
            [b.line_height() for b in body_blocks if b.line_height() > 0] or [12.0]
        )

        merged: List[Block] = []
        grown: set = set()  # blocks assembled here from single lines
        for blk in page.blocks:
            prev = merged[-1] if merged else None
            if (
                prev is not None
                and blk.btype == "Text"
                and prev.btype == "Text"
                and not blk.ignore_for_output
                and not prev.ignore_for_output
                and blk.lines
                and prev.lines
            ):
                # Only ever join a SINGLE line onto a run of single lines. A
                # block PyMuPDF already built with several lines means its own
                # paragraph grouping worked, and block-style paragraphs (no
                # indent, spacing only) must not be welded together.
                prev_single = len(prev.lines) == 1 or id(prev) in grown
                if len(blk.lines) == 1 and prev_single:
                    gap = blk.y_start - prev.y_end
                    last = prev.lines[-1]
                    full_width = last.x_end >= right - ragged_tol * width
                    indented = blk.lines[0].x_start > left + indent_frac * page.width
                    size_ok = abs(blk.max_size() - prev.max_size()) < 1.0
                    if (
                        -2 < gap < max_gap_lines * lh
                        and full_width
                        and not indented
                        and size_ok
                    ):
                        prev.lines.extend(blk.lines)
                        prev.bbox = _bbox_of([ln.bbox for ln in prev.lines])
                        grown.add(id(prev))
                        continue
            merged.append(blk)
        page.blocks = merged


def proc_continuation(
    pages: List[Page], column_gap_ratio=CONTINUATION_COLUMN_GAP
) -> None:
    """marker/processors/text.py - paragraphs continuing across columns/pages.

    Marker skips single-line blocks outright. Here a single-line block is
    still considered when its line ends in a hyphen: a paragraph that starts
    on the last line of a column and breaks mid-word is a legitimate layout,
    and the hyphen is unambiguous evidence. The full-width test alone is not
    accepted for one line, because a lone line is trivially "full width".
    """
    flat = _flat_text_blocks(pages)
    for i, blk in enumerate(flat[:-1]):
        if blk.btype not in ("Text",) or not blk.lines:
            continue
        nxt = flat[i + 1]
        if nxt.btype != "Text" or nxt.ignore_for_output:
            continue

        column_gap = blk.width * column_gap_ratio
        column_break = page_break = False
        next_in_first_quadrant = False

        if nxt.page_idx == blk.page_idx:
            column_break = (
                math.floor(nxt.y_start) <= math.ceil(blk.y_start)
                and nxt.x_start > blk.x_end + column_gap
            )
        else:
            page_break = True
            npage = pages[nxt.page_idx]
            next_in_first_quadrant = (
                nxt.x_start < npage.width // 2 and nxt.y_start < npage.height // 2
            )
        if not (column_break or page_break):
            continue

        min_x = math.ceil(min(ln.x_start for ln in nxt.lines))
        next_starts_indented = nxt.lines[0].x_start > min_x

        lines = [ln for ln in blk.lines if ln.width > 1]
        last_full_width = last_hyphenated = False
        if lines:
            max_x = math.floor(max(ln.x_end for ln in lines))
            last_full_width = lines[-1].x_end >= max_x
            last_hyphenated = bool(HYPHEN_END.match(lines[-1].text.strip()))
        if len(blk.lines) < 2 and not last_hyphenated:
            continue

        if (
            (last_full_width or last_hyphenated)
            and not next_starts_indented
            and ((next_in_first_quadrant and page_break) or column_break)
        ):
            blk.has_continuation = True


def _flat_text_blocks(pages: List[Page]) -> List[Block]:
    out = []
    for p in pages:
        for b in p.blocks:
            if b.ignore_for_output or b.btype in ("PageHeader", "PageFooter"):
                continue
            out.append(b)
    return out


def proc_blockquote(
    pages: List[Page],
    min_x_indent=BLOCKQUOTE_MIN_INDENT,
    x_tol=BLOCKQUOTE_X_TOL,
) -> None:
    """marker/processors/blockquote.py."""
    for page in pages:
        blocks = [
            b for b in page.blocks if b.btype == "Text" and not b.ignore_for_output
        ]
        for i, blk in enumerate(blocks[:-1]):
            if len(blk.lines) < 2:
                continue
            nxt = blocks[i + 1]
            if len(nxt.lines) < 2:
                continue
            matching_end = abs(nxt.x_end - blk.x_end) < x_tol * max(blk.width, 1)
            matching_start = abs(nxt.x_start - blk.x_start) < x_tol * max(blk.width, 1)
            # A real block quote is inset on BOTH sides. Requiring only a left
            # indent turned every indented run - and several section headings -
            # into quotes.
            x_indent = (
                nxt.x_start > blk.x_start + min_x_indent * blk.width
                and nxt.x_end < blk.x_end - 0.02 * blk.width
            )
            y_indent = nxt.y_start > blk.y_end
            if blk.blockquote:
                nxt.blockquote = (matching_end and matching_start) or (
                    x_indent and y_indent
                )
                nxt.blockquote_level = blk.blockquote_level + (
                    1 if (x_indent and y_indent) else 0
                )
            elif x_indent and y_indent:
                nxt.blockquote = True
                nxt.blockquote_level = 1


def proc_list_indent(pages: List[Page], min_x_indent=LIST_MIN_INDENT) -> None:
    """marker/processors/list.py - nesting depth from x-indentation."""
    for page in pages:
        items = [
            b for b in page.blocks if b.btype == "ListItem" and not b.ignore_for_output
        ]
        if not items:
            continue
        tol = min_x_indent * page.width
        stack: List[Block] = []
        for item in items:
            while stack and item.x_start <= stack[-1].x_start + tol:
                stack.pop()
            if stack:
                item.list_indent = stack[-1].list_indent
                if item.x_start > stack[-1].x_start + tol:
                    item.list_indent += 1
            else:
                item.list_indent = 0
            stack.append(item)


def proc_code(pages: List[Page]) -> None:
    """marker/processors/code.py - rebuild leading indentation from geometry.

    The indent is the line's offset over the block's average glyph width. A
    crafted PDF can make that width non-finite or vanishingly small, and the
    indent then becomes millions of spaces. Below CODE_MIN_CHAR_WIDTH the
    lines keep no rebuilt indent; an indent above CODE_MAX_INDENT is cut to
    it. Either way the code text is kept and the page records the limit.
    """
    for page in pages:
        for blk in page.blocks:
            if blk.btype != "Code":
                continue
            min_left = min(ln.x_start for ln in blk.lines)
            total_width = sum(ln.width for ln in blk.lines)
            total_chars = sum(len(ln.text) for ln in blk.lines)
            avg_char_width = total_width / max(total_chars, 1)
            usable = (
                math.isfinite(avg_char_width) and avg_char_width >= CODE_MIN_CHAR_WIDTH
            )
            if avg_char_width and not usable:
                note_limit(
                    page,
                    "code_char_width",
                    round(avg_char_width, 4)
                    if math.isfinite(avg_char_width)
                    else "non-finite",
                    CODE_MIN_CHAR_WIDTH,
                    "indentation not rebuilt",
                )
            widest = 0
            out = []
            for ln in blk.lines:
                prefix = ""
                if usable:
                    offset = ln.x_start - min_left
                    spaces = (
                        int(offset / avg_char_width) if math.isfinite(offset) else 0
                    )
                    widest = max(widest, spaces)
                    prefix = " " * min(max(0, spaces), CODE_MAX_INDENT)
                out.append(prefix + ln.text)
            if widest > CODE_MAX_INDENT:
                note_limit(
                    page,
                    "code_indent",
                    widest,
                    CODE_MAX_INDENT,
                    "indentation cut to the cap",
                )
            blk.code = "\n".join(out).rstrip()


def proc_merge_equations(pages: List[Page], gap_frac=EQUATION_MERGE_GAP) -> None:
    """Re-assemble a display equation from the fragments the text layer emits.

    A LaTeX display equation is not one block: numerators, summation limits, the
    equation number and the operator glyphs each arrive as separate text blocks.
    Marker sidesteps this by cropping the layout model's single Equation region
    and running LaTeX OCR over it. Here, consecutive fragments that overlap
    horizontally and sit within ~2 line-heights of each other are merged back
    into one region, so the vision hand-off gets a whole equation rather than
    five slivers.
    """
    for page in pages:
        merged: List[Block] = []
        for blk in page.blocks:
            prev = merged[-1] if merged else None
            if (
                prev is not None
                and blk.btype == "Equation"
                and prev.btype == "Equation"
                and prev.page_idx == blk.page_idx
            ):
                # Fragments of one display equation sit adjacent either
                # vertically (numerator over denominator) or horizontally
                # (summation sign beside its summand, equation number at the
                # right margin), so measure the gap on both axes.
                ygap = max(
                    0.0, max(prev.y_start, blk.y_start) - min(prev.y_end, blk.y_end)
                )
                xgap = max(
                    0.0, max(prev.x_start, blk.x_start) - min(prev.x_end, blk.x_end)
                )
                span = max(prev.line_height(), blk.line_height(), 1.0)
                if ygap < gap_frac * span and xgap < gap_frac * span:
                    prev.lines.extend(blk.lines)
                    prev.bbox = (
                        min(prev.x_start, blk.x_start),
                        min(prev.y_start, blk.y_start),
                        max(prev.x_end, blk.x_end),
                        max(prev.y_end, blk.y_end),
                    )
                    continue
            merged.append(blk)
        page.blocks = merged


def proc_captions(pages: List[Page], gap_threshold=CAPTION_GAP) -> None:
    """marker/builders/structure.py::group_caption_blocks - keep captions with figures."""
    for page in pages:
        gap_px = gap_threshold * page.height
        blocks = page.blocks
        for i, blk in enumerate(blocks):
            if blk.btype not in ("Table", "Figure"):
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(blocks) and blocks[j].btype == "Caption":
                    # a table does not own a figure's caption: the figure
                    # would then go unmarked (Peng 2009 p. 2)
                    if blk.btype == "Table" and FIGURE_CAPTION.match(
                        blocks[j].text.strip()
                    ):
                        continue
                    gap = max(
                        0.0,
                        max(blocks[j].y_start, blk.y_start)
                        - min(blocks[j].y_end, blk.y_end),
                    )
                    if gap < gap_px:
                        blk.children.append(blocks[j])
                        blocks[j].ignore_for_output = True
