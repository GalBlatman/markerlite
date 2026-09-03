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
        if pg == 0:
            y = f.y + 4
            rows = [["Metric", "2025", "2026", "2027"],
                    ["Share of renewable electricity", "80%", "84%", "88%"],
                    ["Minimum coverage", "67%", "67%", "67%"]]
            y = ruled_table(pdf, margin, y, [200, 60, 60, 60], rows)
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
    f.y += 44 + 10
    f.paragraph("Where A0 is the minimum ambition before adjustment.", space_after=6)
    f.paragraph(paras[1], space_after=6)
    f.paragraph(paras[2], space_after=6)
    pdf.out("images_inline.pdf")


def make_manuscript_numcol():
    make_manuscript("manuscript_numcol.pdf", number_column=True)


def make_hard_footer_first():
    make_hard("hard_footer_first.pdf", footer_first=True)


def make_footnote_biglabel():
    make_footnote_repro("footnote_biglabel.pdf", big_label=True)


MAKERS = {
    "hard": make_hard,
    "repro": make_repro,
    "repro_tight": make_repro_tight,
    "footnote_repro": make_footnote_repro,
    "manuscript": make_manuscript,
    "hard_footer_first": make_hard_footer_first,
    "manuscript_numcol": make_manuscript_numcol,
    "footnote_biglabel": make_footnote_biglabel,
    "watermark": make_watermark,
    "bold_bullets": make_bold_bullets,
    "images_inline": make_images_inline,
    "scanned": make_scanned,      # last: depends on hard.pdf
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
