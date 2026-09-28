"""Regenerate the fpdf2 regression fixtures under tests/fixtures/.

Each fixture exists to reproduce one bug that markerlite has fixed; the
docstring of each ``make_*`` function names it. The PDFs are committed, so
this script only needs to run when a fixture is deliberately changed - after
which ``python tests/regress.py --update`` must be run and the expected
outputs reviewed by hand.

    pip install fpdf2 pymupdf
    python tests/generators/make_fixtures.py            # all fixtures
    python tests/generators/make_fixtures.py hard repro  # a subset

paper.pdf is the one fixture not made here: it is real pdflatex output, see
paper.tex and make_paper.sh in this directory.

Everything is deterministic (fixed creation date, no randomness) so a rerun
reproduces the committed bytes.
"""
from __future__ import annotations

import datetime as dt
import io
import pathlib
import sys

import pymupdf
from fpdf import FPDF

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE.parent / "fixtures"
FIXED_DATE = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)

LETTER_W, LETTER_H = 612.0, 792.0


# --------------------------------------------------------------------------- #
# text bank - distinct paragraphs so proc_ignore_common has nothing to cull
# --------------------------------------------------------------------------- #

SENTENCES = [
    "Reading order is the first thing a converter gets wrong and the last thing a reader forgives.",
    "The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read.",
    "Geometric sorting of blocks discards that signal and replaces it with a guess about columns.",
    "On two-column pages the guess fails at every figure, every table, and every footnote.",
    "We therefore treat stream order as authoritative and only intervene where a page has no text layer at all.",
    "Running heads are the second source of noise, because they repeat on every page and sit exactly where a heading would.",
    "Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates.",
    "Repetition can, since a header recurs across pages while a title appears once.",
    "The benchmark documents in this study were built to exercise those two decisions and nothing else.",
    "Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter.",
    "Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line.",
    "A converter that joins lines with a space will emit a broken word at every such break.",
    "Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback.",
    "Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column.",
    "Their labels are superscript digits, and matching digits appear in the body at the point of reference.",
    "The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use.",
    "The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion.",
    "The text-layer path handles digital publications; a raster copy of the same file drives the recognition path.",
    "Both paths converge on the same block structure before any processor runs.",
    "Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project.",
    "Line heights are clustered to recover heading levels when a document has no section numbers.",
    "When numbers are present they win, because a numbered heading states its own depth.",
    "Captions are recognised by their leading label and attached to the nearest figure or table above them.",
    "Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time.",
    "The remaining processors are direct ports and are documented against the source files they come from.",
    "Every threshold in the code was set by looking at a failure, not by tuning against a corpus.",
    "That makes the thresholds easy to defend and easy to revise when a new failure appears.",
    "We report where the approach breaks so that a reader can decide whether it fits their documents.",
    "Multi-line table cells remain the weakest point and are listed as partial support.",
    "Journals that style every heading identically defeat the height clustering and lose a level.",
    "Scanned pages inherit every error of the recogniser, including stray page numbers in the middle of a paragraph.",
    "None of these failures corrupts the surrounding text; they degrade the structure rather than the content.",
    "The synthetic set is regenerated from scripts, so a fixture can be changed and the change reviewed.",
    "Expected outputs are committed beside the fixtures and compared byte for byte.",
    "A behaviour change that is intended is recorded by rewriting the expected files in the same commit.",
    "An unintended change fails the build before it reaches a release.",
    "The vendored table code is treated as third-party and is not edited locally.",
    "Where the original relied on a learned layout model, a font-size rule stands in for it.",
    "The rule is coarse, but it is inspectable, and a wrong answer can be traced to a number in the source.",
    "Reviewers asked whether the approach generalises beyond journal articles; we make no such claim.",
    "Books, slides and forms have layouts these heuristics were never shown and would misread.",
    "The scope is deliberately narrow: articles with a text layer, converted for reading by a language model.",
    "Within that scope the results are stable across the publishers we tried.",
    "Outside it, users should expect to check the output before trusting it.",
    "A second reviewer asked for timings; conversion runs at a few pages per second on a laptop.",
    "Most of that time is spent in the table detector, which is invoked on every page.",
    "Skipping it on pages with no ruling lines would halve the runtime at no cost to accuracy.",
    "We leave that optimisation for a later release and note it here for completeness.",
]


def paragraphs(count: int, start: int = 0, width: int = 5, step: int = 3):
    """``count`` distinct paragraphs, each a window of ``width`` sentences."""
    out = []
    n = len(SENTENCES)
    for k in range(count):
        i = (start + k * step) % n
        picked = [SENTENCES[(i + j) % n] for j in range(width)]
        out.append(" ".join(picked))
    return out


# --------------------------------------------------------------------------- #
# layout helpers
# --------------------------------------------------------------------------- #


class Doc(FPDF):
    def __init__(self, fmt="letter"):
        super().__init__(unit="pt", format=fmt)
        self.set_auto_page_break(False)
        self.set_creation_date(FIXED_DATE)
        self.set_margins(72, 72, 72)
        self.set_compression(True)
        # WinAnsi is what the core fonts are declared with; latin-1 (the
        # default) rejects the en dash, the ellipsis and the curly quotes.
        self.core_fonts_encoding = "cp1252"

    def text_at(self, x, y, s, font="Times", style="", size=10.0):
        """Draw one line with its baseline-ish top at y (fpdf cell semantics)."""
        self.set_font(font, style, size)
        self.set_xy(x, y)
        self.cell(0, size * 1.2, s)

    def centered(self, y, s, font="Times", style="", size=10.0):
        self.set_font(font, style, size)
        w = self.get_string_width(s)
        self.set_xy((self.w - w) / 2, y)
        self.cell(w, size * 1.2, s)

    def right(self, y, s, font="Times", style="", size=10.0, margin=72):
        self.set_font(font, style, size)
        w = self.get_string_width(s)
        self.set_xy(self.w - margin - w, y)
        self.cell(w, size * 1.2, s)

    def sup(self, x, y, s, size=10.0, font="Times", leading=None,
            raise_frac=0.33, scale=0.6):
        """A superscript run: ``scale`` of the body size, baseline raised
        ``raise_frac`` em above the baseline of a ``cell`` of height
        ``leading`` drawn at y. Body references use the defaults, which
        PyMuPDF flags as superscript; footnote labels use a smaller raise
        (0.25 em, 75%) because a raised glyph at the START of a line is
        otherwise split into its own line by PyMuPDF, as it is in real PDFs.
        """
        leading = leading if leading is not None else size * 1.2
        baseline = y + 0.5 * leading + 0.3 * size      # fpdf2's cell() baseline
        self.set_font(font, "", size * scale)
        self.text(x, baseline - raise_frac * size, s)
        return x + self.get_string_width(s)

    def note_label(self, x, y, s, size, leading):
        return self.sup(x, y, s, size, leading=leading, raise_frac=0.25, scale=0.75)

    def out(self, name: str):
        FIXTURES.mkdir(parents=True, exist_ok=True)
        path = FIXTURES / name
        self.output(str(path))
        print(f"wrote {path.relative_to(HERE.parent.parent)}  ({path.stat().st_size} bytes)")


