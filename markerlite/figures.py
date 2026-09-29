"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import json
import pathlib
import re
from typing import List, Optional, Tuple

import pymupdf

from .classification import body_font_size
from .extraction import _bbox_of
from .model import *
from .render import block_text
from .tables import _overlap_frac


def _prepare_figure_zones(pm, page):
    # Include the label apron around detected artwork; axis labels often sit
    # just outside the raster/path box. This only protects source text.
    pad = 0.04 * page.height
    ypad = 0.01 * page.height
    page.figure_cores = [
        box
        for _, _, _, box in _figure_regions(pm, page)
        if not any(_overlap_frac(box, t) > 0.5 for t in page.table_zones)
    ]
    page.figure_zones = [
        (x0 - pad, y0 - ypad, x1 + pad, y1 + ypad)
        for x0, y0, x1, y1 in page.figure_cores
    ]
    for block in page.blocks:
        if not FIGURE_LABEL.match(block.text.strip()):
            continue
        box = _locate_caption_figure(pm, page, block.bbox)
        if box:
            page.figure_cores.append(box)
            page.figure_zones.append(
                tuple(pymupdf.Rect(box) + (-pad, -ypad, pad, ypad))
            )
            continue
        if not page.raster_covered:
            continue
        # A caption on a page-sized scan has no separate image bounding box.
        # A nearby run of short labels, including three numeric ticks, supplies
        # a text-layer extent. Stop at paragraph-sized text; no OCR vocabulary.
        for below in (True, False):
            candidates = [
                b
                for b in page.blocks
                if b is not block
                and (
                    (b.y_start >= block.y_end) if below else (b.y_end <= block.y_start)
                )
            ]
            candidates.sort(key=lambda b: b.y_start, reverse=not below)
            taken = []
            edge = block.y_end if below else block.y_start
            for b in candidates:
                gap = b.y_start - edge if below else edge - b.y_end
                if gap > 0.07 * page.height or len(b.text.split()) > 12:
                    break
                taken.append(b)
                edge = max(edge, b.y_end) if below else min(edge, b.y_start)
            ticks = sum(
                bool(re.fullmatch(r"[−-]?\d+(?:\.\d+)?", ln.text.strip()))
                for b in taken
                for ln in b.lines
            )
            if ticks >= 3:
                box = _bbox_of([b.bbox for b in taken])
                page.figure_cores.append(box)
                page.figure_zones.append(box)


def _attach_figure_source_text(pages):
    for page in pages:
        figures = [
            b for b in page.blocks if b.btype == "Figure" and not b.ignore_for_output
        ]
        for zone, core in zip(page.figure_zones, page.figure_cores):
            if not figures:
                continue
            figure = min(
                figures, key=lambda f: abs((f.y_start + f.y_end) - (zone[1] + zone[3]))
            )
            for block in page.blocks:
                if (
                    block.ignore_for_output
                    or block.btype in ("Figure", "Table", "Caption", "Footnote")
                    or any(block is c for f in figures for c in f.children)
                ):
                    continue
                contained = sum(
                    _overlap_frac(ln.bbox, zone) > 0.5 for ln in block.lines
                )
                if (
                    not block.lines
                    or contained < 0.8 * len(block.lines)
                    or any(len(ln.text.split()) > 12 for ln in block.lines)
                ):
                    continue
                kept = []
                for line in block.lines:
                    inside = _overlap_frac(line.bbox, core) > 0.5
                    small = max(
                        (sp.size for sp in line.spans), default=0
                    ) < 0.9 * body_font_size([page])
                    if _overlap_frac(line.bbox, zone) > 0.5 and (inside or small):
                        if line.text.strip():
                            figure.figure_text.append(line.text)
                    else:
                        kept.append(line)
                block.lines = kept
                if kept:
                    block.bbox = _bbox_of([ln.bbox for ln in kept])
            remaining = []
            for record in page.suppressed:
                if (
                    record["reason"] == "tilt_filter"
                    and _overlap_frac(record["bbox"], zone) > 0.5
                ):
                    figure.figure_text.append(record["text"])
                else:
                    remaining.append(record)
            page.suppressed = remaining

        for label in list(page.suppressed):
            if label["reason"] != "tilt_filter" or not FIGURE_LABEL.match(
                label["text"].strip()
            ):
                continue
            if not figures:
                continue
            box = pymupdf.Rect(label["bbox"])

            def gap(other):
                r = pymupdf.Rect(other)
                return max(
                    0, r.x0 - box.x1, box.x0 - r.x1, r.y0 - box.y1, box.y0 - r.y1
                )

            figure = min(figures, key=lambda f: gap(f.bbox))
            if gap(figure.bbox) > FIGURE_CAPTION_REACH * page.height:
                continue
            reach = 2 * min(box.width, box.height)
            for record in list(page.suppressed):
                if record["reason"] == "tilt_filter" and gap(record["bbox"]) <= reach:
                    figure.figure_text.append(record["text"])
                    page.suppressed.remove(record)


