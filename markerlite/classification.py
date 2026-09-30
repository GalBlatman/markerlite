"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from statistics import median
from typing import List

from .extraction import _bbox_of
from .model import *


def body_font_size(pages: List[Page]) -> float:
    weighted = Counter()
    for p in pages:
        for b in p.blocks:
            for s in b.spans:
                t = s.text.strip()
                if t:
                    weighted[round(s.size, 1)] += len(t)
    if not weighted:
        return 10.0
    return weighted.most_common(1)[0][0]


def classify(pages: List[Page], body_size: float) -> None:
    # Set once a "References" line has been seen: past it, an OCR page's
    # title-case lines are author names, not headings.
    in_refs = False
    # A reference list is open from its heading to the next heading. Inside
    # it a leading star or dagger marks the entry, it does not open a note.
    list_open = False
    for page in pages:
        for blk in page.blocks:
            if blk.btype == "Table":
                continue
            if blk.btype == "Caption":
                continue  # split off a table candidate by detect_tables
            text = blk.text.strip()
            if not text:
                blk.ignore_for_output = True
                continue

            if blk.journal_front_matter:
                # Keep the original blocks. A narrow journal title may wrap
                # beyond the ordinary three-line heading limit; author and
                # DOI typography should remain prose, not headings/equations.
                blk.btype = "SectionHeader" if blk.journal_title else "Text"
                continue

            first = blk.lines[0].text.strip()
            if REF_LIST_HEAD.match(text) and len(blk.lines) == 1:
                list_open = True
            else:
                blk.in_reference_list = list_open

            if _is_equation(blk, page, text):
                blk.btype = "Equation"
                blk.needs_vision = True
                continue
            if blk.font_ratio("mono") > MONO_MIN_SHARE and len(blk.lines) > 1:
                blk.btype = "Code"
                continue
            if CAPTION_START.match(first) and len(text) < 900:
                blk.btype = "Caption"
                continue
            # Headings are tested BEFORE lists: "2. Method" satisfies the list
            # pattern too, and a numbered heading must not become a bullet.
            is_head = _is_heading(
                blk, body_size, text, first, ocr=page.ocr_used, in_refs=in_refs
            )
            # The references keyword itself is still a heading; the list
            # starts after it.
            if BIB_HINT.match(text):
                in_refs = True
            if is_head:
                blk.btype = "SectionHeader"
                if not REF_LIST_HEAD.match(text):
                    list_open = False
                    blk.in_reference_list = False
                continue
            # Footnotes before lists: "1. Smith and Lee..." at the foot of the
            # page in small type is a note, but it also matches the list-item
            # pattern, and the list test used to win. Numbered footnotes then
            # rendered as bullets and never reached the footnote path at all.
            if _is_footnote(blk, page, body_size, first):
                blk.btype = "Footnote"
                continue
            if LIST_ITEM_START.match(first):
                blk.btype = "ListItem"
                continue
            blk.btype = "Text"

    _split_list_blocks(pages)
    _unmark_lone_lists(pages)
    _demote_toc(pages)


def _demote_toc(pages: List[Page], min_run=TOC_MIN_RUN) -> None:
    """A table of contents is a list, not 40 headings.

    Contents entries are short, title-shaped and often set in the heading face,
    so they classify as SectionHeader and then flood the document outline. A run
    of lines that each end in a page number is the giveaway.
    """
    for page in pages:
        if _demote_split_toc_columns(page, min_run):
            continue
        run: List[Block] = []
        for blk in list(page.blocks) + [None]:
            hit = False
            if blk is not None and blk.btype in ("SectionHeader", "Text", "ListItem"):
                t = blk.text.strip()
                hit = bool(TOC_LINE.match(t)) and len(t) < 160
            if hit:
                run.append(blk)
                continue
            if len(run) >= min_run:
                for b in run:
                    b.btype = "TocEntry"
            run = []