class Flow:
    """Fill text into a sequence of boxes (columns, pages) one line at a time.

    boxes: list of (x, y_top, width, y_bottom). ``on_box`` is called with the
    index of every box after the first when the flow enters it, so a caller
    can start a new page and draw its furniture.
    """

    def __init__(self, pdf: Doc, boxes, size=10.0, leading=12.0, font="Times",
                 on_box=None):
        self.pdf, self.boxes = pdf, list(boxes)
        self.size, self.leading, self.font = size, leading, font
        self.on_box = on_box
        self.i = 0
        self.y = self.boxes[0][1]

    @property
    def box(self):
        return self.boxes[self.i]

    def advance(self):
        self.i += 1
        if self.i >= len(self.boxes):
            raise RuntimeError("Flow ran out of boxes - shorten the text")
        self.y = self.box[1]
        if self.on_box:
            self.on_box(self.i)

    def lines_left(self) -> int:
        return int((self.box[3] - self.y + 0.01) // self.leading)

    def ensure_room(self, lines=1):
        while self.lines_left() < lines:
            self.advance()

    def skip(self, pts: float):
        if self.y + pts + self.leading <= self.box[3]:
            self.y += pts

    def line(self, text: str, indent=0.0, style=""):
        self.ensure_room()
        x, w = self.box[0], self.box[2]
        self.pdf.set_font(self.font, style, self.size)
        self.pdf.set_xy(x + indent, self.y)
        self.pdf.cell(w - indent, self.leading, text)
        self.y += self.leading

    def paragraph(self, text: str, indent=0.0, space_after=0.0, hyphenate=True,
                  sup_refs: dict | None = None):
        """Ragged-right paragraph. At the last line of a box a long word is
        hyphenated so the break lands mid-word (hard.pdf's column case).

        ``sup_refs`` maps a word (as it appears in ``text``) to a superscript
        label drawn immediately after it.
        """
        pdf = self.pdf
        pdf.set_font(self.font, "", self.size)
        sup_refs = sup_refs or {}
        words = text.split()
        first = True
        cur: list[str] = []
        while words:
            self.ensure_room()
            width = self.box[2] - (indent if first else 0)
            w = words[0]
            trial = " ".join(cur + [w])
            if pdf.get_string_width(trial) <= width or not cur:
                cur.append(words.pop(0))
                if words:
                    continue
            elif hyphenate and self.lines_left() == 1:
                # Last line of the box and the paragraph continues: break a
                # word with a hyphen so the continuation starts mid-word. If
                # the next word has no fitting prefix, take back the last word
                # already on the line and split that one instead.
                for _attempt in range(8):
                    w = words[0]
                    split = False
                    if len(w) >= 6 and "-" not in w:
                        for k in range(len(w) - 3, 2, -1):
                            piece = " ".join(cur + [w[:k] + "-"])
                            if pdf.get_string_width(piece) <= width:
                                cur.append(w[:k] + "-")
                                words[0] = w[k:]
                                split = True
                                break
                    if split or len(cur) < 2:
                        break
                    words.insert(0, cur.pop())
            self._emit(cur, indent if first else 0, sup_refs)
            cur, first = [], False
        if space_after:
            self.skip(space_after)

    def _emit(self, words, indent, sup_refs):
        pdf = self.pdf
        x = self.box[0] + indent
        pdf.set_font(self.font, "", self.size)
        if not any(w.rstrip(".,;") in sup_refs for w in words):
            pdf.set_xy(x, self.y)
            pdf.cell(self.box[2] - indent, self.leading, " ".join(words))
        else:
            space = pdf.get_string_width(" ")
            for w in words:
                key = w.rstrip(".,;")
                punct = w[len(key):]
                pdf.set_font(self.font, "", self.size)
                pdf.set_xy(x, self.y)
                pdf.cell(pdf.get_string_width(key), self.leading, key)
                x += pdf.get_string_width(key)
                if key in sup_refs:
                    x = pdf.sup(x, self.y, sup_refs[key], self.size, self.font,
                                leading=self.leading)
                    pdf.set_font(self.font, "", self.size)
                if punct:
                    pdf.set_xy(x, self.y)
                    pdf.cell(pdf.get_string_width(punct), self.leading, punct)
                    x += pdf.get_string_width(punct)
                x += space
        self.y += self.leading

    def heading(self, text: str, size=12.0, before=8.0, after=4.0):
        self.ensure_room(3)
        self.skip(before)
        pdf = self.pdf
        pdf.set_font(self.font, "B", size)
        pdf.set_xy(self.box[0], self.y)
        pdf.cell(self.box[2], size * 1.2, text)
        self.y += size * 1.2 + after


def ruled_table(pdf: Doc, x, y, col_w, rows, size=9.0, row_h=14.0, header=True):
    """A table with full ruling lines (every cell bordered)."""
    for r, row in enumerate(rows):
        pdf.set_font("Times", "B" if (header and r == 0) else "", size)
        cx = x
        for c, cell in enumerate(row):
            pdf.set_xy(cx, y)
            pdf.cell(col_w[c], row_h, cell, border=1, align="C" if c else "L")
            cx += col_w[c]
        y += row_h
    return y


def wrapped_table(pdf: Doc, x, y, col_w, rows, size=9.0, line_h=11.0):
    """A ruled table whose middle column wraps over several lines per row -
    the tall-cell shape of compliance tables. Every cell is bordered."""
    for r, row in enumerate(rows):
        pdf.set_font("Times", "B" if r == 0 else "", size)
        # measure the wrapped column first
        pdf.set_xy(x + col_w[0], y)
        n_lines = len(pdf.multi_cell(col_w[1], line_h, row[1], dry_run=True, output="LINES"))
        row_h = max(1, n_lines) * line_h + 4
        cx = x
        for c, cell in enumerate(row):
            pdf.set_xy(cx, y)
            if c == 1:
                pdf.rect(cx, y, col_w[c], row_h)
                pdf.set_xy(cx, y + 2)
                pdf.multi_cell(col_w[c], line_h, cell)
            else:
                pdf.rect(cx, y, col_w[c], row_h)
                pdf.set_xy(cx, y + 2)
                pdf.cell(col_w[c], line_h, cell)
            cx += col_w[c]
        y += row_h
    return y


def booktabs_table(pdf: Doc, x, y, col_w, rows, size=9.0, row_h=13.0):
    """Horizontal rules only: top, below header, bottom (the LaTeX booktabs look)."""
    total = sum(col_w)
    pdf.set_line_width(0.8)
    pdf.line(x, y, x + total, y)
    for r, row in enumerate(rows):
        pdf.set_font("Times", "B" if r == 0 else "", size)
        cx = x
        for c, cell in enumerate(row):
            pdf.set_xy(cx, y)
            pdf.cell(col_w[c], row_h, cell, align="C" if c else "L")
            cx += col_w[c]
        y += row_h
        if r == 0:
            pdf.set_line_width(0.4)
            pdf.line(x, y, x + total, y)
    pdf.set_line_width(0.8)
    pdf.line(x, y, x + total, y)
    pdf.set_line_width(0.2)
    return y


def raster_figure_png(w=300, h=200) -> bytes:
    """A small synthetic 'photo': smooth gradient plus a few filled shapes,
    rendered by PyMuPDF so no image library is needed."""
    doc = pymupdf.open()
    page = doc.new_page(width=w, height=h)
    shape = page.new_shape()
    steps = 24
    for i in range(steps):
        g = 0.25 + 0.6 * i / steps
        shape.draw_rect(pymupdf.Rect(i * w / steps, 0, (i + 1) * w / steps, h))
        shape.finish(color=None, fill=(0.2, g, 0.9 - g * 0.5))
    shape.draw_circle((w * 0.3, h * 0.5), h * 0.28)
    shape.finish(color=(1, 1, 1), fill=(0.95, 0.75, 0.2), width=2)
    shape.draw_rect(pymupdf.Rect(w * 0.55, h * 0.25, w * 0.9, h * 0.8))
    shape.finish(color=(0.1, 0.1, 0.1), fill=(0.85, 0.3, 0.3), width=2)
    shape.commit()
    pix = page.get_pixmap(dpi=144, alpha=False)
    png = pix.tobytes("png")
    doc.close()
    return png


def vector_chart(pdf: Doc, x, y, w=260, h=150):
    """Axes, tick labels and five bars drawn as paths - a plotted chart."""
    pdf.set_line_width(0.8)
    pdf.set_draw_color(0)
    pdf.line(x, y + h, x + w, y + h)      # x axis
    pdf.line(x, y, x, y + h)              # y axis
    vals = [0.35, 0.62, 0.48, 0.81, 0.57]
    bw = w / (len(vals) * 2)
    fills = [(70, 110, 190), (90, 160, 90), (200, 120, 60), (150, 80, 160), (60, 160, 180)]
    for i, (v, fc) in enumerate(zip(vals, fills)):
        bx = x + bw * (2 * i + 0.6)
        bh = h * v
        pdf.set_fill_color(*fc)
        pdf.rect(bx, y + h - bh, bw * 0.9, bh, style="DF")
        pdf.text_at(bx, y + h + 3, f"C{i + 1}", size=7)
    for t in range(0, 5):
        ty = y + h - h * t / 4
        pdf.line(x - 3, ty, x, ty)
        pdf.text_at(x - 20, ty - 5, f"{t * 25:d}", size=7)
    pdf.set_fill_color(0)
    pdf.set_line_width(0.2)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def make_hard(name="hard.pdf", footer_first=False):
    """Two-column article with a running head, page numbers, a word hyphenated
    across the column break, a ruled table and footnotes.

    Bugs it reproduces: geometric block sorting scrambling columns; running
    heads surviving (or titles being deleted) by position-only marginalia;
    a hyphen at a column break being joined with a space; footnotes being
    swallowed by the footer zone.
    """
    pdf = Doc()
    gutter, margin = 24.0, 72.0
    col_w = (LETTER_W - 2 * margin - gutter) / 2
    left_x, right_x = margin, margin + col_w + gutter
    foot_notes = {1: [], 2: []}

    def furniture(page_no):
        pdf.text_at(margin, 30, "Journal of Synthetic Studies 12(3), 2026", style="I", size=9)
        pdf.right(30, "Lovelace and Babbage", style="I", size=9)

    def folio(page_no):
        # Normally drawn after the body, as LaTeX and Word emit footers. With
        # footer_first the page number is drawn right after the running head,
        # i.e. BEFORE the body in the stream (Acrobat PDFMaker does this).
        pdf.centered(752, str(page_no), size=9)

    pdf.add_page()
    furniture(1)
    if footer_first:
        folio(1)
    pdf.centered(84, "Reading Order Under Adversarial Layout:", style="B", size=17)
    pdf.centered(106, "A Synthetic Benchmark for Weight-Free PDF Conversion", style="B", size=17)
    pdf.centered(136, "Ada Lovelace and Charles Babbage", size=11)
    pdf.centered(150, "Analytical Engine Laboratory, London", style="I", size=10)
    pdf.text_at(margin, 178, "Abstract", style="B", size=10)
    abstract = Flow(pdf, [(margin, 192, LETTER_W - 2 * margin, 320)], size=9, leading=11)
    abstract.paragraph(" ".join(SENTENCES[0:4]) + " " + SENTENCES[19] + " " + SENTENCES[27])
    y_body = abstract.y + 10

    # column boxes: page 1 (two), page 2 (two). Footnotes take the bottom of
    # each column they belong to, so those boxes end higher.
    boxes = [
        (left_x, y_body, col_w, 650),        # p1 left: two notes below
        (right_x, y_body, col_w, 700),       # p1 right
        (left_x, 60, col_w, 700),            # p2 left
        (right_x, 60, col_w, 670),           # p2 right: one note below
    ]

    # Footnotes. Page 1's are drawn when the flow leaves the left column, so
    # in the content stream they sit between the two columns, as a typesetter
    # emits them; page 2's note is drawn after the body.
    def note(x, y, label, text):
        pdf.set_draw_color(0)
        pdf.set_line_width(0.4)
        pdf.line(x, y - 4, x + 80, y - 4)
        pdf.note_label(x, y, label, 8, 9.5)
        pdf.set_font("Times", "", 8)
        Flow(pdf, [(x, y, col_w, y + 60)], size=8, leading=9.5).paragraph(text, indent=6)

    def page1_notes():
        note(left_x, 672, "1",
             "Readers do forgive a wrong word; they rarely forgive a paragraph from the second "
             "column spliced into the first.")
        pdf.note_label(left_x, 700, "2", 8, 9.5)
        pdf.set_font("Times", "", 8)
        Flow(pdf, [(left_x, 700, col_w, 740)], size=8, leading=9.5).paragraph(
            "The footer zone is the bottom thirteen percent of the page in the reference "
            "implementation.", indent=6)

    def on_box(i):
        if i == 1:
            page1_notes()
        if i == 2:
            if not footer_first:
                folio(1)
            pdf.add_page()
            furniture(2)
            if footer_first:
                folio(2)

    flow = Flow(pdf, boxes, size=10, leading=12, on_box=on_box)
    paras = paragraphs(12, start=0, width=4, step=4)

    flow.heading("1 Introduction")
    flow.paragraph(paras[0], space_after=4, sup_refs={"forgives": "1"})
    flow.paragraph(paras[1], space_after=4)
    flow.heading("2 Related Work")
    flow.paragraph(paras[2], space_after=4, sup_refs={"redistributed": "2"})
    flow.paragraph(paras[3], space_after=4)
    flow.paragraph(paras[4], space_after=4)
    flow.heading("3 Benchmark Design")
    flow.paragraph(paras[5], space_after=4)
    flow.paragraph(paras[6], space_after=4)
    # Table 1 goes wherever the flow is when it has room; force it onto page 2
    # left column top if we are still on page 1 right.
    flow.ensure_room(9)
    pdf.set_font("Times", "", 9)
    cap = Flow(pdf, [flow.box], size=9, leading=11)
    cap.y = flow.y
    cap.paragraph("Table 1. Conversion accuracy on the synthetic set, by layout feature. "
                  "Higher is better; the last column counts documents.")
    y = cap.y + 2
    rows = [
        ["Feature", "Precision", "Recall", "N"],
        ["Two columns", "0.98", "0.97", "12"],
        ["Running head", "1.00", "0.94", "12"],
        ["Footnotes", "0.91", "0.88", "9"],
        ["Ruled table", "0.87", "0.83", "6"],
        ["Hyphenation", "0.99", "0.99", "12"],
    ]
    y = ruled_table(pdf, flow.box[0], y, [88, 46, 46, 30], rows)
    flow.y = y + 10
    flow.paragraph(paras[7], space_after=4, sup_refs={"support": "3"})
    flow.heading("4 Results")
    flow.paragraph(paras[8], space_after=4)
    flow.paragraph(paras[9], space_after=4)
    flow.heading("5 Discussion")
    flow.paragraph(paras[10], space_after=4)
    flow.paragraph(paras[11], space_after=4)

    note(right_x, 696, "3",
         "The generators and the fixtures ship in the repository under an Apache-2.0 licence.")
    if not footer_first:
        folio(2)
    pdf.out(name)


def _make_repro(name: str, top: float, header_y: float, header_size=9.0,
                heading_size=14.0):
    """Three pages whose first line is a section heading, a raster figure with
    a caption, a vector chart with a caption, and Symbol+Times equations.

    Bugs: headings at the page top deleted as running heads; figure captions
    not attached; equations set in Symbol + Times missed by font-name tests.
    ``repro_tight`` uses an 11 mm top margin so PyMuPDF merges the running
    head and the heading into one block.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(10, start=7, step=4, width=4)

    def furniture(n):
        # Header only. The page number is drawn after the body (folio): PyMuPDF
        # builds blocks in stream order, and a far-away line between header and
        # heading would keep them apart in the tight variant.
        pdf.text_at(margin, header_y, "Repro and Author: Synthetic figures and equations",
                    style="I", size=header_size)

    def folio(n):
        pdf.centered(752, f"– {n} –", size=9)

    def equation(y, number, parts):
        """parts: list of (font, text). Centered, numbered at the right margin."""
        total = 0.0
        for font, s in parts:
            pdf.set_font(font, "", 11)
            total += pdf.get_string_width(s)
        x = (LETTER_W - total) / 2
        for font, s in parts:
            pdf.set_font(font, "", 11)
            pdf.set_xy(x, y)
            pdf.cell(pdf.get_string_width(s), 14, s)
            x += pdf.get_string_width(s)
        pdf.right(y, f"({number})", size=11)

    # page 1 ------------------------------------------------------------ #
    pdf.add_page()
    furniture(1)
    pdf.text_at(margin, top, "1 Introduction", style="B", size=heading_size)
    f = Flow(pdf, [(margin, top + 26, width, 760)], size=10, leading=12.5)
    f.paragraph(paras[0], space_after=6)
    f.paragraph(paras[1], space_after=6)
    f.paragraph(paras[2], space_after=10)
    y = f.y
    png = raster_figure_png()
    fig_w, fig_h = 300.0, 200.0
    pdf.image(io.BytesIO(png), x=(LETTER_W - fig_w) / 2, y=y, w=fig_w, h=fig_h)
    y += fig_h + 6
    cap = Flow(pdf, [(margin + 20, y, width - 40, 760)], size=9, leading=11)
    cap.paragraph("Figure 1. A raster image embedded as an XObject: gradient background with "
                  "two filled shapes. The caption sits directly under the image.")
    f.y = cap.y + 10
    f.paragraph(paras[3], space_after=6)
    folio(1)

    # page 2 ------------------------------------------------------------ #
    pdf.add_page()
    furniture(2)
    pdf.text_at(margin, top, "2 Materials and Methods", style="B", size=heading_size)
    f = Flow(pdf, [(margin, top + 26, width, 760)], size=10, leading=12.5)
    f.paragraph(paras[4], space_after=6)
    f.paragraph("The model is a linear response with a Gaussian disturbance term:",
                space_after=10)
    equation(f.y, 1, [("Times", "y = "), ("Symbol", "a"), ("Times", " + "),
                      ("Symbol", "b"), ("Times", "x + "), ("Symbol", "e"),
                      ("Times", ",   "), ("Symbol", "e"), ("Times", " ~ N(0, "),
                      ("Symbol", "s"), ("Times", "²)")])
    f.y += 26
    f.paragraph(paras[5], space_after=10)
    y = f.y
    vector_chart(pdf, margin + 40, y, w=280, h=150)
    y += 150 + 16
    cap = Flow(pdf, [(margin + 20, y, width - 40, 760)], size=9, leading=11)
    cap.paragraph("Figure 2. A vector chart drawn with path operators: five conditions, "
                  "response in percent. No image object is involved.")
    f.y = cap.y + 10
    f.paragraph(paras[6], space_after=6)
    folio(2)

    # page 3 ------------------------------------------------------------ #
    pdf.add_page()
    furniture(3)
    pdf.text_at(margin, top, "3 Results and Discussion", style="B", size=heading_size)
    f = Flow(pdf, [(margin, top + 26, width, 760)], size=10, leading=12.5)
    f.paragraph(paras[7], space_after=6)
    f.paragraph("Summing over conditions gives the pooled estimate", space_after=10)
    equation(f.y, 2, [("Symbol", "m"), ("Times", " = (1/n) "), ("Symbol", "S"),
                      ("Times", " y"), ("Times", "i"), ("Times", ",   i = 1, …, n")])
    f.y += 26
    f.paragraph(paras[8], space_after=6)
    f.paragraph(paras[9], space_after=6)
    folio(3)
    pdf.out(name)


def make_repro():
    _make_repro("repro.pdf", top=72.0, header_y=36.0)


def make_repro_tight():
    # 11 mm top margin; the running head sits 11 pt above the heading, close
    # enough that PyMuPDF puts both in one block.
    _make_repro("repro_tight.pdf", top=11 / 25.4 * 72, header_y=11 / 25.4 * 72 - 11)


def make_footnote_repro(name="footnote_repro.pdf", big_label=False):
    """One page: two body references as superscripts, an exponent that is also
    a superscript digit, and a footnote whose body wraps across two blocks.

    Bugs: the second half of a wrapped note rendered as a stray paragraph;
    an exponent turned into a footnote reference; note labels lost.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    pdf.add_page()
    pdf.centered(80, "Footnotes, References and Exponents", style="B", size=16)
    pdf.centered(102, "A one-page reproduction", style="I", size=11)
    f = Flow(pdf, [(margin, 140, width, 640)], size=11, leading=14)
    paras = paragraphs(6, start=3, step=5)
    f.paragraph(paras[0], space_after=8, sup_refs={"authoritative": "1"})
    f.paragraph(paras[1], space_after=8)
    # "r" carries a raised "2" (an exponent), "included" a raised "2" (a note ref)
    f.paragraph("The fit was close, with r = 0.81 across the twelve documents, "
                "and remained above 0.7 when the scanned copies were included in the "
                "pooled sample. " + paras[2], space_after=8,
                sup_refs={"r": "2", "included": "2"})
    f.paragraph(paras[3], space_after=8)
    f.paragraph(paras[4], space_after=8)

    # footnotes
    y = 668
    pdf.set_line_width(0.4)
    pdf.line(margin, y - 6, margin + 90, y - 6)

    def label(y, s):
        if big_label:
            # Word-style: the label is a body-size (11 pt) glyph on the note's
            # baseline, followed by a tab; the note itself is 8.5 pt.
            pdf.set_font("Times", "", 11)
            pdf.text(margin, y + 0.5 * 10 + 0.3 * 8.5, s)
        else:
            pdf.note_label(margin, y, s, 8.5, 10)

    label(y, "1")
    Flow(pdf, [(margin, y, width, y + 20)], size=8.5, leading=10).paragraph(
        "Two columns, in every document in the set; the abstract runs full measure.",
        indent=7)
    y += 12
    label(y, "2")
    note2 = Flow(pdf, [(margin, y, width, y + 12)], size=8.5, leading=10)
    note2.paragraph("Scanned copies were produced by rasterising the digital file at 150 dots "
                    "per inch and recognising it with", indent=7, hyphenate=False)
    # a wider gap than the note's leading, so PyMuPDF starts a new block here
    y = note2.y + 8
    Flow(pdf, [(margin, y, width, y + 30)], size=8.5, leading=10).paragraph(
        "Tesseract at default settings; the recogniser was not tuned for the fonts used, "
        "which understates its accuracy on real scans.", hyphenate=False)
    pdf.centered(752, "1", size=9)
    pdf.out(name)


def make_footnote_bold_wrapped():
    """Bold numbered notes over several lines and blocks, an italic
    continuation, and a genuine star note (PLAN-tables item 8).

    Bug: the renderer re-read each formatted note line for a label, and the
    "**" that opens a bold line is indistinguishable from a two-star symbol
    marker, so every bold line became its own "[^**]:" definition.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    pdf.add_page()
    pdf.centered(80, "Bold Footnotes Across Lines and Blocks", style="B", size=16)
    f = Flow(pdf, [(margin, 130, width, 600)], size=11, leading=14)
    paras = paragraphs(4, start=8, step=5)
    f.paragraph(paras[0], space_after=8, sup_refs={"copyright": "3"})
    f.paragraph(paras[1], space_after=8, sup_refs={"column": "4"})
    f.paragraph(paras[2], space_after=8, sup_refs={"project": "*"})

    y = 630
    pdf.set_line_width(0.4)
    pdf.line(margin, y - 6, margin + 90, y - 6)

    def note_line(y, text, style="B", x=margin):
        pdf.set_font("Times", style, 8.5)
        pdf.set_xy(x, y)
        pdf.cell(width, 10, text)

    # note 3: bold, label run on ("3During"), three lines in one block,
    # the second line ending in a hyphenated word
    note_line(y, "3During the 1960s and early 1970s a number of laws were passed and executive orders")
    note_line(y + 10, "issued to address the civil rights of various groups, including the Readjustment Assis-")
    note_line(y + 20, "tance Act of 1974 and 12 related statutes.")
    # note 4: bold first block, then a gap and an ITALIC continuation block
    # whose first line begins with a number that is not a label
    note_line(y + 34, "4The sample covers every firm that reported in the period; firms that reported in")
    note_line(y + 44, "only one year are excluded from the panel and listed in the appendix.")
    note_line(y + 62, "2 of them were later restored after the audit, as the appendix explains in detail;", style="I")
    note_line(y + 72, "the restoration does not change any estimate reported here.", style="I")
    # a genuine star note in regular type
    note_line(y + 90, "* Corresponding author. The order of authors is alphabetical.", style="")
    pdf.centered(752, "1", size=9)
    pdf.out("footnote_bold_wrapped.pdf")


def make_manuscript(name="manuscript.pdf", number_column=False):
    """Double-spaced submission manuscript: margin line numbers on every line,
    first-line indents, unnumbered centred headings, and a running head with
    page number drawn AFTER the body on each page.

    Bugs: one-block-per-line output not reflowed into paragraphs (or reflowed
    too eagerly); line numbers leaking into the text; a running head drawn
    last in the stream landing at the end of the page's text.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    leading = 24.0
    paras = paragraphs(9, start=11, step=4, width=4)
    line_no = [0]
    pending: list = []          # (y, number) for the current page

    class Numbered(Flow):
        def _emit(self, words, indent, sup_refs):
            line_no[0] += 1
            pending.append((self.y, line_no[0]))
            super()._emit(words, indent, sup_refs)

    col_no = [0]

    def line_numbers():
        # A word processor draws the margin numbers as a separate pass, so
        # they come after the page's text in the stream and form their own
        # blocks rather than sharing a block with each line.
        if number_column:
            # ScholarOne-style: a continuous column of numbers at SINGLE
            # spacing down the margin, independent of the double-spaced
            # text, so PyMuPDF returns all of them as ONE block.
            pdf.set_font("Helvetica", "", 10)
            y = 43.0
            while y < 745:
                col_no[0] += 1
                pdf.text(8, y + 9, str(col_no[0]))
                y += 11.7
            pending.clear()
            return
        for y, n in pending:
            pdf.text_at(40, y + 4, str(n), size=8)
        pending.clear()

    def running_head(n):
        # Drawn last: everything on the page precedes it in the stream.
        line_numbers()
        pdf.text_at(margin, 30, "SYNTHETIC MANUSCRIPT", size=12)
        pdf.right(30, str(n), size=12)

    def centered_heading(flow, text):
        flow.ensure_room(3)
        flow.skip(6)
        pdf.set_font("Times", "B", 12)
        w = pdf.get_string_width(text)
        pdf.set_xy((LETTER_W - w) / 2, flow.y)
        pdf.cell(w, leading, text)
        flow.y += leading

    pdf.add_page()
    pdf.centered(150, "Structure Without Weights: Recovering Document Layout", style="B", size=12)
    pdf.centered(174, "from the Text Layer Alone", style="B", size=12)
    pdf.centered(222, "Ada Lovelace", size=12)
    pdf.centered(246, "Analytical Engine Laboratory", size=12)
    pdf.centered(294, "Author Note", style="B", size=12)
    f = Numbered(pdf, [(margin, 318, width, 720)], size=12, leading=leading)
    f.paragraph("Correspondence concerning this article should be addressed to Ada Lovelace, "
                "Analytical Engine Laboratory, London. This manuscript is a synthetic fixture "
                "and describes no real study.", indent=36)
    running_head(1)

    for page_no, (heading, chunk) in enumerate(
            [("Introduction", paras[0:3]), ("Theory and Hypotheses", paras[3:6]),
             ("Method", paras[6:9])], start=2):
        pdf.add_page()
        f = Numbered(pdf, [(margin, 60, width, 736)], size=12, leading=leading)
        centered_heading(f, heading)
        for k, p in enumerate(chunk):
            f.paragraph(p, indent=36, hyphenate=False)
            if heading == "Theory and Hypotheses" and k == 1:
                f.paragraph("Hypothesis 1: Documents converted with stream order will show "
                            "fewer reading-order errors than documents converted with "
                            "geometric block sorting.", indent=36, hyphenate=False)
        running_head(page_no)
    pdf.out(name)


def make_scanned():
    """hard.pdf rasterised at 150 dpi, grey, one full-page image per page and
    no text layer at all - drives the OCR path. Requires hard.pdf to exist."""
    src = pymupdf.open(FIXTURES / "hard.pdf")
    pdf = Doc()
    for page in src:
        pix = page.get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False)
        png = pix.tobytes("png")
        pdf.add_page()
        pdf.image(io.BytesIO(png), x=0, y=0, w=LETTER_W, h=LETTER_H)
    src.close()
    pdf.out("scanned.pdf")


