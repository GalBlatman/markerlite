"""Mechanical module split from the v0.1.14 implementation."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from .api import convert
from .figures import apply_figures, apply_math
from .paths import ManifestPathError, manifest_target
from .stats import summarize


def _version() -> str:
    # Import lazily: package initialization imports this module.
    from . import __version__

    return __version__


def main() -> None:
    # Never let console encoding take the batch down: on a Windows cp1252
    # console a single non-encodable character in a filename or summary
    # raised UnicodeEncodeError after the first file and stopped the run.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, AttributeError):  # pragma: no cover
                pass
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("-o", "--outdir", default="md_out")
    ap.add_argument(
        "--images",
        action="store_true",
        help="extract figures (embedded rasters and vector drawings)",
    )
    ap.add_argument(
        "--flag-math",
        action="store_true",
        help="crop equation regions for visual transcription",
    )
    ap.add_argument(
        "--flag-figures",
        action="store_true",
        help="crop every figure to <stem>_figures/ with a manifest, "
        "for description by a vision model",
    )
    ap.add_argument(
        "--page-markers",
        action="store_true",
        help="emit <!-- page N --> markers at each page boundary",
    )
    ap.add_argument(
        "--apply-math",
        metavar="JSON",
        help="splice transcribed LaTeX from a filled-in manifest "
        "back into the matching .md, then exit",
    )
    ap.add_argument(
        "--apply-figures",
        metavar="JSON",
        help="put the descriptions of a filled-in figure manifest "
        "under the matching placeholders in the .md, then exit",
    )
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    if args.apply_figures or args.apply_math:
        mpath = pathlib.Path(args.apply_figures or args.apply_math)
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            sys.exit(f"markerlite: cannot read manifest {mpath}: {exc}")
        if args.apply_figures:
            stem = (
                manifest.get("stem")
                if isinstance(manifest, dict) and manifest.get("stem")
                else re.sub(r"_figures$", "", mpath.stem)
            )
        else:
            stem = manifest.get("stem") if isinstance(manifest, dict) else None
        # The manifest is untrusted: its stem may only name a file directly
        # in --outdir (markerlite/paths.py).
        try:
            md = manifest_target(outdir, stem)
        except ManifestPathError as exc:
            sys.exit(f"markerlite: refused: {exc}")
        if not md.is_file():
            sys.exit(f"markerlite: no Markdown file {md} to apply the manifest to")
        if args.apply_figures:
            n = apply_figures(md, mpath)
            print(f"applied {n} figure description(s) to {md}")
        else:
            n = apply_math(md, mpath)
            print(f"applied {n} equation(s) to {md}")
        return

    outdir.mkdir(parents=True, exist_ok=True)
    for p in args.pdfs:
        path = pathlib.Path(p)
        out, manifest = convert(
            path,
            outdir,
            args.images,
            args.flag_math,
            args.page_markers,
            args.flag_figures,
        )
        print(f"{path.name} -> {out}")
        print(f"   {summarize(manifest.get('stats', {}))}")