def _demote_split_toc_columns(page: Page, min_run: int) -> bool:
    """Pair a detached right-hand page-number column with its title lines."""
    number_blocks = [
        block
        for block in page.blocks
        if block.lines
        and block.x_start >= TOC_NUMBER_COLUMN_MIN_X * page.width
        and all(PAGE_NUMBER_ONLY.match(line.text.strip()) for line in block.lines)
    ]
    if not number_blocks:
        return False
    number_lines = [line for block in number_blocks for line in block.lines]
    if len(number_lines) < min_run:
        return False

    number_left = min(block.x_start for block in number_blocks)
    available = list(number_lines)
    matches: dict[int, list[tuple[Line, Line]]] = {}
    for block in page.blocks:
        if block in number_blocks or block.x_end >= number_left:
            continue
        for line in block.lines:
            centre = (line.bbox[1] + line.bbox[3]) / 2
            candidates = sorted(
                available,
                key=lambda number: abs(centre - (number.bbox[1] + number.bbox[3]) / 2),
            )
            if not candidates:
                continue
            number = candidates[0]
            number_centre = (number.bbox[1] + number.bbox[3]) / 2
            if abs(centre - number_centre) > TOC_COLUMN_Y_TOL:
                continue
            matches.setdefault(id(block), []).append((line, number))
            available.remove(number)

    matched = sum(len(items) for items in matches.values())
    if matched < min_run or matched < TOC_COLUMN_MATCH_MIN_SHARE * len(number_lines):
        return False
    matched_blocks = [block for block in page.blocks if id(block) in matches]
    if any(len(matches[id(block)]) != len(block.lines) for block in matched_blocks):
        return False

    rebuilt = []
    for block in page.blocks:
        if block in number_blocks:
            continue
        if id(block) not in matches:
            rebuilt.append(block)
            continue
        for line, number in matches[id(block)]:
            spans = list(line.spans)
            spans[-1] = replace(
                spans[-1], text=spans[-1].text.rstrip() + "  " + number.text.strip()
            )
            joined = Line(
                spans=spans,
                bbox=_bbox_of([line.bbox, number.bbox]),
                char_pos=line.char_pos,
            )
            rebuilt.append(
                Block(
                    lines=[joined],
                    bbox=joined.bbox,
                    page_idx=block.page_idx,
                    char_pos=line.char_pos,
                    btype="TocEntry",
                )
            )
    page.blocks = rebuilt
    first_entry = next(
        (index for index, block in enumerate(page.blocks) if block.btype == "TocEntry"),
        None,
    )
    if first_entry is not None:
        top = min(line.bbox[1] for items in matches.values() for line, _ in items)
        headers = [
            block
            for block in page.blocks
            if block.btype == "SectionHeader" and block.y_end <= top
        ]
        for header in headers:
            page.blocks.remove(header)
        first_entry = next(
            index
            for index, block in enumerate(page.blocks)
            if block.btype == "TocEntry"
        )
        page.blocks[first_entry:first_entry] = headers
    return True


def _split_list_blocks(pages: List[Page]) -> None:
    """marker/builders/structure.py::split_list_groups.

    A layout region (or, here, an OCR paragraph) can hold a whole bullet list.
    Split it into one ListItem per bullet boundary so the renderer emits items
    rather than one run-on paragraph.
    """
    for page in pages:
        out: List[Block] = []
        for blk in page.blocks:
            if blk.btype not in ("Text", "ListItem") or len(blk.lines) < 2:
                out.append(blk)
                continue
            bullets = [
                i for i, ln in enumerate(blk.lines) if LIST_ITEM_START.match(ln.text)
            ]
            if len(bullets) < 2 or bullets[0] != 0:
                out.append(blk)
                continue
            groups: List[List[Line]] = []
            for i, ln in enumerate(blk.lines):
                if i in bullets and (groups or i == 0):
                    groups.append([ln])
                elif groups:
                    groups[-1].append(ln)
            for grp in groups:
                out.append(
                    Block(
                        lines=grp,
                        bbox=_bbox_of([ln.bbox for ln in grp]),
                        page_idx=blk.page_idx,
                        char_pos=grp[0].char_pos,
                        btype="ListItem",
                    )
                )
        page.blocks = out


def _unmark_lone_lists(pages: List[Page]) -> None:
    """marker/builders/structure.py::unmark_lists - "if lists aren't grouped,
    unmark them as list items". An isolated bullet-shaped block ("A. Researcher
    and B. Coauthor") is prose that happens to start like a list item."""
    for page in pages:
        items = [i for i, b in enumerate(page.blocks) if b.btype == "ListItem"]
        grouped = set()
        for i in items:
            if (i - 1) in items or (i + 1) in items:
                grouped.add(i)
        for i in items:
            if i not in grouped:
                page.blocks[i].btype = "Text"


