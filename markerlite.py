#!/usr/bin/env python3
"""markerlite - Marker's document-understanding layer, without the weights.

Marker (github.com/datalab-to/marker) splits into two halves:

  * ~1,800 lines of pure geometric/statistical heuristics (reading order,
    running-header suppression, heading-level clustering, paragraph
    continuation across columns and pages, list nesting, blockquotes, code
    indentation, footnotes, caption grouping, table grid reconstruction), and
  * five model-backed stages (surya layout detection, line detection, OCR,
    LaTeX equation recognition, table-cell detection).

Only the second half needs downloaded weights. This module reimplements the
first half against PyMuPDF's text layer, and substitutes weight-free stand-ins
for the model stages:

  layout detection  -> font-size/geometry classification + PyMuPDF find_tables
  reading order     -> PDF character-stream order (what Marker itself prefers
                       over its learned head on text-layer pages)
  table structure   -> marker.processors.table_recon (already weight-free)
  OCR               -> Tesseract
  equation -> LaTeX -> flagged for visual transcription (see --flag-math)

Usage:
    python3 markerlite.py file.pdf [...] -o OUTDIR [--images] [--flag-math]
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from itertools import groupby
from statistics import median
from typing import List, Optional, Tuple

import numpy as np
import pymupdf
import regex
from rapidfuzz import fuzz
from sklearn.cluster import KMeans
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

try:
    from marker.processors.table_recon import reconstruct_table_html
except Exception:  # pragma: no cover - marker not installed
    reconstruct_table_html = None


# --------------------------------------------------------------------------- #
# patterns (ported from marker)
# --------------------------------------------------------------------------- #

# marker/builders/structure.py, plus a control/private-use glyph class: LaTeX
# itemize bullets arrive as unmapped codepoints (\x88 from a symbol font), not
# as U+2022, so a literal bullet list would miss them.
LIST_ITEM_START = re.compile(
    r"^\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f-]|"
    r"\(?\d{1,3}[.)]|\(?[a-zA-Z][.)]|\(?[ivxlcIVXLC]{1,5}[.)])\s"
)
# marker/processors/text.py
HYPHEN_END = regex.compile(r".*[\p{Ll}|\d][-—¬]\s?$", regex.DOTALL)

# A caption label is followed by real punctuation ("Table 1." / "Figure 2:").
# Requiring the delimiter keeps body sentences that merely open with a
# cross-reference ("Table 1 reports descriptive statistics...") out of the
# caption class - the layout model draws that line for Marker.
CAPTION_START = re.compile(
    r"^\s*(figure|fig\.?|table|tbl\.?|chart|exhibit|scheme|plate|appendix)\s*"
    r"[\dIVXA-Z]+\s*[.:)—-]",
    re.IGNORECASE,
)
NUMBERED_HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*|[IVXLC]+\.|[A-Z]\.)\s+\S")
# "[1] ", "(2) ", "3. ", "*", and LaTeX's superscript-run-on form ("1We thank").
FOOTNOTE_START = re.compile(
    r"^\s*(\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}[.)]?\s|\d{1,3}(?=[A-Z])|[*†‡§¶])"
)
BIB_HINT = re.compile(r"^\s*(references|bibliography|works cited)\s*$", re.IGNORECASE)

# Greek, operators, relations, and the delimiters equations lean on. Font names
# are not enough: an Equation-Editor display equation is Symbol + Times, and the
# Times half dilutes any font-based ratio below every sensible threshold.
MATH_CHARS = re.compile(
    r"[Ͱ-Ͽ∀-⋿⟀-⟯⦀-⧿⨀-⫿"
    r"±×÷√∑∏∫≠≤≥≈"
    r"∞∈∉⊆⊂→⇒′″]"
)
EQ_NUMBER = re.compile(r"\(\s*\d{1,3}[a-z]?\s*\)\s*$")
MATH_OPS = re.compile(r"[=<>+−±×÷/^_]")

MATH_FONT = re.compile(
    r"(cmmi|cmsy|cmex|msam|msbm|mathjax|stix|xits|symbol|mtmi|mtsy|euclid|"
    r"latinmodernmath|cambriamath|asana|neoeuler|lmmath|rsfs|eufm)",
    re.IGNORECASE,
)
MONO_FONT = re.compile(
    r"(mono|courier|consolas|menlo|inconsolata|source ?code|dejavusansmono|cmtt)",
    re.IGNORECASE,
)

BOLD_FLAG = 1 << 4
ITALIC_FLAG = 1 << 1
SUPER_FLAG = 1 << 0
MONO_FLAG = 1 << 3


# --------------------------------------------------------------------------- #
# document model
# --------------------------------------------------------------------------- #


@dataclass
class Span:
    text: str
    bbox: Tuple[float, float, float, float]
    size: float
    font: str
    flags: int
    char_pos: int
    chars: list = field(default_factory=list)

    @property
    def bold(self) -> bool:
        return bool(self.flags & BOLD_FLAG) or "bold" in self.font.lower()

    @property
    def italic(self) -> bool:
        return bool(self.flags & ITALIC_FLAG) or "italic" in self.font.lower()

    @property
    def mono(self) -> bool:
        return bool(self.flags & MONO_FLAG) or bool(MONO_FONT.search(self.font))

    @property
    def math(self) -> bool:
        return bool(MATH_FONT.search(self.font))

    @property
    def superscript(self) -> bool:
        return bool(self.flags & SUPER_FLAG)


@dataclass
class Line:
    spans: List[Span]
    bbox: Tuple[float, float, float, float]
    char_pos: int

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.spans)

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def x_start(self) -> float:
        return self.bbox[0]

    @property
    def x_end(self) -> float:
        return self.bbox[2]

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]


@dataclass
class Block:
    lines: List[Line]
    bbox: Tuple[float, float, float, float]
    page_idx: int
    char_pos: int
    btype: str = "Text"
    # populated by processors / renderers
    heading_level: Optional[int] = None
    list_indent: int = 0
    blockquote: bool = False
    blockquote_level: int = 0
    has_continuation: bool = False
    ignore_for_output: bool = False
    html: Optional[str] = None
    code: Optional[str] = None
    image_path: Optional[str] = None
    needs_vision: bool = False
    eq_id: Optional[str] = None
    children: List["Block"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)

    @property
    def x_start(self) -> float:
        return self.bbox[0]

    @property
    def x_end(self) -> float:
        return self.bbox[2]

    @property
    def y_start(self) -> float:
        return self.bbox[1]

    @property
    def y_end(self) -> float:
        return self.bbox[3]

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def spans(self) -> List[Span]:
        return [s for ln in self.lines for s in ln.spans]

    def line_height(self) -> float:
        hs = [ln.height for ln in self.lines if ln.height > 0]
        return float(median(hs)) if hs else 0.0

    def max_size(self) -> float:
        sizes = [s.size for s in self.spans if s.text.strip()]
        return max(sizes) if sizes else 0.0

    def font_ratio(self, attr: str) -> float:
        spans = [s for s in self.spans if s.text.strip()]
        if not spans:
            return 0.0
        chars = sum(len(s.text) for s in spans)
        if not chars:
            return 0.0
        return sum(len(s.text) for s in spans if getattr(s, attr)) / chars


@dataclass
class Page:
    page_idx: int
    width: float
    height: float
    blocks: List[Block]
    images: List[dict] = field(default_factory=list)
    ocr_used: bool = False


# --------------------------------------------------------------------------- #
# extraction (replaces marker's LineBuilder / provider)
# --------------------------------------------------------------------------- #


def _bbox_of(items) -> Tuple[float, float, float, float]:
    xs0 = min(i[0] for i in items)
    ys0 = min(i[1] for i in items)
    xs1 = max(i[2] for i in items)
    ys1 = max(i[3] for i in items)
    return (xs0, ys0, xs1, ys1)


def _ocr_page(page: pymupdf.Page, page_idx: int, dpi: int = 300) -> Optional[Page]:
    """OCR stand-in for surya's recognition model.

    Marker's OCR path gives the recognizer line boxes and gets back text plus
    geometry. Tesseract's TSV output has the same shape - block/paragraph/line
    grouping with per-word boxes - so the rest of the pipeline (reading order,
    heading sizes, tables) keeps working on scanned pages. ``--psm 1`` turns on
    Tesseract's own page segmentation, which is what keeps a two-column scan
    from interleaving.
    """
    import subprocess
    import tempfile

    try:
        pix = page.get_pixmap(dpi=dpi)
        with tempfile.TemporaryDirectory() as td:
            img = pathlib.Path(td) / "page.png"
            pix.save(img)
            proc = subprocess.run(
                ["tesseract", str(img), "stdout", "--psm", "1", "-c",
                 "preserve_interword_spaces=1", "tsv"],
                capture_output=True, text=True, timeout=180,
            )
        if proc.returncode != 0:
            return None
    except Exception as exc:  # pragma: no cover
        print(f"  ! OCR failed on page {page_idx + 1}: {exc}", file=sys.stderr)
        return None

    scale = 72.0 / dpi
    rows = [r.split("\t") for r in proc.stdout.splitlines()[1:] if r.strip()]
    grouped: dict = defaultdict(list)
    order: List[tuple] = []
    for r in rows:
        if len(r) < 12 or r[0] != "5":  # level 5 = word
            continue
        try:
            conf = float(r[10])
        except ValueError:
            continue
        text = r[11]
        if conf < 30 or not text.strip():
            continue
        # TSV level-5 columns are level,page,block,par,line,word - group by
        # (block, par, line); including word_num would make every word a line.
        key = (int(r[2]), int(r[3]), int(r[4]))
        if key not in grouped:
            order.append(key)
        left, top, w, h = (float(r[6]), float(r[7]), float(r[8]), float(r[9]))
        grouped[key].append(
            (text, (left * scale, top * scale, (left + w) * scale, (top + h) * scale))
        )

    counter = 0
    blocks_by_par: dict = defaultdict(list)
    par_order: List[tuple] = []
    for key in order:
        words = grouped[key]
        spans = []
        for text, bbox in words:
            spans.append(
                Span(text=text + " ", bbox=bbox, size=round(bbox[3] - bbox[1], 1),
                     font="OCR", flags=0, char_pos=counter)
            )
            counter += 1
        line = Line(spans=spans, bbox=_bbox_of([s.bbox for s in spans]),
                    char_pos=spans[0].char_pos)
        par_key = key[:2]  # block, paragraph
        if par_key not in blocks_by_par:
            par_order.append(par_key)
        blocks_by_par[par_key].append(line)

    blocks = []
    for par_key in par_order:
        lines = blocks_by_par[par_key]
        blocks.append(
            Block(lines=lines, bbox=_bbox_of([ln.bbox for ln in lines]),
                  page_idx=page_idx, char_pos=lines[0].char_pos)
        )

    return Page(page_idx=page_idx, width=page.rect.width, height=page.rect.height,
                blocks=blocks, ocr_used=True)


def extract_page(page: pymupdf.Page, page_idx: int, ocr_if_empty: bool = True) -> Page:
    """Blocks in PDF character-stream order.

    Marker orders text-layer pages by pdftext character position rather than by
    its learned reading-order head ("the PDF's own character stream is the most
    reliable reading-order signal ... it beat surya's learned order head on
    multi-column pages" - builders/line.py). PyMuPDF's unsorted rawdict
    preserves that same stream order, so the enumeration index below is the
    direct equivalent of pdftext's ``span.minimum_position``.
    """
    ocr_used = False
    raw = page.get_text("rawdict")
    text_len = sum(
        len(c.get("c", ""))
        for b in raw.get("blocks", [])
        for ln in b.get("lines", [])
        for s in ln.get("spans", [])
        for c in s.get("chars", [])
    )
    if ocr_if_empty and text_len < 20:
        ocr_page = _ocr_page(page, page_idx)
        if ocr_page is not None:
            return ocr_page

    counter = 0
    blocks: List[Block] = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        lines: List[Line] = []
        for ln in b.get("lines", []):
            spans: List[Span] = []
            for s in ln.get("spans", []):
                chars = s.get("chars", [])
                text = "".join(c.get("c", "") for c in chars) or s.get("text", "")
                if not text:
                    continue
                spans.append(
                    Span(
                        text=text,
                        bbox=tuple(s["bbox"]),
                        size=s.get("size", 0.0),
                        font=s.get("font", ""),
                        flags=s.get("flags", 0),
                        char_pos=counter,
                        chars=chars,
                    )
                )
                counter += 1
            if not spans:
                continue
            lines.append(
                Line(
                    spans=spans,
                    bbox=tuple(ln["bbox"]),
                    char_pos=spans[0].char_pos,
                )
            )
        if not lines:
            continue
        blocks.append(
            Block(
                lines=lines,
                bbox=tuple(b["bbox"]),
                page_idx=page_idx,
                char_pos=lines[0].char_pos,
            )
        )

    return Page(
        page_idx=page_idx,
        width=page.rect.width,
        height=page.rect.height,
        blocks=blocks,
        ocr_used=ocr_used,
    )


# --------------------------------------------------------------------------- #
# tables (layout model stand-in + marker's weight-free grid reconstruction)
# --------------------------------------------------------------------------- #


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
                    if t and bx0 <= (sx0 + sx1) / 2 <= bx1 and by0 <= (sy0 + sy1) / 2 <= by1:
                        words.append([t, sx0, sx1, sy1 - sy0])
                if words:
                    gap_thresh = 0.8 * median([w[3] for w in words])
                    for t, x0, x1, _h in words:
                        if tokens and x0 - tokens[-1][2] < gap_thresh:
                            tokens[-1][0] += " " + t
                            tokens[-1][2] = x1
                        else:
                            tokens.append([t, x0, x1])
            for sp in ln.spans:
                for c in sp.chars or []:
                    cx0, cy0, cx1, cy1 = c["bbox"]
                    if not (bx0 <= (cx0 + cx1) / 2 <= bx1 and by0 <= (cy0 + cy1) / 2 <= by1):
                        continue
                    ch = c.get("c", "")
                    gap = 0.5 * max(cy1 - cy0, 1.0)
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


def _grid_to_html(rows: List[List[str]]) -> str:
    rows = [[(c or "").strip() for c in r] for r in rows if any((c or "").strip() for c in r)]
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


def _table_sane(html: str, max_header_ratio=1.4, max_empty_frac=0.45) -> bool:
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
            if area > 0.6 * page_area or area < 200:
                continue  # a "table" covering the page is the page, not a table
            if any(_overlap_frac(bb, prev) > 0.6 for prev in seen_bboxes):
                continue
            seen_bboxes.append(bb)
            found.append(tbl)
    if not found:
        return

    consumed: set = set()
    new_blocks: List[Block] = []
    for tbl in found:
        bbox = tuple(tbl.bbox)
        members = [
            b for i, b in enumerate(page.blocks)
            if i not in consumed and _overlap_frac(b.bbox, bbox) > 0.5
        ]
        if not members:
            continue

        # find_tables' bbox hugs the ruling lines and can clip the first and
        # last character of each row ("Condition" -> "ndition"). Reconstruct
        # from the union of the member blocks instead, padded slightly.
        region = _bbox_of([m.bbox for m in members] + [bbox])
        region = (region[0] - 4, region[1] - 3, region[2] + 4, region[3] + 3)

        html = ""
        score = 0.0
        if reconstruct_table_html is not None:
            lines = _tokens_for_recon(members, region)
            try:
                res = reconstruct_table_html(lines)
            except Exception:
                res = None
            if res:
                html, score = res

        if not html or not _table_sane(html):
            try:
                fallback = _grid_to_html(tbl.extract())
            except Exception:
                fallback = ""
            html = fallback if _table_sane(fallback) else ""
        if not html:
            continue

        for i, b in enumerate(page.blocks):
            if b in members:
                consumed.add(i)
        tb = Block(
            lines=[ln for m in members for ln in m.lines],
            bbox=bbox,
            page_idx=page.page_idx,
            char_pos=min(m.char_pos for m in members),
            btype="Table",
            html=html,
        )
        new_blocks.append(tb)

    if new_blocks:
        page.blocks = [b for i, b in enumerate(page.blocks) if i not in consumed]
        page.blocks.extend(new_blocks)
        page.blocks.sort(key=lambda b: b.char_pos)


# --------------------------------------------------------------------------- #
# classification (layout-model stand-in)
# --------------------------------------------------------------------------- #


def _columns_align(rows, tol=3.0, min_share=0.6) -> bool:
    """True when token starts recur at the same x across rows.

    This is the test that separates a table from justified prose. Both can show
    wide inter-word gaps and a steady token count per line, but only a table
    puts its tokens at the *same* x positions row after row - prose word starts
    scatter. Requires at least two such shared columns beyond the left margin.
    """
    if len(rows) < 3:
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


def propose_tables_from_text(pages: List[Page], min_score=0.62) -> None:
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
            if blk.btype == "Table" or len(blk.lines) < 3 or blk.ignore_for_output:
                continue
            lines = _tokens_for_recon([blk], blk.bbox)
            multi = [ln for ln in lines if len(ln[0]) >= 2]
            if len(multi) < 3:
                continue
            if not _columns_align(multi):
                continue
            try:
                res = reconstruct_table_html(lines)
            except Exception:
                continue
            if not res:
                continue
            html, score = res
            ncols = html.count("<th>") or html.split("</tr>")[0].count("<td>")
            if score < min_score or not (2 <= ncols <= 12) or not _table_sane(html):
                continue
            blk.btype = "Table"
            blk.html = html


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
    for page in pages:
        for blk in page.blocks:
            if blk.btype == "Table":
                continue
            text = blk.text.strip()
            if not text:
                blk.ignore_for_output = True
                continue

            first = blk.lines[0].text.strip()

            if _is_equation(blk, page, text):
                blk.btype = "Equation"
                blk.needs_vision = True
                continue
            if blk.font_ratio("mono") > 0.8 and len(blk.lines) > 1:
                blk.btype = "Code"
                continue
            if CAPTION_START.match(first) and len(text) < 900:
                blk.btype = "Caption"
                continue
            # Headings are tested BEFORE lists: "2. Method" satisfies the list
            # pattern too, and a numbered heading must not become a bullet.
            if _is_heading(blk, body_size, text, first):
                blk.btype = "SectionHeader"
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


TOC_LINE = re.compile(r"^(.*\S)[\s.·•…_]{2,}(\d{1,4})$|^(.*\S)\s+(\d{1,4})$")


def _demote_toc(pages: List[Page], min_run=5) -> None:
    """A table of contents is a list, not 40 headings.

    Contents entries are short, title-shaped and often set in the heading face,
    so they classify as SectionHeader and then flood the document outline. A run
    of lines that each end in a page number is the giveaway.
    """
    for page in pages:
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
            bullets = [i for i, ln in enumerate(blk.lines)
                       if LIST_ITEM_START.match(ln.text)]
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
                    Block(lines=grp, bbox=_bbox_of([ln.bbox for ln in grp]),
                          page_idx=blk.page_idx, char_pos=grp[0].char_pos,
                          btype="ListItem")
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
        abs(centre - page.width / 2) < 0.12 * page.width
        and blk.width < 0.75 * page.width
    )
    numbered = bool(EQ_NUMBER.search(text))
    has_ops = bool(MATH_OPS.search(text))

    if math_font > 0.45:
        return True
    if math_font > 0.25 and len(text) < 40:
        return True
    # Few real words, actual operators, and either math glyphs, an equation
    # number, or display placement.
    if len(words) <= 4 and has_ops and (math_chars > 0.05 or numbered or centred):
        return True
    if math_chars > 0.25 and has_ops:
        return True
    return False


# Footnote marker at the start of a note: "[1]", "(1)", "1.", "1)", "1 ", the
# LaTeX run-on "1We", or a symbol run. Group 1 is the whole marker.
FOOTNOTE_MARKER = re.compile(
    r"^\s*(\[(\d{1,3})\]|\((\d{1,3})\)|(\d{1,3})[.)]?(?=\s)|(\d{1,3})(?=[A-Z])|"
    r"([*\u2020\u2021\u00a7\u00b6]{1,3}))\s*"
)


def footnote_label(text: str):
    """(label, body) for a note that starts with a marker, else (None, text)."""
    m = FOOTNOTE_MARKER.match(text)
    if not m:
        return None, text
    label = next(g for g in m.groups()[1:] if g)
    return label, text[m.end():]


def _is_footnote(blk: Block, page: Page, body_size: float, first: str) -> bool:
    h = page.height or 1
    if blk.y_start / h < 0.70:
        return False
    if body_size and blk.max_size() >= body_size * 0.95:
        return False
    return bool(FOOTNOTE_MARKER.match(first))


def _is_heading(blk: Block, body_size: float, text: str, first: str) -> bool:
    if len(text) > 250 or len(blk.lines) > 3:
        return False
    # An equation is never a heading, however heading-shaped it looks.
    if MATH_CHARS.search(text) and MATH_OPS.search(text):
        return False
    if EQ_NUMBER.search(text) and MATH_OPS.search(text):
        return False
    size = blk.max_size()
    bold = blk.font_ratio("bold") > 0.6
    bigger = size > body_size * 1.06
    if not (bigger or bold):
        return False
    stripped = text.rstrip()
    # Body paragraphs end in sentence punctuation; headings almost never do.
    if stripped.endswith((".", ";", ",")) and not NUMBERED_HEADING.match(first):
        return False
    if bigger:
        return True
    # Bold-only: demand a heading shape (numbered, title case, or all caps).
    if NUMBERED_HEADING.match(first) or BIB_HINT.match(stripped):
        return True
    words = stripped.split()
    if len(words) <= 12 and (stripped.isupper() or _title_case(words)):
        return True
    return False


def _title_case(words: List[str]) -> bool:
    cand = [w for w in words if w[:1].isalpha()]
    if len(cand) < 2:
        return False
    caps = sum(1 for w in cand if w[:1].isupper())
    return caps / len(cand) > 0.6


# --------------------------------------------------------------------------- #
# processors ported from marker (all weight-free)
# --------------------------------------------------------------------------- #

TEXTISH = ("Text", "SectionHeader", "ListItem", "Caption", "Equation")


def proc_ignore_common(pages: List[Page]) -> None:
    """marker/processors/ignoretext.py - repeated first/last blocks are furniture."""
    firsts, lasts = [], []
    for p in pages:
        cand = [b for b in p.blocks if b.btype in TEXTISH and b.text.strip()]
        if cand:
            firsts.append(cand[0])
            lasts.append(cand[-1])
    for group in (firsts, lasts):
        _filter_common(group)


def _clean_text(text: str) -> str:
    text = text.replace("\n", "").strip()
    text = re.sub(r"^\d+\s*", "", text)
    text = re.sub(r"\s*\d+$", "", text)
    return text


def _filter_common(blocks: List[Block], threshold=0.2, min_blocks=3, max_streak=3, match=90):
    if len(blocks) < min_blocks:
        return
    texts = [_clean_text(b.text) for b in blocks]
    streaks = {}
    for key, group in groupby(texts):
        streaks[key] = max(streaks.get(key, 0), len(list(group)))
    counter = Counter(texts)
    common = [
        k for k, v in counter.items()
        if (v >= len(blocks) * threshold or streaks[k] >= max_streak) and v > min_blocks
    ]
    if not common:
        return
    for t, b in zip(texts, blocks):
        if any(fuzz.ratio(t, c) > match for c in common):
            b.ignore_for_output = True


PAGE_NUMBER_ONLY = re.compile(r"^[\s\-\u2013\u2014|]*(?:\d{1,4}|[ivxlcdmIVXLCDM]{1,7})[\s\-\u2013\u2014|]*$")


def proc_marginalia(pages: List[Page], header_zone=0.08, footer_zone=0.13,
                    max_height_frac=0.035, max_chars=150) -> None:
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
            b for b in page.blocks
            if b.btype in TEXTISH and not b.ignore_for_output and b.text.strip()
        ]
        if len(text_blocks) < 2:
            continue
        h = page.height or 1

        def yfrac(b):
            return (b.y_start / h, b.y_end / h)

        body = [
            b for b in text_blocks
            if not (yfrac(b)[1] <= header_zone or yfrac(b)[0] >= 1 - footer_zone)
        ]
        if not body:
            continue
        body_top = min(yfrac(b)[0] for b in body)
        body_bottom = max(yfrac(b)[1] for b in body)
        body_ids = {id(b) for b in body}
        order = [id(b) for b in text_blocks]
        first_body = next((i for i, o in enumerate(order) if o in body_ids), None)
        last_body = next(
            (len(order) - 1 - i for i, o in enumerate(reversed(order)) if o in body_ids),
            None,
        )

        for idx, blk in enumerate(text_blocks):
            y0, y1 = yfrac(blk)
            if (y1 - y0) > max_height_frac:
                continue
            t = blk.text.strip()
            if not t or len(t) > max_chars:
                continue
            is_header = (
                y1 <= header_zone and y1 <= body_top
                and (first_body is None or idx < first_body)
            )
            is_footer = (
                y0 >= 1 - footer_zone and y0 >= body_bottom
                and (last_body is None or idx > last_body)
            )
            if is_header or is_footer:
                candidates.append((page.page_idx, blk, _clean_text(t)))

    if not candidates:
        return

    # A running head that got merged into the block below never appears as a
    # standalone candidate, so the repetition corpus also takes the FIRST LINE
    # of every block starting in the header zone. Without this, a tight top
    # margin hides the header from the evidence that identifies it.
    corpus = list(candidates)
    for page in pages:
        h = page.height or 1
        for blk in page.blocks:
            if not blk.lines or len(blk.lines) < 2:
                continue
            if blk.y_start / h <= 0.10:
                corpus.append(
                    (page.page_idx, blk, _clean_text(blk.lines[0].text.strip()))
                )

    # Pages on which each normalized text appears. Fuzzy, so that a running head
    # carrying a varying page number or section name still groups together.
    groups: dict = defaultdict(set)
    keys: List[str] = []
    for page_idx, _blk, norm in corpus:
        key = next((k for k in keys if fuzz.ratio(k, norm) > 90), None)
        if key is None:
            key = norm
            keys.append(key)
        groups[key].add(page_idx)

    for page_idx, blk, norm in candidates:
        key = next((k for k in keys if fuzz.ratio(k, norm) > 90), norm)
        repeats = len(groups.get(key, set())) >= 2
        bare_number = bool(PAGE_NUMBER_ONLY.match(blk.text.strip()))

        if not (repeats or bare_number):
            continue  # unique text in a margin zone is content, not furniture
        if blk.btype == "SectionHeader" and not repeats:
            continue  # never drop a heading on position alone
        if page_idx == 0 and not repeats and not bare_number:
            continue  # page 1 carries titles; require proof it is furniture
        blk.ignore_for_output = True

    _strip_merged_running_heads(pages, groups, keys)


def _strip_merged_running_heads(pages: List[Page], groups: dict, keys: List[str],
                                header_zone=0.10) -> None:
    """Drop a running head that got merged into the block below it.

    When the gap between the running head and the first line of content is
    small, PyMuPDF returns them as a single block, so suppressing the block
    would take the heading with it. Here the offending LINE is removed instead,
    and only when its text is one of the texts already established as repeating.
    """
    repeated = {k for k, pgs in groups.items() if len(pgs) >= 2}
    if not repeated:
        return
    for page in pages:
        h = page.height or 1
        for blk in page.blocks:
            if len(blk.lines) < 2 or blk.ignore_for_output:
                continue
            if blk.y_start / h > header_zone:
                continue
            first = _clean_text(blk.lines[0].text.strip())
            if not first or len(first) > 90:
                continue
            if not any(fuzz.ratio(first, k) > 90 for k in repeated):
                continue
            # A running head is set smaller than the content it sits above.
            # Requiring that keeps a genuine repeated heading from being eaten.
            head_size = max((s.size for s in blk.lines[0].spans), default=0)
            rest_size = max(
                (s.size for ln in blk.lines[1:] for s in ln.spans), default=0)
            if not (rest_size and head_size < 0.95 * rest_size):
                continue
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
            b.max_size() for b in page.blocks
            if b.btype == "Text" and not b.ignore_for_output
        ]
        body = median(body_sizes) if body_sizes else 0
        for blk in page.blocks:
            if blk.btype not in ("Text", "ListItem") or blk.ignore_for_output:
                continue
            if blk.y_start / h < 0.70:
                continue
            if body and blk.max_size() >= body * 0.95:
                continue
            if not FOOTNOTE_MARKER.match(blk.text.strip()):
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
                and blk.y_start / h >= 0.70
                and (not body or blk.max_size() < body * 0.95)
                and not FOOTNOTE_MARKER.match(blk.text.strip())
                and not PAGE_NUMBER_ONLY.match(blk.text.strip())
            ):
                blk.btype = "Footnote"
                continue
            prev_was_note = False

        notes = [b for b in page.blocks if b.btype == "Footnote" and not b.ignore_for_output]
        if not notes:
            continue

        # Fold continuation blocks into the note above them. A block that opens
        # without a marker, in the same small type, is the tail of a wrapped
        # note, not a new one.
        merged: List[Block] = []
        for blk in notes:
            label, _ = footnote_label(blk.text.strip())
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


def proc_section_levels(pages: List[Page], level_count=4, merge_threshold=0.25,
                        default_level=2, height_tolerance=0.99) -> None:
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


def _bucket_headings(line_heights: List[float], level_count: int, merge_threshold: float):
    if len(line_heights) <= level_count:
        return []
    data = np.asarray(line_heights).reshape(-1, 1)
    labels = KMeans(n_clusters=level_count, random_state=0, n_init="auto").fit_predict(data)
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


def proc_continuation(pages: List[Page], column_gap_ratio=0.02) -> None:
    """marker/processors/text.py - paragraphs continuing across columns/pages."""
    flat = _flat_text_blocks(pages)
    for i, blk in enumerate(flat[:-1]):
        if blk.btype not in ("Text",) or len(blk.lines) < 2:
            continue
        nxt = flat[i + 1]
        if nxt.btype != "Text" or nxt.ignore_for_output:
            continue

        page = pages[blk.page_idx]
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


def proc_blockquote(pages: List[Page], min_x_indent=0.1, x_tol=0.01) -> None:
    """marker/processors/blockquote.py."""
    for page in pages:
        blocks = [b for b in page.blocks if b.btype == "Text" and not b.ignore_for_output]
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
                nxt.blockquote = (matching_end and matching_start) or (x_indent and y_indent)
                nxt.blockquote_level = blk.blockquote_level + (1 if (x_indent and y_indent) else 0)
            elif x_indent and y_indent:
                nxt.blockquote = True
                nxt.blockquote_level = 1


def proc_list_indent(pages: List[Page], min_x_indent=0.01) -> None:
    """marker/processors/list.py - nesting depth from x-indentation."""
    for page in pages:
        items = [b for b in page.blocks if b.btype == "ListItem" and not b.ignore_for_output]
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
    """marker/processors/code.py - rebuild leading indentation from geometry."""
    for page in pages:
        for blk in page.blocks:
            if blk.btype != "Code":
                continue
            min_left = min(ln.x_start for ln in blk.lines)
            total_width = sum(ln.width for ln in blk.lines)
            total_chars = sum(len(ln.text) for ln in blk.lines)
            avg_char_width = total_width / max(total_chars, 1)
            out = []
            for ln in blk.lines:
                prefix = ""
                if avg_char_width:
                    spaces = int((ln.x_start - min_left) / avg_char_width)
                    prefix = " " * max(0, spaces)
                out.append(prefix + ln.text)
            blk.code = "\n".join(out).rstrip()


def proc_merge_equations(pages: List[Page], gap_frac=1.8) -> None:
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
                ygap = max(0.0, max(prev.y_start, blk.y_start) - min(prev.y_end, blk.y_end))
                xgap = max(0.0, max(prev.x_start, blk.x_start) - min(prev.x_end, blk.x_end))
                span = max(prev.line_height(), blk.line_height(), 1.0)
                if ygap < gap_frac * span and xgap < gap_frac * span:
                    prev.lines.extend(blk.lines)
                    prev.bbox = (
                        min(prev.x_start, blk.x_start), min(prev.y_start, blk.y_start),
                        max(prev.x_end, blk.x_end), max(prev.y_end, blk.y_end),
                    )
                    continue
            merged.append(blk)
        page.blocks = merged


def proc_captions(pages: List[Page], gap_threshold=0.05) -> None:
    """marker/builders/structure.py::group_caption_blocks - keep captions with figures."""
    for page in pages:
        gap_px = gap_threshold * page.height
        blocks = page.blocks
        for i, blk in enumerate(blocks):
            if blk.btype not in ("Table", "Figure"):
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(blocks) and blocks[j].btype == "Caption":
                    gap = max(
                        0.0,
                        max(blocks[j].y_start, blk.y_start) - min(blocks[j].y_end, blk.y_end),
                    )
                    if gap < gap_px:
                        blk.children.append(blocks[j])
                        blocks[j].ignore_for_output = True


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: List[List[str]] = []
        self.header: List[str] = []
        self._row: List[str] = []
        self._cell: List[str] = []
        self._in_cell = False
        self._in_head = False

    def handle_starttag(self, tag, attrs):
        if tag == "thead":
            self._in_head = True
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "thead":
            self._in_head = False
        elif tag in ("td", "th"):
            self._in_cell = False
            self._row.append("".join(self._cell).strip())
        elif tag == "tr":
            if self._in_head and not self.header:
                self.header = self._row
            else:
                self.rows.append(self._row)
            self._row = []

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


def table_html_to_markdown(html: str) -> str:
    p = _TableParser()
    p.feed(html)
    header, rows = p.header, p.rows
    if not header and rows:
        header, rows = rows[0], rows[1:]
    if not header:
        return ""
    width = max([len(header)] + [len(r) for r in rows]) if rows else len(header)

    def pad(r):
        r = [unescape(c).replace("|", r"\|").replace("\n", " ") for c in r]
        return r + [""] * (width - len(r))

    out = ["| " + " | ".join(pad(header)) + " |",
           "|" + "|".join([" --- "] * width) + "|"]
    for r in rows:
        out.append("| " + " | ".join(pad(r)) + " |")
    return "\n".join(out)


def _inline(spans: List[Span], fn_labels=frozenset()) -> str:
    """Emit bold/italic runs, coalescing adjacent spans with the same format.

    A superscript span whose text is the label of a known footnote becomes the
    reference ``[^N]``; other superscripts pass through untouched.
    """
    parts = []
    for key3, group in groupby(spans, key=lambda s: (s.bold, s.italic, s.superscript)):
        group = list(group)
        bold, italic, sup = key3
        if sup:
            key = "".join(s.text for s in group).strip()
            if fn_labels and key in fn_labels:
                parts.append(f"[^{key}]")
            elif key:
                # Not a note reference (an exponent, say): keep it raised.
                # <sup> is valid in GFM and Pandoc; bare "103" is not 10^3.
                parts.append(f"<sup>{key}</sup>")
            continue
        text = "".join(s.text for s in group)
        if not text.strip():
            parts.append(text)
            continue
        lead = len(text) - len(text.lstrip())
        trail = len(text) - len(text.rstrip())
        core = text.strip()
        if bold and italic:
            core = f"***{core}***"
        elif bold:
            core = f"**{core}**"
        elif italic:
            core = f"*{core}*"
        parts.append(text[:lead] + core + text[len(text) - trail:] if trail else text[:lead] + core)
    return "".join(parts)


_FN_LABELS: set = set()


def block_text(blk: Block, plain: bool = False) -> str:
    """Join a block's lines, dehyphenating and unwrapping soft line breaks.

    ``plain`` drops inline emphasis - headings and captions carry their own
    markup, and a wholly-bold heading would otherwise render as ``## **Title**``.
    """
    pieces = []
    for i, ln in enumerate(blk.lines):
        seg = (ln.text if plain else _inline(ln.spans, _FN_LABELS)).rstrip()
        if i == 0:
            pieces.append(seg)
            continue
        prev = pieces[-1]
        if HYPHEN_END.match(prev):
            pieces[-1] = re.sub(r"[-—¬]\s*$", "", prev)
            pieces.append(seg.lstrip())
            pieces[-2:] = ["".join(pieces[-2:])]
        else:
            pieces.append(" " + seg.lstrip())
    return re.sub(r"[ \t]+", " ", "".join(pieces)).strip()


def _is_list_line(chunk: str) -> bool:
    last = chunk.rsplit("\n", 1)[-1].lstrip()
    return bool(re.match(r"^(-|\d{1,3}\.)\s", last))


def render(pages: List[Page], keep_footnotes=True, page_markers=False) -> str:
    out: List[str] = []
    pending_paragraph = ""
    anon_counter = [0]
    # Labels of every note in the document, so that a superscript "1" in body
    # text can be emitted as the reference [^1] - and only when note 1 exists,
    # so exponents in prose are left alone.
    fn_labels = set()
    for page in pages:
        for blk in page.blocks:
            if blk.btype == "Footnote" and not blk.ignore_for_output:
                for ln in blk.lines:
                    label, _ = footnote_label(ln.text.strip())
                    if label:
                        fn_labels.add(label)
    global _FN_LABELS
    _FN_LABELS = fn_labels

    def flush():
        nonlocal pending_paragraph
        if pending_paragraph.strip():
            out.append(pending_paragraph.strip())
        pending_paragraph = ""

    for page in pages:
        if page_markers:
            # Cheap in context, and it lets you ask an LLM where in the source
            # PDF something came from.
            flush()
            out.append(f"<!-- page {page.page_idx + 1} -->")
        for blk in page.blocks:
            if blk.ignore_for_output:
                continue
            t = blk.btype

            if t == "Text":
                txt = block_text(blk)
                if not txt:
                    continue
                if pending_paragraph:
                    joined = pending_paragraph.rstrip()
                    if HYPHEN_END.match(joined):
                        pending_paragraph = re.sub(r"[-—¬]\s*$", "", joined) + txt
                    else:
                        pending_paragraph = joined + " " + txt
                else:
                    pending_paragraph = txt
                if blk.blockquote:
                    pending_paragraph = ("> " * max(blk.blockquote_level, 1)) + pending_paragraph
                if not blk.has_continuation:
                    flush()
                continue

            flush()
            if t == "SectionHeader":
                level = min(max(blk.heading_level or 2, 1), 6)
                out.append("#" * level + " " + block_text(blk, plain=True))
            elif t == "ListItem":
                txt = block_text(blk)
                bullet = "-"
                m = re.match(r"^\s*\(?(\d{1,3})[.)]\s*", txt)
                if m:
                    bullet = f"{m.group(1)}."
                    txt = txt[m.end():]
                else:
                    txt = re.sub(LIST_ITEM_START, "", txt, count=1)
                item = "  " * blk.list_indent + f"{bullet} {txt}"
                # Keep a run of items in one list: no blank line between them.
                if out and _is_list_line(out[-1]):
                    out[-1] = out[-1] + "\n" + item
                else:
                    out.append(item)
            elif t == "Table":
                md = table_html_to_markdown(blk.html or "")
                out.append(md or (blk.html or ""))
                for cap in blk.children:
                    out.append("*" + block_text(cap, plain=True) + "*")
            elif t == "Caption":
                out.append("*" + block_text(blk, plain=True) + "*")
            elif t == "TocEntry":
                item = "- " + block_text(blk, plain=True)
                if out and out[-1].rsplit("\n", 1)[-1].startswith("- "):
                    out[-1] += "\n" + item
                else:
                    out.append(item)
            elif t == "Code":
                out.append("```\n" + (blk.code or blk.text) + "\n```")
            elif t == "Equation":
                body = block_text(blk, plain=True)
                if body:
                    out.append(f"$$\n{body}\n$$")
                    if blk.eq_id:
                        # Anchor for --apply-math: a vision transcription of the
                        # matching crop replaces the block above, in place.
                        out.append(f"<!-- markerlite:eq {blk.eq_id} -->")
            elif t == "Footnote":
                if keep_footnotes:
                    notes = [
                        _inline(ln.spans, fn_labels).strip() for ln in blk.lines
                        if ln.text.strip()
                    ]
                    merged = []
                    for n in notes:
                        # A new note starts with its own marker; anything else
                        # is a wrapped continuation of the note above.
                        if footnote_label(n)[0] is not None or not merged:
                            merged.append(n)
                        else:
                            merged[-1] += " " + n
                    for n in merged:
                        label, body = footnote_label(n)
                        if label is None:
                            anon_counter[0] += 1
                            label = f"n{anon_counter[0]}"
                        # Real footnote syntax: a labeled definition. "[^]:"
                        # carried no identity, so downstream tools had to guess
                        # which lines belonged to which note.
                        out.append(f"[^{label}]: {body.strip()}")
            elif t == "Figure":
                if blk.image_path:
                    out.append(f"![]({blk.image_path})")
                for cap in blk.children:
                    out.append("*" + block_text(cap, plain=True) + "*")
    flush()

    text = "\n\n".join(x for x in out if x is not None and x.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


# --------------------------------------------------------------------------- #
# images
# --------------------------------------------------------------------------- #


def _insert_pos(page: Page, y0: float) -> float:
    """Reading-order position for a graphic at vertical offset ``y0``.

    Figures used to be appended with char_pos 1e9, which parked every one of
    them at the end of its page - after the caption that introduced it and after
    the following paragraph. A graphic has no characters, so it has no stream
    position of its own; the honest stand-in is the position of the first text
    block that starts at or below it, minus a hair, so the figure lands just
    above that block.
    """
    below = [b for b in page.blocks if b.y_start >= y0 - 2]
    if below:
        return min(b.char_pos for b in below) - 0.5
    return max((b.char_pos for b in page.blocks), default=0) + 0.5


def _vector_regions(pmpage: pymupdf.Page, min_items=8, min_side=60.0):
    """Bounding boxes of vector drawings (charts, diagrams, flowcharts).

    get_image_info only reports embedded rasters. A plotted chart or a drawn
    diagram is neither an image nor text - it is a pile of path operators, and
    was previously extracted as nothing at all. Cluster the paths and treat a
    dense enough cluster as a figure.
    """
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        return []
    rects = [
        pymupdf.Rect(d["rect"]) for d in drawings
        if d.get("rect") and pymupdf.Rect(d["rect"]).width < pmpage.rect.width * 0.98
    ]
    if len(rects) < min_items:
        return []

    clusters: List[list] = []
    for r in rects:
        placed = False
        for cl in clusters:
            merged = pymupdf.Rect(cl[0])
            for other in cl:
                merged |= other
            if merged.intersects(r + (-14, -14, 14, 14)):
                cl.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])

    out = []
    page_area = pmpage.rect.width * pmpage.rect.height
    for cl in clusters:
        if len(cl) < min_items:
            continue
        box = pymupdf.Rect(cl[0])
        for r in cl:
            box |= r
        if box.width < min_side or box.height < min_side:
            continue
        area = box.width * box.height
        if area > 0.7 * page_area or area < 0.01 * page_area:
            continue
        out.append(box)
    return out


def extract_images(doc, pages: List[Page], outdir: pathlib.Path, stem: str,
                   vectors: bool = True) -> int:
    """Extract raster images and (optionally) vector drawings as figures."""
    imgdir = outdir / f"{stem}_images"
    count = 0
    for page in pages:
        pm = doc[page.page_idx]
        found: List[Tuple[str, tuple]] = []

        for n, info in enumerate(pm.get_image_info(xrefs=True)):
            xref = info.get("xref", 0)
            bbox = info.get("bbox")
            if not xref or not bbox:
                continue
            if (bbox[2] - bbox[0]) < 40 or (bbox[3] - bbox[1]) < 40:
                continue
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                imgdir.mkdir(parents=True, exist_ok=True)
                name = f"page{page.page_idx + 1}_img{n}.png"
                pix.save(imgdir / name)
            except Exception:
                continue
            found.append((name, tuple(bbox)))

        if vectors:
            taken = [b for _n, b in found]
            for n, box in enumerate(_vector_regions(pm)):
                bt = tuple(box)
                if any(_overlap_frac(bt, t) > 0.5 for t in taken):
                    continue  # already captured as a raster
                # A ruled table is also "a pile of path operators". Two tells:
                # it overlaps a detected Table, or the region is mostly text.
                if any(b.btype == "Table" and _overlap_frac(b.bbox, bt) > 0.4
                       for b in page.blocks):
                    continue
                area = max((bt[2] - bt[0]) * (bt[3] - bt[1]), 1.0)
                text_area = sum(
                    _overlap_frac(b.bbox, bt) * b.width * b.height
                    for b in page.blocks if b.lines
                )
                if text_area / area > 0.35:
                    continue
                try:
                    imgdir.mkdir(parents=True, exist_ok=True)
                    name = f"page{page.page_idx + 1}_vec{n}.png"
                    # Pad: the cluster box hugs the path bounds and clips
                    # stroke width and any tick labels sitting just outside.
                    clip = (box + (-5, -5, 5, 5)) & pm.rect
                    pm.get_pixmap(clip=clip, dpi=200).save(imgdir / name)
                except Exception:
                    continue
                found.append((name, tuple(box)))

        for name, bbox in found:
            page.blocks.append(
                Block(
                    lines=[], bbox=bbox, page_idx=page.page_idx,
                    char_pos=_insert_pos(page, bbox[1]), btype="Figure",
                    image_path=f"{imgdir.name}/{name}",
                )
            )
            count += 1
        page.blocks.sort(key=lambda b: b.char_pos)
    return count


# --------------------------------------------------------------------------- #
# vision hand-off (stand-in for surya's equation/complex-region models)
# --------------------------------------------------------------------------- #


def flag_math(doc, pages: List[Page], outdir: pathlib.Path, stem: str, dpi=200) -> dict:
    """Render regions no weight-free heuristic can read, for visual transcription.

    Marker sends equation and complex-region crops to surya's LaTeX recognizer.
    With no weights available, the honest substitute is to crop the same regions
    and hand them to a vision model - here, written to disk with a manifest.
    """
    regions = []
    cropdir = outdir / f"{stem}_math"
    for page in pages:
        targets = [b for b in page.blocks if b.needs_vision and not b.ignore_for_output]
        if not targets:
            continue
        cropdir.mkdir(parents=True, exist_ok=True)
        pm = doc[page.page_idx]
        for n, blk in enumerate(targets):
            rect = pymupdf.Rect(blk.bbox) + (-6, -6, 6, 6)
            pix = pm.get_pixmap(clip=rect, dpi=dpi)
            eq_id = f"page{page.page_idx + 1}_eq{n}"
            blk.eq_id = eq_id
            pix.save(cropdir / f"{eq_id}.png")
            regions.append({
                "id": eq_id,
                "page": page.page_idx + 1,
                "image": f"{cropdir.name}/{eq_id}.png",
                "bbox": [round(v, 1) for v in blk.bbox],
                "text_layer": blk.text,
                "latex": "",  # fill in from the crop, then run --apply-math
            })
    manifest = {"stem": stem, "regions": regions}
    if regions:
        (outdir / f"{stem}_math.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def apply_math(md_path: pathlib.Path, manifest_path: pathlib.Path) -> int:
    """Splice transcribed LaTeX back into the markdown, replacing the
    text-layer approximation for each anchored equation."""
    manifest = json.loads(manifest_path.read_text())
    md = md_path.read_text(encoding="utf-8")
    applied = 0
    for region in manifest.get("regions", []):
        latex = (region.get("latex") or "").strip()
        if not latex or not region.get("id"):
            continue
        anchor = re.escape(f"<!-- markerlite:eq {region['id']} -->")
        # (?:(?!\$\$).)* keeps the match from starting at an earlier equation
        # and swallowing the prose in between.
        pattern = re.compile(
            r"\$\$\n(?:(?!\$\$).)*\n\$\$\n\n" + anchor, re.DOTALL
        )
        new, n = pattern.subn(lambda _m: f"$$\n{latex}\n$$", md, count=1)
        if n:
            md, applied = new, applied + 1
    md_path.write_text(md, encoding="utf-8")
    return applied


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #


def convert(path: pathlib.Path, outdir: pathlib.Path, images=False,
            do_flag_math=False, page_markers=False) -> Tuple[pathlib.Path, dict]:
    """Convert one PDF. Returns (markdown path, info).

    ``info`` carries ``regions`` (equation crops, when --flag-math ran) and
    ``stats`` (pages, bytes, figures, equations) for reporting.
    """
    doc = pymupdf.open(path)
    pages = []
    for i in range(len(doc)):
        p = extract_page(doc[i], i)
        detect_tables(doc[i], p)
        pages.append(p)

    body = body_font_size(pages)
    classify(pages, body)
    propose_tables_from_text(pages)

    proc_ignore_common(pages)
    # Footnotes are relabeled before marginalia so the footer-zone rule can't
    # swallow them (marker excludes Footnote from marginalia for the same reason).
    proc_footnotes(pages)
    proc_marginalia(pages)
    proc_section_levels(pages)
    proc_continuation(pages)
    proc_merge_equations(pages)
    proc_blockquote(pages)
    proc_list_indent(pages)
    proc_code(pages)
    n_figures = 0
    if images:
        n_figures = extract_images(doc, pages, outdir, path.stem)
    proc_captions(pages)

    manifest = {}
    if do_flag_math:
        manifest = flag_math(doc, pages, outdir, path.stem)

    md = render(pages, page_markers=page_markers)
    out = outdir / f"{path.stem}.md"
    out.write_text(md, encoding="utf-8")
    manifest["stats"] = {
        "pages": len(pages),
        "bytes": len(md.encode("utf-8")),
        "figures": n_figures,
        "equations": len(manifest.get("regions", [])),
        "ocr_pages": sum(1 for p in pages if p.ocr_used),
    }
    doc.close()
    return out, manifest


def summarize(stats: dict) -> str:
    """'17 pages -> 76 KB Markdown · 3 figures · 2 equation crops'."""
    kb = stats.get("bytes", 0) / 1024
    size = f"{kb:.0f} KB" if kb >= 1 else f"{stats.get('bytes', 0)} B"
    parts = [f"{stats.get('pages', 0)} pages → {size} Markdown"]
    if stats.get("figures"):
        parts.append(f"{stats['figures']} figure{'s' * (stats['figures'] != 1)}")
    if stats.get("equations"):
        n = stats["equations"]
        parts.append(f"{n} equation crop{'s' * (n != 1)}")
    if stats.get("ocr_pages"):
        parts.append(f"{stats['ocr_pages']} OCR'd")
    return " · ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("-o", "--outdir", default="md_out")
    ap.add_argument("--images", action="store_true",
                    help="extract figures (embedded rasters and vector drawings)")
    ap.add_argument("--flag-math", action="store_true",
                    help="crop equation regions for visual transcription")
    ap.add_argument("--page-markers", action="store_true",
                    help="emit <!-- page N --> markers at each page boundary")
    ap.add_argument("--apply-math", metavar="JSON",
                    help="splice transcribed LaTeX from a filled-in manifest "
                         "back into the matching .md, then exit")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    if args.apply_math:
        mpath = pathlib.Path(args.apply_math)
        md = outdir / (json.loads(mpath.read_text())["stem"] + ".md")
        print(f"applied {apply_math(md, mpath)} equation(s) to {md}")
        return

    outdir.mkdir(parents=True, exist_ok=True)
    for p in args.pdfs:
        path = pathlib.Path(p)
        out, manifest = convert(path, outdir, args.images, args.flag_math,
                                args.page_markers)
        print(f"{path.name} -> {out}")
        print(f"   {summarize(manifest.get('stats', {}))}")


if __name__ == "__main__":
    main()
