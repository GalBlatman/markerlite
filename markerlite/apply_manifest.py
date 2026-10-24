"""Bounded, typed apply manifests and one-pass Markdown replacement."""

from __future__ import annotations

import json
import math
import pathlib
import re
from collections import Counter

from .model import FIGURE_DESCRIPTION_MARK
from .thresholds import APPLY_MAX_MANIFEST_BYTES, APPLY_MAX_MANIFEST_ENTRIES


class ManifestError(ValueError):
    pass


class ManifestLimitError(ManifestError):
    def __init__(self, name, observed, cap):
        super().__init__(f"{name}: {observed} exceeds {cap}; Markdown kept unchanged")
        # Page zero denotes the manifest-wide operation, not a PDF page.
        self.stats = {
            "resource_limits": [
                {
                    "page": 0,
                    "limit": name,
                    "observed": observed,
                    "cap": cap,
                    "action": "manifest refused; Markdown kept unchanged",
                }
            ]
        }


class ApplyManifest(dict):
    """A validated snapshot; CLI passes this on without reading/parsing twice."""

    def __init__(self, source, kind):
        super().__init__(source)
        self.kind = kind


def load_manifest(source, kind):
    if isinstance(source, ApplyManifest) and source.kind == kind:
        return source
    if kind not in {"figures", "math"}:
        raise ManifestError("unknown apply manifest kind")
    if isinstance(source, (str, pathlib.Path)):
        try:
            with pathlib.Path(source).open("rb") as stream:
                data = stream.read(APPLY_MAX_MANIFEST_BYTES + 1)
            if len(data) > APPLY_MAX_MANIFEST_BYTES:
                raise ManifestLimitError(
                    "manifest_bytes", len(data), APPLY_MAX_MANIFEST_BYTES
                )
            raw = json.loads(data.decode("utf-8"))
        except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
            raise ManifestError("manifest is not valid UTF-8 JSON") from exc
    else:
        raw = source
    if kind == "figures" and isinstance(raw, list):
        raw = {"regions": raw}
    if not isinstance(raw, dict) or not isinstance(raw.get("regions"), list):
        raise ManifestError("manifest must be an object with a regions array")
    entries = raw["regions"]
    if len(entries) > APPLY_MAX_MANIFEST_ENTRIES:
        raise ManifestLimitError(
            "manifest_entries", len(entries), APPLY_MAX_MANIFEST_ENTRIES
        )
    if "stem" in raw and not isinstance(raw["stem"], str):
        raise ManifestError("manifest stem must be a string")
    if "stem" in raw:
        try:
            raw["stem"].encode("utf-8")
        except UnicodeError as exc:
            raise ManifestError("manifest stem is not valid UTF-8") from exc
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ManifestError(f"region {index}: expected an object")
        for field in (
            "id",
            "description",
            "latex",
            "caption",
            "image",
            "file",
            "text_layer",
        ):
            if field in entry:
                value = entry[field]
                if not isinstance(value, str):
                    raise ManifestError(f"region {index}: {field} must be a string")
                try:
                    value.encode("utf-8")
                except UnicodeError as exc:
                    raise ManifestError(
                        f"region {index}: {field} is not valid UTF-8"
                    ) from exc
        if "id" in entry and not re.fullmatch(r"[A-Za-z0-9_-]+", entry["id"]):
            raise ManifestError(f"region {index}: invalid id")
        if "page" in entry and (type(entry["page"]) is not int or entry["page"] < 1):
            raise ManifestError(f"region {index}: page must be a positive integer")
        if entry.get("bbox") is not None:
            box = entry["bbox"]
            if (
                not isinstance(box, list)
                or len(box) != 4
                or not all(
                    type(v) in (float, int) and (type(v) is int or math.isfinite(v))
                    for v in box
                )
            ):
                raise ManifestError(
                    f"region {index}: bbox must contain four finite numbers"
                )
        if kind == "math" and entry.get("latex", "").strip() and not entry.get("id"):
            raise ManifestError(f"region {index}: latex requires an id")
        if kind == "figures" and entry.get("description", "").strip():
            match = re.fullmatch(r"fig_p(\d+)_(\d+)", entry.get("id", ""))
            if match and (int(match[1]) < 1 or int(match[2]) < 1):
                raise ManifestError(
                    f"region {index}: figure page and index must be positive"
                )
            if not match and "page" not in entry:
                raise ManifestError(
                    f"region {index}: description requires a page or figure id"
                )
    if not isinstance(source, (str, pathlib.Path)):
        try:
            size = 0
            for piece in json.JSONEncoder().iterencode(raw):
                size += len(piece.encode("utf-8"))
                if size > APPLY_MAX_MANIFEST_BYTES:
                    raise ManifestLimitError(
                        "manifest_bytes", size, APPLY_MAX_MANIFEST_BYTES
                    )
        except (TypeError, RecursionError) as exc:
            raise ManifestError("manifest contains invalid JSON values") from exc
    return ApplyManifest(raw, kind)


_FIGURES = re.compile(
    r"(?P<holder><!-- figure: p\. (?P<page>\d+); caption: .*? -->)"
    + r"(?:\n\n> "
    + re.escape(FIGURE_DESCRIPTION_MARK)
    + r"(?:\n>[^\n]*)*)?",
    re.S,
)
_MATH = re.compile(
    r"\$\$\n(?:(?!\$\$).)*\n\$\$\n\n<!-- markerlite:eq (?P<math_id>[^>\n]+) -->"
    r"|<!-- equation: p\. \d+; set as an image(?:; number [^>\n]*?)? -->\n\n"
    r"(?:!\[\]\([^)\n]*\)\n\n)?<!-- markerlite:eq (?P<picture_id>[^>\n]+) -->",
    re.S,
)


def apply_figures_text(md, manifest):
    descriptions = {}
    multiplicity = Counter()
    fallback_nth = Counter()
    for entry in manifest["regions"]:
        page = entry.get("page")
        match = re.fullmatch(r"fig_p(\d+)_(\d+)", entry.get("id", ""))
        if match:
            page, nth = int(match[1]), int(match[2])
        else:
            fallback_nth[page] += 1
            nth = fallback_nth[page]
        text = entry.get("description", "").strip()
        if text and page is not None:
            descriptions[page, nth] = text
            multiplicity[page, nth] += 1
    seen = Counter()
    applied = 0

    def replace(match):
        nonlocal applied
        page = int(match["page"])
        seen[page] += 1
        key = page, seen[page]
        if key not in descriptions:
            return match[0]
        text = descriptions[key]
        quoted = "\n".join(
            (">" + (" " + line if line.strip() else "")).rstrip()
            for line in text.splitlines()
        )
        applied += multiplicity[key]
        return match["holder"] + "\n\n> " + FIGURE_DESCRIPTION_MARK + "\n" + quoted

    return _FIGURES.sub(replace, md), applied


def apply_math_text(md, manifest):
    latex = {}
    for entry in manifest["regions"]:
        text = entry.get("latex", "").strip()
        if text and entry.get("id"):
            latex.setdefault(entry["id"], text)
    seen = set()
    applied = 0

    def replace(match):
        nonlocal applied
        key = match["math_id"] or match["picture_id"]
        if key not in latex or key in seen:
            return match[0]
        seen.add(key)
        applied += 1
        return "$$\n" + latex[key] + "\n$$"

    return _MATH.sub(replace, md), applied
