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

from .api import convert
from .figures import apply_figures, apply_math
from .stats import summarize

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
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("-o", "--outdir", default="md_out")
    ap.add_argument("--images", action="store_true",
                    help="extract figures (embedded rasters and vector drawings)")
    ap.add_argument("--flag-math", action="store_true",
                    help="crop equation regions for visual transcription")
    ap.add_argument("--flag-figures", action="store_true",
                    help="crop every figure to <stem>_figures/ with a manifest, "
                         "for description by a vision model")
    ap.add_argument("--page-markers", action="store_true",
                    help="emit <!-- page N --> markers at each page boundary")
    ap.add_argument("--apply-math", metavar="JSON",
                    help="splice transcribed LaTeX from a filled-in manifest "
                         "back into the matching .md, then exit")
    ap.add_argument("--apply-figures", metavar="JSON",
                    help="put the descriptions of a filled-in figure manifest "
                         "under the matching placeholders in the .md, then exit")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    if args.apply_figures:
        mpath = pathlib.Path(args.apply_figures)
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        stem = manifest["stem"] if isinstance(manifest, dict) and manifest.get("stem") \
            else re.sub(r"_figures$", "", mpath.stem)
        md = outdir / (stem + ".md")
        print(f"applied {apply_figures(md, mpath)} figure description(s) to {md}")
        return
    if args.apply_math:
        mpath = pathlib.Path(args.apply_math)
        md = outdir / (json.loads(mpath.read_text())["stem"] + ".md")
        print(f"applied {apply_math(md, mpath)} equation(s) to {md}")
        return

    outdir.mkdir(parents=True, exist_ok=True)
    for p in args.pdfs:
        path = pathlib.Path(p)
        out, manifest = convert(path, outdir, args.images, args.flag_math,
                                args.page_markers, args.flag_figures)
        print(f"{path.name} -> {out}")
        print(f"   {summarize(manifest.get('stats', {}))}")