def make_scanned_with_stamp():
    """hard.pdf pages 1-2 as full-page rasters plus a ONE-LINE native copyright
    stamp at the foot of each, the way ProQuest and ResearchGate deliver scans.

    Bug: the stamp's 100-odd native characters exceeded the 20-character OCR
    gate, so the page was never recognised and converted to the stamp alone.

    Second bug (page 2): the running head is the same on both pages but the
    scan reads its page number differently ("579" vs "S81"), and the
    repetition test then missed it, so the head survived as a heading.
    """
    src = pymupdf.open(FIXTURES / "hard.pdf")
    # page 3: a references page in the Organization Studies style - a
    # one-word "References" label, then author lines in title case each
    # followed by the entry. Bugs: the one-word heading was missed and every
    # author line became a heading on the recognised page.
    refs = src.new_page(width=LETTER_W, height=LETTER_H)
    refs.insert_text((72, 40), "1995 Suchman 583", fontsize=10, fontname="tiro")
    # one-word headings that the title-case test cannot see
    refs.insert_text((72, 80), "Abstract", fontsize=11, fontname="tibo")
    refs.insert_textbox(pymupdf.Rect(72, 90, 540, 150), SENTENCES[0] + " " + SENTENCES[1],
                        fontsize=10, fontname="tiro")
    refs.insert_text((72, 170), "Introduction", fontsize=11, fontname="tibo")
    refs.insert_textbox(pymupdf.Rect(72, 180, 540, 240), SENTENCES[2] + " " + SENTENCES[3],
                        fontsize=10, fontname="tiro")
    refs.insert_text((72, 270), "References", fontsize=11, fontname="tibo")
    y = 300
    for author, entry in [
        ("Abbot, Andrew", "1988 The system of professions: An essay on the division of expert labour. Chicago: University of Chicago Press."),
        ("Abrahamson, Eric", "1991 Managerial fads and fashions: The diffusion and rejection of innovations. Academy of Management Review 16/3: 586-612."),
        ("Ackroyd, Stephen", "1995 The new public management and the professionals. Working Paper No. 24, Stockholm University."),
        ("Barley, Stephen, and Pamela Tolbert", "1997 Institutionalization and structuration: Studying the links between action and institution. Organization Studies 18/1: 93-117."),
    ]:
        # author on its own line, the entry hanging-indented below it with a
        # year in the margin, as Organization Studies sets its references
        refs.insert_text((72, y), author, fontsize=10, fontname="tibo")
        refs.insert_text((72, y + 16), entry[:4], fontsize=10, fontname="tiro")
        refs.insert_textbox(pymupdf.Rect(110, y + 6, 540, y + 60), entry[5:], fontsize=10, fontname="tiro")
        y += 74
    heads = ["1995 Suchman 579", "1995 Suchman S81", None]
    pdf = Doc()
    for i, head in enumerate(heads):
        page = src[i]
        if head is None:
            pix = page.get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False)
            pdf.add_page()
            pdf.image(io.BytesIO(pix.tobytes("png")), x=0, y=0, w=LETTER_W, h=LETTER_H)
            pdf.set_font("Helvetica", "", 8)
            pdf.text(40, LETTER_H - 14, "Reproduced with permission of the copyright owner. "
                     "Further reproduction prohibited without permission.")
            continue
        # replace hard.pdf's running head with a Suchman-style one
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(0, 20, LETTER_W, 46))
        shape.finish(color=None, fill=(1, 1, 1))
        shape.commit()
        page.insert_text((72, 40), head, fontsize=10, fontname="tiro")
        pix = page.get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False)
        pdf.add_page()
        pdf.image(io.BytesIO(pix.tobytes("png")), x=0, y=0, w=LETTER_W, h=LETTER_H)
        pdf.set_font("Helvetica", "", 8)
        pdf.text(40, LETTER_H - 14, "Reproduced with permission of the copyright owner. "
                 "Further reproduction prohibited without permission.")
    src.close()
    pdf.out("scanned_with_stamp.pdf")