def _insert_pos(page: Page, y0: float) -> float:
    """Reading-order position for a graphic at vertical offset ``y0``.

    Figures used to be appended with char_pos 1e9, which parked every one of
    them at the end of its page - after the caption that introduced it and after
    the following paragraph. A graphic has no characters, so it has no stream
    position of its own; the honest stand-in is the position of the first text
    block that starts at or below it, minus a hair, so the figure lands just
    above that block.
    """
    below = [b for b in page.blocks if b.y_start >= y0 - 2]
    if below:
        return min(b.char_pos for b in below) - 0.5
    return max((b.char_pos for b in page.blocks), default=0) + 0.5


def _vector_regions(
    pmpage: pymupdf.Page,
    min_items=FIGURE_VECTOR_MIN_SEGMENTS,
    min_side=FIGURE_VECTOR_MIN_SIDE,
):
    """Bounding boxes of vector drawings (charts, diagrams, flowcharts).

    get_image_info only reports embedded rasters. A plotted chart or a drawn
    diagram is neither an image nor text - it is a pile of path operators, and
    was previously extracted as nothing at all. Cluster the paths and treat a
    dense enough cluster as a figure.
    """
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        return []
    rects = [
        pymupdf.Rect(d["rect"])
        for d in drawings
        if d.get("rect")
        and pymupdf.Rect(d["rect"]).width < pmpage.rect.width * FIGURE_PAGE_LINE_FRAC
    ]
    if len(rects) < min_items:
        return []

    clusters: List[list] = []
    for r in rects:
        placed = False
        for cl in clusters:
            merged = pymupdf.Rect(cl[0])
            for other in cl:
                merged |= other
            if merged.intersects(r + (-14, -14, 14, 14)):
                cl.append(r)
                placed = True
                break
        if not placed:
            clusters.append([r])

    out = []
    page_area = pmpage.rect.width * pmpage.rect.height
    for cl in clusters:
        if len(cl) < min_items:
            continue
        box = pymupdf.Rect(cl[0])
        for r in cl:
            box |= r
        if box.width < min_side or box.height < min_side:
            continue
        area = box.width * box.height
        if (
            area > FIGURE_MAX_AREA_FRAC * page_area
            or area < FIGURE_MIN_AREA_FRAC * page_area
        ):
            continue
        out.append(box)
    return out


def _content_images(
    pm: pymupdf.Page,
    min_side: float = FIGURE_IMAGE_MIN_SIDE,
    max_page_frac: float = FIGURE_IMAGE_MAX_PAGE_FRAC,
    span_frac: float = FIGURE_IMAGE_SPAN_FRAC,
) -> List[Tuple[int, int, tuple]]:
    """(index, xref, bbox) of the embedded rasters that are content.

    Two kinds are not: icons (either side under ``min_side`` points) and
    backgrounds. A background covers more than ``max_page_frac`` of the page,
    or spans the page's full height or full width (``span_frac``): Word
    exports a page-sized raster behind every page of some documents, and on
    landscape pages splits it into page-height vertical bands that are each
    well under 90% of the area. None of these is a figure to extract or an
    image worth announcing.
    """
    out = []
    prect = pm.rect
    page_area = max(prect.width * prect.height, 1.0)
    for n, info in enumerate(pm.get_image_info(xrefs=True)):
        xref = info.get("xref", 0)
        bbox = info.get("bbox")
        if not xref or not bbox:
            continue
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w < min_side or h < min_side:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height > max_page_frac * page_area:
            continue
        if (
            clip.height >= span_frac * prect.height
            or clip.width >= span_frac * prect.width
        ):
            continue
        out.append((n, xref, tuple(bbox)))
    return out