def _is_equation(blk: Block, page: Page, text: str) -> bool:
    """Math evidence from glyphs and placement, not just font names.

    The font-only rule missed the most common real-world display equation -
    Symbol for the operators, Times for everything else - because the Times half
    drags the math-font ratio under any usable threshold. That block then looked
    short, centred and punctuation-free, i.e. exactly like a heading.
    """
    if len(text) > 400 or len(blk.lines) > 6:
        return False

    math_font = blk.font_ratio("math")
    dense = [c for c in text if not c.isspace()]
    math_chars = sum(1 for c in dense if MATH_CHARS.match(c)) / max(len(dense), 1)
    words = [w for w in re.split(r"\s+", text) if re.search(r"[A-Za-z]{3,}", w)]

    # Centred and inset on both sides - how display equations are set.
    centre = (blk.x_start + blk.x_end) / 2
    centred = (
        abs(centre - page.width / 2) < EQUATION_CENTER_TOL * page.width
        and blk.width < EQUATION_MAX_WIDTH * page.width
    )
    numbered = bool(EQ_NUMBER.search(text))
    has_ops = bool(MATH_OPS.search(text))

    if math_font > EQUATION_MATH_FONT_STRONG:
        return True
    if math_font > EQUATION_MATH_FONT_WEAK and len(text) < 40:
        return True
    # Few real words, actual operators, and either math glyphs, an equation
    # number, or display placement.
    if (
        len(words) <= 4
        and has_ops
        and (math_chars > EQUATION_MATH_CHAR_WEAK or numbered or centred)
    ):
        return True
    if math_chars > EQUATION_MATH_CHAR_STRONG and has_ops:
        return True
    return False


def _symbol_is_notation(blk: Block, page: Page) -> bool:
    """True when a block that opens with a footnote symbol is NOT a note.

    The glyphs are not banned: a star footnote is a real thing. The decision
    is taken from context. The block is notation when
      - it is a line of a significance legend, with or without its relation
        glyph, or carries three or more runs of marks on its first line;
      - it stands inside a recognised reference list;
      - it opens like a reference ("* Surname, I.") and the page either
        explains its marks in a legend line or holds several such entries.
    """
    if not blk.lines:
        return False
    first = blk.lines[0].text.strip()
    if not SYMBOL_LED.match(first):
        return False
    if SIGNIFICANCE_LEGEND.match(first) or SIGNIFICANCE_LEGEND_BARE.match(first):
        return True
    if len(re.findall(r"[*\u2020\u2021]+", first)) >= 3:
        return True
    if blk.in_reference_list:
        return True
    if REF_ENTRY_SHAPE.match(first):
        entries, legend = 0, False
        for other in page.blocks:
            if not other.lines or other.btype == "Table":
                continue
            head = other.lines[0].text.strip()
            if SYMBOL_LED.match(head) and REF_ENTRY_SHAPE.match(head):
                entries += 1
            if MARK_LEGEND.search(other.text):
                legend = True
        return legend or entries >= 2
    return False


def footnote_label(text: str):
    """(label, body) for a note that starts with a marker, else (None, text)."""
    m = FOOTNOTE_MARKER.match(text)
    if not m:
        return None, text
    label = next(g for g in m.groups()[1:] if g)
    return label, text[m.end() :]


def note_text_size(blk: Block) -> float:
    """The type size of a footnote's TEXT, ignoring its label.

    Word sets the label as a body-size glyph (a "2" at 12 pt followed by a
    tab) in front of a 10 pt note, so ``max_size`` is the label and the note
    failed every "smaller than body" test. The median size of the spans after
    the first non-empty span is the note's own size; a one-span block falls
    back to that span.
    """
    spans = [s for s in blk.spans if s.text.strip()]
    if not spans:
        return 0.0
    rest = spans[1:] or spans
    return float(median(s.size for s in rest))


