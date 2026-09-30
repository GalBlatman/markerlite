"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from statistics import median
from typing import List, Optional, Tuple

import regex
from sklearn.exceptions import ConvergenceWarning

from .thresholds import *

warnings.filterwarnings("ignore", category=ConvergenceWarning)

LIST_ITEM_START = re.compile(
    r"^\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f-]|"
    r"\(?\d{1,3}[.)]|\(?[a-zA-Z][.)]|\(?[ivxlcIVXLC]{1,5}[.)])\s"
)

BULLET_START = re.compile(r"^\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f])\s")

BULLET_IN_EMPHASIS = re.compile(
    r"^(\s*(?:\*{1,3}|_{1,2}))\s*(?:[•●○ഠ ം◦■▪▫–—-]|[\x80-\x9f])\s+"
)

HYPHEN_END = regex.compile(r".*[\p{Ll}|\d][-—¬]\s?$", regex.DOTALL)

CAPTION_START = re.compile(
    r"^\s*(figure|fig\.?|table|tbl\.?|chart|exhibit|scheme|plate|appendix)\s*"
    r"[\dIVXA-Z]+\s*[.:)—-]",
    re.IGNORECASE,
)

NUMBERED_HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*|[IVXLC]+\.|[A-Z]\.)\s+\S")

BIB_HINT = re.compile(r"^\s*(references|bibliography|works cited)\s*$", re.IGNORECASE)

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

_COMMON_WORDS = frozenset(
    """
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
""".split()
)

_WORD_TOKEN = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*")

PI_FONT_MAP = {"2": "−", ",": "<"}

TABLE_LABEL = re.compile(r"^\s*(table|tbl\.?)\s*(\d{1,3}|[IVX]{1,4})[a-z]?\b", re.I)

TABLE_NOTE = re.compile(
    r"^\s*(notes?|sources?)\s*[.:]|^\s*[*\u2020\u2021]+\s*p\s*[<=\u2264]", re.I
)

TOC_LINE = re.compile(r"^(.*\S)[\s.·•…_]{2,}(\d{1,4})$|^(.*\S)\s+(\d{1,4})$")

FOOTNOTE_MARKER = re.compile(
    r"^\s*(\[(\d{1,3})\]|\((\d{1,3})\)|(\d{1,3})[.)]?(?=\s)|(\d{1,3})(?=[A-Z])|"
    r"([*\u2020\u2021\u00a7\u00b6]{1,3}))\s*"
)

SIGNIFICANCE_LEGEND = re.compile(r"^\s*[*†‡+]{1,3}\s*p\s*[<≤,]\s*0?\.\d", re.I)

SIGNIFICANCE_LEGEND_BARE = re.compile(
    r"^\s*[*\u2020\u2021+]{1,3}\s*p[\s\x00-\x1f]{1,4}0?\.\d", re.I
)

SYMBOL_LED = re.compile(r"^\s*([*\u2020\u2021\u00a7\u00b6]{1,3})")

REF_LIST_HEAD = re.compile(
    r"^\s*(references|bibliography|works cited|literature cited)\s*[a-z*\u2020\u2021]?\s*$",
    re.I,
)

REF_ENTRY_SHAPE = re.compile(
    r"^\s*[*\u2020\u2021\u00a7\u00b6]{0,3}\s*[A-Z][\w\u00a8\u2019' .\-]{1,40},\s+(?:[A-Z]\.\s*){1,4}"
)

MARK_LEGEND = re.compile(
    r"\b(marked|denoted|indicated|preceded|identified)\b.{0,40}\b(asterisks?|daggers?|stars?)\b"
    r"|\b(asterisks?|daggers?)\b.{0,60}\b(indicates?|denotes?|marks?|(?:were|are) included)\b",
    re.I | re.S,
)

TEXTISH = ("Text", "SectionHeader", "ListItem", "Caption", "Equation")

PAGE_NUMBER_ONLY = re.compile(
    r"^[\s\-\u2013\u2014|]*(?:\d{1,4}|[ivxlcdmIVXLCDM]{1,7})[\s\-\u2013\u2014|]*$"
)

