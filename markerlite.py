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
from dataclasses import dataclass, field, replace
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
from table_wrap import recover_wrapped_lines

warnings.filterwarnings("ignore", category=ConvergenceWarning)

# Table-grid reconstruction. table_recon.py is vendored from Marker (Apache-2.0,
# see third_party/marker/LICENSE) because it is already weight-free. The vendored
# copy is preferred; an installed marker-pdf is only a fallback. Never let this
# silently degrade to None on a normal install.
try:
    from table_recon import reconstruct_table_html
except ImportError:
    try:
        from marker.processors.table_recon import reconstruct_table_html
    except ImportError:
        reconstruct_table_html = None
        import warnings as _w
        _w.warn("table_recon.py not found beside markerlite.py; borderless "
                "table reconstruction is disabled", RuntimeWarning)


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
# The bullet-glyph half of LIST_ITEM_START on its own: a line that opens with
# a bullet is a list item whatever its weight or size, never a heading.
BULLET_START = re.compile(r"^\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f])\s")
# "**• item**": the same glyph after the emphasis markers block_text adds.
BULLET_IN_EMPHASIS = re.compile(r"^(\s*(?:\*{1,3}|_{1,2}))\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f])\s+")
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
    # The block stands inside a recognised reference list (classify).
    in_reference_list: bool = False
    # How a Figure block was found: "img" (embedded raster), "vec" (cluster
    # of paths) or "cap" (a caption no region claimed).
    figure_kind: str = ""
    # An equation that the source sets as a picture: it has no text layer.
    raster_equation: bool = False
    # A caption that detect_tables split off the top of its table: it is
    # emitted before the table, where the source has it.
    leads: bool = False
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
    # table_recon vs. geometric-cell decisions on this page (see
    # TABLE_FALLBACK_MIN_KEEP): how many tables were emitted, and how many of
    # them took PyMuPDF's cell text because the reconstruction lost words.
    tables_emitted: int = 0
    tables_fell_back: int = 0
    # Caption isolation and row extent (PLAN-tables item 7): tables whose
    # caption was split off before reconstruction, the words of those
    # captions, and source lines kept out of a grid because they stand below
    # its bottom rule. Caption words are counted apart from table words.
    table_captions_isolated: int = 0
    table_caption_words: int = 0
    table_lines_excluded: int = 0
    # text-only table proposals: accepted, and rejected because the grid lost words
    proposals_emitted: int = 0
    proposals_kept_prose: int = 0
    # A raster covers the page and the native layer is (at most) a stamp:
    # the page's content is in the image, whether or not OCR ran.
    image_only: bool = False
    # A raster covers the page (whatever the native layer holds): with OCR
    # unavailable such a page can emit almost nothing, see LOW_YIELD_WORDS.
    raster_covered: bool = False
    # The page was stored rotated or printed sideways and was turned upright.
    derotated: bool = False
    # The native layer extracts as nonsense (readable share under GARBLE_MIN).
    garbled: bool = False
    readable: float = 1.0
    # Words the source holds for this page: the native text layer's, or
    # Tesseract's (every confidence) when the page was recognised. 0 for a
    # page dropped as provenance. Compared with the words emitted; see
    # CONSERVATION_MIN.
    source_words: int = 0


# --------------------------------------------------------------------------- #
# extraction (replaces marker's LineBuilder / provider)
# --------------------------------------------------------------------------- #


def _bbox_of(items) -> Tuple[float, float, float, float]:
    xs0 = min(i[0] for i in items)
    ys0 = min(i[1] for i in items)
    xs1 = max(i[2] for i in items)
    ys1 = max(i[3] for i in items)
    return (xs0, ys0, xs1, ys1)


# When to OCR. A page with (almost) no native text is the obvious case. The
# other is an aggregator scan: ProQuest and ResearchGate deliver page images
# with a one-line native copyright stamp on every page (38-103 characters),
# which is enough to look like "a page with text" and left 40-page articles
# converting to nothing. So a page whose area is covered by one raster is
# also OCR'd when its native layer is shorter than this, and that native
# layer (the stamp) is discarded in favour of the recognised text. ProQuest's
# first page adds a 275-character citation banner to the stamp and shrinks
# the page image to 89.6% of the page to make room for it. A digital
# page that is mostly one figure with a caption is above the limit.
OCR_MAX_NATIVE_CHARS = 500
OCR_RASTER_MIN_FRAC = 0.8
OCR_STAMP_MARGIN = 0.15   # native text must lie in the top/bottom 15% to be a stamp
# Garbled text layers. A font whose ToUnicode map is wrong renders a clean
# page and extracts as nonsense ("Wkh txlfn eurzq ira"). Running text in any
# of the languages below is 25-60% function words and numerals, reference
# lists included; nonsense is near 0. A page with enough tokens whose share
# falls under GARBLE_MIN is treated like an image-only page: it is OCR'd and
# its native layer discarded. The measure is deliberately coarse - it finds a
# page that cannot be read, not a page with a few wrong characters.
GARBLE_MIN = 0.10
GARBLE_MIN_TOKENS = 50
_COMMON_WORDS = frozenset("""
the of and to in a is that for it as was with be by on not he this are or his from at which but
have an had they you were their one all we can her has there been if more when will would who so
no out up into than them only its some could these two may then do first any my now such like our
over man me even most made after also did many before must through back years where much your way
well down should because each just those people how too little state good very make world still
own see men work long get here between both life being under never day same another know while
last might us great old year off come since against go came right used take three
de la le les des et en un une du que qui dans pour pas au sur est par plus ne se ce il elle sont avec
der die das und den von zu mit sich auf ist nicht ein eine im dem des für als auch es an werden aus
er hat dass sie nach bei
el los las del y una por con para su al lo como más pero sus ya o este
di che per non sono da della si nel alla più anche
het een van dat op te zijn voor met niet aan ook bij door
""".split())
_WORD_TOKEN = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*")


def readable_ratio(text: str) -> Tuple[int, float]:
    """(tokens, share of them that are common words or numerals)."""
    tokens = _WORD_TOKEN.findall(text)
    if not tokens:
        return 0, 0.0
    hits = sum(1 for tok in tokens if tok.isdigit() or tok.lower() in _COMMON_WORDS)
    return len(tokens), hits / len(tokens)


# A page is "sideways" when at least this share of its characters runs
# vertically: a landscape table set on a portrait page, or a page stored with
# /Rotate. Such a page is turned upright before extraction. Below the share,
# vertical lines are axis labels or a watermark and are dropped as before.
ROTATED_PAGE_MIN_FRAC = 0.8


def _normalise_rotation(page: pymupdf.Page) -> Tuple[pymupdf.Page, bool]:
    """Return the page with its text upright, and whether it was turned.

    The tilt filter in extract_page drops every line that is not horizontal.
    That is right for a diagonal watermark and wrong for two real layouts,
    which it deleted whole: a page stored with /Rotate 90 (its text is
    vertical in unrotated coordinates although it displays upright), and a
    landscape table printed sideways on a portrait page.
    """
    doc, number = page.parent, page.number
    turned = False
    if page.rotation:
        page.remove_rotation()
        page = doc[number]
        turned = True
    up = down = total = 0
    for b in page.get_text("rawdict").get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            n = sum(len(sp.get("chars", [])) for sp in ln.get("spans", []))
            total += n
            dx, dy = ln.get("dir", (1.0, 0.0))
            if abs(dx) < 0.1 and dy < -0.9:
                up += n
            elif abs(dx) < 0.1 and dy > 0.9:
                down += n
    if total >= 100 and max(up, down) >= ROTATED_PAGE_MIN_FRAC * total:
        page.set_rotation(90 if up >= down else 270)
        page.remove_rotation()
        page = doc[number]
        turned = True
    return page, turned
# A page covered by a raster that emits fewer words than this is "low yield":
# the reader is looking at a page of text and the Markdown has a stamp or
# nothing. Without Tesseract every scanned page is one; with it, a page whose
# recognition failed. stats["low_yield_pages"] lists them so the GUI and the
# run log can say so instead of reporting a tiny file in silence.
LOW_YIELD_WORDS = 15
# Per-page conservation. A page whose emitted words are fewer than this share
# of the words its source holds is "lossy" and is reported with both numbers.
# It generalises the low-yield rule from raster pages to every page: the
# sideways table pages that a filter once deleted whole had a full native
# layer and converted to nothing without a word of warning. 0.5 is loose on
# purpose - furniture removal, dehyphenation and table reconstruction all
# cost a few percent - so a flag means a large part of the page is missing.
CONSERVATION_MIN = 0.5
# Pages holding fewer source words than this are not judged: a page that is
# only a running head and a number loses 100% of nothing.
CONSERVATION_MIN_SOURCE = 20


def _page_raster_covered(page: pymupdf.Page) -> bool:
    prect = page.rect
    area = max(prect.width * prect.height, 1.0)
    try:
        infos = page.get_image_info()
    except Exception:
        return False
    for info in infos:
        bbox = info.get("bbox")
        if not bbox:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height >= OCR_RASTER_MIN_FRAC * area:
            return True
    return False


# Mathematical-pi fonts carry operators on digit and punctuation codes and
# ship without a usable ToUnicode map: the minus sign extracts as "2" and
# "<" as ",". A regression table then reads "20.10" for -0.10. Such a font
# never draws a letter, and its "2" is always glued to the front of a number
# set in another font; both are required before anything is remapped.
PI_FONT_MAP = {"2": "−", ",": "<"}