def _is_footnote(blk: Block, page: Page, body_size: float, first: str) -> bool:
    h = page.height or 1
    if blk.y_start / h < FOOTNOTE_MIN_Y:
        return False
    if body_size and note_text_size(blk) >= body_size * FOOTNOTE_MAX_SIZE:
        return False
    if SIGNIFICANCE_LEGEND.match(first):
        return False
    if _symbol_is_notation(blk, page):
        return False
    return bool(FOOTNOTE_MARKER.match(first))


def _is_heading(
    blk: Block,
    body_size: float,
    text: str,
    first: str,
    ocr: bool = False,
    in_refs: bool = False,
) -> bool:
    if len(text) > 250 or len(blk.lines) > 3:
        return False
    # An equation is never a heading, however heading-shaped it looks.
    if MATH_CHARS.search(text) and MATH_OPS.search(text):
        return False
    if EQ_NUMBER.search(text) and MATH_OPS.search(text):
        return False
    # A bulleted line is a list item regardless of weight. Compliance
    # documents set their criteria bullets in bold at a size above the
    # (table-dominated) body median, and each one became a heading.
    if BULLET_START.match(first):
        return False
    # "A", "B D": the panel letters of a multi-panel figure are bold and
    # short, which is a heading's shape, but a heading has a word in it.
    if all(len(w.strip(".,:;()[]")) <= 1 for w in text.split()):
        return False
    size = blk.max_size()
    bold = blk.font_ratio("bold") > HEADING_BOLD_MIN_SHARE
    bigger = size > body_size * 1.06
    stripped = text.rstrip()
    words = stripped.split()
    if ocr:
        # On a recognised page the "size" is Tesseract's line box, which
        # swells on a tall ascender, a superscript, or a speck: a scanned
        # page shows 5-13 pt around an 8 pt body, and a single body line
        # clears 6% easily (some 60 false headings in one article). Line
        # height is therefore only shape evidence there, like bold: the
        # block must also look like a heading (numbered, title case, caps).
        bold = bold or bigger
        bigger = False
        # Two shapes need no size evidence at all, because a bold heading
        # set at body size has neither a bold flag nor a taller line box
        # after OCR: the references keyword, and a lone capitalised word in
        # its own one-line block ("Abstract", "Introduction", "Note").
        if len(blk.lines) == 1 and not in_refs:
            if BIB_HINT.match(stripped):
                return True
            if (
                len(words) == 1
                and words[0].isalpha()
                and words[0][0].isupper()
                and len(words[0]) >= 4
            ):
                return True
    if not (bigger or bold):
        return False
    # A heading of one word ("Conclusion", "Contributions") fails the
    # title-case test, which needs two. With real weight or size evidence, a
    # lone capitalised word in its own one-line block is a heading.
    if (
        not ocr
        and len(blk.lines) == 1
        and len(words) == 1
        and words[0].isalpha()
        and words[0][0].isupper()
        and len(words[0]) >= 4
    ):
        return True
    # Body paragraphs end in sentence punctuation; headings almost never do.
    if stripped.endswith((".", ";", ",")) and not NUMBERED_HEADING.match(first):
        return False
    if bigger:
        return True
    # Bold-only: demand a heading shape (numbered, title case, or all caps).
    if ocr and in_refs:
        # Inside a recognised reference list only an all-caps line can be a
        # heading: "1995 'Hospital reorganization after merger'" is numbered
        # and a wrapped surname ("Hinings") is a lone capitalised word.
        return len(words) <= 12 and stripped.isupper()
    if NUMBERED_HEADING.match(first) or BIB_HINT.match(stripped):
        # A recognised footnote opens "1 Currently, the most accepted
        # definition ..." and matches the numbered pattern; a numbered
        # heading is short.
        return not ocr or len(words) <= 12
    if len(words) <= 12 and stripped.isupper():
        return True
    # Title case is not enough after "References" on a recognised page: each
    # author line ("Ackroyd, Stephen") is title case and Tesseract gives it
    # its own block, so a reference list became fifty headings.
    if len(words) <= 12 and _title_case(words) and not (ocr and in_refs):
        return True
    return False


def _title_case(words: List[str]) -> bool:
    cand = [w for w in words if w[:1].isalpha()]
    if len(cand) < 2:
        return False
    caps = sum(1 for w in cand if w[:1].isupper())
    return caps / len(cand) > HEADING_TITLE_MIN_SHARE