def _insert_block(page: Page, blk: Block) -> None:
    """Put a lineless block (figure, marker) in front of the first text block
    that starts at or below it, leaving the rest of the page order alone.

    Sorting the whole page by char_pos looked equivalent but was not:
    proc_footnotes had already moved the notes to the end of the page, and a
    sort pulled them back to their stream position, mid-page.
    """
    y0 = blk.y_start
    for i, b in enumerate(page.blocks):
        if b.lines and b.btype != "Footnote" and b.y_start >= y0 - 2:
            page.blocks.insert(i, blk)
            return
    page.blocks.append(blk)


def _figure_regions(pm: pymupdf.Page, page: Page) -> List[Tuple[str, int, int, tuple]]:
    """(kind, index, xref, bbox) of every figure on the page: embedded rasters
    that are content, then clusters of vector paths that are neither a table
    nor mostly text."""
    found: List[Tuple[str, int, int, tuple]] = [
        ("img", n, xref, bbox) for n, xref, bbox in _content_images(pm)
    ]
    taken = [f[3] for f in found]
    for n, box in enumerate(_vector_regions(pm)):
        bt = tuple(box)
        if any(_overlap_frac(bt, tk) > FIGURE_TABLE_OVERLAP for tk in taken):
            continue  # already captured as a raster
        # A ruled table is also "a pile of path operators". Two tells: it
        # overlaps a detected Table, or the region is mostly text.
        if any(
            b.btype == "Table"
            and _overlap_frac(b.bbox, bt) > FIGURE_RULED_TABLE_OVERLAP
            for b in page.blocks
        ):
            continue
        area = max((bt[2] - bt[0]) * (bt[3] - bt[1]), 1.0)
        text_area = sum(
            _overlap_frac(b.bbox, bt) * b.width * b.height
            for b in page.blocks
            if b.lines
        )
        if text_area / area > FIGURE_MAX_TEXT_DENSITY:
            continue
        found.append(("vec", n, 0, bt))
    return found


def _promote_figure_captions(
    pages: List[Page], max_words: int = FIGURE_CAPTION_MAX_WORDS
) -> int:
    """Relabel a short text block that is a figure caption without a
    delimiter, so it can be attached to its figure or mark one."""
    count = 0
    for page in pages:
        for blk in page.blocks:
            # A bold caption in capitals has usually been taken for a heading.
            if (
                blk.btype not in ("Text", "SectionHeader")
                or blk.ignore_for_output
                or not blk.lines
            ):
                continue
            text = blk.text.strip()
            if len(text.split()) > max_words:
                continue
            m = FIGURE_LABEL.match(text)
            if not m:
                continue
            rest = m.group(3).lstrip()
            first_line_is_label = (
                FIGURE_LABEL.match(blk.lines[0].text.strip()) is not None
                and not FIGURE_LABEL.match(blk.lines[0].text.strip()).group(3).strip()
            )
            if first_line_is_label or not rest or rest[:1].isupper():
                blk.btype = "Caption"
                count += 1
    return count


