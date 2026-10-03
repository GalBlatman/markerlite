"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import replace
from statistics import median
from typing import Callable, Iterable, List, Mapping, Optional, Tuple

import pymupdf

from .model import *


def discover_tesseract(
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[..., str | None] = shutil.which,
    is_file: Callable[[pathlib.Path], bool] | None = None,
    registry_reader: Callable[[], Iterable[str]] | None = None,
) -> str | None:
    """Return the full path to Tesseract using the Windows installer locations."""
    environment = os.environ if env is None else env
    file_exists = pathlib.Path.is_file if is_file is None else is_file

    def full_path(value: str | os.PathLike[str]) -> str | None:
        text = str(value).strip().strip('"')
        if not text:
            return None
        candidate = pathlib.Path(text)
        if file_exists(candidate):
            return str(candidate.resolve())
        found = which(text, path=environment.get("PATH"))
        return str(pathlib.Path(found).resolve()) if found else None

    configured = environment.get("TESSERACT_CMD")
    if configured and (found := full_path(configured)):
        return found
    if found := which("tesseract", path=environment.get("PATH")):
        return str(pathlib.Path(found).resolve())

    def installed_dirs() -> Iterable[str]:
        if registry_reader is not None:
            yield from registry_reader()
            return
        if sys.platform != "win32":
            return
        try:
            import winreg

            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(root, r"SOFTWARE\Tesseract-OCR") as key:
                        value, _kind = winreg.QueryValueEx(key, "InstallDir")
                        if value:
                            yield str(value)
                except OSError:
                    continue
        except ImportError:  # pragma: no cover - only possible on non-Windows Python
            return

    for directory in installed_dirs():
        if found := full_path(pathlib.Path(directory) / "tesseract.exe"):
            return found
    for variable, suffix in (
        ("ProgramFiles", ("Tesseract-OCR",)),
        ("ProgramFiles(x86)", ("Tesseract-OCR",)),
        ("LOCALAPPDATA", ("Programs", "Tesseract-OCR")),
    ):
        base = environment.get(variable)
        if base and (
            found := full_path(pathlib.Path(base).joinpath(*suffix, "tesseract.exe"))
        ):
            return found
    return None


def tesseract_version(
    executable: str, *, run: Callable[..., subprocess.CompletedProcess] = subprocess.run
) -> str:
    """Return Tesseract's first version line for status and diagnostics."""
    try:
        flags = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if sys.platform == "win32"
            else {}
        )
        proc = run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            **flags,
        )
        first = (proc.stdout or proc.stderr).strip().splitlines()
        return first[0].strip() if first else "tesseract (version unknown)"
    except Exception:
        return "tesseract (version unknown)"


def _bbox_of(items) -> Tuple[float, float, float, float]:
    xs0 = min(i[0] for i in items)
    ys0 = min(i[1] for i in items)
    xs1 = max(i[2] for i in items)
    ys1 = max(i[3] for i in items)
    return (xs0, ys0, xs1, ys1)


def oversized_images(page: pymupdf.Page) -> List[tuple]:
    """(xref, width, height) of the page's images whose source holds more
    than FIGURE_IMAGE_MAX_PIXELS pixels. Read from the image dictionaries,
    which costs nothing; decoding is what costs memory."""
    try:
        items = page.get_images(full=True)
    except Exception:
        return []
    return [
        (item[0], item[2], item[3])
        for item in items
        if item[2] * item[3] > FIGURE_IMAGE_MAX_PIXELS
    ]


def text_flags(page: pymupdf.Page, base: int) -> int:
    """Text-extraction flags for ``page``. MuPDF decodes every image when
    image blocks are requested (rawdict and dict ask for them by default);
    the converter never uses those blocks. On a page with an oversized image
    they are not requested, so the image is never decoded."""
    if oversized_images(page):
        return base & ~pymupdf.TEXT_PRESERVE_IMAGES
    return base