def make_provenance_pages():
    """Five native-text pages: a real title page (control), a JSTOR terms
    page, a ResearchGate cover, a ProQuest citation banner over a body page
    with the per-page permission stamp, and a SAGE download stamp.

    Bug: the covers and banner came through as content (the ResearchGate
    title as an h2, "CITATIONS 2,718", "SEE PROFILE"), and nothing recorded
    where the file came from once they were removed by hand.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    paras = paragraphs(6, start=21, step=4, width=4)

    # p1: control - a genuine title page that must survive intact
    pdf.add_page()
    pdf.centered(120, "Institutional Distance and Legitimacy", style="B", size=16)
    pdf.centered(150, "Ada Lovelace and Charles Babbage", size=11)
    f = Flow(pdf, [(margin, 190, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=8)
    f.paragraph(paras[1], space_after=8)

    # p2: JSTOR terms page
    pdf.add_page()
    y = 72
    for line, style, size in [
        ("Institutional Distance and Legitimacy", "B", 12),
        ("Author(s): Ada Lovelace and Charles Babbage", "", 10),
        ("Source: The Journal of Synthetic Studies, Vol. 12, No. 3 (Jul., 2026), pp. 571-610", "", 10),
        ("Published by: Academy of Synthetic Studies", "", 10),
        ("Stable URL: https://www.jstor.org/stable/258788", "", 10),
        ("Accessed: 14-09-2026 10:22 UTC", "", 10),
    ]:
        pdf.text_at(margin, y, line, style=style, size=size)
        y += 16
    f = Flow(pdf, [(margin, y + 20, width, 740)], size=9, leading=12)
    f.paragraph("JSTOR is a not-for-profit service that helps scholars, researchers, and "
                "students discover, use, and build upon a wide range of content in a trusted "
                "digital archive. We use information technology and tools to increase "
                "productivity and facilitate new forms of scholarship.", space_after=8)
    f.paragraph("Your use of the JSTOR archive indicates your acceptance of the Terms & "
                "Conditions of Use, available at https://about.jstor.org/terms", space_after=8)

    # p3: ResearchGate cover
    pdf.add_page()
    pdf.text_at(margin, 60, "See discussions, stats, and author profiles for this publication at: "
                "https://www.researchgate.net/publication/234021651", size=7)
    pdf.text_at(margin, 90, "Institutional Distance and Legitimacy: The Case of the", style="B", size=14)
    pdf.text_at(margin, 108, "Multinational Enterprise", style="B", size=14)
    pdf.text_at(margin, 140, "Article  in  Journal of Synthetic Studies \u00b7 January 2026", size=8)
    pdf.text_at(margin, 154, "DOI: 10.2307/259037", size=7)
    pdf.text_at(margin, 190, "CITATIONS", size=6)
    pdf.text_at(margin + 200, 190, "READS", size=6)
    pdf.text_at(margin, 200, "2,718", size=9)
    pdf.text_at(margin + 200, 200, "3,585", size=9)
    pdf.text_at(margin, 240, "2 authors, including:", size=8)
    pdf.text_at(margin, 256, "Charles Babbage", size=8)
    pdf.text_at(margin, 268, "SEE PROFILE", size=6)
    pdf.text_at(margin, 720, "All content following this page was uploaded by Charles Babbage on 03 May 2026.", size=7)
    pdf.text_at(margin, 734, "The user has requested enhancement of the downloaded file.", size=7)

    # p4: ProQuest banner above a body page, permission stamp at the foot
    pdf.add_page()
    pdf.text_at(30, 14, "Institutional distance and legitimacy", style="B", size=10)
    pdf.text_at(30, 26, "Lovelace, Ada", size=8)
    pdf.text_at(30, 36, "Academy of Synthetic Studies. The Journal of Synthetic Studies; Jul 2026; 12, 3; "
                "ABI/INFORM Global", style="I", size=8)
    pdf.text_at(30, 46, "pg. 571", size=8)
    pdf.text_at(margin, 100, "1 Introduction", style="B", size=14)
    f = Flow(pdf, [(margin, 126, width, 740)], size=10, leading=13)
    f.paragraph(paras[2], space_after=8)
    f.paragraph(paras[3], space_after=8)
    pdf.set_font("Helvetica", "", 8)
    pdf.text(30, LETTER_H - 14, "Reproduced with permission of the copyright owner. "
             "Further reproduction prohibited without permission.")

    # p5: SAGE Journals Online stamp at the foot of a body page, in the three
    # native pieces SAGE emits (the host is a hyperlink), plus the page-1
    # collections line
    pdf.add_page()
    pdf.text_at(margin, 100, "2 Method", style="B", size=14)
    f = Flow(pdf, [(margin, 126, width, 740)], size=10, leading=13)
    f.paragraph(paras[4], space_after=8)
    f.paragraph(paras[5], space_after=8)
    pdf.set_font("Helvetica", "", 5)
    pdf.text(200, LETTER_H - 30, "Downloaded from ")
    pdf.text(238, LETTER_H - 30, "oss.sagepub.com")
    pdf.text(276, LETTER_H - 30, " at SAGE Publications on December 7, 2012")
    pdf.text(14, LETTER_H - 16, "from the SAGE Social Science Collections. All Rights Reserved.")

    # p6: EBSCOhost notice page (native text, nothing else on the page)
    pdf.add_page(format="a4")
    f = Flow(pdf, [(margin, 72, 450, 300)], size=10, leading=13)
    f.paragraph("Copyright of Journal of Synthetic Studies is the property of Academy of "
                "Synthetic Studies and its content may not be copied or emailed to multiple "
                "sites or posted to a listserv without the copyright holder's express written "
                "permission. However, users may print, download, or email articles for "
                "individual use.", hyphenate=False)

    # p7: WRAP (Warwick) repository cover sheet
    pdf.add_page(format="a4")
    y = 80
    for line, style in [
        ("warwick.ac.uk/lib-publications", "B"),
        ("", ""),
        ("Manuscript version: Author's Accepted Manuscript", "B"),
        ("The version presented in WRAP is the author's accepted manuscript and may differ from the", ""),
        ("published version or, Version of Record.", ""),
        ("", ""),
        ("Persistent WRAP URL:", "B"),
        ("http://wrap.warwick.ac.uk/147367", ""),
        ("", ""),
        ("How to cite:", "B"),
        ("Please refer to published version for the most recent bibliographic citation information.", ""),
        ("", ""),
        ("Copyright and reuse:", "B"),
        ("The Warwick Research Archive Portal (WRAP) makes this work of researchers of the", ""),
        ("University of Warwick available open access under the following conditions.", ""),
        ("This article is made available under the Creative Commons Attribution-NonCommercial-", ""),
        ("NoDerivatives 4.0 International (CC BY-NC-ND 4.0) and may be reused according to the", ""),
        ("conditions of the license.", ""),
        ("", ""),
        ("For more information, please contact the WRAP Team at: wrap@warwick.ac.uk.", ""),
    ]:
        if line:
            pdf.text_at(90, y, line, font="Helvetica", style=style, size=10)
        y += 15
    pdf.out("provenance_pages.pdf")


def _justified_source(with_table: bool):
    """A two-column page of JUSTIFIED prose (fpdf2 multi_cell align="J"),
    optionally followed by a genuine two-column numeric table."""
    pdf = Doc()
    pdf.add_page()
    margin, gutter = 72.0, 24.0
    col_w = (LETTER_W - 2 * margin - gutter) / 2
    pdf.text_at(margin, 60, "3 Results", style="B", size=14)
    paras = paragraphs(4, start=25, step=4, width=5)
    pdf.set_font("Times", "", 10)
    bottom = 430 if with_table else 720
    for ci, x in enumerate((margin, margin + col_w + gutter)):
        pdf.set_xy(x, 90)
        for para in paras[2 * ci: 2 * ci + 2]:
            pdf.set_x(x)
            pdf.multi_cell(col_w, 12.5, para, align="J")
            pdf.ln(4)
            if pdf.get_y() > bottom:
                break
    if with_table:
        pdf.text_at(margin, 470, "Table 2. Throughput by condition (a real table).", style="I", size=9)
        rows = [["Condition", "N", "Mean", "SD"],
                ["Baseline", "120", "41.2", "3.4"],
                ["Treatment A", "118", "52.7", "4.1"],
                ["Treatment B", "121", "48.9", "3.9"],
                ["Pooled", "359", "47.6", "6.2"]]
        ruled_table(pdf, margin, 490, [130, 60, 70, 60], rows, size=10, row_h=20)
    return pdf


def make_justified_scan():
    """Two rasters (as scanned.pdf is made) of a two-column page of justified
    prose; the second page adds a genuine ruled numeric table below the prose.

    Bug: Tesseract's justified word gaps let propose_tables_from_text fire on
    the prose and _columns_align pass, and the reconstruction dropped rows.
    With the text-loss guard the prose stays prose with every word; the
    control page's real table must still be detected.
    """
    pdf = Doc()
    for with_table in (False, True):
        src = _justified_source(with_table)
        with pymupdf.open(stream=bytes(src.output()), filetype="pdf") as doc:
            pix = doc[0].get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False)
        pdf.add_page()
        pdf.image(io.BytesIO(pix.tobytes("png")), x=0, y=0, w=LETTER_W, h=LETTER_H)
    pdf.out("justified_scan.pdf")


def make_rotated_pages():
    """Three pages: upright prose; a table drawn sideways on a page stored
    with /Rotate (it displays upright); a table printed sideways on a
    portrait page.

    Bug: extract_page drops every non-horizontal line (the watermark fix), so
    both table pages converted to nothing at all, silently.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    paras = paragraphs(3, start=29, step=4, width=4)
    pdf.add_page()
    pdf.text_at(margin, 60, "5 Results", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=8)
    f.paragraph(paras[1], space_after=8)
    rows = [["Variable", "Mean", "SD", "VIF"],
            ["Certified buildings", "3.77", "11.84", "2.21"],
            ["Population density", "0.27", "0.31", "1.66"],
            ["Income per capita", "0.04", "0.01", "1.35"],
            ["Housing starts", "0.48", "0.24", "1.44"]]
    for label in ("Table 1. Descriptive statistics (stored rotated)",
                  "Table 2. Descriptive statistics (printed sideways)"):
        pdf.add_page()
        cx, cy = LETTER_W / 2, LETTER_H / 2
        with pdf.rotation(90, cx, cy):
            # inside the rotation the usable frame is the landscape page
            # keep to a square about the centre, which lies on the page in
            # both the drawn and the turned orientation
            x0, y0 = cx - 180, cy - 110
            pdf.set_font("Times", "B", 11)
            pdf.text(x0, y0, label)
            ruled_table(pdf, x0, y0 + 14, [150, 70, 70, 70], rows, size=10, row_h=22)
            pdf.set_font("Times", "", 9)
            pdf.text(x0, y0 + 144, "Notes: N = 5,110 observations. All values are synthetic.")
    raw = bytes(pdf.output())
    doc = pymupdf.open(stream=raw, filetype="pdf")
    doc[1].set_rotation(90)          # page 2: /Rotate makes the sideways table display upright
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "rotated_pages.pdf"
    doc.save(str(path), garbage=0, deflate=True, no_new_id=True)
    doc.close()
    print(f"wrote {path.relative_to(HERE.parent.parent)}  ({path.stat().st_size} bytes)")


