"""Pure GUI helpers that do not import Tk or construct widgets."""

from __future__ import annotations

import pathlib
import platform
import sys
from dataclasses import dataclass

from . import __version__
from .display import safe_display
from .stats import ConversionStats, stat_warnings, summarize

APP_NAME = "markerlite"


def run_log_line(name: str, summary: str, warnings: list[str]) -> str:
    """One run-log line for a converted file. The file name is displayed
    safely: a name holding a line feed must not forge a second log line."""
    line = f"{safe_display(name)}: {summary}"
    if warnings:
        line += " | WARNINGS: " + "; ".join(warnings)
    return line


def failure_message(exc: BaseException) -> str:
    """The text shown and logged for a conversion that raised."""
    return safe_display(f"{type(exc).__name__}: {exc}")


def failure_log_line(name: str, message: str) -> str:
    return f"{safe_display(name)}: FAILED {message}"


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


def bug_report_line(
    tesseract: str | None, system: str, version: str = __version__
) -> str:
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


def cancelled_log_line(name: str) -> str:
    return f"{safe_display(name)}: CANCELLED (no output written)"


def skipped_log_line(name: str) -> str:
    return f"{safe_display(name)}: SKIPPED (batch cancelled)"


def run_batch(files, opts: ConversionOptions, convert, cancel, emit, log) -> dict:
    """Convert ``files`` one after another; the GUI worker thread runs this.

    ``convert`` is markerlite.convert; ``cancel`` a CancelToken checked
    before each file and, inside convert(), between pages; ``emit(event)``
    reports progress to the window; ``log(outdir, line)`` appends to that
    folder's run log. A failed file never sinks the batch. On cancel the
    current file's staged output is discarded by convert(), files already
    converted stay, and the rest are skipped. Returns counts by outcome.
    """
    from .cancel import Cancelled
    from .stats import stat_warnings as _warnings
    from .stats import summarize as _summarize

    outcome = {"done": [], "failed": [], "cancelled": [], "skipped": []}
    for pdf in files:
        outdir = output_directory(pdf, opts.mode, opts.directory)
        if cancel is not None and cancel.is_set():
            outcome["skipped"].append(pdf)
            log(outdir, skipped_log_line(pdf.name))
            emit(("skipped", str(pdf)))
            continue
        emit(("busy", str(pdf)))
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            md, manifest = convert(
                pdf, outdir, opts.images, opts.math, opts.page_markers, cancel=cancel
            )
        except Cancelled:
            outcome["cancelled"].append(pdf)
            log(outdir, cancelled_log_line(pdf.name))
            emit(("cancelled", str(pdf)))
            continue
        except Exception as exc:
            msg = failure_message(exc)
            outcome["failed"].append(pdf)
            log(outdir, failure_log_line(pdf.name, msg))
            emit(("error", str(pdf), msg))
            continue
        stats = manifest.get("stats", {})
        log(outdir, run_log_line(pdf.name, _summarize(stats), _warnings(stats)))
        outcome["done"].append(pdf)
        emit(("done", str(pdf), str(md), stats))
    return outcome


def finish_status(outcome: dict, summary: str) -> str:
    """The status-bar line after a batch. A cancelled batch says so first."""
    if outcome.get("cancelled") or outcome.get("skipped"):
        parts = ["Cancelled"]
        if outcome.get("done"):
            parts.append(f"{len(outcome['done'])} converted")
        if outcome.get("skipped"):
            parts.append(f"{len(outcome['skipped'])} skipped")
        return " · ".join(parts)
    return summary


CANCELLING = "Cancelling\u2026"


def busy_status(name: str, cancelling: bool) -> str:
    """Status-bar text when a file starts. Once Cancel or Esc was pressed
    the bar keeps saying "Cancelling…" until the batch is idle, even if a
    progress event queued before the press arrives after it."""
    return CANCELLING if cancelling else f"Converting {safe_display(name)}"


def cancel_pressed(running: bool) -> tuple:
    """What a Cancel/Esc press does to the window, decided at once on the
    Tk thread: (cancel the token, status text, Convert/Cancel button state).
    Outside a batch it does nothing."""
    if not running:
        return (False, None, None)
    return (True, CANCELLING, "disabled")