def readable_ratio(text: str) -> Tuple[int, float]:
    """(tokens, share of them that are common words or numerals)."""
    tokens = _WORD_TOKEN.findall(text)
    if not tokens:
        return 0, 0.0
    hits = sum(1 for tok in tokens if tok.isdigit() or tok.lower() in _COMMON_WORDS)
    return len(tokens), hits / len(tokens)


def _normalise_rotation(page: pymupdf.Page) -> Tuple[pymupdf.Page, bool]:
    """Return the page with its text upright, and whether it was turned.

    The tilt filter in extract_page drops every line that is not horizontal.
    That is right for a diagonal watermark and wrong for two real layouts,
    which it deleted whole: a page stored with /Rotate 90 (its text is
    vertical in unrotated coordinates although it displays upright), and a
    landscape table printed sideways on a portrait page.
    """
    doc, number = page.parent, page.number
    turned = False
    if page.rotation:
        page.remove_rotation()
        page = doc[number]
        turned = True
    up = down = total = 0
    raw_blocks = page.get_text(
        "rawdict", flags=text_flags(page, pymupdf.TEXTFLAGS_RAWDICT)
    ).get("blocks", [])
    for b in raw_blocks:
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            n = sum(len(sp.get("chars", [])) for sp in ln.get("spans", []))
            total += n
            dx, dy = ln.get("dir", (1.0, 0.0))
            if abs(dx) < ROTATION_AXIS_TOL and dy < -ROTATION_VERTICAL_MIN:
                up += n
            elif abs(dx) < ROTATION_AXIS_TOL and dy > ROTATION_VERTICAL_MIN:
                down += n
    if total >= ROTATION_MIN_CHARS and max(up, down) >= ROTATED_PAGE_MIN_FRAC * total:
        page.set_rotation(90 if up >= down else 270)
        page.remove_rotation()
        page = doc[number]
        turned = True
    return page, turned


def _page_raster_covered(page: pymupdf.Page) -> bool:
    prect = page.rect
    area = max(prect.width * prect.height, 1.0)
    try:
        infos = page.get_image_info()
    except Exception:
        return False
    for info in infos:
        bbox = info.get("bbox")
        if not bbox:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height >= OCR_RASTER_MIN_FRAC * area:
            return True
    return False


def _remap_pi_fonts(pages: List[Page]) -> int:
    """Rewrite the glyphs of pi fonts in place; returns the spans changed."""
    inventory: dict = defaultdict(
        lambda: [0, 0, 0, 0]
    )  # spans, letters, twos, twos-before-number
    for page in pages:
        if page.ocr_used:
            continue
        for blk in page.blocks:
            for ln in blk.lines:
                for i, sp in enumerate(ln.spans):
                    text = sp.text.strip()
                    if not text:
                        continue
                    inv = inventory[sp.font]
                    inv[0] += 1
                    if any(ch.isalpha() for ch in text):
                        inv[1] += 1
                    if text == "2":
                        inv[2] += 1
                        nxt = ln.spans[i + 1] if i + 1 < len(ln.spans) else None
                        if (
                            nxt is not None
                            and nxt.font != sp.font
                            and re.match(r"\s*\.?\d", nxt.text)
                        ):
                            inv[3] += 1
    pi = {
        font
        for font, (n, letters, twos, glued) in inventory.items()
        if n >= PI_FONT_MIN_GLYPHS
        and letters == 0
        and twos >= PI_FONT_MIN_SUSPICIOUS
        and glued >= PI_FONT_MIN_GLUED_SHARE * twos
    }
    changed = 0
    for page in pages:
        if page.ocr_used:
            continue
        for blk in page.blocks:
            for ln in blk.lines:
                for sp in ln.spans:
                    if sp.font in pi and any(ch in PI_FONT_MAP for ch in sp.text):
                        sp.text = "".join(PI_FONT_MAP.get(ch, ch) for ch in sp.text)
                        for c in sp.chars or []:
                            if c.get("c") in PI_FONT_MAP:
                                c["c"] = PI_FONT_MAP[c["c"]]
                        changed += 1
    return changed