def make_ebsco_notice_scan():
    """A digital page followed by the EBSCOhost notice delivered as a raster
    (Greenwood & Suddaby 2006 ends this way). Needs OCR to be recognised.

    Bug: the recognised notice came through as the article's last paragraph.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    pdf.text_at(margin, 60, "6 Conclusion", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    for para in paragraphs(2, start=33, step=4, width=4):
        f.paragraph(para, space_after=8)
    notice = Doc()
    notice.add_page()
    nf = Flow(notice, [(40, 60, 520, 300)], size=12, leading=15, font="Helvetica")
    nf.paragraph("Copyright of Journal of Synthetic Studies is the property of Academy of "
                 "Synthetic Studies and its content may not be copied or emailed to multiple "
                 "sites or posted to a listserv without the copyright holder's express written "
                 "permission. However, users may print, download, or email articles for "
                 "individual use.", hyphenate=False)
    with pymupdf.open(stream=bytes(notice.output()), filetype="pdf") as doc:
        png = doc[0].get_pixmap(dpi=150, colorspace=pymupdf.csGRAY, alpha=False).tobytes("png")
    pdf.add_page()
    pdf.image(io.BytesIO(png), x=0, y=0, w=LETTER_W, h=LETTER_H)
    pdf.out("ebsco_notice_scan.pdf")


def make_table_legend():
    """A regression table at the foot of the page with its significance
    legend in small type, and one genuine numbered footnote below it.

    Bug: the legend lines ("* p < .05") open with the symbols of a symbol
    footnote and sit in the footnote zone, so they were emitted as the notes
    [^*], [^**], [^***] and moved to the end of the page.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    pdf.text_at(margin, 60, "4 Estimates", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 520)], size=10, leading=13)
    paras = paragraphs(3, start=37, step=3, width=4)
    f.paragraph(paras[0], space_after=8, sup_refs={"source": "1"})
    f.paragraph(paras[1], space_after=8)
    y = 560
    pdf.text_at(margin, y - 18, "Table 3. Negative binomial estimates", style="I", size=9)
    rows = [["Variable", "(1)", "(2)", "(3)"],
            ["Population density", "0.55***", "0.49***", "0.50***"],
            ["Income per capita", "0.10*", "0.09", "0.11*"],
            ["Housing starts", "0.04", "0.06**", "0.05"]]
    y = ruled_table(pdf, margin, y, [200, 80, 80, 80], rows, size=9, row_h=16)
    for k, line in enumerate(["* p < .05", "** p < .01", "*** p < .001 (two-tailed tests)"]):
        pdf.text_at(margin, y + 6 + 11 * k, line, size=8)
    y += 56
    pdf.set_line_width(0.4)
    pdf.line(margin, y - 4, margin + 90, y - 4)
    pdf.note_label(margin, y, "1", 8.5, 10)
    Flow(pdf, [(margin, y, width, y + 30)], size=8.5, leading=10).paragraph(
        "The model is nonlinear, so interaction coefficients are interpreted graphically.",
        indent=7, hyphenate=False)
    pdf.out("table_legend.pdf")


