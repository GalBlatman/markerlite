"""Document-scoped decode accounting and bounded device raster geometry."""

from __future__ import annotations

import math
from contextlib import contextmanager
from contextvars import ContextVar

from .model import note_limit
from .thresholds import CROP_MAX_DEVICE_SIDE, CROP_MAX_PIXELS, DOCUMENT_DECODED_BYTES

_CURRENT = ContextVar("raster_budget", default=None)


@contextmanager
def document_raster_budget():
    state = {"decoded": 0, "limits": []}
    token = _CURRENT.set(state)
    try:
        yield state
    finally:
        _CURRENT.reset(token)


def reserve_decode(pm, amount):
    """Reserve before decoding, including repeat decodes of the same source."""
    state = _CURRENT.get()
    if state is None:
        return True
    observed = state["decoded"] + amount
    if observed > DOCUMENT_DECODED_BYTES:
        state["limits"].append(
            (
                pm.number,
                "document_decoded_bytes",
                observed,
                DOCUMENT_DECODED_BYTES,
                "source image not decoded; placement and source text kept",
            )
        )
        return False
    state["decoded"] = observed
    return True


def image_bytes(pm):
    # Four decoded channels conservatively cover RGB/CMYK source images.
    return sum(item[2] * item[3] * 4 for item in pm.get_images(full=True))


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
    return pm.get_pixmap(clip=clip, dpi=chosen)