def _page_is_image_only(page: pymupdf.Page, native_chars: int, native_lines=()) -> bool:
    """A page-covering raster with, at most, a stamp of native text.

    ``native_lines`` are the rawdict line bboxes. A stamp or citation banner
    sits in the top or bottom margin; a title printed over a decorative
    full-page background (a report cover) sits mid-page and is real text,
    so that page keeps its native layer.
    """
    if native_chars >= OCR_MAX_NATIVE_CHARS:
        return False
    prect = page.rect
    for x0, y0, x1, y1 in native_lines:
        yc = (y0 + y1) / 2 / max(prect.height, 1.0)
        if OCR_STAMP_MARGIN < yc < 1 - OCR_STAMP_MARGIN:
            return False
    area = max(prect.width * prect.height, 1.0)
    try:
        infos = page.get_image_info()
    except Exception:
        return False
    for info in infos:
        bbox = info.get("bbox")
        if not bbox:
            continue
        clip = pymupdf.Rect(bbox) & prect
        if clip.width * clip.height >= OCR_RASTER_MIN_FRAC * area:
            return True
    return False


def ocr_dpi(page: pymupdf.Page, dpi: int = OCR_DPI) -> Tuple[int, int]:
    """(dpi to render at, pixels the page would have at ``dpi``).

    The page is rendered for Tesseract at OCR_DPI. A crafted page can be
    metres wide: its pixel count is computed from the page box before
    anything is rendered, and above OCR_MAX_PIXELS the resolution is lowered
    so that the render stays within the budget."""
    w = page.rect.width * dpi / 72.0
    h = page.rect.height * dpi / 72.0
    pixels = int(w) * int(h)
    if pixels <= OCR_MAX_PIXELS:
        return dpi, pixels
    lowered = int(dpi * math.sqrt(OCR_MAX_PIXELS / pixels))
    return max(lowered, 1), pixels