def _figures_from_captions(pages: List[Page]) -> int:
    """A figure caption that no detected region claimed still marks a figure.

    On a scanned page the figure is part of the page image, and some drawn
    figures are too sparse to cluster; in both cases the caption is the only
    evidence. The placeholder is put where the caption stands, and the
    caption becomes its child like any other.

    A detected region that is still without a caption comes first: axis
    labels and legend text often stand between a chart and its caption in
    the stream, so proc_captions, which looks only at neighbours, misses
    the pair and the figure would be marked twice.
    """
    count = 0
    for page in pages:
        reach = FIGURE_CAPTION_REACH * page.height
        for i, blk in enumerate(list(page.blocks)):
            if blk.btype != "Caption" or blk.ignore_for_output:
                continue
            if not FIGURE_CAPTION.match(blk.text.strip()):
                continue
            best, best_gap = None, reach
            for other in page.blocks:
                if other.btype != "Figure" or other.ignore_for_output:
                    continue
                if any(c.btype == "Caption" for c in other.children):
                    continue
                gap = max(
                    0.0, max(other.y_start, blk.y_start) - min(other.y_end, blk.y_end)
                )
                if gap < best_gap:
                    best, best_gap = other, gap
            if best is not None:
                best.children.append(blk)
                blk.ignore_for_output = True
                continue
            i = page.blocks.index(blk)
            fig = Block(
                lines=[],
                bbox=blk.bbox,
                page_idx=page.page_idx,
                char_pos=blk.char_pos - 0.5,
                btype="Figure",
                figure_kind="cap",
            )
            fig.children.append(blk)
            blk.ignore_for_output = True
            page.blocks.insert(i, fig)
            count += 1
    return count


def _equation_neighbourhood(fig: Block, page: Page) -> Tuple[bool, Optional[Block]]:
    """(is an equation, the text block above) for a raster without caption.

    A picture has no glyphs, so the evidence is around it: an equation number
    alone at the right margin beside it, a "Where:" or a definition line
    under it, or a sentence above it that announces a formula.
    """
    h = page.height or 1.0
    reach = RASTER_EQ_REACH * h
    x0, y0, x1, y1 = fig.bbox
    mid = (y0 + y1) / 2
    texts = [
        b
        for b in page.blocks
        if b.lines
        and not b.ignore_for_output
        and b.btype not in ("Table", "Figure")
        and b.text.strip()
    ]
    above = [
        b for b in texts if b.y_start < y0 and b.y_end <= mid and y0 - b.y_end <= reach
    ]
    below = [b for b in texts if b.y_start >= mid and b.y_start - y1 <= reach]
    upper = max(above, key=lambda b: b.y_end) if above else None
    lower = min(below, key=lambda b: b.y_start) if below else None

    numbered = False
    for b in texts:
        for ln in b.lines:
            cy = (ln.bbox[1] + ln.bbox[3]) / 2
            if (
                y0 - 2 <= cy <= y1 + 2
                and EQ_NUMBER_ALONE.match(ln.text)
                and ln.bbox[0] >= (x0 + x1) / 2
            ):
                numbered = True
                if len(b.lines) == 1:
                    # the number belongs to the equation, not to the prose
                    fig.children.append(b)
    after = bool(lower) and bool(
        EQ_WHERE.match(lower.text) or EQ_DEFINITION.match(lower.text)
    )
    before = bool(upper) and bool(EQ_LEADIN.search(upper.text[-600:]))
    return (numbered or after or before), upper


def _route_raster_equations(pages: List[Page]) -> int:
    """Turn a caption-less picture of a formula from a Figure into an
    Equation, so that it is cropped by --flag-math and not described as a
    figure. It is placed after the sentence that announces it."""
    count = 0
    for page in pages:
        for blk in list(page.blocks):
            if (
                blk.btype != "Figure"
                or blk.figure_kind != "img"
                or blk.ignore_for_output
            ):
                continue
            if any(c.btype == "Caption" for c in blk.children):
                continue
            if blk.height > RASTER_EQ_MAX_HEIGHT * (page.height or 1.0):
                continue
            is_eq, upper = _equation_neighbourhood(blk, page)
            if not is_eq:
                blk.children = [c for c in blk.children if c.btype == "Caption"]
                continue
            blk.btype = "Equation"
            blk.needs_vision = True
            blk.raster_equation = True
            for child in blk.children:
                child.ignore_for_output = True
            if upper is not None and any(upper is b for b in page.blocks):
                page.blocks = [b for b in page.blocks if b is not blk]
                at = next(i for i, b in enumerate(page.blocks) if b is upper)
                blk.char_pos = upper.char_pos + 0.5
                page.blocks.insert(at + 1, blk)
            count += 1
    return count


