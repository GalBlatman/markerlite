"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import re
from dataclasses import replace
from html import escape, unescape
from html.parser import HTMLParser
from itertools import groupby
from typing import List, Optional, Tuple

from .classification import footnote_label
from .model import *


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

    out = [
        "| " + " | ".join(pad(header)) + " |",
        "|" + "|".join([" --- "] * width) + "|",
    ]
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
        parts.append(
            text[:lead] + core + text[len(text) - trail :]
            if trail
            else text[:lead] + core
        )
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
            out.append(
                replace(
                    sp, text=sp.text[n:], chars=list(sp.chars[n:]) if sp.chars else []
                )
            )
            n = 0
    return out


def _footnote_groups(
    blk: Block, fn_labels=frozenset()
) -> List[Tuple[Optional[str], str]]:
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
        if (
            label is not None
            and label.isdigit()
            and groups
            and prev_num is not None
            and int(label) <= prev_num
        ):
            label = None
        if label is not None or not groups:
            spans = (
                _strip_source_label(ln.spans, raw)
                if label is not None
                else list(ln.spans)
            )
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
                if _digit_break(tail, spans[0].text):
                    merged[-1] = replace(last, text=last.text.rstrip())
                    spans = [replace(spans[0], text=spans[0].text.lstrip())] + list(
                        spans[1:]
                    )
                elif HYPHEN_END.match(tail):
                    merged[-1] = replace(
                        last, text=re.sub(r"[-\u2014\u00ac]\s*$", "", last.text)
                    )
                    spans = [replace(spans[0], text=spans[0].text.lstrip())] + list(
                        spans[1:]
                    )
                elif not last.text.endswith((" ", "\t")):
                    merged[-1] = replace(last, text=last.text + " ")
            merged.extend(spans)
        body = re.sub(r"[ \t]+", " ", _inline(merged, fn_labels)).strip()
        out.append((label, body))
    return out


def _digit_break(prev: str, nxt: str) -> bool:
    """A line ending in a digit and a dash, followed by one opening with a
    digit (model.DIGIT_BREAK)."""
    return (
        bool(DIGIT_BREAK.search(prev.rstrip()))
        and nxt.lstrip().lstrip("*_")[:1].isdigit()
    )


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
        if _digit_break(prev, seg):
            pieces[-1] = prev.rstrip()
            pieces.append(seg.lstrip())
            pieces[-2:] = ["".join(pieces[-2:])]
        elif HYPHEN_END.match(prev):
            pieces[-1] = re.sub(r"[-—¬]\s*$", "", prev)
            pieces.append(seg.lstrip())
            pieces[-2:] = ["".join(pieces[-2:])]
        else:
            pieces.append(" " + seg.lstrip())
    return re.sub(r"[ \t]+", " ", "".join(pieces)).strip()


def _escape_list_start(text: str) -> str:
    """Escape the marker of a paragraph that is not a list item."""
    m = LIST_LOOKALIKE.match(text)
    if not m:
        return text
    if m.group(2):
        return m.group(1) + "\\" + text[m.end(1) :]
    return m.group(1) + m.group(3) + "\\" + text[m.end(3) :]


def _is_list_line(chunk: str) -> bool:
    last = chunk.rsplit("\n", 1)[-1].lstrip()
    return bool(re.match(r"^(-|\d{1,3}\.)\s", last))


def fallback_prose(blk: Block) -> List[str]:
    """Source paragraphs, with soft line breaks and no grid or token repairs."""
    return [
        "\n".join(
            _escape_list_start(escape(line, quote=False).replace("|", "&#124;"))
            for line in paragraph.splitlines()
        )
        for paragraph in blk.fallback_paragraphs
    ]


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
            if not blk.lines and t not in (
                "Figure",
                "Equation",
                "Table",
                "ImageMarker",
            ):
                continue

            if t == "Text":
                txt = block_text(blk)
                if not txt:
                    continue
                if pending_paragraph:
                    joined = pending_paragraph.rstrip()
                    if _digit_break(joined, txt):
                        pending_paragraph = joined + txt.lstrip()
                    elif HYPHEN_END.match(joined):
                        pending_paragraph = re.sub(r"[-—¬]\s*$", "", joined) + txt
                    else:
                        pending_paragraph = joined + " " + txt
                else:
                    pending_paragraph = txt
                if blk.blockquote:
                    pending_paragraph = (
                        "> " * max(blk.blockquote_level, 1)
                    ) + pending_paragraph
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
                    txt = txt[m.end() :]
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
                if blk.fallback_paragraphs:
                    out.append(
                        f"<!-- table p. {page.page_idx + 1}: "
                        "reconstruction failed; text kept as prose -->"
                    )
                    out.extend(fallback_prose(blk))
                else:
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
                    out.append(
                        f"<!-- equation: p. {blk.page_idx + 1}; "
                        f"set as an image{number} -->"
                    )
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
                out.append(
                    f"<!-- figure: p. {blk.page_idx + 1}; caption: {caption} -->"
                )
                for source_line in blk.figure_text:
                    safe = source_line.replace("--", "&#45;&#45;").replace("\n", " ")
                    out.append(f"<!-- figure text: {safe} -->")
                if blk.image_path:
                    out.append(f"![]({blk.image_path})")
                for cap in blk.children:
                    out.append("*" + block_text(cap, plain=True) + "*")
    flush()

    text = "\n\n".join(x for x in out if x is not None and x.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