def _remap_pi_fonts(pages: List[Page]) -> int:
    """Rewrite the glyphs of pi fonts in place; returns the spans changed."""
    inventory: dict = defaultdict(lambda: [0, 0, 0, 0])   # spans, letters, twos, twos-before-number
    for page in pages:
        if page.ocr_used:
            continue
        for blk in page.blocks:
            for ln in blk.lines:
                for i, sp in enumerate(ln.spans):
                    text = sp.text.strip()
                    if not text:
                        continue
                    inv = inventory[sp.font]
                    inv[0] += 1
                    if any(ch.isalpha() for ch in text):
                        inv[1] += 1
                    if text == "2":
                        inv[2] += 1
                        nxt = ln.spans[i + 1] if i + 1 < len(ln.spans) else None
                        if nxt is not None and nxt.font != sp.font \
                                and re.match(r"\s*\.?\d", nxt.text):
                            inv[3] += 1
    pi = {font for font, (n, letters, twos, glued) in inventory.items()
          if n >= 5 and letters == 0 and twos >= 3 and glued >= 0.8 * twos}
    changed = 0
    for page in pages:
        if page.ocr_used:
            continue
        for blk in page.blocks:
            for ln in blk.lines:
                for sp in ln.spans:
                    if sp.font in pi and any(ch in PI_FONT_MAP for ch in sp.text):
                        sp.text = "".join(PI_FONT_MAP.get(ch, ch) for ch in sp.text)
                        for c in sp.chars or []:
                            if c.get("c") in PI_FONT_MAP:
                                c["c"] = PI_FONT_MAP[c["c"]]
                        changed += 1
    return changed


def _emitted_words(page: Page) -> int:
    """Words this page contributes to the Markdown: the text of every block
    that is rendered, and for a table the words of the HTML it renders from
    (its grid may hold fewer words than the blocks it consumed)."""
    total = 0
    for blk in page.blocks:
        if blk.ignore_for_output or blk.btype in ("PageHeader", "PageFooter", "ImageMarker"):
            continue
        if blk.btype == "Table":
            total += _html_word_count(blk.html or "")
        else:
            total += len(blk.text.split())
        for child in blk.children:
            total += len(child.text.split())
    return total


def content_words(md: str) -> int:
    """The project's one word metric ("content words"): whitespace tokens of
    the Markdown after removing HTML comments, table separator rows, HTML
    tags, heading hashes, pipes, emphasis stars and $$ fences, NFKC-normalised.
    tests/audit_table_recovery.py and the GUI both use this."""
    import unicodedata
    text = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    text = re.sub(r"(?m)^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", " ", text)
    # Real tags only (<sup>, </sup>, <br>): a bare "<" is content ("p < .05")
    # and must not swallow everything up to the next ">".
    text = re.sub(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?>", " ", text)
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    # The escape render puts before a list-like paragraph start is markup,
    # not content: "\\* Alexander" and "1995\\. The" count as before.
    text = re.sub(r"(?m)^(\s*(?:>\s*)*)\\([*+-])(?=\s)", r"\1\2", text)
    text = re.sub(r"(?m)^(\s*(?:>\s*)*\d{1,9})\\([.)])(?=\s)", r"\1\2", text)
    text = text.replace("|", " ").replace("*", "").replace("$$", "")
    return len(unicodedata.normalize("NFKC", unescape(text)).split())


def stat_warnings(stats: dict) -> List[str]:
    """Human-readable warnings derived from convert()'s stats, shared by
    summarize(), the GUI's file list and the run log."""
    out: List[str] = []
    if stats.get("image_only_pages") and not stats.get("ocr_pages"):
        n = stats["image_only_pages"]
        out.append(f"{n} image-only page{'s' * (n != 1)}, 0 OCR'd \u2014 check Tesseract")
    low = stats.get("low_yield_pages") or []
    if low:
        shown = ", ".join(str(n) for n in low[:8]) + (", \u2026" if len(low) > 8 else "")
        out.append(f"{len(low)} low-yield page{'s' * (len(low) != 1)} ({shown})")
    garbled = stats.get("garbled_pages") or []
    if garbled:
        shown = ", ".join(str(n) for n in garbled[:8]) + (", \u2026" if len(garbled) > 8 else "")
        fate = ("OCR'd instead" if stats.get("garbled_ocr") == len(garbled)
                else "OCR unavailable \u2014 check Tesseract")
        out.append(f"{len(garbled)} garbled page{'s' * (len(garbled) != 1)} ({shown}): "
                   f"text layer unreadable, {fate}")
    lossy = stats.get("lossy_pages") or []
    if lossy:
        shown = ", ".join(f"p{d['page']} {d['emitted']}/{d['source']}" for d in lossy[:6])
        shown += ", \u2026" if len(lossy) > 6 else ""
        out.append(f"{len(lossy)} lossy page{'s' * (len(lossy) != 1)} ({shown})")
    if stats.get("tables_fallback"):
        n = stats["tables_fallback"]
        out.append(f"{n} of {stats.get('tables', n)} table{'s' * (n != 1)} fell back to cell text")
    if stats.get("proposals_kept_prose"):
        n = stats["proposals_kept_prose"]
        out.append(f"{n} text-table proposal{'s' * (n != 1)} kept as prose")
    if stats.get("provenance"):
        out.append("provenance page dropped: " + ", ".join(stats["provenance"]))
    return out


def _page_is_image_only(page: pymupdf.Page, native_chars: int,
                        native_lines=()) -> bool:
    """A page-covering raster with, at most, a stamp of native text.

    ``native_lines`` are the rawdict line bboxes. A stamp or citation banner
    sits in the top or bottom margin; a title printed over a decorative
    full-page background (a report cover) sits mid-page and is real text,
    so that page keeps its native layer.
    """
    if native_chars >= OCR_MAX_NATIVE_CHARS:
        return False
    prect = page.rect
    for x0, y0, x1, y1 in native_lines:
        yc = (y0 + y1) / 2 / max(prect.height, 1.0)
        if OCR_STAMP_MARGIN < yc < 1 - OCR_STAMP_MARGIN:
            return False
    area = max(prect.width * prect.height, 1.0)
    try:
        infos = page.get_image_info()
    except Exception:
        return False
    for info in infos:
        bbox = info.get("bbox")
        if not bbox:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height >= OCR_RASTER_MIN_FRAC * area:
            return True
    return False


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
    recognised = 0
    for r in rows:
        if len(r) < 12 or r[0] != "5":  # level 5 = word
            continue
        try:
            conf = float(r[10])
        except ValueError:
            continue
        text = r[11]
        if text.strip():
            recognised += 1
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
                blocks=blocks, ocr_used=True, source_words=recognised)


def _attach_drop_caps(blocks: List[Block]) -> int:
    """Put a drop capital back on the front of its paragraph.

    A drop cap is one capital letter set two or three lines tall beside the
    paragraph's opening lines. In the stream it is its own line, often ahead
    of the paragraph or after the heading above, so the heading gained a stray
    letter ("Strategy T") and the paragraph lost its first ("s part of a
    broader movement"). The cap is attached to the line that starts beside
    it, at its top, with a lowercase letter; without such a line it is left
    alone (the spaced letters of "A R T I C L E" are not drop caps).
    """
    sizes = [sp.size for b in blocks for ln in b.lines for sp in ln.spans if sp.text.strip()]
    if not sizes:
        return 0
    body = median(sizes)
    attached = 0
    for blk in list(blocks):
        for ln in list(blk.lines):
            text = ln.text.strip()
            if len(text) != 1 or not text.isalpha() or not text.isupper():
                continue
            if max(sp.size for sp in ln.spans) < 2.0 * body:
                continue
            x0, y0, x1, y1 = ln.bbox
            best = None
            for other in blocks:
                for cand in other.lines:
                    if cand is ln or not cand.spans:
                        continue
                    cx0, cy0, _cx1, cy1 = cand.bbox
                    ctext = cand.text.lstrip()
                    if (ctext[:1].islower() and y0 - 4 <= cy0 <= y1
                            and x1 - 3 <= cx0 <= x1 + 40
                            and (best is None or cy0 < best.bbox[1])):
                        best = cand
            if best is None:
                continue
            first = best.spans[0]
            best.spans[0] = replace(first, text=text + first.text.lstrip())
            blk.lines.remove(ln)
            attached += 1
        if not blk.lines and blk in blocks:
            blocks.remove(blk)
    return attached