def place_figures(
    doc, pages: List[Page], outdir: Optional[pathlib.Path] = None, stem: str = ""
) -> int:
    """Put a Figure block at the reading position of every figure.

    This runs whether or not --images was given: a figure that leaves no
    trace reads as if the page had none, and the sentence "as Figure 2
    shows" points at nothing. With ``outdir`` the figure is also saved and
    linked; without it only the placeholder is emitted. Figure interiors are
    never recognised as text.
    """
    imgdir = outdir / f"{stem}_images" if outdir is not None else None
    count = 0
    for page in pages:
        if not page.blocks and not page.source_words:
            continue  # a page dropped as provenance
        pm = doc[page.page_idx]
        for kind, n, xref, bbox in _figure_regions(pm, page):
            path = None
            if imgdir is not None:
                try:
                    imgdir.mkdir(parents=True, exist_ok=True)
                    if kind == "img":
                        pix = pymupdf.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:
                            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                        name = f"page{page.page_idx + 1}_img{n}.png"
                        pix.save(imgdir / name)
                    else:
                        name = f"page{page.page_idx + 1}_vec{n}.png"
                        # Pad: the cluster box hugs the path bounds and clips
                        # stroke width and tick labels just outside.
                        clip = (pymupdf.Rect(bbox) + (-5, -5, 5, 5)) & pm.rect
                        pm.get_pixmap(clip=clip, dpi=200).save(imgdir / name)
                    path = f"{imgdir.name}/{name}"
                except Exception:
                    path = None
            _insert_block(
                page,
                Block(
                    lines=[],
                    bbox=bbox,
                    page_idx=page.page_idx,
                    char_pos=_insert_pos(page, bbox[1]),
                    btype="Figure",
                    image_path=path,
                    figure_kind=kind,
                ),
            )
            count += 1
    return count


def _locate_caption_figure(pm: pymupdf.Page, page: Page, caption) -> Optional[tuple]:
    """The region of a figure that is known from its caption only.

    A diagram of a few boxes and arrows is too sparse to be found as a
    cluster of paths, so its placeholder stands on the caption alone. For a
    crop the region is needed: starting at the caption, the drawings and
    rasters that follow one another closely on one side of it are collected,
    and the side that holds more is the figure. Page frames, rules and
    anything inside a table are left out. None when nothing is there, as on
    a scanned page, where the figure is part of the page image.
    """
    prect = pm.rect
    gap = FIGURE_GROW_GAP * prect.height
    rects = []
    try:
        drawings = pm.get_drawings()
    except Exception:
        drawings = []
    tables = [b.bbox for b in page.blocks if b.btype == "Table"]
    for d in drawings:
        r = d.get("rect")
        if not r:
            continue
        r = pymupdf.Rect(r)
        if r.width >= 0.9 * prect.width or r.height >= 0.9 * prect.height:
            continue  # a page frame
        if r.height < 1.5 and r.width > 0.25 * prect.width:
            continue  # a rule
        if r.width < 1.5 and r.height > 0.25 * prect.height:
            continue
        # Inside a table region only its ruling is left out: strokes made of
        # straight lines. A curve or a filled shape there is a diagram that
        # the table detector took for a grid (Peng 2009 p. 2).
        ruling = d.get("type") == "s" and all(
            it[0] in ("l", "re") for it in d.get("items", [])
        )
        if ruling and any(
            _overlap_frac(tuple(r), t) > FIGURE_RULED_TABLE_OVERLAP for t in tables
        ):
            continue
        rects.append(tuple(r))
    rects += [bbox for _n, _x, bbox in _content_images(pm)]
    if not rects:
        return None
    cx0, cy0, cx1, cy1 = caption

    def grow(below: bool):
        edge = cy1 if below else cy0
        taken, lo, hi = [], edge, edge
        pending = list(rects)
        changed = True
        while changed:
            changed = False
            for r in list(pending):
                if below and r[1] >= cy0 - 1 and r[1] - hi <= gap:
                    pass
                elif not below and r[3] <= cy1 + 1 and lo - r[3] <= gap:
                    pass
                else:
                    continue
                pending.remove(r)
                taken.append(r)
                lo, hi = min(lo, r[1]), max(hi, r[3])
                changed = True
        return taken

    best = max(
        (grow(True), grow(False)),
        key=lambda t: sum((r[2] - r[0]) * (r[3] - r[1]) for r in t),
    )
    if len(best) < 2 and not any(
        r in [b for _n, _x, b in _content_images(pm)] for r in best
    ):
        return None
    box = _bbox_of(best)
    # the labels of the diagram: text that stands inside the region
    inside = [
        b.bbox
        for b in page.blocks
        if b.lines and _overlap_frac(b.bbox, box) > 0.5 and b.btype != "Caption"
    ]
    box = _bbox_of([box] + inside)
    if (box[2] - box[0]) < 40 or (box[3] - box[1]) < 30:
        return None
    return box