def _ocr_page(page: pymupdf.Page, page_idx: int, dpi: int = OCR_DPI) -> Optional[Page]:
    """OCR stand-in for surya's recognition model.

    Marker's OCR path gives the recognizer line boxes and gets back text plus
    geometry. Tesseract's TSV output has the same shape - block/paragraph/line
    grouping with per-word boxes - so the rest of the pipeline (reading order,
    heading sizes, tables) keeps working on scanned pages. ``--psm 1`` turns on
    Tesseract's own page segmentation, which is what keeps a two-column scan
    from interleaving.
    """
    import tempfile

    try:
        executable = discover_tesseract()
        if executable is None:
            return None
        requested = dpi
        dpi, pixels = ocr_dpi(page, dpi)
        pix = page.get_pixmap(dpi=dpi)
        with tempfile.TemporaryDirectory() as td:
            img = pathlib.Path(td) / "page.png"
            pix.save(img)
            tsv_path = pathlib.Path(td) / "page.tsv"
            with open(tsv_path, "wb") as tsv_file:
                proc = subprocess.run(
                    [
                        executable,
                        str(img),
                        "stdout",
                        "--psm",
                        str(OCR_PSM),
                        "-c",
                        "preserve_interword_spaces=1",
                        "tsv",
                    ],
                    stdout=tsv_file,
                    stderr=subprocess.DEVNULL,
                    timeout=OCR_TIMEOUT_SECONDS,
                )
            # Tesseract's output is written to a file and at most
            # OCR_MAX_TSV_BYTES of it are read, cut at a line end.
            tsv_size = tsv_path.stat().st_size
            with open(tsv_path, "rb") as fh:
                data = fh.read(OCR_MAX_TSV_BYTES)
            if tsv_size > OCR_MAX_TSV_BYTES:
                data = data[: data.rfind(b"\n") + 1]
            tsv = data.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            return None
    except Exception as exc:  # pragma: no cover
        print(f"  ! OCR failed on page {page_idx + 1}: {exc}", file=sys.stderr)
        return None

    scale = 72.0 / dpi
    rows = [r.split("\t") for r in tsv.splitlines()[1:] if r.strip()]
    grouped: dict = defaultdict(list)
    order: List[tuple] = []
    recognised = 0
    for r in rows:
        if len(r) < 12 or r[0] != "5":  # level 5 = word
            continue
        try:
            conf = float(r[10])
        except ValueError:
            continue
        text = r[11]
        if text.strip():
            recognised += 1
        if conf < OCR_MIN_CONFIDENCE or not text.strip():
            continue
        # TSV level-5 columns are level,page,block,par,line,word - group by
        # (block, par, line); including word_num would make every word a line.
        key = (int(r[2]), int(r[3]), int(r[4]))
        if key not in grouped:
            order.append(key)
        left, top, w, h = (float(r[6]), float(r[7]), float(r[8]), float(r[9]))
        grouped[key].append(
            (text, (left * scale, top * scale, (left + w) * scale, (top + h) * scale))
        )

    counter = 0
    blocks_by_par: dict = defaultdict(list)
    par_order: List[tuple] = []
    for key in order:
        words = grouped[key]
        spans = []
        for text, bbox in words:
            spans.append(
                Span(
                    text=text + " ",
                    bbox=bbox,
                    size=round(bbox[3] - bbox[1], 1),
                    font="OCR",
                    flags=0,
                    char_pos=counter,
                )
            )
            counter += 1
        line = Line(
            spans=spans,
            bbox=_bbox_of([s.bbox for s in spans]),
            char_pos=spans[0].char_pos,
        )
        par_key = key[:2]  # block, paragraph
        if par_key not in blocks_by_par:
            par_order.append(par_key)
        blocks_by_par[par_key].append(line)

    blocks = []
    for par_key in par_order:
        lines = blocks_by_par[par_key]
        blocks.append(
            Block(
                lines=lines,
                bbox=_bbox_of([ln.bbox for ln in lines]),
                page_idx=page_idx,
                char_pos=lines[0].char_pos,
            )
        )

    result = Page(
        page_idx=page_idx,
        width=page.rect.width,
        height=page.rect.height,
        blocks=blocks,
        ocr_used=True,
        source_words=recognised,
    )
    if dpi != requested:
        note_limit(
            result,
            "ocr_pixels",
            pixels,
            OCR_MAX_PIXELS,
            f"page rendered for OCR at {dpi} dpi instead of {requested}",
        )
    if tsv_size > OCR_MAX_TSV_BYTES:
        note_limit(
            result,
            "ocr_tsv_bytes",
            tsv_size,
            OCR_MAX_TSV_BYTES,
            "recognised text cut at the cap",
        )
    return result


