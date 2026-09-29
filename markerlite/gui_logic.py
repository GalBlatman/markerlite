"""Pure GUI helpers that do not import Tk or construct widgets."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from .stats import ConversionStats, stat_warnings, summarize


@dataclass(frozen=True)
class ConversionOptions:
    images: bool
    math: bool
    page_markers: bool
    mode: str
    directory: str


def snapshot_options(
    images: object,
    math: object,
    page_markers: object,
    mode: object,
    directory: object,
) -> ConversionOptions:
    """Copy main-thread option values into an immutable worker payload."""
    return ConversionOptions(
        images=bool(images),
        math=bool(math),
        page_markers=bool(page_markers),
        mode=str(mode),
        directory=str(directory),
    )


def output_directory(pdf: pathlib.Path, mode: str, directory: str) -> pathlib.Path:
    return pathlib.Path(directory) if mode == "fixed" else pdf.parent


def warning_lines(stats: ConversionStats) -> list[str]:
    return stat_warnings(stats)


def summary_text(stats: ConversionStats) -> str:
    return summarize(stats)


def provenance_comments(md: pathlib.Path) -> list[str]:
    """Read leading ``source:`` comments without loading the whole document."""
    out = []
    try:
        with md.open(encoding="utf-8") as handle:
            for _ in range(8):
                line = handle.readline()
                if line.startswith("<!-- source:"):
                    out.append(line.strip()[len("<!-- ") : -len(" -->")])
    except OSError:
        pass
    return out
