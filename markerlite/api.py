"""Mechanical module split from the v0.1.14 implementation."""

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
from html import escape, unescape
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

from .model import *
from .extraction import (
    _drop_ocr_notice,
    _drop_provenance_lines,
    _remap_pi_fonts,
    detect_provenance,
    extract_page,
)
from .tables import detect_tables, propose_tables_from_text
from .classification import body_font_size, classify
from .processors import (
    _protect_numeric_records,
    proc_blockquote,
    proc_captions,
    proc_code,
    proc_continuation,
    proc_footnotes,
    proc_ignore_common,
    proc_line_numbers,
    proc_list_indent,
    proc_marginalia,
    proc_merge_equations,
    proc_reflow,
    proc_section_levels,
)
from .figures import (
    _attach_figure_source_text,
    _figures_from_captions,
    _prepare_figure_zones,
    _promote_figure_captions,
    _route_raster_equations,
    flag_figures,
    flag_math,
    place_figures,
)
from .render import render
from .stats import _emitted_words, content_words


def convert(
    path: pathlib.Path,
    outdir: pathlib.Path,
    images=False,
    do_flag_math=False,
    page_markers=False,
    do_flag_figures=False,
) -> Tuple[pathlib.Path, dict]:
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
            removed = [
                {
                    "page": i + 1,
                    "bbox": list(ln["bbox"]),
                    "text": "".join(sp["text"] for sp in ln["spans"]),
                    "reason": "provenance",
                }
                for block in doc[i].get_text("dict")["blocks"]
                for ln in block.get("lines", [])
            ]
            pages.append(
                Page(
                    page_idx=i,
                    width=doc[i].rect.width,
                    height=doc[i].rect.height,
                    blocks=[],
                    suppressed=removed,
                )
            )
            continue
        p = extract_page(doc[i], i)  # may turn a sideways page upright, in memory
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

    for page in pages:
        if page.blocks or page.source_words:
            _protect_numeric_records(page)
            _prepare_figure_zones(doc[page.page_idx], page)
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
    _attach_figure_source_text(pages)

    manifest = {}
    if do_flag_math:
        manifest = flag_math(doc, pages, outdir, path.stem)
    if do_flag_figures:
        manifest["figures"] = flag_figures(doc, pages, outdir, path.stem, link=images)[
            "regions"
        ]

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
        if (
            p.source_words >= CONSERVATION_MIN_SOURCE
            and emitted < CONSERVATION_MIN * p.source_words
        ):
            lossy.append(
                {"page": p.page_idx + 1, "source": p.source_words, "emitted": emitted}
            )
    manifest["stats"] = {
        "suppressed": [record for page in pages for record in page.suppressed],
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
        "figures_saved": sum(
            1 for p in pages for b in p.blocks if b.btype == "Figure" and b.image_path
        ),
        "equations": len(manifest.get("regions", [])),
        "ocr_pages": sum(1 for p in pages if p.ocr_used),
        "image_only_pages": sum(1 for p in pages if p.image_only),
        "provenance": [
            c.split(";")[0].replace("<!-- source: ", "") for c in provenance
        ],
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