def flag_figures(
    doc,
    pages: List[Page],
    outdir: pathlib.Path,
    stem: str,
    dpi=FIGURE_CROP_DPI,
    link: bool = False,
) -> dict:
    """Crop every figure for a description by something that can see.

    markerlite does not read figures. It knows where they are and what their
    captions say; this writes each one as an image with a manifest beside
    it, the way flag_math does for equations. One entry per figure
    placeholder, in the order of the placeholders. With ``link`` (--images
    given as well) the Markdown links to the same crops, so that nothing is
    saved twice.
    """
    figdir = outdir / f"{stem}_figures"
    regions = []
    for page in pages:
        figs = [
            b for b in page.blocks if b.btype == "Figure" and not b.ignore_for_output
        ]
        if not figs:
            continue
        pm = doc[page.page_idx]
        for n, blk in enumerate(figs, 1):
            fig_id = f"fig_p{page.page_idx + 1}_{n}"
            caption = " ".join(
                block_text(c, plain=True) for c in blk.children if c.btype == "Caption"
            ).strip()
            bbox = blk.bbox
            if blk.figure_kind == "cap":
                bbox = _locate_caption_figure(pm, page, blk.bbox)
            entry = {
                "id": fig_id,
                "page": page.page_idx + 1,
                "bbox": [round(v, 1) for v in bbox] if bbox else None,
                "caption": caption,
                "file": "",
                "description": "",  # fill in from the crop, then run --apply-figures
            }
            if bbox:
                figdir.mkdir(parents=True, exist_ok=True)
                # Pad: a region hugs path bounds and clips stroke width and
                # the labels just outside.
                clip = (pymupdf.Rect(bbox) + (-5, -5, 5, 5)) & pm.rect
                name = f"{fig_id}.png"
                pm.get_pixmap(clip=clip, dpi=dpi).save(figdir / name)
                entry["file"] = f"{figdir.name}/{name}"
                if link:
                    blk.image_path = entry["file"]
            else:
                entry["note"] = (
                    "region not located: the figure is known from its caption only"
                )
            regions.append(entry)
    manifest = {"stem": stem, "regions": regions}
    if regions:
        (outdir / f"{stem}_figures.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return manifest


def apply_figures(md_path: pathlib.Path, manifest_path: pathlib.Path) -> int:
    """Put the descriptions of a filled-in figure manifest under the
    placeholders of the matching figures.

    Each description becomes a block quote that opens with
    FIGURE_DESCRIPTION_MARK, so that a reader can tell it from the text of
    the document. Entries without a description are skipped. Applying the
    same manifest again replaces the descriptions, it does not add them a
    second time. Entry ``fig_p<N>_<M>`` belongs to the M-th figure
    placeholder of page N.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("regions", []) if isinstance(manifest, dict) else manifest
    md = md_path.read_text(encoding="utf-8")
    applied = 0
    seen: dict = {}
    for entry in entries:
        page = entry.get("page")
        m = re.match(r"^fig_p(\d+)_(\d+)$", str(entry.get("id") or ""))
        if m:
            page, nth = int(m.group(1)), int(m.group(2))
        else:
            seen[page] = nth = seen.get(page, 0) + 1
        text = (entry.get("description") or "").strip()
        if not text or page is None:
            continue
        holders = list(
            re.finditer(
                r"<!-- figure: p\. " + str(int(page)) + r"; caption: .*? -->", md, re.S
            )
        )
        if nth > len(holders):
            continue
        end = holders[nth - 1].end()
        old = _FIGURE_DESCRIPTION_BLOCK.match(md, end)
        tail = md[old.end() :] if old else md[end:]
        quoted = "\n".join(
            (">" + (" " + ln if ln.strip() else "")).rstrip()
            for ln in text.splitlines()
        )
        md = md[:end] + "\n\n> " + FIGURE_DESCRIPTION_MARK + "\n" + quoted + tail
        applied += 1
    md_path.write_text(md, encoding="utf-8")
    return applied


def flag_math(
    doc,
    pages: List[Page],
    outdir: pathlib.Path,
    stem: str,
    dpi=FIGURE_CROP_DPI,
) -> dict:
    """Render regions no weight-free heuristic can read, for visual transcription.

    Marker sends equation and complex-region crops to surya's LaTeX recognizer.
    With no weights available, the honest substitute is to crop the same regions
    and hand them to a vision model - here, written to disk with a manifest.
    """
    regions = []
    cropdir = outdir / f"{stem}_math"
    for page in pages:
        targets = [b for b in page.blocks if b.needs_vision and not b.ignore_for_output]
        if not targets:
            continue
        cropdir.mkdir(parents=True, exist_ok=True)
        pm = doc[page.page_idx]
        for n, blk in enumerate(targets):
            rect = pymupdf.Rect(blk.bbox) + (-6, -6, 6, 6)
            pix = pm.get_pixmap(clip=rect, dpi=dpi)
            eq_id = f"page{page.page_idx + 1}_eq{n}"
            blk.eq_id = eq_id
            pix.save(cropdir / f"{eq_id}.png")
            regions.append(
                {
                    "id": eq_id,
                    "page": page.page_idx + 1,
                    "image": f"{cropdir.name}/{eq_id}.png",
                    "bbox": [round(v, 1) for v in blk.bbox],
                    "text_layer": blk.text,
                    "latex": "",  # fill in from the crop, then run --apply-math
                }
            )
    manifest = {"stem": stem, "regions": regions}
    if regions:
        (outdir / f"{stem}_math.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def apply_math(md_path: pathlib.Path, manifest_path: pathlib.Path) -> int:
    """Splice transcribed LaTeX back into the markdown, replacing the
    text-layer approximation for each anchored equation."""
    manifest = json.loads(manifest_path.read_text())
    md = md_path.read_text(encoding="utf-8")
    applied = 0
    for region in manifest.get("regions", []):
        latex = (region.get("latex") or "").strip()
        if not latex or not region.get("id"):
            continue
        anchor = re.escape(f"<!-- markerlite:eq {region['id']} -->")
        # (?:(?!\$\$).)* keeps the match from starting at an earlier equation
        # and swallowing the prose in between.
        pattern = re.compile(r"\$\$\n(?:(?!\$\$).)*\n\$\$\n\n" + anchor, re.DOTALL)
        new, n = pattern.subn(lambda _m: f"$$\n{latex}\n$$", md, count=1)
        if not n:
            # An equation set as a picture has a comment where the text-layer
            # approximation would be, and perhaps a link to the saved image.
            pictured = re.compile(
                r"<!-- equation: p\. \d+; set as an image(?:; number [^>\n]*?)? -->\n\n"
                r"(?:!\[\]\([^)\n]*\)\n\n)?" + anchor
            )
            new, n = pictured.subn(lambda _m: f"$$\n{latex}\n$$", md, count=1)
        if n:
            md, applied = new, applied + 1
    md_path.write_text(md, encoding="utf-8")
    return applied