def make_pi_minus():
    """A coefficient table whose minus signs are drawn from a separate font
    that never draws a letter, glued to the front of the number - the shape a
    mathematical-pi font without a ToUnicode map has after extraction, where
    the minus reads "2" and "<" reads ",". The fixture cannot embed a broken
    map, so the pi glyphs are literally "2" and "," set in Courier.

    Bug: "-0.10" extracted as "20.10", in prose and in table cells.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    pdf.text_at(margin, 60, "4 Estimates", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 300)], size=10, leading=13)
    f.paragraph(paragraphs(1, start=41, step=3, width=4)[0], space_after=8)

    def number(x, y, text, size=10.0):
        """Draw a number; a leading '-' or '<' comes from the pi font."""
        if text[0] in "-<":
            pdf.set_font("Courier", "", size)
            glyph = "2" if text[0] == "-" else ","
            pdf.text(x, y, glyph)
            x += pdf.get_string_width(glyph)
            text = text[1:]
        pdf.set_font("Times", "", size)
        pdf.text(x, y, text)

    pdf.set_font("Times", "", 10)
    pdf.text(margin, 200, "The effect of density is")
    number(margin + 108, 200, "-0.10")
    pdf.set_font("Times", "", 10)
    pdf.text(margin + 140, 200, "and that of income is")
    number(margin + 232, 200, "-0.09")
    pdf.set_font("Times", "", 10)
    pdf.text(margin + 264, 200, "with p")
    number(margin + 292, 200, "<.05")
    pdf.set_font("Times", "", 10)
    pdf.text(margin + 320, 200, "in 2 of the 3 models.")
    rows = [["Variable", "(1)", "(2)", "(3)"],
            ["Population density", "-0.10", "-0.09", "-0.11"],
            ["Income per capita", "0.55", "0.49", "-0.50"],
            ["Housing starts", "-6.65", "2.10", "-2.46"]]
    col = [200, 80, 80, 80]
    y = 240
    for ri, row in enumerate(rows):
        x = margin
        for ci, cell in enumerate(row):
            pdf.rect(x, y, col[ci], 18)
            if ci == 0 or ri == 0:
                pdf.set_font("Times", "B" if ri == 0 else "", 10)
                pdf.text(x + 4, y + 13, cell)
            else:
                number(x + 20, y + 13, cell)
            x += col[ci]
        y += 18
    pdf.out("pi_minus.pdf")


def make_dropcap():
    """Two sections that open with a three-line drop capital, drawn after
    the section heading as a separate text object (the AMP house style).

    Bug: the capital joined the heading ("Two Core Propositions T") and the
    paragraph began "he first proposition ...".
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    paras = paragraphs(4, start=2, step=5, width=4)
    y = 72
    for head, cap, para, follow in (
            ("Strategy Tripod", "T", "he first " + paras[0][0].lower() + paras[0][1:], paras[1]),
            ("Two Core Propositions", "A", "s part of " + paras[2][0].lower() + paras[2][1:], paras[3])):
        pdf.text_at(margin, y, head, style="B", size=14)
        pdf.set_font("Times", "", 40)
        pdf.text(margin, y + 58, cap)
        capw = pdf.get_string_width(cap) + 3
        pdf.set_font("Times", "", 10)
        words = para.split()
        yy = y + 28
        line_no = 0
        cur = []
        while words:
            x = margin + (capw if line_no < 3 else 0)
            w = width - (capw if line_no < 3 else 0)
            cur = []
            while words and pdf.get_string_width(" ".join(cur + [words[0]])) <= w:
                cur.append(words.pop(0))
            pdf.text(x, yy + 9, " ".join(cur))
            yy += 12.5
            line_no += 1
        f = Flow(pdf, [(margin, yy + 6, width, 740)], size=10, leading=12.5)
        f.paragraph(follow, space_after=8)
        y = f.y + 20
    pdf.out("dropcap.pdf")


def make_panel_letters():
    """A four-panel figure whose panels are labelled with bold capitals, on
    their own lines, between two paragraphs.

    Bug: "A", "B D" and "C" were emitted as section headings.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    pdf.text_at(margin, 60, "5 Interaction Effects", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 300)], size=10, leading=13)
    paras = paragraphs(2, start=44, step=3, width=4)
    f.paragraph(paras[0], space_after=8)
    y = f.y + 20
    for row, letters in enumerate((("A", "B"), ("C", "D"))):
        for col, letter in enumerate(letters):
            x = margin + 40 + col * 220
            yy = y + row * 150
            pdf.text_at(x + 80, yy - 14, letter, style="B", size=11)
            vector_chart(pdf, x, yy + 18, w=160, h=100)
    pdf.text_at(margin + 20, y + 310, "Figure 2. Predicted adoption by condition, four panels.", size=9)
    f2 = Flow(pdf, [(margin, y + 336, width, 760)], size=10, leading=13)
    f2.paragraph(paras[1], space_after=8)
    pdf.out("panel_letters.pdf")


def make_garbled_font():
    """A page of ordinary prose whose fonts carry a scrambled ToUnicode map:
    it renders cleanly and extracts as nonsense. Built with fpdf2, then each
    font is given a CMap that sends every letter to a different letter.

    Bug: the nonsense was emitted as the page's text.
    """
    pdf = Doc()
    margin, width = 72.0, LETTER_W - 144
    pdf.add_page()
    pdf.text_at(margin, 60, "2 Theory", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=11, leading=14)
    for para in paragraphs(3, start=0, step=6, width=4):
        f.paragraph(para, space_after=8, hyphenate=False)
    doc = pymupdf.open(stream=bytes(pdf.output()), filetype="pdf")
    import string
    lower, upper = string.ascii_lowercase, string.ascii_uppercase
    pairs = []
    for alphabet in (lower, upper):
        for i, ch in enumerate(alphabet):
            pairs.append((ord(ch), ord(alphabet[(i * 7 + 11) % 26])))
    body = "\n".join(f"<{src:02X}> <{dst:04X}>" for src, dst in pairs)
    cmap = (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<00> <FF>\nendcodespacerange\n"
        f"{len(pairs)} beginbfchar\n{body}\nendbfchar\n"
        "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    ).encode("ascii")
    for font in doc[0].get_fonts():
        xref = doc.get_new_xref()
        doc.update_object(xref, "<<>>")
        doc.update_stream(xref, cmap)
        doc.xref_set_key(font[0], "ToUnicode", f"{xref} 0 R")
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "garbled_font.pdf"
    doc.save(str(path), garbage=0, deflate=True, no_new_id=True)
    doc.close()
    print(f"wrote {path.relative_to(HERE.parent.parent)}  ({path.stat().st_size} bytes)")


def make_watermark():
    """Two pages of prose with a large diagonal "RETIRED" drawn across each
    page as real text at 45 degrees (a Word/Acrobat watermark), plus a small
    ruled table.

    Bug: the rotated glyphs were kept as text and seeded fake table columns
    and stray one-letter cells; the word itself leaked into the output.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(8, start=5, step=4, width=4)
    for pg in range(2):
        pdf.add_page()
        pdf.text_at(margin, 30, "Protocol for Something, version 2", style="I", size=9)
        f = Flow(pdf, [(margin, 72, width, 740)], size=10, leading=13)
        if pg == 0:
            pdf.text_at(margin, 72, "1 Scope", style="B", size=14)
            f.y = 98
        f.paragraph(paras[4 * pg], space_after=8)
        f.paragraph(paras[4 * pg + 1], space_after=8)
        # A ruled table across the middle of the page, where the diagonal
        # watermark crosses it, on both pages: page 1 short cells, page 2
        # tall wrapped cells (the shape that makes the grid sweep give up and
        # fall back to PyMuPDF's own cell text).
        f.y = max(f.y + 4, 330)
        if pg == 0:
            rows = [["Metric", "2025", "2026", "2027"],
                    ["Share of renewable electricity", "80%", "84%", "88%"],
                    ["Minimum coverage", "67%", "67%", "67%"],
                    ["Reporting frequency", "annual", "annual", "annual"]]
            y = ruled_table(pdf, margin, f.y, [200, 60, 60, 60], rows, row_h=22)
        else:
            rows = [["Criterion", "Requirement", "Assessment"],
                    ["C1 Boundary", "All subsidiaries must be reported and included within "
                     "the parent company inventory in accordance with the chosen "
                     "consolidation approach.", "Met if all included"],
                    ["C2 Gases", "All relevant gases required by the protocol must be "
                     "covered; exclusions must be justified and stay below five "
                     "percent of the inventory.", "Met if none excluded"],
                    ["C3 Scopes", "At least one target covering scope 1 and scope 2 must "
                     "be submitted, combined or separate, when each is above the "
                     "exclusion threshold.", "Met if both covered"]]
            y = wrapped_table(pdf, margin, f.y, [110, 220, 138], rows)
        f.y = y + 12
        f.paragraph(paras[4 * pg + 2], space_after=8)
        f.paragraph(paras[4 * pg + 3], space_after=8)
        # the watermark: 110 pt light grey text rotated 45 degrees about the
        # page centre, drawn after the body as Word does
        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Helvetica", "B", 110)
        w = pdf.get_string_width("RETIRED")
        with pdf.rotation(45, LETTER_W / 2, LETTER_H / 2):
            pdf.text(LETTER_W / 2 - w / 2, LETTER_H / 2 + 35, "RETIRED")
        pdf.set_text_color(0, 0, 0)
        pdf.centered(752, str(pg + 1), size=9)
    pdf.out("watermark.pdf")