def _attach_drop_caps(blocks: List[Block]) -> int:
    """Put a drop capital back on the front of its paragraph.

    A drop cap is one capital letter set two or three lines tall beside the
    paragraph's opening lines. In the stream it is its own line, often ahead
    of the paragraph or after the heading above, so the heading gained a stray
    letter ("Strategy T") and the paragraph lost its first ("s part of a
    broader movement"). The cap is attached to the line that starts beside
    it, at its top, with a lowercase letter; without such a line it is left
    alone (the spaced letters of "A R T I C L E" are not drop caps).
    """
    sizes = [
        sp.size for b in blocks for ln in b.lines for sp in ln.spans if sp.text.strip()
    ]
    if not sizes:
        return 0
    body = median(sizes)
    attached = 0
    for blk in list(blocks):
        for ln in list(blk.lines):
            text = ln.text.strip()
            if len(text) != 1 or not text.isalpha() or not text.isupper():
                continue
            if max(sp.size for sp in ln.spans) < DROP_CAP_MIN_SCALE * body:
                continue
            x0, y0, x1, y1 = ln.bbox
            best = None
            for other in blocks:
                for cand in other.lines:
                    if cand is ln or not cand.spans:
                        continue
                    cx0, cy0, _cx1, cy1 = cand.bbox
                    ctext = cand.text.lstrip()
                    if (
                        ctext[:1].islower()
                        and y0 - 4 <= cy0 <= y1
                        and x1 - 3 <= cx0 <= x1 + 40
                        and (best is None or cy0 < best.bbox[1])
                    ):
                        best = cand
            if best is None:
                continue
            first = best.spans[0]
            best.spans[0] = replace(first, text=text + first.text.lstrip())
            blk.lines.remove(ln)
            attached += 1
        if not blk.lines and blk in blocks:
            blocks.remove(blk)
    return attached


def _mark_fill_backed_banners(pmpage: pymupdf.Page, blocks: List[Block]) -> None:
    """Mark text drawn inside a wide dark band for late page-local placement.

    Placement waits until tables, continuations, and figures are settled so
    the exception cannot change any structural decision.
    """
    try:
        drawings = pmpage.get_drawings()
    except Exception:
        return
    bands = []
    for drawing in drawings:
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        if not fill or not rect:
            continue
        box = pymupdf.Rect(rect)
        luma = sum(fill[:3]) / 3
        if (
            box.width >= BANNER_MIN_PAGE_WIDTH * pmpage.rect.width
            and luma <= BANNER_FILL_MAX_LUMA
        ):
            bands.append(box)
    for band in bands:
        candidates = []
        for block in blocks:
            box = pymupdf.Rect(block.bbox)
            overlap = box & band
            if overlap.is_empty:
                continue
            if overlap.get_area() >= BANNER_TEXT_OVERLAP * max(box.get_area(), 1):
                candidates.append(block)
        for block in candidates:
            block.fill_backed_banner = True


def place_fill_backed_banners(pages: List[Page]) -> None:
    """Place marked banners geometrically without sorting any other block."""
    for page in pages:
        for block in [b for b in page.blocks if b.fill_backed_banner]:
            old_index = page.blocks.index(block)
            target = next(
                (
                    index
                    for index, other in enumerate(page.blocks)
                    if other is not block
                    and not other.ignore_for_output
                    and other.y_start >= block.y_end
                ),
                old_index,
            )
            if target >= old_index:
                continue
            page.blocks.pop(old_index)
            page.blocks.insert(target, block)


