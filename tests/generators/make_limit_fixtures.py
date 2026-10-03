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


FIXTURES = {"projection": projection}


def main(argv: list[str]) -> None:
    out = pathlib.Path(argv[0] if argv else ".")
    out.mkdir(parents=True, exist_ok=True)
    for make in FIXTURES.values():
        print("wrote", make(out))


if __name__ == "__main__":
    main(sys.argv[1:])