_FN_LABELS: set = set()

LIST_LOOKALIKE = re.compile(r"^(\s*)(?:([*+-])|(\d{1,9})([.)]))(?=\s)")

FIGURE_CAPTION = re.compile(r"^\s*(figure|fig\.?)\s*[\dIVXA-Z]+", re.I)

FIGURE_LABEL = re.compile(
    r"^\s*(figure|fig\.?)\s*([A-Z]?\d{1,3}|[IVX]{1,4})[a-z]?\b\s*(.*)$", re.I | re.S
)

EQ_LEADIN = re.compile(
    r"\b(formula|equation|expression)s?\s+(below|that\s+follows)\b"
    r"|\b(following|below)\s+(formula|equation|expression)s?\b",
    re.I,
)

EQ_WHERE = re.compile(r"^\s*where\b", re.I)

EQ_DEFINITION = re.compile(r"^\s*[A-Za-z][\w\u0080-\uffff]{0,12}\s*=\s+\S")

EQ_NUMBER_ALONE = re.compile(r"^\s*\(\d{1,3}[a-z]?\)\s*$")

FIGURE_DESCRIPTION_MARK = "<!-- figure description: model-transcribed -->"

_FIGURE_DESCRIPTION_BLOCK = re.compile(
    r"\n\n> " + re.escape(FIGURE_DESCRIPTION_MARK) + r"(?:\n>[^\n]*)*"
)

_JSTOR_PHRASES = ("JSTOR is a not-for-profit service", "Your use of the JSTOR archive")

_RG_PHRASES = (
    "See discussions, stats, and author profiles",
    "All content following this page was uploaded",
)

_PROQUEST_STAMP = "Reproduced with permission of the copyright owner"

_RG_FOOTER = "View publication stats"

_EBSCO_PHRASE = "may not be copied or emailed to multiple sites or posted to a listserv"

_EBSCO_CITE = re.compile(
    r"Copyright of (.+?) is the property of (.+?) and its content", re.S
)

_WRAP_PHRASES = (
    "warwick.ac.uk/lib-publications",
    "Persistent WRAP URL",
    "Warwick Research Archive Portal",
)

_SAGE_HOST = re.compile(r"\b[\w.-]*sagepub\.com\b", re.I)

_SAGE_DOWNLOADED = "Downloaded from"

_SAGE_COLLECTIONS = "SAGE Social Science Collections"

_JSTOR_CITE = re.compile(r"^(Author\(s\)|Source|Published by|Stable URL)\s*:", re.I)

_RG_CITE = re.compile(
    r"^(Article|Chapter|Conference Paper|Preprint|Book|Thesis)\b.*\bin\b", re.I
)

_PROQUEST_PG = re.compile(r"^pg\.\s*\d+", re.I)


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
    # Keep the table identity for processors/captions and statistics, but
    # render failed reconstruction from the untouched source, not a bad grid.
    fallback_paragraphs: List[str] = field(default_factory=list)
    # A rejected journal candidate leaves these original blocks available
    # for classification, but must not propose them as tables again.
    journal_front_matter: bool = False
    journal_title: bool = False
    figure_text: List[str] = field(default_factory=list)
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
    # Text printed inside a wide dark fill. Its PDF stream position can be
    # late; api.place_fill_backed_banners moves it only after all processors.
    fill_backed_banner: bool = False
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
    suppressed: List[dict] = field(default_factory=list)
    section_heads_emitted: List[dict] = field(default_factory=list)
    table_zones: List[tuple] = field(default_factory=list)
    figure_zones: List[tuple] = field(default_factory=list)
    figure_cores: List[tuple] = field(default_factory=list)
    ocr_used: bool = False
    # table_recon vs. geometric-cell decisions on this page (see
    # TABLE_FALLBACK_MIN_KEEP): how many tables were emitted, and how many of
    # them keep source prose because reconstruction failed or lost words.
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


# Phase 3 keeps constants byte-for-byte while their eventual ownership is
# deferred to the approved thresholds phase. Split modules need the private
# patterns as well as the public model types.
__all__ = [name for name in globals() if not name.startswith("__")]
