"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import pathlib
from typing import Optional, Tuple

import pymupdf

from .cancel import CancelToken
from .cancel import check as check_cancel
from .classification import body_font_size, classify
from .extraction import (
    ProvenanceMatcher,
    _drop_ocr_notice,
    _drop_provenance_lines,
    _remap_pi_fonts,
    detect_provenance,
    discover_tesseract,
    extract_page,
    oversized_images,
    place_fill_backed_banners,
    tesseract_version,
    text_flags,
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
from .model import *
from .output import Output
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
from .render import render
from .stats import build_stats
from .table_joins import link_continued_tables
from .tables import detect_tables, propose_tables_from_text


def convert(
    path: pathlib.Path,
    outdir: pathlib.Path,
    images=False,
    do_flag_math=False,
    page_markers=False,
    do_flag_figures=False,
    cancel: Optional[CancelToken] = None,
    grids=False,
) -> Tuple[pathlib.Path, dict]:
    """Convert one PDF. Returns (markdown path, info).

    ``info`` carries ``regions`` (equation crops, when --flag-math ran) and
    ``stats`` (pages, bytes, figures, equations) for reporting.

    ``grids`` defaults to False: tables keep ordered source prose. Pass True
    to opt into reconstructed grids, which require verification before use.

    ``cancel`` (a CancelToken) is checked between pages; a cancel raises
    Cancelled and, like any failure, leaves no output behind.
    """
    out = Output(outdir)
    try:
        md_path, manifest = _convert(
            path,
            out,
            images,
            do_flag_math,
            page_markers,
            do_flag_figures,
            cancel,
            grids,
        )
        out.commit()
    except BaseException:
        # A failure or a cancel leaves no .part behind and the previous
        # complete output as it was (markerlite/output.py).
        out.discard()
        raise
    return md_path, manifest


def _convert(
    path, out, images, do_flag_math, page_markers, do_flag_figures, cancel, grids
):
    outdir = out.outdir
    doc = pymupdf.open(path)
    drop_pages, drop_lines, provenance = detect_provenance(doc)
    pages = []
    provenance_matcher = ProvenanceMatcher(drop_lines)
    for i in range(len(doc)):
        check_cancel(cancel)
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
                for block in doc[i].get_text(
                    "dict", flags=text_flags(doc[i], pymupdf.TEXTFLAGS_DICT)
                )["blocks"]
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
        # may turn a sideways page upright, in memory
        p = extract_page(doc[i], i, cancel=cancel)
        big = oversized_images(doc[i])
        if big:
            note_limit(
                p,
                "image_pixels",
                max(w * h for _x, w, h in big),
                FIGURE_IMAGE_MAX_PIXELS,
                "image not decoded; located by its placement, exported as a page crop",
            )
        # On an OCR'd page the native layer is gone, but Tesseract reads the
        # stamp off the rendered page, so the same texts are dropped there.
        _drop_provenance_lines(p, drop_lines, provenance_matcher)
        _drop_ocr_notice(p, provenance)
        pages.append(p)
    if provenance_matcher.capped and pages:
        note_limit(
            pages[0],
            "provenance_pieces",
            provenance_matcher.pieces,
            PROVENANCE_MAX_PIECES,
            "joined stamp pieces not matched; exact stamp lines still dropped",
        )
    # Glyph repair needs the whole document's font inventory and must happen
    # before tables are built from the characters, so tables come second.
    pi_spans = _remap_pi_fonts(pages)
    for p in pages:
        check_cancel(cancel)
        if p.blocks:
            detect_tables(doc[p.page_idx], p)

    body = body_font_size(pages)
    classify(pages, body)
    propose_tables_from_text(pages)

    for page in pages:
        if page.blocks or page.source_words:
            _protect_numeric_records(page)
            _prepare_figure_zones(doc[page.page_idx], page)
    check_cancel(cancel)
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
    save_here = out if (images and not do_flag_figures) else None
    n_figures = place_figures(doc, pages, save_here, path.stem)
    _promote_figure_captions(pages)
    proc_captions(pages)
    n_figures += _figures_from_captions(pages)
    n_figures -= _route_raster_equations(pages)
    _attach_figure_source_text(pages)
    place_fill_backed_banners(pages)
    if grids:
        link_continued_tables(pages)
    else:
        for page in pages:
            for block in page.blocks:
                if block.btype != "Table" or block.ignore_for_output:
                    continue
                block.grids_disabled = True
                if not block.fallback_paragraphs:
                    block.fallback_paragraphs = [
                        "\n".join(
                            line.text.strip()
                            for line in block.lines
                            if line.text.strip()
                        )
                    ]

    check_cancel(cancel)
    manifest = {}
    if do_flag_math:
        manifest = flag_math(doc, pages, out, path.stem)
    if do_flag_figures:
        manifest["figures"] = flag_figures(doc, pages, out, path.stem, link=images)[
            "regions"
        ]

    # Version is conversion metadata, kept beside rather than inside the
    # hash-locked public stats dictionary.
    from . import __version__

    manifest["version"] = __version__
    tesseract = discover_tesseract()
    manifest["tesseract"] = {
        "path": tesseract,
        "version": tesseract_version(tesseract) if tesseract else None,
    }

    check_cancel(cancel)
    md = render(pages, page_markers=page_markers)
    if provenance:
        md = "\n".join(provenance) + "\n\n" + md
    out.file(f"{path.stem}.md").write_text(md, encoding="utf-8")
    manifest["stats"] = build_stats(
        pages, md, manifest, provenance, pi_spans, n_figures
    )
    doc.close()
    return outdir / f"{path.stem}.md", manifest
