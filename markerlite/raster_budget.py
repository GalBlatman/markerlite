"""Document-scoped decode accounting and bounded device raster geometry."""

from __future__ import annotations

import math
from contextlib import contextmanager
from contextvars import ContextVar

from .cancel import check as check_cancel
from .model import note_limit
from .thresholds import (
    CROP_MAX_DEVICE_SIDE,
    CROP_MAX_PIXELS,
    DOCUMENT_DECODED_BYTES,
    DOCUMENT_MAX_CROP_BYTES,
    DOCUMENT_MAX_CROPS,
)

_CURRENT = ContextVar("raster_budget", default=None)


@contextmanager
def document_raster_budget(cancel=None):
    state = {"decoded": 0, "limits": [], "cancel": cancel, "crops": 0, "crop_bytes": 0}
    token = _CURRENT.set(state)
    try:
        yield state
    finally:
        _CURRENT.reset(token)


def reserve_decode(pm, amount, page_idx=None):
    """Reserve before decoding, including repeat decodes of the same source."""
    state = _CURRENT.get()
    if state is None:
        return True
    observed = state["decoded"] + amount
    if observed > DOCUMENT_DECODED_BYTES:
        state["limits"].append(
            (
                pm.number if page_idx is None else page_idx,
                "document_decoded_bytes",
                observed,
                DOCUMENT_DECODED_BYTES,
                "source image not decoded; placement and source text kept",
            )
        )
        return False
    state["decoded"] = observed
    return True


def reserve_render(pm, page_idx=None):
    """Rendering may decode embedded sources too; reserve before MuPDF runs."""
    return reserve_decode(pm, image_bytes(pm), page_idx)


def image_bytes(pm):
    # Resource dictionaries omit inline images and can list one reused image
    # once. Plain placement metadata does not decode and covers both cases.
    resources = sum(item[2] * item[3] * 4 for item in pm.get_images(full=True))
    placements = sum(
        item["width"] * item["height"] * max(4, item["colorspace"])
        for item in pm.get_image_info()
    )
    return max(resources, placements)


def flush_limits(state, pages):
    lookup = {p.page_idx: p for p in pages}
    for index, name, observed, cap, action in state["limits"]:
        if index in lookup:
            note_limit(lookup[index], name, observed, cap, action)
    state["limits"].clear()


def device_size(rect, dpi):
    dims = (rect.width, rect.height)
    if not all(math.isfinite(v) and v > 0 for v in dims):
        raise ValueError("non-finite or empty raster dimensions")
    if not math.isfinite(dpi) or dpi <= 0:
        raise ValueError("invalid raster resolution")
    # Minimum-clamped point dimensions and rounded-up device dimensions:
    # neither a fractional page side nor truncation can bypass the estimate.
    return tuple(max(1, math.ceil(max(1.0, value) * dpi / 72)) for value in dims)


def crop_pixmap(pm, page, clip, dpi):
    if not can_crop(page):
        return None
    try:
        width, height = device_size(clip, dpi)
    except ValueError:
        note_limit(
            page,
            "crop_geometry",
            "invalid",
            CROP_MAX_DEVICE_SIDE,
            "crop skipped; placeholder and source text kept",
        )
        return None
    ratio = min(
        1.0,
        CROP_MAX_DEVICE_SIDE / max(width, height),
        math.sqrt(CROP_MAX_PIXELS / (width * height)),
    )
    chosen = max(1, int(dpi * ratio))
    w, h = device_size(clip, chosen)
    if max(w, h) > CROP_MAX_DEVICE_SIDE or w * h > CROP_MAX_PIXELS:
        note_limit(
            page,
            "crop_device_side",
            max(width, height),
            CROP_MAX_DEVICE_SIDE,
            "crop skipped; placeholder and source text kept",
        )
        return None
    if chosen != dpi:
        note_limit(
            page,
            "crop_device_side",
            max(width, height),
            CROP_MAX_DEVICE_SIDE,
            f"crop resolution reduced to {chosen} dpi; source text kept",
        )
    if not reserve_render(pm, page.page_idx):
        return None
    return pm.get_pixmap(clip=clip, dpi=chosen)


def checkpoint():
    state = _CURRENT.get()
    if state is not None:
        check_cancel(state["cancel"])


def checked(items):
    for item in items:
        checkpoint()
        yield item


def pending_limit(pm, name, observed, cap, action, page_idx=None):
    state = _CURRENT.get()
    if state is not None:
        state["limits"].append(
            (pm.number if page_idx is None else page_idx, name, observed, cap, action)
        )
        return True
    return False


def can_crop(page):
    state = _CURRENT.get()
    if state is not None and state["crops"] >= DOCUMENT_MAX_CROPS:
        note_limit(
            page,
            "document_crop_count",
            state["crops"] + 1,
            DOCUMENT_MAX_CROPS,
            "crop skipped; placeholder and source text kept",
        )
        return False
    return True


def save_crop(pix, path, page):
    """Check total bytes before any disk write; PNG encoding is unchanged."""
    if not can_crop(page):
        return False
    data = pix.tobytes("png")
    state = _CURRENT.get()
    if state is not None:
        observed = state["crop_bytes"] + len(data)
        if observed > DOCUMENT_MAX_CROP_BYTES:
            note_limit(
                page,
                "document_crop_bytes",
                observed,
                DOCUMENT_MAX_CROP_BYTES,
                "crop not written; placeholder and source text kept",
            )
            return False
    try:
        path.write_bytes(data)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    if state is not None:
        state["crops"] += 1
        state["crop_bytes"] += len(data)
    return True
