"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import re
from html import unescape
from typing import List, TypedDict

from .model import *
from .tables import _html_word_count


class SuppressionRecord(TypedDict):
    """Stable serialized record for one source line removed as furniture."""

    page: int
    bbox: list[float]
    text: str
    reason: str


class FragmentPage(TypedDict):
    page: int
    letter_tokens: int
    short_share: float


class LossyPage(TypedDict):
    page: int
    source: int
    emitted: int


class ConversionStats(TypedDict):
    """The public ``info['stats']`` dictionary returned by :func:`convert`."""

    suppressed: list[SuppressionRecord]
    pages: int
    bytes: int
    words: int
    low_yield_pages: list[int]
    lossy_pages: list[LossyPage]
    garbled_pages: list[int]
    garbled_ocr: int
    rotated_pages: list[int]
    pi_glyphs_repaired: int
    figures: int
    figure_crops: int
    figures_saved: int
    equations: int
    ocr_pages: int
    image_only_pages: int
    provenance: list[str]
    tables: int
    tables_fallback: int
    table_captions_isolated: int
    table_caption_words: int
    table_lines_excluded: int
    proposals: int
    proposals_kept_prose: int
    section_heads_emitted: list[dict]
    resource_limits: list[dict]
    table_candidates_released: int
    fragment_pages: list[FragmentPage]


SUPPRESSION_REASONS = frozenset(
    {
        "provenance",
        "tilt_filter",
        "proc_line_numbers",
        "proc_ignore_common",
        "proc_marginalia",
    }
)


def _emitted_words(page: Page) -> int:
    """Words this page contributes to the Markdown: the text of every block
    that is rendered, and for a table the words of the HTML it renders from
    (its grid may hold fewer words than the blocks it consumed)."""
    total = 0
    for blk in page.blocks:
        if blk.ignore_for_output or blk.btype in (
            "PageHeader",
            "PageFooter",
            "ImageMarker",
        ):
            continue
        if blk.btype == "Table" and not blk.fallback_paragraphs:
            total += _html_word_count(blk.html or "")
        else:
            total += len(blk.text.split())
        total += sum(len(text.split()) for text in blk.figure_text)
        for child in blk.children:
            total += len(child.text.split())
    return total


_LETTER_RUN = re.compile(r"[^\W\d_]+")


def _fragment_share(page: Page) -> tuple[int, float]:
    """(letter tokens, share of them at most FRAGMENT_MAX_LETTERS long) in
    the text this page emits. Figure text is a comment and not counted; a
    table counts the cell text of the HTML it renders from."""
    runs: List[str] = []
    for blk in page.blocks:
        if blk.ignore_for_output or blk.btype in (
            "PageHeader",
            "PageFooter",
            "ImageMarker",
        ):
            continue
        if blk.btype == "Table" and not blk.fallback_paragraphs:
            text = unescape(re.sub(r"<[^<>]*>", " ", blk.html or ""))
        else:
            text = blk.text
        runs.extend(_LETTER_RUN.findall(text))
        for child in blk.children:
            runs.extend(_LETTER_RUN.findall(child.text))
    if not runs:
        return 0, 0.0
    short = sum(1 for run in runs if len(run) <= FRAGMENT_MAX_LETTERS)
    return len(runs), short / len(runs)


def content_words(md: str) -> int:
    """The project's one word metric ("content words"): whitespace tokens of
    the Markdown after removing HTML comments, table separator rows, HTML
    tags, heading hashes, pipes, emphasis stars and $$ fences, NFKC-normalised.
    tests/audit_table_recovery.py and the GUI both use this."""
    import unicodedata

    # A description spliced in by --apply-figures is not the document's
    # text: the whole block quote goes, before its opening comment does.
    text = _FIGURE_DESCRIPTION_BLOCK.sub(" ", md)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
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


def build_stats(
    pages: List[Page],
    md: str,
    manifest: dict,
    provenance: list[str],
    pi_spans: int,
    n_figures: int,
) -> ConversionStats:
    """Build the exact v0.1.14 public stats shape in one typed location."""
    low_yield = []
    lossy = []
    fragments = []
    for page in pages:
        letters, share = _fragment_share(page)
        if letters >= FRAGMENT_MIN_LETTER_TOKENS and share >= FRAGMENT_SHORT_SHARE:
            fragments.append(
                {
                    "page": page.page_idx + 1,
                    "letter_tokens": letters,
                    "short_share": round(share, 3),
                }
            )
        emitted = _emitted_words(page)
        if page.raster_covered and emitted < LOW_YIELD_WORDS:
            low_yield.append(page.page_idx + 1)
        if (
            page.source_words >= CONSERVATION_MIN_SOURCE
            and emitted < CONSERVATION_MIN * page.source_words
        ):
            lossy.append(
                {
                    "page": page.page_idx + 1,
                    "source": page.source_words,
                    "emitted": emitted,
                }
            )
    stats: ConversionStats = {
        "suppressed": [record for page in pages for record in page.suppressed],
        "pages": len(pages),
        "bytes": len(md.encode("utf-8")),
        "words": content_words(md),
        "low_yield_pages": low_yield,
        "lossy_pages": lossy,
        "garbled_pages": [page.page_idx + 1 for page in pages if page.garbled],
        "garbled_ocr": sum(1 for page in pages if page.garbled and page.ocr_used),
        "rotated_pages": [page.page_idx + 1 for page in pages if page.derotated],
        "pi_glyphs_repaired": pi_spans,
        "figures": n_figures,
        "figure_crops": sum(1 for f in manifest.get("figures", []) if f.get("file")),
        "figures_saved": sum(
            1
            for page in pages
            for block in page.blocks
            if block.btype == "Figure" and block.image_path
        ),
        "equations": len(manifest.get("regions", [])),
        "ocr_pages": sum(1 for page in pages if page.ocr_used),
        "image_only_pages": sum(1 for page in pages if page.image_only),
        "provenance": [
            comment.split(";")[0].replace("<!-- source: ", "") for comment in provenance
        ],
        "tables": sum(page.tables_emitted for page in pages),
        "tables_fallback": sum(page.tables_fell_back for page in pages),
        "table_captions_isolated": sum(page.table_captions_isolated for page in pages),
        "table_caption_words": sum(page.table_caption_words for page in pages),
        "table_lines_excluded": sum(page.table_lines_excluded for page in pages),
        "proposals": sum(page.proposals_emitted for page in pages),
        "proposals_kept_prose": sum(page.proposals_kept_prose for page in pages),
    }
    section_heads = [record for page in pages for record in page.section_heads_emitted]
    if section_heads:
        stats["section_heads_emitted"] = section_heads
    # Present only when a limit tripped, so ordinary output is unchanged.
    released = sum(page.table_candidates_released for page in pages)
    if released:
        stats["table_candidates_released"] = released
    limits = [record for page in pages for record in page.limit_events]
    if limits:
        stats["resource_limits"] = limits
    # Flag only: the text stays as emitted. Present only when a page trips.
    if fragments:
        stats["fragment_pages"] = fragments
    return stats


