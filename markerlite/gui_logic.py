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


def run_batch(
    files, opts: ConversionOptions, convert, cancel, emit, log, page_count=None
) -> dict:
    """Convert ``files`` one after another; the GUI worker thread runs this.

    ``convert`` is markerlite.convert; ``cancel`` a CancelToken checked
    before each file and, inside convert(), between pages; ``emit(event)``
    reports progress to the window; ``log(outdir, line)`` appends to that
    folder's run log. A failed file never sinks the batch. On cancel the
    current file's staged output is discarded by convert(), files already
    converted stay, and the rest are skipped. Returns counts by outcome.

    With ``page_count`` (a function of the PDF path), each file's page count
    is emitted as ``("pages", src, n)`` before it converts, and a
    :class:`ProgressToken` is told the file's size so it can report how far
    the conversion has got.
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
        if page_count is not None:
            try:
                pages = int(page_count(pdf))
            except Exception:
                pages = 0
            if pages:
                emit(("pages", str(pdf), pages))
            if isinstance(cancel, ProgressToken):
                cancel.begin(str(pdf), pages)
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


MENU_ITEMS = (
    "Open Markdown",
    "Open PDF",
    "Show in folder",
    "Copy Markdown",
    "Show warnings",
    "Re-convert",
    "Remove from list",
)


def menu_state(
    pdf_exists: bool, md_exists: bool, converted: bool, running: bool
) -> dict:
    """Which right-click entries apply to a file row. Re-convert and Remove
    wait for the running batch; nothing here deletes or renames a file."""
    return {
        "Open Markdown": md_exists,
        "Open PDF": pdf_exists,
        "Show in folder": md_exists or pdf_exists,
        "Copy Markdown": md_exists,
        "Show warnings": converted,
        "Re-convert": pdf_exists and not running,
        "Remove from list": not running,
    }


def warning_details(stats: dict) -> list:
    """The "Show warnings" window: one line per finding in a file's stats,
    or "No warnings"."""
    out = []
    for d in stats.get("lossy_pages") or []:
        out.append(
            f"Lossy page {d['page']}: {d['emitted']} of {d['source']} source words emitted"
        )
    for d in stats.get("fragment_pages") or []:
        out.append(
            f"Fragment page {d['page']}: {d['short_share']:.0%} of "
            f"{d['letter_tokens']} words are one or two letters"
        )
    if stats.get("tables_fallback"):
        n, m = stats["tables_fallback"], stats.get("tables", stats["tables_fallback"])
        out.append(f"Tables kept as prose: {n} of {m}")
    for d in stats.get("resource_limits") or []:
        out.append(
            f"Resource limit {d.get('limit')} on page {d.get('page')}: "
            f"{d.get('observed')} over {d.get('cap')}; {d.get('action')}"
        )
    return [safe_display(line) for line in out] or ["No warnings"]


def reveal_command(path: pathlib.Path, platform_name: str = sys.platform) -> list:
    """argv that shows ``path`` selected in the file manager. Always a list
    for subprocess without a shell; the path is one argument."""
    if platform_name == "win32":
        return ["explorer", f"/select,{path}"]
    if platform_name == "darwin":
        return ["open", "-R", str(path)]
    return ["xdg-open", str(pathlib.Path(path).parent)]


def launch_paths(args: list) -> tuple:
    """Split file arguments (from Explorer's Send to, or a second launch)
    into what the window takes - PDFs and folders, whose PDFs are added as
    on a drop - and the rest, which are skipped with one log line each."""
    take, skip = [], []
    for raw in args:
        if not raw or str(raw).startswith("--"):
            continue
        p = pathlib.Path(raw)
        if p.suffix.lower() == ".pdf" or p.is_dir():
            take.append(p)
        else:
            skip.append(p)
    return take, skip


def app_log_path() -> pathlib.Path:
    """markerlite-app.log for events that belong to no output folder
    (Send to changes, hand-offs, skipped launch arguments)."""
    import os

    base = os.environ.get("LOCALAPPDATA") or str(pathlib.Path.home())
    return pathlib.Path(base) / "markerlite" / "markerlite-app.log"


def app_log(line: str, path: pathlib.Path | None = None) -> None:
    import datetime as _dt

    path = path or app_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"{stamp} {safe_display(line)}\n")
    except OSError:
        pass


def handoff_plan(new: list, running: bool, pending: list) -> tuple:
    """Files arriving from Send to or a second launch: convert them now, or
    queue them behind the batch that is running. Returns (start_now,
    pending). Nothing is dropped and a file already queued is not added
    twice."""
    if not running:
        return list(new), list(pending)
    queued = list(pending)
    for p in new:
        if p not in queued:
            queued.append(p)
    return [], queued


# ---------------------------------------------------------------- progress
try:
    from .cancel import CancelToken as _CancelToken
except Exception:  # pragma: no cover - cancel.py has no third-party imports
    _CancelToken = object


def progress_checks(pages: int) -> int:
    """How many cancel checks convert() makes for a document of ``pages``
    pages: one per page while extracting, one per page while finding
    tables, and four between the later stages (markerlite/api.py). OCR adds
    a check per Tesseract call, so the estimate runs ahead on scans and is
    capped below 100 until the file is done."""
    return 2 * max(0, pages) + 4


class ProgressToken(_CancelToken):
    """A CancelToken that also reports progress through the current file.

    convert() checks the token between pages; counting those checks against
    :func:`progress_checks` gives a percentage without any change to the
    converter. ``report(src, percent)`` is called from the worker thread
    whenever the whole-number percentage grows.
    """

    def __init__(self, report=None) -> None:
        super().__init__()
        self._report = report
        self._src = ""
        self._calls = 0
        self._total = 0
        self._last = -1

    def begin(self, src: str, pages: int) -> None:
        self._src, self._calls, self._last = src, 0, -1
        self._total = progress_checks(pages) if pages else 0

    def check(self) -> None:
        super().check()
        if not self._total:
            return
        self._calls += 1
        percent = min(99, self._calls * 100 // self._total)
        if percent > self._last:
            self._last = percent
            if self._report is not None:
                self._report(self._src, percent)


# ------------------------------------------------------------ status column
STATUS_DOTS = ("muted", "busy", "ok", "warn", "bad")


def status_cell(state: str, percent: int | None = None, warnings: int = 0) -> tuple:
    """(text, dot) for the file list's Status column.

    ``state`` is one of queued, converting, cancelling, done, failed,
    cancelled, skipped; ``dot`` names the dot colour (one of STATUS_DOTS).
    A done file with warnings says how many, and its count is what the user
    clicks to open Show warnings.
    """
    if state == "queued":
        return "Queued", "muted"
    if state == "converting":
        if percent is None:
            return "Converting…", "busy"
        return f"Converting {max(0, min(99, int(percent)))}%", "busy"
    if state == "cancelling":
        return CANCELLING, "warn"
    if state == "done":
        if warnings:
            return f"Done with {warnings} warning{'s' * (warnings != 1)}", "warn"
        return "Done", "ok"
    if state == "failed":
        return "Failed", "bad"
    if state == "cancelled":
        return "Cancelled", "muted"
    if state == "skipped":
        return "Skipped", "muted"
    raise ValueError(f"unknown status: {state}")


def elapsed_text(seconds: float | None) -> str:
    """The Time column: tenths below a minute, then m:ss."""
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds:.1f} s"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def overall_progress(finished: int, current_percent: int, total: int) -> float:
    """The bottom progress bar, 0-100 over the whole batch."""
    if total <= 0:
        return 0.0
    return min(100.0, (finished * 100 + max(0, current_percent)) / total)


# ------------------------------------------------------------------ theme
def theme_for(apps_use_light: int | None, override: str | None = None) -> str:
    """ "light" or "dark" from Windows' AppsUseLightTheme value (1 light,
    0 dark, None when it cannot be read: light). MARKERLITE_THEME, when set
    to light or dark, overrides it."""
    if override and override.strip().lower() in ("light", "dark"):
        return override.strip().lower()
    return "dark" if apps_use_light == 0 else "light"


def windows_apps_use_light() -> int | None:
    """The Windows "app mode" setting, read once at startup."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        with key:
            return int(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
    except Exception:
        return None


# ----------------------------------------------------------------- colours
# The logo blue: the primary button, selection and checked controls. The
# theme's own accent sprites are recoloured to it (tools/recolour_sprites.py).
ACCENT = "#2F4C8F"

# Colours the theme does not set, per Windows app mode. Text colours meet
# WCAG AA (4.5:1) on the background; dots, which are not text, meet 3:1
# (tests/test_gui_status.py).
PALETTES = {
    "light": {
        "bg": "#fafafa",
        "card": "#ffffff",
        "ink": "#1a1a1a",
        "muted": "#5d5d5d",
        "line": "#d6d6d6",
        "sel_bg": "#d9e1f2",
        "sel_fg": "#1a1a1a",
        "ok": "#0f7b0f",
        "warn": "#9d5d00",
        "bad": "#c42b1c",
        "busy": ACCENT,
        "dot_muted": "#8a8a8a",
        "focus": ACCENT,
    },
    "dark": {
        "bg": "#1c1c1c",
        "card": "#2b2b2b",
        "ink": "#f3f3f3",
        "muted": "#ababab",
        "line": "#454545",
        "sel_bg": ACCENT,
        "sel_fg": "#ffffff",
        "ok": "#6ccb5f",
        "warn": "#fce100",
        "bad": "#ff99a4",
        "busy": "#8fa7dc",
        "dot_muted": "#8a8a8a",
        "focus": "#8fa7dc",
    },
}
DOT_COLOUR = {
    "muted": "dot_muted",
    "busy": "busy",
    "ok": "ok",
    "warn": "warn",
    "bad": "bad",
}


def row_details(stats: dict) -> str:
    """The counts the file list's columns used to show (content words, OCR
    pages, tables and how many fell back to prose), for the row tooltip."""
    pages = stats.get("pages", 0)
    parts = [f"{stats.get('words', 0):,} content words"]
    if stats.get("ocr_pages") or stats.get("image_only_pages"):
        parts.append(f"{stats.get('ocr_pages', 0)}/{pages} pages OCR'd")
    tables = stats.get("tables", 0)
    if tables:
        fell = stats.get("tables_fallback", 0)
        parts.append(
            f"{tables} table{'s' * (tables != 1)}"
            + (f" ({fell} kept as prose)" if fell else "")
        )
    return " · ".join(parts)


def main_menu_state(
    running: bool, row_states: list[dict], has_output: bool, has_log: bool
) -> dict:
    """Main menu commands use the same per-row decisions as the context menu."""
    return {
        "Convert": bool(row_states) and not running,
        "Cancel": running,
        "Copy Markdown": any(row.get("Copy Markdown", False) for row in row_states),
        "Show warnings": any(row.get("Show warnings", False) for row in row_states),
        "Remove from list": bool(row_states) and not running,
        "Clear finished": has_output and not running,
        "Clear list": bool(row_states) and not running,
        "Select all": bool(row_states),
        "Open output folder": has_output,
        "Log": has_log,
    }
