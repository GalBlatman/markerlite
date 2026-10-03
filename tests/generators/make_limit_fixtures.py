"""Crafted PDFs that trip markerlite's resource limits (tests/REPORT-security.md).

No third-party content: every page is drawn here. The fixtures are generated
at test time into a temporary folder, not committed, because some of them are
large on purpose. Each function returns the path it wrote.

    python tests/generators/make_limit_fixtures.py OUTDIR   # write all of them
"""

from __future__ import annotations

import pathlib
import sys

import pymupdf

BIG = "1" + "0" * 30  # PDF numbers have no exponent notation


def _append(page: pymupdf.Page, ops: str) -> None:
    xref = page.get_contents()[0]
    doc = page.parent
    doc.update_stream(xref, doc.xref_stream(xref) + b"\n" + ops.encode("ascii"))


def _raw_page(doc: pymupdf.Document, ops: str, width=612, height=792) -> pymupdf.Page:
    """A page whose content stream is exactly ``ops``, with Helvetica as /helv."""
    page = doc.new_page(width=width, height=height)
    page.insert_text((0, 0), " ", fontsize=1)  # registers /helv on the page
    xref = page.get_contents()[0]
    doc.update_stream(xref, ops.encode("ascii"))
    return page


def _text(
    x: float, y_top: float, text: str, size: float = 10, height: float = 792
) -> str:
    return f"BT /helv {size} Tf 1 0 0 1 {x} {height - y_top} Tm ({text}) Tj ET"


def projection(out: pathlib.Path) -> pathlib.Path:
    """A column-aligned block, the shape a text-table proposal accepts, whose
    "Beta" row carries one glyph drawn with a 1e30 vertical scale. The glyph's
    box reaches about 5e19 pt above and below the page."""
    doc = pymupdf.open()
    ops = [_text(72, 72, "Results by group", 12)]
    rows = [
        ("Group", "Mean", "SD"),
        ("Alpha", "4.1", "0.9"),
        ("Beta", "3.7", "1.2"),
        ("Gamma", "5.0", "0.8"),
        ("Delta", "2.9", "1.1"),
    ]
    y = 110
    for row in rows:
        for x, cell in zip((72, 220, 320), row):
            ops.append(_text(x, y, cell))
        if row[0] == "Beta":
            ops.append(f"BT /helv 10 Tf 1 0 0 {BIG} 360 {792 - y} Tm (X) Tj ET")
        y += 14
    _raw_page(doc, "\n".join(ops))
    path = out / "limit_projection.pdf"
    doc.save(path)
    return path


def _rules_page(
    out: pathlib.Path, name: str, rows: int, segments_per_row: int
) -> pathlib.Path:
    """A page of horizontal rules between 10% and 90% of its height, each
    row drawn as ``segments_per_row`` touching segments, plus one line of
    text so the page is not empty."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 40), "Ruled page", fontsize=10)
    shape = page.new_shape()
    top, bottom = 0.1 * 792, 0.9 * 792
    step = (bottom - top) / max(rows - 1, 1)
    width = (540 - 72) / segments_per_row
    for r in range(rows):
        y = top + r * step
        for k in range(segments_per_row):
            shape.draw_line((72 + k * width, y), (72 + (k + 1) * width, y))
    shape.finish(color=(0, 0, 0), width=0.3)
    shape.commit()
    path = out / name
    doc.save(path)
    return path


def rule_rows(out: pathlib.Path) -> pathlib.Path:
    """450 full-width rule rows: over TABLE_RULE_ROWS_MAX (400)."""
    return _rules_page(out, "limit_rule_rows.pdf", 450, 1)


def rule_segments(out: pathlib.Path) -> pathlib.Path:
    """100 rule rows of 11 segments each, 1,100 segments: over
    TABLE_RULES_MAX (1000)."""
    return _rules_page(out, "limit_rule_segments.pdf", 100, 11)


def _code_page(out, name, size, indent_pt, width=612):
    """A monospaced block of four lines; the third is indented by
    ``indent_pt``."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=792)
    page.insert_text((72, 60), "Listing", fontsize=12)
    lines = ["def f(x):", "    if x:", "return x", "    return 0"]
    for i, text in enumerate(lines):
        x = 72 + (indent_pt if i == 2 else 0)
        page.insert_text(
            (x, 100 + i * size * 1.4), text, fontsize=size, fontname="cour"
        )
    path = out / name
    doc.save(path)
    return path


def code_tiny_glyphs(out: pathlib.Path) -> pathlib.Path:
    """Courier at 0.3 pt: glyphs 0.18 pt wide, under CODE_MIN_CHAR_WIDTH."""
    return _code_page(out, "limit_code_tiny.pdf", 0.3, 50)


def code_deep_indent(out: pathlib.Path) -> pathlib.Path:
    """Courier at 10 pt on a 4000 pt wide page, one line indented by
    3000 pt: about 500 spaces, over CODE_MAX_INDENT (120)."""
    return _code_page(out, "limit_code_indent.pdf", 10, 3000, width=4000)


def provenance_pieces(out: pathlib.Path) -> pathlib.Path:
    """100 pages, each with a body line and its own SAGE-style download
    stamp: 100 distinct stamp pieces, over PROVENANCE_MAX_PIECES (80). The
    last page also carries two pieces run together on one line, as OCR
    would read them."""
    doc = pymupdf.open()
    for n in range(100):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 100), f"Body text of page {n + 1}.", fontsize=11)
        page.insert_text(
            (72, 770),
            f"Downloaded from fixture.sagepub.com at Library {n} on May {n % 28 + 1}, 2020",
            fontsize=7,
        )
    joined = (
        "Downloaded from fixture.sagepub.com at Library 1 on May 2, 2020 "
        "Downloaded from fixture.sagepub.com at Library 2 on May 3, 2020"
    )
    doc[-1].insert_text((72, 300), joined, fontsize=7)
    path = out / "limit_provenance.pdf"
    doc.save(path)
    return path


FIXTURES = {
    "provenance_pieces": provenance_pieces,
    "code_tiny_glyphs": code_tiny_glyphs,
    "code_deep_indent": code_deep_indent,
    "projection": projection,
    "rule_rows": rule_rows,
    "rule_segments": rule_segments,
}


def main(argv: list[str]) -> None:
    out = pathlib.Path(argv[0] if argv else ".")
    out.mkdir(parents=True, exist_ok=True)
    for make in FIXTURES.values():
        print("wrote", make(out))


if __name__ == "__main__":
    main(sys.argv[1:])
