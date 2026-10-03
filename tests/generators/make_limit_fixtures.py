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


FIXTURES = {
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