def extract_page(
    page: pymupdf.Page,
    page_idx: int,
    ocr_if_empty: bool = True,
    max_line_tilt: float = MAX_LINE_TILT,
) -> Page:
    """Blocks in PDF character-stream order.

    Marker orders text-layer pages by pdftext character position rather than by
    its learned reading-order head ("the PDF's own character stream is the most
    reliable reading-order signal ... it beat surya's learned order head on
    multi-column pages" - builders/line.py). PyMuPDF's unsorted rawdict
    preserves that same stream order, so the enumeration index below is the
    direct equivalent of pdftext's ``span.minimum_position``.
    """
    ocr_used = False
    page, derotated = _normalise_rotation(page)
    raw = page.get_text("rawdict", flags=text_flags(page, pymupdf.TEXTFLAGS_RAWDICT))
    text_len = sum(
        len(c.get("c", ""))
        for b in raw.get("blocks", [])
        for ln in b.get("lines", [])
        for s in ln.get("spans", [])
        for c in s.get("chars", [])
    )
    native_lines = [
        tuple(ln["bbox"])
        for b in raw.get("blocks", [])
        if b.get("type") == 0
        for ln in b.get("lines", [])
    ]
    image_only = _page_is_image_only(page, text_len, native_lines)
    raster_covered = image_only or _page_raster_covered(page)
    n_tokens, readable = readable_ratio(page.get_text())
    garbled = n_tokens >= GARBLE_MIN_TOKENS and readable < GARBLE_MIN
    if ocr_if_empty and (text_len < OCR_MIN_NATIVE_CHARS or image_only or garbled):
        ocr_page = _ocr_page(page, page_idx)
        if ocr_page is not None:
            ocr_page.garbled = garbled
            ocr_page.readable = readable
            ocr_page.image_only = image_only
            ocr_page.raster_covered = raster_covered
            ocr_page.derotated = derotated
            return ocr_page

    counter = 0
    suppressed = []
    blocks: List[Block] = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        lines: List[Line] = []
        for ln in b.get("lines", []):
            # Rotated text is never body text: a diagonal "DRAFT"/"RETIRED"
            # watermark kept as a line seeds fake table columns and leaks
            # one-letter cells. rawdict gives each line its writing direction;
            # anything not near-horizontal is dropped here, before any
            # processor sees it.
            direction = ln.get("dir", (1.0, 0.0))
            # Orthogonal words in a scan's native layer are printed content
            # (often a sideways table), not a diagonal overlay watermark.
            scan_orthogonal = (
                raster_covered
                and len(direction) == 2
                and abs(direction[0]) <= max_line_tilt
            )
            if (
                len(direction) == 2
                and abs(direction[1]) > max_line_tilt
                and not scan_orthogonal
            ):
                text = "".join(
                    "".join(c.get("c", "") for c in sp.get("chars", []))
                    or sp.get("text", "")
                    for sp in ln.get("spans", [])
                )
                if text.strip():
                    suppressed.append(
                        {
                            "page": page_idx + 1,
                            "bbox": list(ln["bbox"]),
                            "text": text,
                            "reason": "tilt_filter",
                        }
                    )
                continue
            spans: List[Span] = []
            for s in ln.get("spans", []):
                chars = s.get("chars", [])
                text = "".join(c.get("c", "") for c in chars) or s.get("text", "")
                if not text:
                    continue
                spans.append(
                    Span(
                        text=text,
                        bbox=tuple(s["bbox"]),
                        size=s.get("size", 0.0),
                        font=s.get("font", ""),
                        flags=s.get("flags", 0),
                        char_pos=counter,
                        chars=chars,
                    )
                )
                counter += 1
            if not spans:
                continue
            lines.append(
                Line(
                    spans=spans,
                    bbox=tuple(ln["bbox"]),
                    char_pos=spans[0].char_pos,
                )
            )
        if not lines:
            continue
        blocks.append(
            Block(
                lines=lines,
                bbox=tuple(b["bbox"]),
                page_idx=page_idx,
                char_pos=lines[0].char_pos,
            )
        )

    _attach_drop_caps(blocks)
    _mark_fill_backed_banners(page, blocks)
    return Page(
        page_idx=page_idx,
        width=page.rect.width,
        height=page.rect.height,
        blocks=blocks,
        suppressed=suppressed,
        ocr_used=ocr_used,
        image_only=image_only,
        raster_covered=raster_covered,
        derotated=derotated,
        source_words=len(page.get_text().split()),
        garbled=garbled,
        readable=readable if n_tokens >= GARBLE_MIN_TOKENS else 1.0,
    )


def _lines_of(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]