def make_bold_bullets():
    """Body text at 9 pt (a table-heavy document's median) and a bulleted list
    set in 10 pt bold, the way a compliance document emphasises its criteria.

    Bug: the bullets were larger than the body size and bold, so _is_heading
    promoted each of them to a section heading.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(6, start=9, step=4, width=4)
    pdf.add_page()
    pdf.text_at(margin, 60, "C16 - Absolute targets", style="B", size=12)
    f = Flow(pdf, [(margin, 84, width, 740)], size=9, leading=11.5)
    for k in range(3):
        f.paragraph(paras[k], space_after=6)
    f.skip(4)
    pdf.set_font("Times", "B", 10)
    pdf.set_xy(margin, f.y)
    pdf.cell(width, 12, "Criterion met if:")
    f.y += 14
    items = ["Company is in compliance with criterion C16. AND",
             "The ambition is at a minimum aligned with the 1.5\u00b0C threshold. OR",
             "For base years after 2020 the reduction meets the minimum value"]
    for it in items:
        pdf.set_font("Times", "B", 10)
        pdf.set_xy(margin + 10, f.y)
        pdf.cell(width - 10, 12.5, "\u2022 " + it)
        f.y += 19  # Word space-after: each bullet is its own block
    f.skip(8)
    for k in range(3, 6):
        f.paragraph(paras[k], space_after=6)
    pdf.out("bold_bullets.pdf")


def make_images_inline():
    """A page whose first drawing operation is a full-page raster background,
    with prose and a small raster (an equation pasted as a picture) between
    two paragraphs.

    Bug: without --images the equation image vanished with no trace, and with
    --images the page-sized background was extracted as a figure.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(4, start=13, step=4, width=4)
    pdf.add_page()
    # full-page background: a very light gradient
    bg = pymupdf.open()
    pg = bg.new_page(width=306, height=396)
    sh = pg.new_shape()
    for i in range(16):
        g = 0.97 - 0.03 * i / 16
        sh.draw_rect(pymupdf.Rect(0, i * 396 / 16, 306, (i + 1) * 396 / 16))
        sh.finish(color=None, fill=(g, g, 1.0))
    sh.commit()
    pdf.image(io.BytesIO(pg.get_pixmap(dpi=72, alpha=False).tobytes("png")),
              x=0, y=0, w=LETTER_W, h=LETTER_H)
    bg.close()
    # a second decoration: a page-HEIGHT strip down the left edge (Word splits
    # some page backgrounds into vertical bands; each is far under 90% of
    # the page area but spans its full height)
    strip = pymupdf.open()
    sp = strip.new_page(width=30, height=396)
    ssh = sp.new_shape()
    ssh.draw_rect(pymupdf.Rect(0, 0, 30, 396))
    ssh.finish(color=None, fill=(0.85, 0.9, 1.0))
    ssh.commit()
    pdf.image(io.BytesIO(sp.get_pixmap(dpi=72, alpha=False).tobytes("png")),
              x=0, y=0, w=60, h=LETTER_H)
    strip.close()
    pdf.text_at(margin, 60, "2 Model", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=6)
    f.paragraph("The forward-looking adjustment is given by the following formula:",
                space_after=8)
    # the "formula": a small raster drawn by PyMuPDF (text rendered to pixels)
    eq = pymupdf.open()
    ep = eq.new_page(width=240, height=44)
    ep.insert_text((8, 30), "A = A0 - (NZA - RTD) / (2050 - Y)", fontsize=18, fontname="tiro")
    png = ep.get_pixmap(dpi=144, alpha=False).tobytes("png")
    eq.close()
    pdf.image(io.BytesIO(png), x=(LETTER_W - 240) / 2, y=f.y, w=240, h=44)
    f.y += 44 + 8
    # the journal's caption style: label in capitals on its own line, the
    # title below it, no punctuation after the number
    pdf.centered(f.y, "FIGURE 1", style="B", size=9)
    pdf.centered(f.y + 11, "Forward-Looking Adjustment as Printed", style="B", size=9)
    f.y += 34
    f.paragraph("Figure 1 shows the adjustment as the source printed it.", space_after=6)
    f.paragraph("Where A0 is the minimum ambition before adjustment.", space_after=6)
    f.paragraph(paras[1], space_after=6)
    f.paragraph(paras[2], space_after=6)
    pdf.out("images_inline.pdf")