def extract_page(page: pymupdf.Page, page_idx: int, ocr_if_empty: bool = True,
                 max_line_tilt: float = 0.1) -> Page:
    """Blocks in PDF character-stream order.

    Marker orders text-layer pages by pdftext character position rather than by
    its learned reading-order head ("the PDF's own character stream is the most
    reliable reading-order signal ... it beat surya's learned order head on
    multi-column pages" - builders/line.py). PyMuPDF's unsorted rawdict
    preserves that same stream order, so the enumeration index below is the
    direct equivalent of pdftext's ``span.minimum_position``.
    """
    ocr_used = False
    page, derotated = _normalise_rotation(page)
    raw = page.get_text("rawdict")
    text_len = sum(
        len(c.get("c", ""))
        for b in raw.get("blocks", [])
        for ln in b.get("lines", [])
        for s in ln.get("spans", [])
        for c in s.get("chars", [])
    )
    native_lines = [tuple(ln["bbox"]) for b in raw.get("blocks", []) if b.get("type") == 0
                    for ln in b.get("lines", [])]
    image_only = _page_is_image_only(page, text_len, native_lines)
    raster_covered = image_only or _page_raster_covered(page)
    n_tokens, readable = readable_ratio(page.get_text())
    garbled = n_tokens >= GARBLE_MIN_TOKENS and readable < GARBLE_MIN
    if ocr_if_empty and (text_len < 20 or image_only or garbled):
        ocr_page = _ocr_page(page, page_idx)
        if ocr_page is not None:
            ocr_page.garbled = garbled
            ocr_page.readable = readable
            ocr_page.image_only = image_only
            ocr_page.raster_covered = raster_covered
            ocr_page.derotated = derotated
            return ocr_page

    counter = 0
    blocks: List[Block] = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        lines: List[Line] = []
        for ln in b.get("lines", []):
            # Rotated text is never body text: a diagonal "DRAFT"/"RETIRED"
            # watermark kept as a line seeds fake table columns and leaks
            # one-letter cells. rawdict gives each line its writing direction;
            # anything not near-horizontal is dropped here, before any
            # processor sees it.
            direction = ln.get("dir", (1.0, 0.0))
            if len(direction) == 2 and abs(direction[1]) > max_line_tilt:
                continue
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

    _attach_drop_caps(blocks)
    return Page(
        page_idx=page_idx,
        width=page.rect.width,
        height=page.rect.height,
        blocks=blocks,
        ocr_used=ocr_used,
        image_only=image_only,
        raster_covered=raster_covered,
        derotated=derotated,
        source_words=len(page.get_text().split()),
        garbled=garbled,
        readable=readable if n_tokens >= GARBLE_MIN_TOKENS else 1.0,
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


# A grid reconstruction may keep no less than this share of the words that
# PyMuPDF's own geometric cells hold for the same table. table_recon assigns
# text to rows by y-band and has nowhere to put the continuation lines of a
# tall wrapped cell, so on compliance-style tables it can "win" the sanity
# check with a tidy grid that has silently dropped most of the cell text (the
# SBTi protocol lost 70% of some pages this way). Silent data loss is worse
# than an ugly grid: below this ratio the geometric cells are used instead.
TABLE_FALLBACK_MIN_KEEP = 0.9


def _html_word_count(html: str) -> int:
    """Words of visible text in a table's HTML (tags stripped)."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(unescape(text).split())


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


# --------------------------------------------------------------------------- #
# caption isolation and row extent (PLAN-tables item 7; markerlite-owned)
# --------------------------------------------------------------------------- #

# A table label. No punctuation is demanded after the number ("Table 1 Study
# 1 Descriptive ..."): inside a table candidate the safety that the delimiter
# gives in running text comes from layout instead - the line leads the
# candidate, stands alone in its row and is not split into cells.
TABLE_LABEL = re.compile(r"^\s*(table|tbl\.?)\s*(\d{1,3}|[IVX]{1,4})[a-z]?\b", re.I)
# The first line under a bottom rule when it is a note, not a row.
TABLE_NOTE = re.compile(
    r"^\s*(notes?|sources?)\s*[.:]|^\s*[*\u2020\u2021]+\s*p\s*[<=\u2264]", re.I)
# A horizontal rule counts for a candidate when its segments cover this share
# of the candidate's width (journals draw a rule as one segment per column).
RULE_MIN_COVER = 0.6


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
    bands: List[list] = []          # [y, covered length]
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


def _isolate_table(members: List[Block], bbox, rules: list, others: list,
                   bound_rows: bool = True):
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
    entries = sorted(((ln, blk) for blk in members for ln in blk.lines if ln.text.strip()),
                     key=lambda e: (e[0].bbox[1], e[0].bbox[0]))
    if len(entries) < 3:
        return [], [], None
    ys = _rules_in(rules, bbox)

    def alone(i: int) -> bool:
        ln = entries[i][0]
        mid = (ln.bbox[1] + ln.bbox[3]) / 2
        return not any(j != i and o.bbox[1] <= mid <= o.bbox[3]
                       for j, (o, _b) in enumerate(entries))

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
            if abs(_line_size(ln) - _line_size(first)) > 0.6:
                break
            if ln.bbox[1] - prev.bbox[3] > 0.8 * max(prev.height, 1.0):
                break
            if abs(ln.bbox[0] - first.bbox[0]) > 3.0 and abs(
                    (ln.bbox[0] + ln.bbox[2]) - (first.bbox[0] + first.bbox[2])) > 10.0:
                break
            caption.append(ln)
        rest = [e for e in entries if not any(e[0] is c for c in caption)]
        bands = {round(e[0].bbox[1] / 4) for e in rest}
        if len(bands) < 2:
            caption = []        # nothing like a grid is left: not a caption split
    top = bbox[1]
    if caption:
        top = max(c.bbox[3] for c in caption)
        ys = [y for y in ys if y >= top - 1.5]

    excluded: List[Line] = []
    bottom = bbox[3]
    if bound_rows and len(ys) >= 2:
        last = ys[-1]
        below = [e[0] for e in entries
                 if (e[0].bbox[1] + e[0].bbox[3]) / 2 > last + 0.5
                 and not any(e[0] is c for c in caption)]
        # Strokes that are not rules inside the grid - cell borders, a frame
        # around the rows - mean the table is boxed after all: it is closed
        # by its frame, and what stands under an inner rule is a row.
        framed = any(o[1] < last - 1 and o[3] > top + 1
                     and min(o[2], bbox[2]) - max(o[0], bbox[0]) > 0
                     and min(o[3], bbox[3]) - max(o[1], bbox[1]) >= 0
                     for o in others)
        if below and not framed:
            diagram = any(o[1] >= last - 1 and o[3] <= bbox[3] + 2 and (o[3] - o[1]) > 3
                          and min(o[2], bbox[2]) - max(o[0], bbox[0]) > 0
                          for o in others)
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
        return Block(lines=lines, bbox=_bbox_of([ln.bbox for ln in lines]),
                     page_idx=src.page_idx, char_pos=lines[0].char_pos, btype=btype)

    grid_members, leftovers, touched, cap_lines, cap_src = [], [], [], [], None
    for blk in members:
        cap = [ln for ln in blk.lines if among(ln, caption)]
        out = [ln for ln in blk.lines if among(ln, excluded)]
        grid = [ln for ln in blk.lines if not among(ln, caption) and not among(ln, excluded)]
        if not cap and not out:
            grid_members.append(blk)
            touched.append(blk)
            continue
        if not cap and not grid:
            continue                    # wholly below the grid: stays on the page
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
            if area > 0.6 * page_area or area < 200:
                continue  # a "table" covering the page is the page, not a table
            if any(_overlap_frac(bb, prev) > 0.6 for prev in seen_bboxes):
                continue
            seen_bboxes.append(bb)
            found.append(tbl)
            if kw:
                ruled_only.add(id(tbl))
    if not found:
        return

    consumed: set = set()
    new_blocks: List[Block] = []
    rules, others = _page_graphics(pmpage)
    for tbl in found:
        bbox = tuple(tbl.bbox)
        members = [
            b for i, b in enumerate(page.blocks)
            if i not in consumed and _overlap_frac(b.bbox, bbox) > 0.5
        ]
        if not members:
            continue

        # The caption and whatever stands under the bottom rule leave the
        # candidate before anything is reconstructed or counted. ``members``
        # is from here on the grid's own source: the text-loss guard and the
        # audit compare table words with table words, so a caption that
        # survived cannot make up for a number that did not.
        caption_block, leftovers, caption_tokens, lines_excluded = None, [], 0, 0
        touched = members
        try:
            cap_lines, out_lines, extent = _isolate_table(
                members, bbox, rules, others, bound_rows=id(tbl) in ruled_only)
        except Exception:
            cap_lines, out_lines, extent = [], [], None
        if extent is not None:
            grid_members, caption_block, leftovers, touched = _split_members(
                members, cap_lines, out_lines)
            if len(grid_members) == 0:
                caption_block, leftovers, touched, extent = None, [], members, None
            else:
                members = grid_members
                bbox = (bbox[0], max(bbox[1], extent[0]), bbox[2], min(bbox[3], extent[1] + 1.0))
                lines_excluded = len(out_lines)
                if caption_block is not None:
                    caption_tokens = len(caption_block.text.split())

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
                res = recover_wrapped_lines(lines, res, tbl)
            except Exception:
                res = None
            if res:
                html, score = res

        # PyMuPDF's geometric cells: text assigned by cell bbox, so wrapped
        # lines stay in their cell. Used when the reconstruction is unusable,
        # and also when it is "sane" but has lost words (TABLE_FALLBACK_MIN_KEEP).
        try:
            fallback = _grid_to_html(_grid_from_members(tbl, members))
        except Exception:
            fallback = ""
        fell_back = False
        if not html or not _table_sane(html):
            # No usable reconstruction: the geometric grid stands in only if
            # it passes the same sanity check (else the region stays prose).
            html = fallback if _table_sane(fallback) else ""
            fell_back = bool(html)
        elif fallback:
            # A usable reconstruction still loses to the geometric grid when
            # it has dropped words. The grid is not required to be "sane"
            # here: a sparse criteria table has many genuinely empty cells,
            # which is what _table_sane rejects, and its text is geometric
            # truth - every word sits in the cell the ruling lines put it in.
            kept, cells = _html_word_count(html), _html_word_count(fallback)
            if kept < TABLE_FALLBACK_MIN_KEEP * cells:
                html, fell_back = fallback, True
        if not html:
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
                res = recover_wrapped_lines(lines, res)
            except Exception:
                continue
            if not res:
                continue
            html, score = res
            ncols = html.count("<th>") or html.split("</tr>")[0].count("<td>")
            if score < min_score or not (2 <= ncols <= 12) or not _table_sane(html):
                continue
            # Text-loss guard, the proposal path's counterpart of the one in
            # detect_tables. The proposal consumes this block, so the block's
            # own words are the baseline: a grid that keeps fewer than
            # TABLE_FALLBACK_MIN_KEEP of them has dropped rows (justified OCR
            # prose on a two-column scan loses half its lines this way) and
            # the block stays prose. This rejects proposals only; it does not
            # change what is admitted (PLAN-tables items 4 and 5 still stand).
            src_words = len(blk.text.split())
            if src_words and _html_word_count(html) < TABLE_FALLBACK_MIN_KEEP * src_words:
                page.proposals_kept_prose += 1
                continue
            page.tables_emitted += 1
            page.proposals_emitted += 1
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
                continue        # split off a table candidate by detect_tables
            text = blk.text.strip()
            if not text:
                blk.ignore_for_output = True
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
            if blk.font_ratio("mono") > 0.8 and len(blk.lines) > 1:
                blk.btype = "Code"
                continue
            if CAPTION_START.match(first) and len(text) < 900:
                blk.btype = "Caption"
                continue
            # Headings are tested BEFORE lists: "2. Method" satisfies the list
            # pattern too, and a numbered heading must not become a bullet.
            is_head = _is_heading(blk, body_size, text, first, ocr=page.ocr_used,
                                  in_refs=in_refs)
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


# "* p < .05", "** p < .01", "† p < .10": the significance legend under a
# regression table opens with the same symbols as a symbol footnote. It
# belongs to its table, not to the page's notes. Some fonts map "<" to ","
# so both are accepted.
SIGNIFICANCE_LEGEND = re.compile(
    r"^\s*[*†‡+]{1,3}\s*p\s*[<≤,]\s*0?\.\d", re.I)


# The same legend when the relation glyph did not survive extraction: a pi
# font with no Unicode mapping leaves "* p  .05", or a control character
# where the "<" was (R00315 p. 15 has U+0007 there).
SIGNIFICANCE_LEGEND_BARE = re.compile(
    r"^\s*[*\u2020\u2021+]{1,3}\s*p[\s\x00-\x1f]{1,4}0?\.\d", re.I)

# Symbols that open a symbol footnote - and a starred reference, a legend, a
# membership mark. Which of these a line is, only its context can say.
SYMBOL_LED = re.compile(r"^\s*([*\u2020\u2021\u00a7\u00b6]{1,3})")
# The heading of a reference list, which may carry a note mark of its own
# ("REFERENCES" with a raised "a" that explains the stars).
REF_LIST_HEAD = re.compile(
    r"^\s*(references|bibliography|works cited|literature cited)\s*[a-z*\u2020\u2021]?\s*$",
    re.I)
# "Surname, I." or "Surname, I. J." after the marks: how a reference opens.
REF_ENTRY_SHAPE = re.compile(
    r"^\s*[*\u2020\u2021\u00a7\u00b6]{0,3}\s*[A-Z][\w\u00a8\u2019' .\-]{1,40},\s+(?:[A-Z]\.\s*){1,4}")
# A line that says what the marks mean: "Studies marked with an asterisk were
# included in ...; those with a dagger, in ...".
MARK_LEGEND = re.compile(
    r"\b(marked|denoted|indicated|preceded|identified)\b.{0,40}\b(asterisks?|daggers?|stars?)\b"
    r"|\b(asterisks?|daggers?)\b.{0,60}\b(indicates?|denotes?|marks?|(?:were|are) included)\b",
    re.I | re.S)


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
    return label, text[m.end():]


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
    if blk.y_start / h < 0.70:
        return False
    if body_size and note_text_size(blk) >= body_size * 0.95:
        return False
    if SIGNIFICANCE_LEGEND.match(first):
        return False
    if _symbol_is_notation(blk, page):
        return False
    return bool(FOOTNOTE_MARKER.match(first))


def _is_heading(blk: Block, body_size: float, text: str, first: str,
                ocr: bool = False, in_refs: bool = False) -> bool:
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
    bold = blk.font_ratio("bold") > 0.6
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
            if len(words) == 1 and words[0].isalpha() and words[0][0].isupper() \
                    and len(words[0]) >= 4:
                return True
    if not (bigger or bold):
        return False
    # A heading of one word ("Conclusion", "Contributions") fails the
    # title-case test, which needs two. With real weight or size evidence, a
    # lone capitalised word in its own one-line block is a heading.
    if (not ocr and len(blk.lines) == 1 and len(words) == 1 and words[0].isalpha()
            and words[0][0].isupper() and len(words[0]) >= 4):
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
    return caps / len(cand) > 0.6


# --------------------------------------------------------------------------- #
# processors ported from marker (all weight-free)
# --------------------------------------------------------------------------- #

TEXTISH = ("Text", "SectionHeader", "ListItem", "Caption", "Equation")


def proc_line_numbers(pages: List[Page], margin_frac=0.14, min_count=8) -> None:
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
        inc = sum(1 for a, b in zip(vals, vals[1:]) if b > a)
        return inc >= 0.8 * (len(vals) - 1)

    for page in pages:
        cands = []
        for blk in page.blocks:
            if blk.ignore_for_output:
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
            if (len(lines) >= min_count
                    and all(x.isdigit() and len(x) <= 4 for x in lines)
                    and _increasing([int(x) for x in lines])):
                blk.ignore_for_output = True
        if len(cands) < min_count:
            continue
        vals = [v for v, _ in sorted(cands, key=lambda c: c[1].y_start)]
        if _increasing(vals):
            for _v, blk in cands:
                blk.ignore_for_output = True


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
    """Furniture text with its page-number tokens removed, for repetition
    matching. A leading or trailing token that merely CONTAINS a digit goes
    too: OCR reads "1995 Suchman 579" on one page and "1995 Suchman $79" on
    the next, and "Suchman $79" missed the fuzzy match against "Suchman"."""
    text = text.replace("\n", "").strip()
    text = re.sub(r"^\S*\d\S*\s*", "", text)
    text = re.sub(r"\s*\S*\d\S*$", "", text)
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
            if b.btype in (*TEXTISH, "Table") and not b.ignore_for_output and b.text.strip()
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

        for blk in text_blocks:
            y0, y1 = yfrac(blk)
            if (y1 - y0) > max_height_frac:
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
            if body and note_text_size(blk) >= body * 0.95:
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
                and blk.y_start / h >= 0.70
                and (not body or note_text_size(blk) < body * 0.95)
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


def proc_reflow(pages: List[Page], max_gap_lines=2.4, ragged_tol=0.15,
                indent_frac=0.015, margin_frac=0.14) -> None:
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
        texts = [b for b in page.blocks if b.btype == "Text" and not b.ignore_for_output
                 and b.lines]
        if len(texts) < 2:
            continue
        # The column edges come from body-sized blocks that are not parked in
        # a margin. A line-number column at x=8 once set ``left`` for the whole
        # page, which made every body line look indented and stopped all
        # joining (the Ragins manuscript case).
        size_med = median([b.max_size() for b in texts])
        body_blocks = [
            b for b in texts
            if b.max_size() >= 0.9 * size_med
            and b.x_end > margin_frac * page.width
            and b.x_start < (1 - margin_frac) * page.width
        ] or texts
        left = min(b.x_start for b in body_blocks)
        right = max(b.x_end for b in body_blocks)
        width = max(right - left, 1.0)
        lh = median([b.line_height() for b in body_blocks if b.line_height() > 0] or [12.0])

        merged: List[Block] = []
        grown: set = set()  # blocks assembled here from single lines
        for blk in page.blocks:
            prev = merged[-1] if merged else None
            if (
                prev is not None
                and blk.btype == "Text" and prev.btype == "Text"
                and not blk.ignore_for_output and not prev.ignore_for_output
                and blk.lines and prev.lines
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
                    if (-2 < gap < max_gap_lines * lh and full_width and not indented
                            and size_ok):
                        prev.lines.extend(blk.lines)
                        prev.bbox = _bbox_of([ln.bbox for ln in prev.lines])
                        grown.add(id(prev))
                        continue
            merged.append(blk)
        page.blocks = merged


def proc_continuation(pages: List[Page], column_gap_ratio=0.02) -> None:
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
                    # a table does not own a figure's caption: the figure
                    # would then go unmarked (Peng 2009 p. 2)
                    if blk.btype == "Table" and FIGURE_CAPTION.match(blocks[j].text.strip()):
                        continue
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


def _strip_source_label(spans: List[Span], raw: str) -> List[Span]:
    """The line's spans without the footnote label that opens ``raw``.

    Only the characters FOOTNOTE_MARKER matched in the SOURCE text are
    removed; nothing is inferred from formatted Markdown, where the ``**`` of
    a bold note looks exactly like a two-star symbol marker.
    """
    m = FOOTNOTE_MARKER.match(raw)
    n = m.end() if m else 0
    out: List[Span] = []
    for sp in spans:
        if n <= 0:
            out.append(sp)
        elif len(sp.text) <= n:
            n -= len(sp.text)
        else:
            out.append(replace(sp, text=sp.text[n:], chars=list(sp.chars[n:]) if sp.chars else []))
            n = 0
    return out


def _footnote_groups(blk: Block, fn_labels=frozenset()) -> List[Tuple[Optional[str], str]]:
    """(label, formatted body) for every note in a Footnote block.

    Labels and continuation boundaries come from the raw line text. A line
    opens a new note when it starts with a source marker; a numeric marker on
    a later line must also be larger than the previous note's number, so a
    wrapped line that happens to begin "12 firms ..." stays a continuation.
    The label is removed from the spans, the note's lines are merged (soft
    breaks unwrapped, line-end hyphens closed), and only then is the body
    formatted, so emphasis runs across lines without seams.
    """
    groups: List[list] = []
    prev_num: Optional[int] = None
    for ln in blk.lines:
        raw = ln.text
        if not raw.strip():
            continue
        label, _body = footnote_label(raw)
        if label is not None and label.isdigit() and groups and prev_num is not None \
                and int(label) <= prev_num:
            label = None
        if label is not None or not groups:
            spans = _strip_source_label(ln.spans, raw) if label is not None else list(ln.spans)
            groups.append([label, [spans]])
            if label is not None and label.isdigit():
                prev_num = int(label)
        else:
            groups[-1][1].append(list(ln.spans))

    out: List[Tuple[Optional[str], str]] = []
    for label, lines in groups:
        merged: List[Span] = []
        for spans in lines:
            if not spans:
                continue
            if merged:
                tail = "".join(sp.text for sp in merged).rstrip()
                last = merged[-1]
                if HYPHEN_END.match(tail):
                    merged[-1] = replace(last, text=re.sub(r"[-\u2014\u00ac]\s*$", "", last.text))
                    spans = [replace(spans[0], text=spans[0].text.lstrip())] + list(spans[1:])
                elif not last.text.endswith((" ", "\t")):
                    merged[-1] = replace(last, text=last.text + " ")
            merged.extend(spans)
        body = re.sub(r"[ \t]+", " ", _inline(merged, fn_labels)).strip()
        out.append((label, body))
    return out


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


# How a Markdown list item opens: a bullet or a number with "." or ")",
# then white space. A paragraph that merely begins that way - a starred
# reference ("* Alexander, J. A. ..."), a sentence that opens with a year
# ("1995. The ...") - would be shown as a list by any renderer.
LIST_LOOKALIKE = re.compile(r"^(\s*)(?:([*+-])|(\d{1,9})([.)]))(?=\s)")


def _escape_list_start(text: str) -> str:
    """Escape the marker of a paragraph that is not a list item."""
    m = LIST_LOOKALIKE.match(text)
    if not m:
        return text
    if m.group(2):
        return m.group(1) + "\\" + text[m.end(1):]
    return m.group(1) + m.group(3) + "\\" + text[m.end(3):]


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
            out.append(_escape_list_start(pending_paragraph.strip()))
        pending_paragraph = ""

    for page in pages:
        if page_markers:
            # Cheap in context, and it lets you ask an LLM where in the source
            # PDF something came from.
            flush()
            out.append(f"<!-- page {page.page_idx + 1} -->")
        if page.ocr_used:
            flush()
            out.append(f"<!-- ocr page {page.page_idx + 1} -->")
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
                    # The glyph may sit inside the emphasis markers that
                    # block_text wrapped around a bold or italic item.
                    txt = BULLET_IN_EMPHASIS.sub(r"\1", txt, count=1)
                    txt = re.sub(LIST_ITEM_START, "", txt, count=1)
                item = "  " * blk.list_indent + f"{bullet} {txt}"
                # Keep a run of items in one list: no blank line between them.
                if out and _is_list_line(out[-1]):
                    out[-1] = out[-1] + "\n" + item
                else:
                    out.append(item)
            elif t == "Table":
                md = table_html_to_markdown(blk.html or "")
                for cap in blk.children:
                    if cap.leads:
                        out.append("*" + block_text(cap, plain=True) + "*")
                out.append(md or (blk.html or ""))
                for cap in blk.children:
                    if not cap.leads:
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
                if blk.raster_equation:
                    # No text layer to show. The comment keeps the place;
                    # --apply-math replaces it with the transcription.
                    number = " ".join(c.text.strip() for c in blk.children)
                    number = f"; number {number}" if number else ""
                    out.append(f"<!-- equation: p. {blk.page_idx + 1}; "
                               f"set as an image{number} -->")
                    if blk.image_path:
                        out.append(f"![]({blk.image_path})")
                    if blk.eq_id:
                        out.append(f"<!-- markerlite:eq {blk.eq_id} -->")
                elif body:
                    out.append(f"$$\n{body}\n$$")
                    if blk.eq_id:
                        # Anchor for --apply-math: a vision transcription of the
                        # matching crop replaces the block above, in place.
                        out.append(f"<!-- markerlite:eq {blk.eq_id} -->")
            elif t == "Footnote":
                if keep_footnotes:
                    # Labels are read from the source spans, never from the
                    # formatted string: "**3During ...**" reparsed as Markdown
                    # gave every bold line the label "**".
                    for label, body in _footnote_groups(blk, fn_labels):
                        if label is None:
                            anon_counter[0] += 1
                            label = f"n{anon_counter[0]}"
                        # Real footnote syntax: a labeled definition. "[^]:"
                        # carried no identity, so downstream tools had to guess
                        # which lines belonged to which note.
                        out.append(f"[^{label}]: {body.strip()}")
            elif t == "Figure":
                # Always a placeholder at the figure's reading position; the
                # link follows when --images saved the figure. "--" cannot
                # appear inside an HTML comment.
                caption = " ".join(block_text(cap, plain=True) for cap in blk.children)
                caption = caption.replace("--", "\u2013").strip() or "none found"
                out.append(f"<!-- figure: p. {blk.page_idx + 1}; caption: {caption} -->")
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


def _content_images(pm: pymupdf.Page, min_side: float = 40.0,
                    max_page_frac: float = 0.9,
                    span_frac: float = 0.95) -> List[Tuple[int, int, tuple]]:
    """(index, xref, bbox) of the embedded rasters that are content.

    Two kinds are not: icons (either side under ``min_side`` points) and
    backgrounds. A background covers more than ``max_page_frac`` of the page,
    or spans the page's full height or full width (``span_frac``): Word
    exports a page-sized raster behind every page of some documents, and on
    landscape pages splits it into page-height vertical bands that are each
    well under 90% of the area. None of these is a figure to extract or an
    image worth announcing.
    """
    out = []
    prect = pm.rect
    page_area = max(prect.width * prect.height, 1.0)
    for n, info in enumerate(pm.get_image_info(xrefs=True)):
        xref = info.get("xref", 0)
        bbox = info.get("bbox")
        if not xref or not bbox:
            continue
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w < min_side or h < min_side:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height > max_page_frac * page_area:
            continue
        if clip.height >= span_frac * prect.height or clip.width >= span_frac * prect.width:
            continue
        out.append((n, xref, tuple(bbox)))
    return out


def _insert_block(page: Page, blk: Block) -> None:
    """Put a lineless block (figure, marker) in front of the first text block
    that starts at or below it, leaving the rest of the page order alone.

    Sorting the whole page by char_pos looked equivalent but was not:
    proc_footnotes had already moved the notes to the end of the page, and a
    sort pulled them back to their stream position, mid-page.
    """
    y0 = blk.y_start
    for i, b in enumerate(page.blocks):
        if b.lines and b.btype != "Footnote" and b.y_start >= y0 - 2:
            page.blocks.insert(i, blk)
            return
    page.blocks.append(blk)


def _figure_regions(pm: pymupdf.Page, page: Page) -> List[Tuple[str, int, int, tuple]]:
    """(kind, index, xref, bbox) of every figure on the page: embedded rasters
    that are content, then clusters of vector paths that are neither a table
    nor mostly text."""
    found: List[Tuple[str, int, int, tuple]] = [
        ("img", n, xref, bbox) for n, xref, bbox in _content_images(pm)]
    taken = [f[3] for f in found]
    for n, box in enumerate(_vector_regions(pm)):
        bt = tuple(box)
        if any(_overlap_frac(bt, tk) > 0.5 for tk in taken):
            continue  # already captured as a raster
        # A ruled table is also "a pile of path operators". Two tells: it
        # overlaps a detected Table, or the region is mostly text.
        if any(b.btype == "Table" and _overlap_frac(b.bbox, bt) > 0.4 for b in page.blocks):
            continue
        area = max((bt[2] - bt[0]) * (bt[3] - bt[1]), 1.0)
        text_area = sum(_overlap_frac(b.bbox, bt) * b.width * b.height
                        for b in page.blocks if b.lines)
        if text_area / area > 0.35:
            continue
        found.append(("vec", n, 0, bt))
    return found


FIGURE_CAPTION = re.compile(r"^\s*(figure|fig\.?)\s*[\dIVXA-Z]+", re.I)


# Journals that set the label on its own line or in capitals put no
# punctuation after the number: "FIGURE 1 / A Process Model of ...",
# "Figure 1 Institutional Complexity and Organizational Responses". The
# general caption pattern demands a delimiter so that a sentence opening
# "Figure 1 shows ..." stays prose; for figures the same safety comes from
# what follows the number: nothing, or a capitalised word.
FIGURE_LABEL = re.compile(r"^\s*(figure|fig\.?)\s*(\d{1,3}|[IVX]{1,4})[a-z]?\b\s*(.*)$", re.I | re.S)


def _promote_figure_captions(pages: List[Page], max_words: int = 60) -> int:
    """Relabel a short text block that is a figure caption without a
    delimiter, so it can be attached to its figure or mark one."""
    count = 0
    for page in pages:
        for blk in page.blocks:
            # A bold caption in capitals has usually been taken for a heading.
            if blk.btype not in ("Text", "SectionHeader") or blk.ignore_for_output                     or not blk.lines:
                continue
            text = blk.text.strip()
            if len(text.split()) > max_words:
                continue
            m = FIGURE_LABEL.match(text)
            if not m:
                continue
            rest = m.group(3).lstrip()
            first_line_is_label = FIGURE_LABEL.match(blk.lines[0].text.strip()) is not None \
                and not FIGURE_LABEL.match(blk.lines[0].text.strip()).group(3).strip()
            if first_line_is_label or not rest or rest[:1].isupper():
                blk.btype = "Caption"
                count += 1
    return count


# How far, as a share of page height, a figure caption may stand from an
# uncaptioned figure region on the same page and still belong to it.
FIGURE_CAPTION_REACH = 0.25


def _figures_from_captions(pages: List[Page]) -> int:
    """A figure caption that no detected region claimed still marks a figure.

    On a scanned page the figure is part of the page image, and some drawn
    figures are too sparse to cluster; in both cases the caption is the only
    evidence. The placeholder is put where the caption stands, and the
    caption becomes its child like any other.

    A detected region that is still without a caption comes first: axis
    labels and legend text often stand between a chart and its caption in
    the stream, so proc_captions, which looks only at neighbours, misses
    the pair and the figure would be marked twice.
    """
    count = 0
    for page in pages:
        reach = FIGURE_CAPTION_REACH * page.height
        for i, blk in enumerate(list(page.blocks)):
            if blk.btype != "Caption" or blk.ignore_for_output:
                continue
            if not FIGURE_CAPTION.match(blk.text.strip()):
                continue
            best, best_gap = None, reach
            for other in page.blocks:
                if other.btype != "Figure" or other.ignore_for_output:
                    continue
                if any(c.btype == "Caption" for c in other.children):
                    continue
                gap = max(0.0, max(other.y_start, blk.y_start)
                          - min(other.y_end, blk.y_end))
                if gap < best_gap:
                    best, best_gap = other, gap
            if best is not None:
                best.children.append(blk)
                blk.ignore_for_output = True
                continue
            i = page.blocks.index(blk)
            fig = Block(lines=[], bbox=blk.bbox, page_idx=page.page_idx,
                        char_pos=blk.char_pos - 0.5, btype="Figure", figure_kind="cap")
            fig.children.append(blk)
            blk.ignore_for_output = True
            page.blocks.insert(i, fig)
            count += 1
    return count


# --------------------------------------------------------------------------- #
# equations set as pictures
# --------------------------------------------------------------------------- #

# The sentence before a displayed formula says so: "as shown by the formula
# below", "described by the following formula:".
EQ_LEADIN = re.compile(
    r"\b(formula|equation|expression)s?\s+(below|that\s+follows)\b"
    r"|\b(following|below)\s+(formula|equation|expression)s?\b", re.I)
# What follows one: "Where:", "where n is ...", or a definition "RTD = ...".
EQ_WHERE = re.compile(r"^\s*where\b", re.I)
EQ_DEFINITION = re.compile(r"^\s*[A-Za-z][\w\u0080-\uffff]{0,12}\s*=\s+\S")
# The number of a displayed equation, alone on its line: "(3)", "(4a)".
EQ_NUMBER_ALONE = re.compile(r"^\s*\(\d{1,3}[a-z]?\)\s*$")
# A picture taller than this share of the page is not a displayed formula.
RASTER_EQ_MAX_HEIGHT = 0.2
# How far, as a share of page height, the sentence before or the line after
# may stand from the picture.
RASTER_EQ_REACH = 0.06


def _equation_neighbourhood(fig: Block, page: Page) -> Tuple[bool, Optional[Block]]:
    """(is an equation, the text block above) for a raster without caption.

    A picture has no glyphs, so the evidence is around it: an equation number
    alone at the right margin beside it, a "Where:" or a definition line
    under it, or a sentence above it that announces a formula.
    """
    h = page.height or 1.0
    reach = RASTER_EQ_REACH * h
    x0, y0, x1, y1 = fig.bbox
    mid = (y0 + y1) / 2
    texts = [b for b in page.blocks
             if b.lines and not b.ignore_for_output and b.btype not in ("Table", "Figure")
             and b.text.strip()]
    above = [b for b in texts if b.y_start < y0 and b.y_end <= mid and y0 - b.y_end <= reach]
    below = [b for b in texts if b.y_start >= mid and b.y_start - y1 <= reach]
    upper = max(above, key=lambda b: b.y_end) if above else None
    lower = min(below, key=lambda b: b.y_start) if below else None

    numbered = False
    for b in texts:
        for ln in b.lines:
            cy = (ln.bbox[1] + ln.bbox[3]) / 2
            if y0 - 2 <= cy <= y1 + 2 and EQ_NUMBER_ALONE.match(ln.text) \
                    and ln.bbox[0] >= (x0 + x1) / 2:
                numbered = True
                if len(b.lines) == 1:
                    # the number belongs to the equation, not to the prose
                    fig.children.append(b)
    after = bool(lower) and bool(EQ_WHERE.match(lower.text) or EQ_DEFINITION.match(lower.text))
    before = bool(upper) and bool(EQ_LEADIN.search(upper.text[-600:]))
    return (numbered or after or before), upper


def _route_raster_equations(pages: List[Page]) -> int:
    """Turn a caption-less picture of a formula from a Figure into an
    Equation, so that it is cropped by --flag-math and not described as a
    figure. It is placed after the sentence that announces it."""
    count = 0
    for page in pages:
        for blk in list(page.blocks):
            if blk.btype != "Figure" or blk.figure_kind != "img" or blk.ignore_for_output:
                continue
            if any(c.btype == "Caption" for c in blk.children):
                continue
            if blk.height > RASTER_EQ_MAX_HEIGHT * (page.height or 1.0):
                continue
            is_eq, upper = _equation_neighbourhood(blk, page)
            if not is_eq:
                blk.children = [c for c in blk.children if c.btype == "Caption"]
                continue
            blk.btype = "Equation"
            blk.needs_vision = True
            blk.raster_equation = True
            for child in blk.children:
                child.ignore_for_output = True
            if upper is not None and any(upper is b for b in page.blocks):
                page.blocks = [b for b in page.blocks if b is not blk]
                at = next(i for i, b in enumerate(page.blocks) if b is upper)
                blk.char_pos = upper.char_pos + 0.5
                page.blocks.insert(at + 1, blk)
            count += 1
    return count


def place_figures(doc, pages: List[Page], outdir: Optional[pathlib.Path] = None,
                  stem: str = "") -> int:
    """Put a Figure block at the reading position of every figure.

    This runs whether or not --images was given: a figure that leaves no
    trace reads as if the page had none, and the sentence "as Figure 2
    shows" points at nothing. With ``outdir`` the figure is also saved and
    linked; without it only the placeholder is emitted. Figure interiors are
    never recognised as text.
    """
    imgdir = outdir / f"{stem}_images" if outdir is not None else None
    count = 0
    for page in pages:
        if not page.blocks and not page.source_words:
            continue        # a page dropped as provenance
        pm = doc[page.page_idx]
        for kind, n, xref, bbox in _figure_regions(pm, page):
            path = None
            if imgdir is not None:
                try:
                    imgdir.mkdir(parents=True, exist_ok=True)
                    if kind == "img":
                        pix = pymupdf.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:
                            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                        name = f"page{page.page_idx + 1}_img{n}.png"
                        pix.save(imgdir / name)
                    else:
                        name = f"page{page.page_idx + 1}_vec{n}.png"
                        # Pad: the cluster box hugs the path bounds and clips
                        # stroke width and tick labels just outside.
                        clip = (pymupdf.Rect(bbox) + (-5, -5, 5, 5)) & pm.rect
                        pm.get_pixmap(clip=clip, dpi=200).save(imgdir / name)
                    path = f"{imgdir.name}/{name}"
                except Exception:
                    path = None
            _insert_block(page, Block(
                lines=[], bbox=bbox, page_idx=page.page_idx,
                char_pos=_insert_pos(page, bbox[1]), btype="Figure", image_path=path,
                figure_kind=kind,
            ))
            count += 1
    return count


# --------------------------------------------------------------------------- #
# vision hand-off (stand-in for surya's equation/complex-region models)
# --------------------------------------------------------------------------- #


# How far, as a share of page height, one drawing of a figure may stand from
# the next, or the first from the caption, and still be the same figure.
FIGURE_GROW_GAP = 0.04


def _locate_caption_figure(pm: pymupdf.Page, page: Page, caption) -> Optional[tuple]:
    """The region of a figure that is known from its caption only.

    A diagram of a few boxes and arrows is too sparse to be found as a
    cluster of paths, so its placeholder stands on the caption alone. For a
    crop the region is needed: starting at the caption, the drawings and
    rasters that follow one another closely on one side of it are collected,
    and the side that holds more is the figure. Page frames, rules and
    anything inside a table are left out. None when nothing is there, as on
    a scanned page, where the figure is part of the page image.
    """
    prect = pm.rect
    gap = FIGURE_GROW_GAP * prect.height
    rects = []
    try:
        drawings = pm.get_drawings()
    except Exception:
        drawings = []
    tables = [b.bbox for b in page.blocks if b.btype == "Table"]
    for d in drawings:
        r = d.get("rect")
        if not r:
            continue
        r = pymupdf.Rect(r)
        if r.width >= 0.9 * prect.width or r.height >= 0.9 * prect.height:
            continue                    # a page frame
        if r.height < 1.5 and r.width > 0.25 * prect.width:
            continue                    # a rule
        if r.width < 1.5 and r.height > 0.25 * prect.height:
            continue
        # Inside a table region only its ruling is left out: strokes made of
        # straight lines. A curve or a filled shape there is a diagram that
        # the table detector took for a grid (Peng 2009 p. 2).
        ruling = d.get("type") == "s" and all(
            it[0] in ("l", "re") for it in d.get("items", []))
        if ruling and any(_overlap_frac(tuple(r), t) > 0.4 for t in tables):
            continue
        rects.append(tuple(r))
    rects += [bbox for _n, _x, bbox in _content_images(pm)]
    if not rects:
        return None
    cx0, cy0, cx1, cy1 = caption

    def grow(below: bool):
        edge = cy1 if below else cy0
        taken, lo, hi = [], edge, edge
        pending = list(rects)
        changed = True
        while changed:
            changed = False
            for r in list(pending):
                if below and r[1] >= cy0 - 1 and r[1] - hi <= gap:
                    pass
                elif not below and r[3] <= cy1 + 1 and lo - r[3] <= gap:
                    pass
                else:
                    continue
                pending.remove(r)
                taken.append(r)
                lo, hi = min(lo, r[1]), max(hi, r[3])
                changed = True
        return taken

    best = max((grow(True), grow(False)),
               key=lambda t: sum((r[2] - r[0]) * (r[3] - r[1]) for r in t))
    if len(best) < 2 and not any(r in [b for _n, _x, b in _content_images(pm)] for r in best):
        return None
    box = _bbox_of(best)
    # the labels of the diagram: text that stands inside the region
    inside = [b.bbox for b in page.blocks
              if b.lines and _overlap_frac(b.bbox, box) > 0.5 and b.btype != "Caption"]
    box = _bbox_of([box] + inside)
    if (box[2] - box[0]) < 40 or (box[3] - box[1]) < 30:
        return None
    return box


def flag_figures(doc, pages: List[Page], outdir: pathlib.Path, stem: str, dpi=200,
                 link: bool = False) -> dict:
    """Crop every figure for a description by something that can see.

    markerlite does not read figures. It knows where they are and what their
    captions say; this writes each one as an image with a manifest beside
    it, the way flag_math does for equations. One entry per figure
    placeholder, in the order of the placeholders. With ``link`` (--images
    given as well) the Markdown links to the same crops, so that nothing is
    saved twice.
    """
    figdir = outdir / f"{stem}_figures"
    regions = []
    for page in pages:
        figs = [b for b in page.blocks if b.btype == "Figure" and not b.ignore_for_output]
        if not figs:
            continue
        pm = doc[page.page_idx]
        for n, blk in enumerate(figs, 1):
            fig_id = f"fig_p{page.page_idx + 1}_{n}"
            caption = " ".join(block_text(c, plain=True) for c in blk.children
                               if c.btype == "Caption").strip()
            bbox = blk.bbox
            if blk.figure_kind == "cap":
                bbox = _locate_caption_figure(pm, page, blk.bbox)
            entry = {
                "id": fig_id,
                "page": page.page_idx + 1,
                "bbox": [round(v, 1) for v in bbox] if bbox else None,
                "caption": caption,
                "file": "",
                "description": "",  # fill in from the crop, then run --apply-figures
            }
            if bbox:
                figdir.mkdir(parents=True, exist_ok=True)
                # Pad: a region hugs path bounds and clips stroke width and
                # the labels just outside.
                clip = (pymupdf.Rect(bbox) + (-5, -5, 5, 5)) & pm.rect
                name = f"{fig_id}.png"
                pm.get_pixmap(clip=clip, dpi=dpi).save(figdir / name)
                entry["file"] = f"{figdir.name}/{name}"
                if link:
                    blk.image_path = entry["file"]
            else:
                entry["note"] = "region not located: the figure is known from its caption only"
            regions.append(entry)
    manifest = {"stem": stem, "regions": regions}
    if regions:
        (outdir / f"{stem}_figures.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


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
        if not n:
            # An equation set as a picture has a comment where the text-layer
            # approximation would be, and perhaps a link to the saved image.
            pictured = re.compile(
                r"<!-- equation: p\. \d+; set as an image(?:; number [^>\n]*?)? -->\n\n"
                r"(?:!\[\]\([^)\n]*\)\n\n)?" + anchor)
            new, n = pictured.subn(lambda _m: f"$$\n{latex}\n$$", md, count=1)
        if n:
            md, applied = new, applied + 1
    md_path.write_text(md, encoding="utf-8")
    return applied


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# provenance pages (aggregator covers and banners)
# --------------------------------------------------------------------------- #

# Content signatures, never position: each aggregator prints fixed boilerplate.
# JSTOR and ResearchGate prepend a whole page; ProQuest prints a citation
# banner above the first page's image and a permission stamp on every page.
_JSTOR_PHRASES = ("JSTOR is a not-for-profit service", "Your use of the JSTOR archive")
_RG_PHRASES = ("See discussions, stats, and author profiles",
               "All content following this page was uploaded")
_PROQUEST_STAMP = "Reproduced with permission of the copyright owner"
_RG_FOOTER = "View publication stats"
# SAGE Journals Online: "Downloaded from <journal>.sagepub.com at <institution>
# on <date>" at the foot of every page, split across three native lines, and
# "from the SAGE Social Science Collections. All Rights Reserved." on page 1.
# EBSCOhost appends a notice page (native text, or a raster of it): "Copyright
# of <journal> is the property of <publisher> and its content may not be
# copied or emailed to multiple sites or posted to a listserv ...".
_EBSCO_PHRASE = "may not be copied or emailed to multiple sites or posted to a listserv"
_EBSCO_CITE = re.compile(r"Copyright of (.+?) is the property of (.+?) and its content", re.S)
# WRAP (Warwick Research Archive Portal) puts a cover sheet in front of the
# author's accepted manuscript.
_WRAP_PHRASES = ("warwick.ac.uk/lib-publications", "Persistent WRAP URL",
                 "Warwick Research Archive Portal")
_SAGE_HOST = re.compile(r"\b[\w.-]*sagepub\.com\b", re.I)
_SAGE_DOWNLOADED = "Downloaded from"
_SAGE_COLLECTIONS = "SAGE Social Science Collections"
_JSTOR_CITE = re.compile(r"^(Author\(s\)|Source|Published by|Stable URL)\s*:", re.I)
_RG_CITE = re.compile(r"^(Article|Chapter|Conference Paper|Preprint|Book|Thesis)\b.*\bin\b", re.I)
_PROQUEST_PG = re.compile(r"^pg\.\s*\d+", re.I)


def _lines_of(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]


def detect_provenance(doc) -> Tuple[dict, set, List[str]]:
    """Find aggregator cover pages and banners by their boilerplate.

    Returns ``(drop_pages, drop_lines, comments)``: page indices to leave out
    entirely, exact native line texts to drop wherever they occur, and one
    HTML comment per detection carrying the citation the page supplied (title,
    source line, DOI or stable URL), so the provenance survives the removal.
    """
    drop_pages: dict = {}
    drop_lines: set = {_RG_FOOTER}
    comments: List[str] = []
    for idx in range(len(doc)):
        text = doc[idx].get_text()
        lines = _lines_of(text)
        if not lines:
            continue
        flat = re.sub(r"\s+", " ", text)
        if _EBSCO_PHRASE in flat and len(flat) < 700:
            comments.append(_ebsco_comment(flat))
            drop_pages[idx] = "EBSCOhost"
            continue
        if sum(ph in flat for ph in _WRAP_PHRASES) >= 2:
            cite = [ln for ln in lines if ln.startswith("Manuscript version")]
            for i, ln in enumerate(lines):
                if ln.startswith("Persistent WRAP URL"):
                    url = ln.split(":", 1)[1].strip() or (lines[i + 1] if i + 1 < len(lines) else "")
                    cite.append("Persistent WRAP URL: " + url.strip())
            licence = re.search(r"\(CC [A-Z-]+ [\d.]+\)", flat)
            if licence:
                cite.append(licence.group(0).strip("()"))
            comments.append(f"<!-- source: WRAP (University of Warwick); {'; '.join(cite)} -->")
            drop_pages[idx] = "WRAP"
            continue
        if any(ph in text for ph in _JSTOR_PHRASES):
            # Title is the first line; the citation is the labelled lines.
            cite = [lines[0]] + [ln for ln in lines[1:] if _JSTOR_CITE.match(ln)]
            comments.append(f"<!-- source: JSTOR; {'; '.join(cite)} -->")
            drop_pages[idx] = "JSTOR"
            continue
        if any(ph in text for ph in _RG_PHRASES):
            # Title is everything between the "See discussions" line and the
            # "Article in <journal> · <date>" line; then the DOI line.
            start = next((i for i, ln in enumerate(lines) if _RG_PHRASES[0] in ln), -1)
            art = next((i for i, ln in enumerate(lines) if _RG_CITE.match(ln)), None)
            title = " ".join(lines[start + 1:art]) if art is not None else ""
            cite = [t for t in (title, lines[art] if art is not None else "") if t]
            cite += [ln for ln in lines if ln.upper().startswith("DOI")]
            comments.append(f"<!-- source: ResearchGate; {'; '.join(cite)} -->")
            drop_pages[idx] = "ResearchGate"
            continue
        if _SAGE_HOST.search(text) and (_SAGE_DOWNLOADED in text or _SAGE_COLLECTIONS in text):
            # The stamp is one visual line in three native pieces ("Downloaded
            # from ", "oss.sagepub.com", " at SAGE Publications on ..."); drop
            # each piece, and record the host and download line once.
            pieces = [ln for ln in lines
                      if _SAGE_HOST.search(ln) or ln.startswith(_SAGE_DOWNLOADED)
                      or ln.startswith("at ") or _SAGE_COLLECTIONS in ln]
            drop_lines.update(pieces)
            if not any(c.startswith("<!-- source: SAGE") for c in comments):
                host = _SAGE_HOST.search(text).group(0)
                # "at <institution> on <date>" follows the host, either in
                # the same line or in the next native piece.
                # The native pieces may arrive in any order (SAGE emits
                # them right-to-left), so look for the "at ..." piece first
                # and only then for "at ..." after the host in a merged line.
                at_piece = next((ln for ln in pieces if ln.lower().startswith("at ")), None)
                if at_piece is None:
                    stamp = " ".join(ln for ln in pieces if _SAGE_COLLECTIONS not in ln)
                    tail = stamp.split(host, 1)[1] if host in stamp else ""
                    m_at = re.search(r"\bat\s+(.+)", tail)
                    at_piece = ("at " + m_at.group(1).strip()) if m_at else ""
                at = at_piece
                comments.append(f"<!-- source: SAGE Journals ({host}); downloaded {at} -->".replace(" ;", ";").replace("  ", " "))
            continue
        if _PROQUEST_STAMP in text:
            stamp = next(ln for ln in lines if _PROQUEST_STAMP in ln)
            drop_lines.add(stamp)
            pg = next((ln for ln in lines if _PROQUEST_PG.match(ln)), None)
            if pg is not None and ("ABI/INFORM" in text or "ProQuest" in text or idx == 0):
                # The banner: every native line up to and including "pg. N"
                # (title, author, journal; date; volume; database).
                banner = []
                for ln in lines:
                    if ln == stamp:
                        continue
                    banner.append(ln)
                    if _PROQUEST_PG.match(ln):
                        break
                drop_lines.update(banner)
                comments.append(f"<!-- source: ProQuest; {'; '.join(banner)} -->")
    return drop_pages, drop_lines, comments


def _ebsco_comment(flat: str) -> str:
    m = _EBSCO_CITE.search(flat)
    if m:
        return (f"<!-- source: EBSCOhost; Copyright of {m.group(1).strip()} is the property of "
                f"{m.group(2).strip()} -->")
    return "<!-- source: EBSCOhost -->"


def _drop_ocr_notice(page: Page, provenance: List[str]) -> None:
    """An aggregator notice page delivered as a raster is only recognisable
    after OCR. When a recognised page is nothing but the EBSCO notice, hide
    it and record the source, as detect_provenance does for the native form."""
    if not page.ocr_used:
        return
    flat = re.sub(r"\s+", " ", " ".join(b.text for b in page.blocks))
    squeezed = re.sub(r"[^a-z]", "", flat.lower())
    key = re.sub(r"[^a-z]", "", _EBSCO_PHRASE.lower())
    if key in squeezed and len(flat) < 700:
        for blk in page.blocks:
            blk.ignore_for_output = True
        page.raster_covered = False     # nothing to yield: not a low-yield page
        page.source_words = 0           # dropped on purpose: not a lossy page
        comment = _ebsco_comment(flat)
        if not any(c.startswith("<!-- source: EBSCOhost") for c in provenance):
            provenance.append(comment)


def _drop_provenance_lines(page: Page, drop_lines: set) -> None:
    """Hide blocks made only of provenance lines. A stamp that is several
    native pieces ("Downloaded from ", "oss.sagepub.com", " at ...") is one
    OCR line, so a line also matches when it is the pieces run together."""
    def norm(t):
        return re.sub(r"\s+", " ", t).strip()
    def is_prov(t):
        t = norm(t)
        if t in drop_lines:
            return True
        # every word of the line belongs to some provenance piece
        pieces = " ".join(drop_lines)
        return bool(t) and all(w in pieces for w in t.split())
    for blk in page.blocks:
        if blk.lines and all(is_prov(ln.text) for ln in blk.lines):
            blk.ignore_for_output = True


def convert(path: pathlib.Path, outdir: pathlib.Path, images=False,
            do_flag_math=False, page_markers=False,
            do_flag_figures=False) -> Tuple[pathlib.Path, dict]:
    """Convert one PDF. Returns (markdown path, info).

    ``info`` carries ``regions`` (equation crops, when --flag-math ran) and
    ``stats`` (pages, bytes, figures, equations) for reporting.
    """
    doc = pymupdf.open(path)
    drop_pages, drop_lines, provenance = detect_provenance(doc)
    pages = []
    for i in range(len(doc)):
        if i in drop_pages:
            # An aggregator cover: nothing on it is the article. Keep an
            # empty page so page numbers in markers stay true to the PDF.
            pages.append(Page(page_idx=i, width=doc[i].rect.width,
                              height=doc[i].rect.height, blocks=[]))
            continue
        p = extract_page(doc[i], i)   # may turn a sideways page upright, in memory
        # On an OCR'd page the native layer is gone, but Tesseract reads the
        # stamp off the rendered page, so the same texts are dropped there.
        _drop_provenance_lines(p, drop_lines)
        _drop_ocr_notice(p, provenance)
        pages.append(p)
    # Glyph repair needs the whole document's font inventory and must happen
    # before tables are built from the characters, so tables come second.
    pi_spans = _remap_pi_fonts(pages)
    for p in pages:
        if p.blocks:
            detect_tables(doc[p.page_idx], p)

    body = body_font_size(pages)
    classify(pages, body)
    propose_tables_from_text(pages)

    proc_line_numbers(pages)
    proc_reflow(pages)
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
    # With --flag-figures the crops are the saved figures: --images then
    # links to them instead of saving every figure a second time.
    save_here = outdir if (images and not do_flag_figures) else None
    n_figures = place_figures(doc, pages, save_here, path.stem)
    _promote_figure_captions(pages)
    proc_captions(pages)
    n_figures += _figures_from_captions(pages)
    n_figures -= _route_raster_equations(pages)

    manifest = {}
    if do_flag_math:
        manifest = flag_math(doc, pages, outdir, path.stem)
    if do_flag_figures:
        manifest["figures"] = flag_figures(doc, pages, outdir, path.stem,
                                           link=images)["regions"]

    md = render(pages, page_markers=page_markers)
    if provenance:
        md = "\n".join(provenance) + "\n\n" + md
    out = outdir / f"{path.stem}.md"
    out.write_text(md, encoding="utf-8")
    low_yield = []
    lossy = []
    for p in pages:
        emitted = _emitted_words(p)
        if p.raster_covered and emitted < LOW_YIELD_WORDS:
            low_yield.append(p.page_idx + 1)
        if (p.source_words >= CONSERVATION_MIN_SOURCE
                and emitted < CONSERVATION_MIN * p.source_words):
            lossy.append({"page": p.page_idx + 1, "source": p.source_words,
                          "emitted": emitted})
    manifest["stats"] = {
        "pages": len(pages),
        "bytes": len(md.encode("utf-8")),
        "words": content_words(md),
        "low_yield_pages": low_yield,
        "lossy_pages": lossy,
        "garbled_pages": [p.page_idx + 1 for p in pages if p.garbled],
        "garbled_ocr": sum(1 for p in pages if p.garbled and p.ocr_used),
        "rotated_pages": [p.page_idx + 1 for p in pages if p.derotated],
        "pi_glyphs_repaired": pi_spans,
        "figures": n_figures,
        "figure_crops": sum(1 for f in manifest.get("figures", []) if f.get("file")),
        "figures_saved": sum(1 for p in pages for b in p.blocks
                             if b.btype == "Figure" and b.image_path),
        "equations": len(manifest.get("regions", [])),
        "ocr_pages": sum(1 for p in pages if p.ocr_used),
        "image_only_pages": sum(1 for p in pages if p.image_only),
        "provenance": [c.split(";")[0].replace("<!-- source: ", "") for c in provenance],
        "tables": sum(p.tables_emitted for p in pages),
        "tables_fallback": sum(p.tables_fell_back for p in pages),
        "table_captions_isolated": sum(p.table_captions_isolated for p in pages),
        "table_caption_words": sum(p.table_caption_words for p in pages),
        "table_lines_excluded": sum(p.table_lines_excluded for p in pages),
        "proposals": sum(p.proposals_emitted for p in pages),
        "proposals_kept_prose": sum(p.proposals_kept_prose for p in pages),
    }
    doc.close()
    return out, manifest


def summarize(stats: dict) -> str:
    """'17 pages -> 76 KB Markdown · 3 figures · 2 equation crops'."""
    kb = stats.get("bytes", 0) / 1024
    size = f"{kb:.0f} KB" if kb >= 1 else f"{stats.get('bytes', 0)} B"
    # ASCII arrow: the summary is printed to whatever console the user has,
    # and a cp1252 console cannot encode U+2192.
    parts = [f"{stats.get('pages', 0)} pages -> {size} Markdown"]
    if stats.get("figures"):
        n = stats["figures"]
        saved = stats.get("figures_saved", 0)
        note = "" if saved == n else (f" ({saved} saved)" if saved else " (placeholders)")
        parts.append(f"{n} figure{'s' * (n != 1)}{note}")
    if stats.get("equations"):
        n = stats["equations"]
        parts.append(f"{n} equation crop{'s' * (n != 1)}")
    if stats.get("ocr_pages"):
        parts.append(f"{stats['ocr_pages']} OCR'd")
    # Warnings (image-only pages with no OCR, low-yield pages, table
    # fallbacks, provenance) come from stat_warnings so the CLI, the GUI
    # and the run log say the same thing. Silence here was the bug.
    parts.extend(stat_warnings(stats))
    return " · ".join(parts)


def main() -> None:
    # Never let console encoding take the batch down: on a Windows cp1252
    # console a single non-encodable character in a filename or summary
    # raised UnicodeEncodeError after the first file and stopped the run.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, AttributeError):  # pragma: no cover
                pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("-o", "--outdir", default="md_out")
    ap.add_argument("--images", action="store_true",
                    help="extract figures (embedded rasters and vector drawings)")
    ap.add_argument("--flag-math", action="store_true",
                    help="crop equation regions for visual transcription")
    ap.add_argument("--flag-figures", action="store_true",
                    help="crop every figure to <stem>_figures/ with a manifest, "
                         "for description by a vision model")
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
                                args.page_markers, args.flag_figures)
        print(f"{path.name} -> {out}")
        print(f"   {summarize(manifest.get('stats', {}))}")


if __name__ == "__main__":
    main()