def detect_provenance(doc) -> Tuple[dict, set, List[str]]:
    """Find aggregator cover pages and banners by their boilerplate.

    Returns ``(drop_pages, drop_lines, comments)``: page indices to leave out
    entirely, exact native line texts to drop wherever they occur, and one
    HTML comment per detection carrying the citation the page supplied (title,
    source line, DOI or stable URL), so the provenance survives the removal.
    """
    drop_pages: dict = {}
    drop_lines: set = {_RG_FOOTER}
    comments: List[str] = []
    for idx in range(len(doc)):
        text = doc[idx].get_text()
        lines = _lines_of(text)
        if not lines:
            continue
        flat = re.sub(r"\s+", " ", text)
        if _EBSCO_PHRASE in flat and len(flat) < 700:
            comments.append(_ebsco_comment(flat))
            drop_pages[idx] = "EBSCOhost"
            continue
        if sum(ph in flat for ph in _WRAP_PHRASES) >= 2:
            cite = [ln for ln in lines if ln.startswith("Manuscript version")]
            for i, ln in enumerate(lines):
                if ln.startswith("Persistent WRAP URL"):
                    url = ln.split(":", 1)[1].strip() or (
                        lines[i + 1] if i + 1 < len(lines) else ""
                    )
                    cite.append("Persistent WRAP URL: " + url.strip())
            licence = re.search(r"\(CC [A-Z-]+ [\d.]+\)", flat)
            if licence:
                cite.append(licence.group(0).strip("()"))
            comments.append(
                f"<!-- source: WRAP (University of Warwick); {'; '.join(cite)} -->"
            )
            drop_pages[idx] = "WRAP"
            continue
        if any(ph in text for ph in _JSTOR_PHRASES):
            # Title is the first line; the citation is the labelled lines.
            cite = [lines[0]] + [ln for ln in lines[1:] if _JSTOR_CITE.match(ln)]
            comments.append(f"<!-- source: JSTOR; {'; '.join(cite)} -->")
            drop_pages[idx] = "JSTOR"
            continue
        if any(ph in text for ph in _RG_PHRASES):
            # Title is everything between the "See discussions" line and the
            # "Article in <journal> · <date>" line; then the DOI line.
            start = next((i for i, ln in enumerate(lines) if _RG_PHRASES[0] in ln), -1)
            art = next((i for i, ln in enumerate(lines) if _RG_CITE.match(ln)), None)
            title = " ".join(lines[start + 1 : art]) if art is not None else ""
            cite = [t for t in (title, lines[art] if art is not None else "") if t]
            cite += [ln for ln in lines if ln.upper().startswith("DOI")]
            comments.append(f"<!-- source: ResearchGate; {'; '.join(cite)} -->")
            drop_pages[idx] = "ResearchGate"
            continue
        if _SAGE_HOST.search(text) and (
            _SAGE_DOWNLOADED in text or _SAGE_COLLECTIONS in text
        ):
            # The stamp is one visual line in three native pieces ("Downloaded
            # from ", "oss.sagepub.com", " at SAGE Publications on ..."); drop
            # each piece, and record the host and download line once.
            pieces = [
                ln
                for ln in lines
                if _SAGE_HOST.search(ln)
                or ln.startswith(_SAGE_DOWNLOADED)
                or ln.startswith("at ")
                or _SAGE_COLLECTIONS in ln
            ]
            drop_lines.update(pieces)
            if not any(c.startswith("<!-- source: SAGE") for c in comments):
                host = _SAGE_HOST.search(text).group(0)
                # "at <institution> on <date>" follows the host, either in
                # the same line or in the next native piece.
                # The native pieces may arrive in any order (SAGE emits
                # them right-to-left), so look for the "at ..." piece first
                # and only then for "at ..." after the host in a merged line.
                at_piece = next(
                    (ln for ln in pieces if ln.lower().startswith("at ")), None
                )
                if at_piece is None:
                    stamp = " ".join(ln for ln in pieces if _SAGE_COLLECTIONS not in ln)
                    tail = stamp.split(host, 1)[1] if host in stamp else ""
                    m_at = re.search(r"\bat\s+(.+)", tail)
                    at_piece = ("at " + m_at.group(1).strip()) if m_at else ""
                at = at_piece
                comments.append(
                    f"<!-- source: SAGE Journals ({host}); downloaded {at} -->".replace(
                        " ;", ";"
                    ).replace("  ", " ")
                )
            continue
        if _PROQUEST_STAMP in text:
            stamp = next(ln for ln in lines if _PROQUEST_STAMP in ln)
            drop_lines.add(stamp)
            pg = next((ln for ln in lines if _PROQUEST_PG.match(ln)), None)
            if pg is not None and (
                "ABI/INFORM" in text or "ProQuest" in text or idx == 0
            ):
                # The banner: every native line up to and including "pg. N"
                # (title, author, journal; date; volume; database).
                banner = []
                for ln in lines:
                    if ln == stamp:
                        continue
                    banner.append(ln)
                    if _PROQUEST_PG.match(ln):
                        break
                drop_lines.update(banner)
                comments.append(f"<!-- source: ProQuest; {'; '.join(banner)} -->")
    return drop_pages, drop_lines, comments


