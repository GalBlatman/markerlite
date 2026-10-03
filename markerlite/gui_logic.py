"""Pure GUI helpers that do not import Tk or construct widgets."""

from __future__ import annotations

import pathlib
import platform
import sys
from dataclasses import dataclass

from . import __version__
from .stats import ConversionStats, stat_warnings, summarize

APP_NAME = "markerlite"


def window_title(version: str = __version__) -> str:
    """The window title. The windowed exe has no console, so the title is
    where a user reads the version they run."""
    return f"{APP_NAME} {version}"


def version_label(version: str = __version__) -> str:
    """The short version shown at the right end of the status bar."""
    return f"v{version}"


def windows_build() -> str:
    """The operating system, as one short token for a bug report:
    "Windows 10.0.26300" (Windows 11 reports 10.0 and a build number)."""
    if sys.platform == "win32":
        return f"Windows {platform.version()}"
    return f"{platform.system()} {platform.release()}".strip()


def bug_report_line(tesseract: str | None, system: str,
                    version: str = __version__) -> str:
    """The line the version label copies, for pasting into a bug report.

    ``tesseract`` is Tesseract's first version line ("tesseract 5.5.0") or
    None when no executable was found.
    """
    if tesseract:
        words = tesseract.split()
        if words and words[0].lower() == "tesseract":
            words = words[1:]
        tess = " ".join(words) or "version unknown"
    else:
        tess = "not found"
    return f"{APP_NAME} {version} \u00b7 Tesseract {tess} \u00b7 {system}"


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
