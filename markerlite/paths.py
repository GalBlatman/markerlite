"""Path confinement for the files a manifest names.

A figure or math manifest is a JSON file that a person or a model has filled
in. Its ``stem`` names the Markdown file that ``--apply-figures`` and
``--apply-math`` rewrite. The manifest is untrusted input: a stem such as
``../notes`` or ``C:\\Users\\x\\report`` would point the rewrite outside the
output folder. Both commands therefore resolve the target through
``manifest_target``, which accepts only a plain file name inside ``--outdir``.
"""

from __future__ import annotations

import pathlib
import re

# A drive ("C:"), a separator of either kind, or a control character.
_FORBIDDEN = re.compile(r"[\\/:\x00-\x1f\x7f]")


class ManifestPathError(ValueError):
    """The manifest names a target outside the output folder."""


def plain_stem(stem: object) -> str:
    """Return ``stem`` if it is a plain file name, else raise.

    Rejected: anything that is not a non-empty string; "." and ".."; any
    path separator, forward or back (so absolute, relative, UNC and mixed
    forms all fail); a colon (drive letters, alternate data streams); control
    characters; leading or trailing white space or dots, which Windows
    silently strips and which would make the name ambiguous.
    """
    if not isinstance(stem, str) or not stem:
        raise ManifestPathError("the manifest's stem is missing or not a string")
    if stem in (".", "..") or _FORBIDDEN.search(stem):
        raise ManifestPathError(
            f"the manifest's stem {stem!r} is not a plain file name"
        )
    if stem != stem.strip() or stem.endswith("."):
        raise ManifestPathError(
            f"the manifest's stem {stem!r} has leading or trailing spaces or dots"
        )
    return stem


def manifest_target(outdir: pathlib.Path, stem: object) -> pathlib.Path:
    """The Markdown file ``<outdir>/<stem>.md``, confined to ``outdir``.

    The stem is checked as a plain name first; the resolved target must then
    sit directly in the resolved output folder, which also defeats a link or
    junction planted in its place.
    """
    name = plain_stem(stem) + ".md"
    root = pathlib.Path(outdir).resolve()
    target = (root / name).resolve()
    if target.parent != root:
        raise ManifestPathError(
            f"the manifest's target {name!r} resolves outside the output folder {root}"
        )
    return target