def make_figure_dedup():
    """Two figures that were each marked wrongly before 1e7af01.

    Page 1: a chart drawn as paths over its own raster export (a plotting
    library's fallback image), with an axis title and a legend line standing
    between the chart and its caption in the stream. Bug: one placeholder
    for the region with "caption: none found" and a second for the caption.

    Page 2: a ruled table directly above a figure caption, the figure itself
    a diagram of text boxes. Bug: the table took the caption and the figure
    had no placeholder at all.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(4, start=23, step=3, width=4)
    pdf.add_page()
    pdf.text_at(margin, 60, "3 Results", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=10)
    cx, cy, cw, ch = margin + 90, f.y + 10, 260, 150
    # the raster export first, the paths on top of it
    exp = pymupdf.open()
    ep = exp.new_page(width=cw, height=ch)
    sh = ep.new_shape()
    for i, v in enumerate((0.35, 0.62, 0.48, 0.81, 0.57)):
        bw = cw / 10
        sh.draw_rect(pymupdf.Rect(bw * (2 * i + 0.6), ch - ch * v, bw * (2 * i + 1.5), ch))
        sh.finish(color=None, fill=(0.8, 0.85, 0.95))
    sh.commit()
    pdf.image(io.BytesIO(ep.get_pixmap(dpi=72, alpha=False).tobytes("png")),
              x=cx, y=cy, w=cw, h=ch)
    exp.close()
    vector_chart(pdf, cx, cy, w=cw, h=ch)
    pdf.centered(cy + ch + 16, "Condition", size=8)
    pdf.centered(cy + ch + 30, "Bars show means; whiskers omitted", size=8)
    pdf.centered(cy + ch + 52, "Figure 1 Adoption by Condition", style="B", size=9)
    f.y = cy + ch + 80
    f.paragraph("Figure 1 shows adoption rising with each condition.", space_after=6)
    f.paragraph(paras[1], space_after=6)

    pdf.add_page()
    pdf.text_at(margin, 60, "4 Process", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    f.paragraph(paras[2], space_after=10)
    rows = [["Stage", "Actors", "Outcome"],
            ["Entry", "Founders", "Charter"],
            ["Growth", "Managers", "Routines"],
            ["Reform", "Boards", "Audit"]]
    y = ruled_table(pdf, margin + 60, f.y, [110, 110, 110], rows)
    pdf.centered(y + 14, "Figure 2 Process Model of Adoption", style="B", size=9)
    by = y + 40
    pdf.set_line_width(0.6)
    for i, label in enumerate(("Entry pressures", "Internal debate", "Adopted practice")):
        bx = margin + 20 + i * 150
        pdf.rect(bx, by, 120, 34, style="D")
        pdf.text_at(bx + 14, by + 12, label, size=9)
        if i < 2:
            pdf.line(bx + 120, by + 17, bx + 150, by + 17)
    pdf.set_line_width(0.2)
    f.y = by + 60
    f.paragraph(paras[3], space_after=6)
    pdf.out("figure_dedup.pdf")


CAPTION_TABLE_ROWS = [
    ["Variable", "Hybrid A", "Business", "Hybrid B", "Charity"],
    ["Intent", "5.16", "4.91", "5.19", "5.40"],
    ["Cognitive", "4.64", "4.66", "4.43", "4.41"],
    ["Moral", "5.64", "5.35", "5.62", "5.89"],
]


def make_caption_inside_table():
    """A booktabs table under a running-head rule, its two-line caption set
    tight above the header so that both arrive in one extraction block, a
    note below the bottom rule, and a boxed diagram with labels under that.

    Bug (R02611 p. 18): the candidate ran from the running-head rule to the
    bottom of the diagram box. The caption became the header row, split over
    the columns, and the diagram labels became the last rows of the table.
    The caption has no punctuation after its number.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(2, start=31, step=3, width=4)
    pdf.add_page()
    pdf.text_at(margin, 40, "412", size=10)
    pdf.right(40, "Journal of Fixtures 12(3)", size=10)
    pdf.set_line_width(0.25)
    pdf.line(margin, 56, margin + width, 56)
    y = 70
    pdf.text_at(margin, y, "Table 1 Study 1 Descriptive Statistics of Model Variables by", size=9)
    pdf.text_at(margin, y + 10, "Experimental Condition", size=9)
    col_w = [108, 90, 90, 90, 90]
    bottom = booktabs_table(pdf, margin, y + 22, col_w, CAPTION_TABLE_ROWS, size=9, row_h=11)
    pdf.text_at(margin, bottom + 4, "Note. Means on a seven-point scale.", size=8)
    # the diagram: a frame, three nodes, two coefficients
    top = bottom + 26
    pdf.set_line_width(0.5)
    pdf.rect(margin, top, width, 110, style="D")
    for label, bx, by in (("Hybrid", margin + 30, top + 66), ("Legitimacy", margin + 190, top + 14),
                          ("Transact", margin + 350, top + 66)):
        pdf.rect(bx, by, 90, 30, style="D")
        pdf.text_at(bx + 22, by + 9, label, size=8)
    pdf.line(margin + 120, top + 72, margin + 190, top + 40)
    pdf.line(margin + 280, top + 40, margin + 350, top + 72)
    pdf.line(margin + 120, top + 86, margin + 350, top + 86)
    pdf.text_at(margin + 130, top + 46, ".003", size=7)
    pdf.text_at(margin + 320, top + 46, ".087", size=7)
    pdf.text_at(margin + 222, top + 88, ".019", size=7)
    pdf.set_line_width(0.2)
    pdf.text_at(margin, top + 116, "Figure 1. Effects of Hybrid on Intent to Transact.", size=9)
    f = Flow(pdf, [(margin, top + 140, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=6)
    f.paragraph("Table 1 reports the means by condition.", space_after=6)
    f.paragraph(paras[1], space_after=6)
    pdf.out("caption_inside_table.pdf")


BIB_ENTRIES = [
    ("* ", "Alder, J. A., & Succi, M. J. 1996. Determinants of profound change:",
     "Choice of conversion or closure. Fixture Quarterly, 41: 507-529."),
    ("", "Ames, P. M. 1955. The dynamics of bureaucracy: A study of two",
     "agencies. Chicago: Fixture Press."),
    ("*\u2020 ", "Barre, I., & Fuller, C. 2006. To conform or to perform? Mimetic",
     "behaviour and performance. Journal of Fixtures, 43: 1559-1581."),
    ("\u2020 ", "Baum, J. A. C. 1997. Competitive and institutional isomorphism in",
     "populations. Working paper, Fixture School of Management."),
    ("", "Bijl, T. H. A., & Pieters, R. G. M. 2001. Meta-analysis when studies",
     "contain multiple measurements. Fixture Letters, 12: 157-169."),
    ("* ", "Chuang, Y., & Thomson, K. 2004. Diversity and similarity of form in",
     "nursing homes. Fixture Science, 15: 120-135."),
    ("*\u2020 ", "Deep, D. L., & Carter, S. M. 2005. An examination of differences",
     "between legitimacy and reputation. Journal of Fixtures, 42: 329-360."),
    ("\u2020 ", "Edel, L. B. 1992. Legal ambiguity and symbolic structures.",
     "American Journal of Fixtures, 97: 1531-1576."),
    ("", "Frank, D. J. 2000. The nation-state and the natural environment.",
     "Fixture Review, 65: 96-116."),
    ("*\u2020 ", "Glynn, M. A., & Abzug, R. 2002. Institutionalizing identity:",
     "Symbolic isomorphism and names. Fixture Journal, 45: 267-280."),
    ("* ", "Goes, J. B., & Park, S. H. 1997. Interorganizational links and",
     "innovation: The case of hospital services. Fixture Journal, 40: 673-696."),
    ("\u2020 ", "Han, S. 1994. Mimetic isomorphism and its effect on the audit",
     "services market. Social Fixtures, 73: 637-664."),
    ("", "Hunt, J. E. 2004. Methods of meta-analysis: Correcting error and bias",
     "in research findings. Thousand Oaks: Fixture."),
    ("*\u2020 ", "Korn, H. J., & Baum, J. A. C. 1999. Chance, imitative, and",
     "strategic antecedents of competition. Fixture Journal, 42: 171-193."),
    ("* ", "Kraatz, M. S., & Moore, J. H. 2002. Executive migration and",
     "institutional change. Fixture Journal, 45: 120-143."),
    ("\u2020 ", "Lu, J. W. 2002. Intra- and inter-organizational imitative behaviour.",
     "Journal of Fixture Studies, 33: 19-37."),
    ("*\u2020 ", "Oliver, C. 1997. The influence of institutional and task environment",
     "relationships on performance. Journal of Fixtures, 34: 99-124."),
    ("* ", "Rao, H., Greve, H. R., & Davis, G. F. 2001. Fool's gold: Social proof",
     "in the initiation of coverage. Fixture Quarterly, 46: 502-526."),
    ("\u2020 ", "Zajac, E. J., & Kraatz, M. S. 1993. A diametric forces model of",
     "strategic change. Fixture Journal, 14: 83-102."),
]


def make_bibliography_symbols():
    """Page 1: prose with a genuine star footnote. Page 2: a reference list
    whose heading carries a raised "a", entries marked with stars and
    daggers down to the foot of the page, and the legend that explains the
    marks.

    Bug (R00315 pp. 18-25): every marked entry in the lower part of a page
    is in small type, in the footnote zone, and opens with a footnote
    symbol. 36 references were emitted as the notes [^*], [^\u2020] and
    [^*\u2020] and moved to the end of their page. The star footnote on
    page 1 must survive.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(4, start=41, step=3, width=4)
    # a page of body text first: the reference list is long, and without it
    # the document's body size would be the size of its references
    pdf.add_page()
    pdf.text_at(margin, 60, "1 Scope", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 720)], size=10, leading=13)
    for para in paragraphs(9, start=5, step=2, width=4):
        f.paragraph(para, space_after=8)
    pdf.add_page()
    pdf.text_at(margin, 60, "2 Sample", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 640)], size=10, leading=13)
    f.paragraph(paras[0], space_after=8)
    f.paragraph("The sample was drawn from both collections and coded twice. "
                + paras[1], space_after=8, sup_refs={"twice": "*"})
    f.paragraph(paras[2], space_after=8)
    y = 690
    pdf.set_line_width(0.4)
    pdf.line(margin, y - 6, margin + 90, y - 6)
    pdf.note_label(margin, y, "*", 8.5, 10)
    Flow(pdf, [(margin, y, width, y + 30)], size=8.5, leading=10).paragraph(
        "We thank the editor and two reviewers for their comments on the coding.",
        indent=7, hyphenate=False)

    pdf.add_page()
    pdf.set_font("Times", "B", 10)
    w = pdf.get_string_width("REFERENCES")
    x = (LETTER_W - w) / 2
    pdf.text_at(x, 60, "REFERENCES", style="B", size=10)
    pdf.sup(x + w, 60, "a", size=10)
    y = 84
    for marks, first, second in BIB_ENTRIES:
        pdf.text_at(margin, y, marks + first, size=9)
        pdf.text_at(margin + 18, y + 11, second, size=9)
        y += 11 * 2 + 9
    pdf.note_label(margin + 10, 706, "a", 8.5, 10)
    pdf.text_at(margin + 16, 706, "Studies marked with an asterisk were included in the first "
                "sample; those with a dagger, in the second.", size=8.5)
    pdf.out("bibliography_symbols.pdf")


def make_manuscript_numcol():
    make_manuscript("manuscript_numcol.pdf", number_column=True)


def make_hard_footer_first():
    make_hard("hard_footer_first.pdf", footer_first=True)


def make_footnote_biglabel():
    make_footnote_repro("footnote_biglabel.pdf", big_label=True)


def make_all_text_wrapped():
    """The same all-text table with and without rules, including sparse wraps.

    A span-rich continuation in two columns must not become a new record;
    a percentage within prose must stay with its owner. Short and tall rows
    alternate, with unique words for checking loss, duplication, and cells.
    """
    pdf = Doc()
    rows = [
        [["Record", "Requirement", "Assessment"]],
        [["Alpha", "Include the whole reporting boundary", "Accepted"],
         ["", "and retain every subsidiary without", ""],
         ["", "dropping any exception from the account.", "Review continues"]],
        [["Beta", "Report the short independent entry.", "Pending"]],
        [["Gamma", "Cover at least 7% of relevant activity", "Reviewed"],
         ["", "without treating the percentage as a new row.", ""],
         ["", "Publish all checks and name their owners.", ""]],
        [["Delta", "Keep the final independent record.", "Complete"]],
    ]
    for ruled in (True, False):
        pdf.add_page()
        pdf.text_at(72, 90, "All-text inventory: " + ("ruled" if ruled else "unruled"),
                    style="B", size=14)
        y = 160
        xs = [72, 192, 412]
        widths = [120, 220, 128]
        for r, lines in enumerate(rows):
            height = len(lines) * 12 + (2 if ruled else 0)
            if ruled:
                for x, width in zip(xs, widths):
                    pdf.rect(x, y, width, height)
            for i, cells in enumerate(lines):
                for x, cell in zip(xs, cells):
                    if cell:
                        # A vertically centered key must not pull the first
                        # requirement line back into the preceding row.
                        offset = 12 if ruled and cell == "Gamma" else 0
                        pdf.text_at(x + 3, y + i * 12 + offset, cell,
                                    style="B" if r == 0 else "", size=9)
            y += height
    pdf.out("all_text_wrapped.pdf")


def make_isolated_ocr_page():
    """OCR provenance on isolated raster pages, without requiring page markers.

    Includes digital prose, a raster copyright notice, a truly blank page,
    and a scanned table. The notice is visible content, not a blank page.
    """
    pdf = Doc()
    pdf.add_page()
    pdf.text_at(72, 90, "Digital introduction", style="B", size=14)
    pdf.text_at(72, 130, "This page has a text layer and does not require recognition.", size=12)

    def raster_page(source):
        with pymupdf.open(stream=bytes(source.output()), filetype="pdf") as doc:
            png = doc[0].get_pixmap(dpi=144).tobytes("png")
        pdf.add_page()
        pdf.image(io.BytesIO(png), x=0, y=0, w=LETTER_W, h=LETTER_H)

    notice = Doc()
    notice.add_page()
    notice.text_at(72, 120, "Copyright of the Example Research Society.", size=14)
    notice.text_at(72, 150, "Readers may print this notice for individual use.", size=14)
    raster_page(notice)
    pdf.add_page()  # no marks, no text layer

    table = Doc()
    table.add_page()
    table.text_at(72, 90, "Scanned inventory", size=14)
    ruled_table(table, 72, 140, [156, 156, 156], [
        ["Product", "Quantity", "Location"],
        ["Apples", "120", "North"],
        ["Pears", "240", "South"],
        ["Plums", "360", "West"],
    ], size=12, row_h=32)
    raster_page(table)
    pdf.out("isolated_ocr_page.pdf")


def make_table_only_footer():
    """Tables must establish body bounds for repeated textual footers.

    The footer is drawn first, as in SBTi. The third page has a unique
    margin note that must survive, rather than repetition evidence.
    """
    pdf = Doc()
    for n, label in enumerate(("Alpha", "Beta", "Gamma")):
        pdf.add_page()
        footer = "Protocol validation edition" if n < 2 else "Unique margin observation"
        pdf.text_at(72, 745, footer, size=9)
        ruled_table(pdf, 72, 200, [156, 156, 156], [
            ["Category", "Description", "Assessment"],
            [label, "Inventory boundary", "Included"],
            [label + " revised", "Reported exclusions", "Reviewed"],
            [label + " final", "Published account", "Accepted"],
        ], row_h=28)
    pdf.out("table_only_footer.pdf")


def make_tall_cell():
    """A bordered three-column table whose middle column wraps over three to
    four lines per row, between two prose paragraphs, with no watermark.

    Bug: the grid reconstruction wins over PyMuPDF's geometric cells and keeps
    only the first line of each wrapped cell; the rest of the cell text is
    silently dropped. The text-loss guard makes the cell text win instead.
    """
    pdf = Doc()
    margin = 72.0
    width = LETTER_W - 2 * margin
    paras = paragraphs(3, start=17, step=4, width=4)
    pdf.add_page()
    pdf.text_at(margin, 60, "4 Requirements", style="B", size=14)
    f = Flow(pdf, [(margin, 86, width, 740)], size=10, leading=13)
    f.paragraph(paras[0], space_after=10)
    rows = [["Criterion", "Requirement", "Assessment"],
            ["C1 Boundary", "All subsidiaries must be reported and included within "
             "the parent company inventory in accordance with the chosen "
             "consolidation approach, and any exclusion must be justified.",
             "Met if all included"],
            ["C2 Gases", "All relevant gases required by the protocol must be "
             "covered; exclusions must be justified and stay below five "
             "percent of the inventory and target boundary.",
             "Met if none excluded"],
            ["C3 Scopes", "At least one target covering scope 1 and scope 2 must "
             "be submitted, combined or separate, when each is above the "
             "exclusion threshold of five percent.",
             "Met if both covered"]]
    y = wrapped_table(pdf, margin, f.y, [110, 220, 138], rows)
    f.y = y + 12
    f.paragraph(paras[1], space_after=8)
    f.paragraph(paras[2], space_after=8)
    pdf.out("tall_cell.pdf")


MAKERS = {
    "hard": make_hard,
    "repro": make_repro,
    "repro_tight": make_repro_tight,
    "footnote_repro": make_footnote_repro,
    "manuscript": make_manuscript,
    "hard_footer_first": make_hard_footer_first,
    "manuscript_numcol": make_manuscript_numcol,
    "footnote_biglabel": make_footnote_biglabel,
    "footnote_bold_wrapped": make_footnote_bold_wrapped,
    "watermark": make_watermark,
    "bold_bullets": make_bold_bullets,
    "images_inline": make_images_inline,
    "bibliography_symbols": make_bibliography_symbols,
    "figure_dedup": make_figure_dedup,
    "caption_inside_table": make_caption_inside_table,
    "garbled_font": make_garbled_font,
    "panel_letters": make_panel_letters,
    "dropcap": make_dropcap,
    "pi_minus": make_pi_minus,
    "table_legend": make_table_legend,
    "ebsco_notice_scan": make_ebsco_notice_scan,
    "rotated_pages": make_rotated_pages,
    "provenance_pages": make_provenance_pages,
    "tall_cell": make_tall_cell,
    "table_only_footer": make_table_only_footer,
    "isolated_ocr_page": make_isolated_ocr_page,
    "all_text_wrapped": make_all_text_wrapped,
    "scanned": make_scanned,      # last: depends on hard.pdf
    "scanned_with_stamp": make_scanned_with_stamp,
    "justified_scan": make_justified_scan,
}


def main(argv):
    names = argv or list(MAKERS)
    unknown = [n for n in names if n not in MAKERS]
    if unknown:
        sys.exit(f"unknown fixture(s): {', '.join(unknown)}; choose from {', '.join(MAKERS)}")
    for n in MAKERS:            # dictionary order keeps scanned after hard
        if n in names:
            MAKERS[n]()


if __name__ == "__main__":
    main(sys.argv[1:])