def _ebsco_comment(flat: str) -> str:
    m = _EBSCO_CITE.search(flat)
    if m:
        return (
            f"<!-- source: EBSCOhost; Copyright of {m.group(1).strip()} is the property of "
            f"{m.group(2).strip()} -->"
        )
    return "<!-- source: EBSCOhost -->"


def _drop_ocr_notice(page: Page, provenance: List[str]) -> None:
    """An aggregator notice page delivered as a raster is only recognisable
    after OCR. When a recognised page is nothing but the EBSCO notice, hide
    it and record the source, as detect_provenance does for the native form."""
    if not page.ocr_used:
        return
    flat = re.sub(r"\s+", " ", " ".join(b.text for b in page.blocks))
    squeezed = re.sub(r"[^a-z]", "", flat.lower())
    key = re.sub(r"[^a-z]", "", _EBSCO_PHRASE.lower())
    if key in squeezed and len(flat) < 700:
        for blk in page.blocks:
            _suppress_block(page, blk, "provenance")
        page.raster_covered = False  # nothing to yield: not a low-yield page
        page.source_words = 0  # dropped on purpose: not a lossy page
        comment = _ebsco_comment(flat)
        if not any(c.startswith("<!-- source: EBSCOhost") for c in provenance):
            provenance.append(comment)


def _norm_space(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


class ProvenanceMatcher:
    """Decides whether a line is provenance. Built once per document.

    A line matches when it is one of the exact native stamp lines, or, since
    OCR reads a stamp of several native pieces ("Downloaded from ",
    "oss.sagepub.com", " at ...") as one line, when it is complete pieces run
    together. Substrings or bags of stamp words are not provenance: they also
    match real table glyphs. The run-together pattern used to be rebuilt for
    every line; it is compiled here once. Above PROVENANCE_MAX_PIECES pieces
    it is not built at all (``capped``): exact stamp lines are still dropped,
    joined ones are kept as text, and the document records the limit.
    """

    def __init__(self, drop_lines: set):
        self.lines = drop_lines
        pieces = [re.escape(_norm_space(p)) for p in drop_lines if _norm_space(p)]
        self.pieces = len(pieces)
        self.capped = self.pieces > PROVENANCE_MAX_PIECES
        self.pattern = None
        if pieces and not self.capped:
            piece = "(?:" + "|".join(pieces) + ")"
            self.pattern = re.compile(piece + r"(?:\s+" + piece + ")*")

    def __call__(self, text: str) -> bool:
        t = _norm_space(text)
        if t in self.lines:
            return True
        return bool(self.pattern and self.pattern.fullmatch(t))


def _drop_provenance_lines(
    page: Page, drop_lines: set, matcher: ProvenanceMatcher | None = None
) -> None:
    """Hide blocks made only of provenance lines (see ProvenanceMatcher)."""
    is_prov = matcher or ProvenanceMatcher(drop_lines)
    for blk in page.blocks:
        if blk.lines and all(is_prov(ln.text) for ln in blk.lines):
            _suppress_block(page, blk, "provenance")