def stat_warnings(stats: ConversionStats) -> List[str]:
    """Human-readable warnings derived from convert()'s stats, shared by
    summarize(), the GUI's file list and the run log."""
    out: List[str] = []
    if stats.get("image_only_pages") and not stats.get("ocr_pages"):
        n = stats["image_only_pages"]
        out.append(
            f"{n} image-only page{'s' * (n != 1)}, 0 OCR'd \u2014 check Tesseract"
        )
    low = stats.get("low_yield_pages") or []
    if low:
        shown = ", ".join(str(n) for n in low[:8]) + (
            ", \u2026" if len(low) > 8 else ""
        )
        out.append(f"{len(low)} low-yield page{'s' * (len(low) != 1)} ({shown})")
    garbled = stats.get("garbled_pages") or []
    if garbled:
        shown = ", ".join(str(n) for n in garbled[:8]) + (
            ", \u2026" if len(garbled) > 8 else ""
        )
        fate = (
            "OCR'd instead"
            if stats.get("garbled_ocr") == len(garbled)
            else "OCR unavailable \u2014 check Tesseract"
        )
        out.append(
            f"{len(garbled)} garbled page{'s' * (len(garbled) != 1)} ({shown}): "
            f"text layer unreadable, {fate}"
        )
    lossy = stats.get("lossy_pages") or []
    if lossy:
        shown = ", ".join(
            f"p{d['page']} {d['emitted']}/{d['source']}" for d in lossy[:6]
        )
        shown += ", \u2026" if len(lossy) > 6 else ""
        out.append(f"{len(lossy)} lossy page{'s' * (len(lossy) != 1)} ({shown})")
    fragments = stats.get("fragment_pages") or []
    if fragments:
        shown = ", ".join(f"p{d['page']}" for d in fragments[:8])
        shown += ", \u2026" if len(fragments) > 8 else ""
        out.append(
            f"{len(fragments)} page{'s' * (len(fragments) != 1)} emit text as "
            f"fragments ({shown}): mostly one- or two-letter pieces, check the source"
        )
    if stats.get("tables_fallback"):
        n = stats["tables_fallback"]
        out.append(
            f"{n} of {stats.get('tables', n)} table{'s' * (n != 1)} kept as prose"
        )
    if stats.get("proposals_kept_prose"):
        n = stats["proposals_kept_prose"]
        out.append(f"{n} text-table proposal{'s' * (n != 1)} kept as prose")
    if stats.get("provenance"):
        out.append("provenance page dropped: " + ", ".join(stats["provenance"]))
    limits = stats.get("resource_limits") or []
    if limits:
        shown = ", ".join(f"{d['limit']} p{d['page']}" for d in limits[:6])
        shown += ", \u2026" if len(limits) > 6 else ""
        out.append(
            f"{len(limits)} resource limit{'s' * (len(limits) != 1)} reached "
            f"({shown}); content kept, see stats"
        )
    return out


def summarize(stats: ConversionStats) -> str:
    """'17 pages -> 76 KB Markdown · 3 figures · 2 equation crops'."""
    kb = stats.get("bytes", 0) / 1024
    size = f"{kb:.0f} KB" if kb >= 1 else f"{stats.get('bytes', 0)} B"
    # ASCII arrow: the summary is printed to whatever console the user has,
    # and a cp1252 console cannot encode U+2192.
    parts = [f"{stats.get('pages', 0)} pages -> {size} Markdown"]
    if stats.get("figures"):
        n = stats["figures"]
        saved = stats.get("figures_saved", 0)
        note = (
            "" if saved == n else (f" ({saved} saved)" if saved else " (placeholders)")
        )
        parts.append(f"{n} figure{'s' * (n != 1)}{note}")
    if stats.get("equations"):
        n = stats["equations"]
        parts.append(f"{n} equation crop{'s' * (n != 1)}")
    if stats.get("ocr_pages"):
        parts.append(f"{stats['ocr_pages']} OCR'd")
    # Warnings (image-only pages with no OCR, low-yield pages, table
    # fallbacks, provenance) come from stat_warnings so the CLI, the GUI
    # and the run log say the same thing. Silence here was the bug.
    parts.append(f"{len(stats.get('suppressed', []))} source lines suppressed")
    parts.extend(stat_warnings(stats))
    return " · ".join(parts)
