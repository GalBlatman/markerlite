#!/usr/bin/env python3
"""markerlite GUI - drag PDFs in, get Markdown out.

A thin Tk front end over markerlite.convert(). Conversion runs on a worker
thread so the window stays responsive, and each file's status is reported
independently: one bad PDF never sinks the batch.

Drag-and-drop needs tkinterdnd2 (`pip install tkinterdnd2`). Without it the
window still works - the drop zone becomes an "Add files" button.
"""

from __future__ import annotations

import os
import pathlib
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import traceback
import webbrowser
from tkinter import filedialog, messagebox, ttk

from markerlite import __version__
from markerlite.display import safe_display
from markerlite.extraction import discover_tesseract, tesseract_version
from markerlite.gui_logic import (
    DOT_COLOUR,
    MENU_ITEMS,
    PALETTES,
    ConversionOptions,
    ProgressToken,
    app_log,
    bug_report_line,
    busy_status,
    cancel_pressed,
    elapsed_text,
    finish_status,
    handoff_plan,
    launch_paths,
    main_menu_state,
    menu_state,
    output_directory,
    overall_progress,
    provenance_comments,
    reveal_command,
    row_details,
    run_batch,
    snapshot_options,
    status_cell,
    summary_text,
    theme_for,
    version_label,
    warning_details,
    warning_lines,
    window_title,
    windows_apps_use_light,
    windows_build,
)
from markerlite.gui_settings import load_settings, recent_files, save_settings

# Crisp text on high-DPI Windows displays; harmless elsewhere.
#
# Per-monitor awareness (v2) matters on mixed-scaling setups: with plain
# "system DPI aware" (mode 1), a window opened on a monitor whose scaling
# differs from the primary display is bitmap-stretched by Windows AFTER Tk has
# sized it, so it ends up larger than the screen it is on.
if sys.platform == "win32":
    try:
        from ctypes import windll

        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4 (Windows 10 1703+)
            if not windll.user32.SetProcessDpiAwarenessContext(-4):
                raise OSError
        except Exception:
            try:
                windll.shcore.SetProcessDpiAwareness(2)  # per-monitor (v1)
            except Exception:
                windll.shcore.SetProcessDpiAwareness(1)  # system
    except Exception:
        pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

DND_ERROR = ""
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAVE_DND = True
except Exception as _exc:  # pragma: no cover
    HAVE_DND = False
    DND_ERROR = f"{type(_exc).__name__}: {_exc}"

APP = "markerlite"

BASE_SIZE = 10  # points: the one body size
GRID = 8  # spacing unit in pixels at 96 dpi, scaled to the monitor


def bundle_dir() -> pathlib.Path:
    """Where bundled files live: PyInstaller unpacks data under
    sys._MEIPASS; from source the assets folder sits beside this file."""
    return pathlib.Path(
        getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent)
    )


def _apply_accent(root: tk.Tk, theme: str) -> int:
    """Copy the recoloured accent sprites over sv-ttk's own images; returns
    how many sprites were replaced. Raises if anything is missing.

    sv-ttk draws its accent controls from a spritesheet, so the accent is
    not a colour option. assets/sv-ttk holds the same sheets with the accent
    sprites in the logo blue (tools/recolour_sprites.py). Copying keeps each
    pixel's alpha, in Tk 8.6 and 9. Sprite positions come from sv-ttk's own
    sprite table."""
    import re

    import sv_ttk

    sheet = bundle_dir() / "assets" / "sv-ttk" / f"spritesheet_{theme}.png"
    table = pathlib.Path(sv_ttk.__file__).with_name("theme") / f"sprites_{theme}.tcl"
    for path in (sheet, table):
        if not path.is_file():
            raise FileNotFoundError(path)
    image_sheet = tk.PhotoImage(master=root, file=str(sheet))
    root._accent_sheet = image_sheet  # keep a reference while Tk uses it
    sprites = {
        name: tuple(map(int, rest))
        for name, *rest in re.findall(
            r"(\S+) (\d+) (\d+) (\d+) (\d+)", table.read_text()
        )
    }
    call = root.tk.call
    pairs = root.tk.splitlist(call("array", "get", f"ttk::theme::sv_{theme}::I"))
    copied = 0
    for name, image in zip(pairs[0::2], pairs[1::2]):
        if name in sprites:
            x, y, w, h = sprites[name]
            call(
                image, "copy", image_sheet,
                "-from", x, y, x + w, y + h,
                "-to", 0, 0,
                "-compositingrule", "set",
            )  # fmt: skip
            copied += 1
    if not copied:
        raise RuntimeError("no sv-ttk sprites matched")
    return copied


def load_theme(root: tk.Tk, theme: str) -> str:
    """Apply sv-ttk in ``theme`` with the logo-blue accent. Never raises:
    a failed recolour keeps sv-ttk's stock accent, a missing sv-ttk falls
    back to Tk's clam theme. Returns one line saying which happened, for
    the window and for --diag."""
    try:
        import sv_ttk

        sv_ttk.set_theme(theme, root)
    except Exception as exc:
        try:
            ttk.Style(root).theme_use("clam")
        except tk.TclError:
            pass
        return f"clam (sv-ttk not loaded: {type(exc).__name__}: {exc})"
    try:
        from importlib.metadata import version

        name = f"sv-ttk {version('sv-ttk')}"
    except Exception:
        name = "sv-ttk (version unknown)"
    try:
        accent = f"accent recoloured ({_apply_accent(root, theme)} sprites)"
    except Exception as exc:
        accent = f"stock accent (recolour failed: {type(exc).__name__}: {exc})"
    tk_version = root.tk.call("info", "patchlevel")
    return f"{name} {theme}, {accent}, Tk {tk_version}"


class App:
    def __init__(self, root: tk.Tk, events=None, initial=None):
        self.root = root
        self.settings = load_settings(log=app_log)
        self.preview_size = BASE_SIZE
        self.files: list[pathlib.Path] = []
        self.results: dict[str, dict] = {}
        # Per-row display state behind the Pages, Status and Time columns.
        self.rows: dict[str, dict] = {}
        # Worker progress and hand-offs from later launches both arrive
        # here and are taken off on the Tk thread by _drain (after()).
        self.events: "queue.Queue[tuple]" = events or queue.Queue()
        self.pending: list[pathlib.Path] = []
        self.running = False
        self.cancel_token = None
        self.outcome: dict = {}
        self.log_paths: list[pathlib.Path] = []
        self.batch_total = 0
        self.batch_finished = 0
        self.current_src: str | None = None

        # The version comes from markerlite/VERSION through __version__: the
        # windowed exe has no console, so this is where a user reads it.
        root.title(window_title())
        self.tess_version: str | None = None
        # Light or dark follows the Windows app setting, read once here.
        self.theme = theme_for(
            windows_apps_use_light(),
            os.environ.get("MARKERLITE_THEME") or self.settings["theme"],
        )
        self.c = PALETTES[self.theme]
        self._match_monitor_dpi()
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)

        self._style()
        self._build()
        self._build_menus()
        self._set_icon()
        self._enable_drop()
        self._fit_to_screen()
        self._check_tesseract()
        # Esc does what the Cancel button does; outside a batch it does nothing.
        root.bind("<Escape>", lambda _e: self.cancel())
        self.root.after(80, self._drain)
        if initial:
            # Files from the command line (Explorer's Send to): after the
            # window is up, add them and convert with the current settings.
            self.root.after(200, lambda: self._receive(list(initial)))
        if self.sendto_var is not None and self.sendto_var.get():
            # Repair the Send to shortcut only when the option is on, in the
            # background, after the window has appeared.
            self.root.after(1500, self._sendto_repair)

    def _save_settings(self):
        try:
            save_settings(self.settings)
        except OSError as exc:
            app_log(f"Could not save settings: {exc}")
            self.status.configure(text=f"Could not save settings: {safe_display(exc)}")

    def _build_menus(self):
        self.menu_bar = tk.Menu(self.root)
        self.menus = {}
        self.menu_entries = {}
        for name in ("File", "Edit", "View", "Tools", "Help"):
            menu = tk.Menu(
                self.menu_bar, tearoff=False, postcommand=self._refresh_menus
            )
            self.menu_bar.add_cascade(label=name, underline=0, menu=menu)
            self.menus[name] = menu
        self.root.configure(menu=self.menu_bar)

        def entry(group, label, command, shortcut="", key=None):
            menu = self.menus[group]
            menu.add_command(
                label=label, underline=0, command=command, accelerator=shortcut
            )
            self.menu_entries[label] = (menu, menu.index("end"))
            if key:

                def invoke(event):
                    self._refresh_menus()
                    if menu.entrycget(label, "state") != "disabled":
                        command()
                    return "break"

                self.root.bind(key, invoke)

        entry("File", "Open PDFs…", self.browse, "Ctrl+O", "<Control-o>")
        entry("File", "Open folder…", self.browse_folder)
        self.recent_menu = tk.Menu(self.menus["File"], tearoff=False)
        self.menus["File"].add_cascade(
            label="Recent files", underline=0, menu=self.recent_menu
        )
        self.menus["File"].add_separator()
        entry("File", "Convert", self.start, "F5", "<F5>")
        entry("File", "Cancel", self.cancel, "Esc", "<Escape>")
        entry("File", "Open output folder", self.open_out)
        entry("File", "Exit", self._exit)
        self.root.protocol("WM_DELETE_WINDOW", self._exit)
        entry(
            "Edit",
            "Copy Markdown",
            lambda: self._selected_action("Copy Markdown"),
            "Ctrl+Shift+C",
            "<Control-Shift-C>",
        )
        entry(
            "Edit",
            "Remove from list",
            lambda: self._selected_action("Remove from list"),
            "Del",
            "<Delete>",
        )
        entry("Edit", "Clear finished", self.clear_finished)
        entry("Edit", "Clear list", self.clear)
        entry("Edit", "Select all", self.select_all, "Ctrl+A", "<Control-a>")
        entry("View", "Preview", lambda: self.tabs.select(0))
        entry("View", "Log", lambda: self.tabs.select(1))
        entry("View", "Show warnings", lambda: self._selected_action("Show warnings"))
        self.theme_choice = tk.StringVar(value=self.settings["theme"])
        themes = tk.Menu(self.menus["View"], tearoff=False)
        self.menus["View"].add_cascade(label="Theme", underline=0, menu=themes)
        for label in ("System", "Light", "Dark"):
            themes.add_radiobutton(
                label=label,
                underline=0,
                variable=self.theme_choice,
                value=label.lower(),
                command=self.change_theme,
            )
        entry(
            "View",
            "Larger preview text",
            lambda: self.resize_preview(1),
            "Ctrl+=",
            "<Control-equal>",
        )
        entry(
            "View",
            "Smaller preview text",
            lambda: self.resize_preview(-1),
            "Ctrl+-",
            "<Control-minus>",
        )
        entry("Tools", "Preferences…", self.preferences, "Ctrl+,", "<Control-comma>")
        entry("Tools", "Check OCR", self.check_ocr)
        entry("Tools", "Save diagnostics file", self.save_diagnostics)
        entry(
            "Help",
            "User guide",
            lambda: self.open_link(
                "https://github.com/GalBlatman/markerlite/blob/main/README.md"
            ),
        )
        entry(
            "Help",
            "What's new",
            lambda: self.open_link(
                "https://github.com/GalBlatman/markerlite/releases/latest"
            ),
        )
        entry("Help", "Report a problem", self.report_problem)
        entry("Help", "Check for updates", self.check_updates)
        entry("Help", "About markerlite", self.about)
        self._refresh_menus()

    def _refresh_menus(self):
        states = [self._row_state(str(p)) for p in self.files]
        state = main_menu_state(
            self.running,
            states,
            any("md" in r for r in self.results.values()),
            bool(self.log_paths),
        )
        selected = list(self.tree.selection())
        for label in ("Copy Markdown", "Show warnings", "Remove from list"):
            state[label] = any(
                self._row_state(src).get(label, False) for src in selected
            )
        for label, enabled in state.items():
            menu, index = self.menu_entries[label]
            menu.entryconfigure(index, state="normal" if enabled else "disabled")
        self.recent_menu.delete(0, "end")
        for path in self.settings["recent_files"]:
            self.recent_menu.add_command(
                label=safe_display(path),
                command=lambda p=path: self.add([p]),
                state="normal" if pathlib.Path(path).is_file() else "disabled",
            )
        if not self.settings["recent_files"]:
            self.recent_menu.add_command(label="No recent files", state="disabled")

    def _selected_action(self, label):
        actions = {
            "Copy Markdown": self._copy_markdown,
            "Show warnings": self._show_warnings,
            "Remove from list": self._remove,
        }
        for src in list(self.tree.selection()):
            if self._row_state(src).get(label, False):
                actions[label](src)
                if label != "Remove from list":
                    break

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def clear_finished(self):
        for src in list(self.results):
            if "md" in self.results[src]:
                self._remove(src)

    def resize_preview(self, delta):
        self.preview_size = max(6, min(32, self.preview_size + delta))
        self.preview.configure(font=(self.font_mono[0], self.preview_size))

    def change_theme(self):
        self.settings["theme"] = self.theme_choice.get()
        self._save_settings()
        self.theme = theme_for(
            windows_apps_use_light(),
            os.environ.get("MARKERLITE_THEME") or self.settings["theme"],
        )
        self.c = PALETTES[self.theme]
        self._style()
        for widget in (self.preview, self.log_text):
            widget.configure(
                bg=self.c["card"],
                fg=self.c["ink"],
                insertbackground=self.c["ink"],
                selectbackground=self.c["sel_bg"],
                selectforeground=self.c["sel_fg"],
                inactiveselectbackground=self.c["sel_bg"],
                highlightbackground=self.c["line"],
                highlightcolor=self.c["focus"],
            )
        self.resize_preview(0)
        for src in self.rows:
            self._set_row(src)

    def _exit(self):
        if self.running:
            self.cancel()
            self.root.after(100, self._exit)
        elif getattr(self, "update_thread", None) and self.update_thread.is_alive():
            self.root.after(100, self._exit)
        else:
            self.root.destroy()

    def open_link(self, url):
        try:
            if sys.platform == "win32":
                os.startfile(url)
            else:
                webbrowser.open(url)
        except OSError as exc:
            self.status.configure(text=f"Could not open browser: {safe_display(exc)}")

    def report_problem(self):
        self.copy_version()
        self.open_link("https://github.com/GalBlatman/markerlite/issues/new")

    def save_diagnostics(self):
        destination = filedialog.asksaveasfilename(
            title="Save diagnostics file",
            initialfile="markerlite-diag.txt",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")],
        )
        if destination:
            try:
                source = write_diagnostics()
                pathlib.Path(destination).write_bytes(source.read_bytes())
                self.status.configure(text=f"Diagnostics saved to {destination}")
            except OSError as exc:
                messagebox.showerror("Diagnostics", str(exc), parent=self.root)

    def about(self):
        win = tk.Toplevel(self.root)
        win.title("About markerlite")
        win.transient(self.root)
        ttk.Label(
            win, text=f"markerlite {__version__}\nApache-2.0", padding=self.g(2)
        ).pack()
        credits = (
            (
                "markerlite — Apache-2.0",
                "https://github.com/GalBlatman/markerlite/blob/main/LICENSE",
            ),
            (
                "Marker — Apache-2.0",
                "https://github.com/datalab-to/marker/blob/master/LICENSE",
            ),
            (
                "PyMuPDF — AGPL-3.0 / commercial",
                "https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright",
            ),
            (
                "Tesseract — Apache-2.0",
                "https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE",
            ),
            (
                "sv-ttk — MIT",
                "https://github.com/rdbende/Sun-Valley-ttk-theme/blob/main/LICENSE",
            ),
        )
        for label, url in credits:
            ttk.Button(win, text=label, command=lambda u=url: self.open_link(u)).pack(
                fill="x", padx=self.g(2), pady=self.g(0.5)
            )
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=self.g(2))
        win.bind("<Escape>", lambda _e: win.destroy())

    def check_updates(self):
        if getattr(self, "update_thread", None) and self.update_thread.is_alive():
            return
        self.status.configure(text="Checking for updates…")

        def check():
            from markerlite.gui_updates import check_for_updates

            self.events.put(("update-result", check_for_updates()))

        self.update_thread = threading.Thread(target=check, daemon=True)
        self.update_thread.start()

    def show_update(self, result):
        win = tk.Toplevel(self.root)
        win.title("Check for updates")
        win.transient(self.root)
        ttk.Label(win, text=result.message, padding=self.g(2)).pack()
        if result.url:
            ttk.Button(
                win,
                text="Open release page"
                if "available" in result.message
                else "Open Releases",
                command=lambda: self.open_link(result.url),
            ).pack(pady=self.g(1))
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=self.g(1))
        win.bind("<Escape>", lambda _e: win.destroy())
        self.status.configure(text=result.message)

    def check_ocr(self):
        self._check_tesseract()
        executable = discover_tesseract()
        messagebox.showinfo(
            "Check OCR",
            f"Tesseract: {self.tess_version or 'not found'}\nPath: {executable or 'not found'}\nInstall Tesseract or set TESSERACT_CMD to its executable.",
            parent=self.root,
        )

    def preferences(self):
        win = tk.Toplevel(self.root)
        win.title("Preferences")
        win.transient(self.root)
        ttk.Label(win, text="Appearance", padding=self.g(2)).pack(anchor="w")
        for label in ("System", "Light", "Dark"):
            ttk.Radiobutton(
                win,
                text=label,
                variable=self.theme_choice,
                value=label.lower(),
                command=self.change_theme,
            ).pack(anchor="w", padx=self.g(2))
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=self.g(2))
        win.bind("<Escape>", lambda _e: win.destroy())

    def _match_monitor_dpi(self):
        """Size fonts and spacing for the monitor the window opens on.

        Tk takes its scaling from the primary monitor. With per-monitor DPI
        awareness and two monitors at different scaling, a window opened on
        the other one was drawn at the primary's size. Before anything is
        built, take the DPI of the monitor under the window instead."""
        if sys.platform != "win32":
            return
        try:
            import ctypes

            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            if dpi:
                self.root.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            pass

    def g(self, n: float = 1) -> int:
        """n units of the 8 px spacing grid, in this monitor's pixels."""
        return int(round(GRID * n * self.scale))

    def _work_area(self):
        """(x, y, w, h) of the usable desktop - the screen minus the taskbar -
        for the monitor the window is on. Falls back to Tk's screen size."""
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                hwnd = self.root.winfo_id()
                mon = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # nearest

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.DWORD),
                        ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT),
                        ("dwFlags", wintypes.DWORD),
                    ]

                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                    r = mi.rcWork
                    return r.left, r.top, r.right - r.left, r.bottom - r.top
            except Exception:
                pass
        return 0, 0, sw, sh - 48  # leave room for a taskbar we cannot measure

    def _fit_to_screen(self):
        """Size the window to its content, capped to the usable screen.

        A fixed "1000x700" is in device pixels; on a 150% display the widgets
        render larger than that box and the button row falls off the bottom -
        and Tk has no window-level scrolling to rescue it. Ask the layout what
        it needs, cap it to the work area of the monitor it is on, and check
        the result: if the bottom edge still lands off-screen, shrink again.
        """
        self.root.update_idletasks()
        need_w, need_h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        ax, ay, aw, ah = self._work_area()
        chrome = 60  # title bar + borders, roughly
        w = min(max(need_w, int(aw * 0.55)), int(aw * 0.92))
        h = min(max(need_h, int(ah * 0.6)), ah - chrome)
        x, y = ax + (aw - w) // 2, ay + 16
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.update_idletasks()
        # Verify against reality: on a mixed-DPI setup the window can come out
        # larger than requested. If so, size to what fits.
        bottom = self.root.winfo_rooty() + self.root.winfo_height()
        limit = ay + ah
        if bottom > limit:
            h = max(int(ah * 0.5), h - (bottom - limit) - 8)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(min(560, w), min(420, h))

    def _check_tesseract(self) -> bool:
        """Show Tesseract's version in the header, or a warning when it
        is unavailable. Called at startup and again when Convert is pressed,
        because the user may install it while the window is open."""
        exe = discover_tesseract()
        if exe:
            version = tesseract_version(exe)
            self.tess_version = version
            self.tess_label.configure(text=f"OCR: {version} ({exe})", style="Ok.TLabel")
            return True
        self.tess_version = None
        self.tess_label.configure(
            text="Tesseract not found \u2014 install Tesseract, or set "
            "TESSERACT_CMD to tesseract.exe",
            style="Warn.TLabel",
        )
        return False

    def _enable_drop(self):
        """Drag-and-drop comes from tkinterdnd2; without it, say so plainly."""
        self.drop_backend = "tkdnd" if HAVE_DND else None
        if not HAVE_DND:
            self.status.configure(
                text="Drag-and-drop unavailable — "
                + (DND_ERROR or "tkinterdnd2 not found")
                + ". Run: pip install tkinterdnd2  (or click the zone / Add folder)."
            )

    def _set_icon(self):
        """Title-bar and taskbar icon. Best effort: a missing file is not fatal.

        PyInstaller unpacks bundled data under sys._MEIPASS; from source the
        assets folder sits beside this file.
        """
        base = pathlib.Path(
            getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent)
        )
        ico = base / "assets" / "icon.ico"
        png = base / "assets" / "icon-256.png"
        try:
            if sys.platform == "win32" and ico.exists():
                self.root.iconbitmap(default=str(ico))
            elif png.exists():
                self._icon_img = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    # ---------------------------------------------------------------- style
    def _style(self):
        """Sun Valley (sv-ttk), the Windows 11 look, in the Windows app mode,
        with the logo blue as its accent. Without sv-ttk (a source run that
        lacks it) the stock clam theme is used and everything still works;
        if only the accent cannot be recoloured, sv-ttk keeps its own."""
        s = ttk.Style()
        c = self.c
        self.theme_status = load_theme(self.root, self.theme)
        families = set(tkfont.families(self.root))

        def pick(*names):
            return next((n for n in names if n in families), names[-1])

        body = pick("Segoe UI Variable Text", "Segoe UI")
        strong = pick("Segoe UI Variable Text Semibold", "Segoe UI Semibold")
        display = pick("Segoe UI Variable Display Semibold", "Segoe UI Semibold")
        # One base size, in points so it follows the monitor's DPI (sv-ttk
        # sizes its own fonts in pixels).
        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkTooltipFont",
            "SunValleyBodyFont",
            "SunValleyCaptionFont",
            "SunValleyBodyStrongFont",
        ):
            try:
                tkfont.nametofont(name, self.root).configure(
                    family=strong if "Strong" in name else body, size=BASE_SIZE
                )
            except tk.TclError:
                pass
        self.font_body = (body, BASE_SIZE)
        self.font_strong = (strong, BASE_SIZE)
        self.font_mono = (pick("Cascadia Mono", "Consolas"), BASE_SIZE)
        self.font_drop = (display, BASE_SIZE + 4)
        self.font_wordmark = (display, BASE_SIZE + 6)

        s.configure(".", font=self.font_body)
        s.configure("Muted.TLabel", foreground=c["muted"])
        s.configure("Ok.TLabel", foreground=c["muted"])
        s.configure("Warn.TLabel", foreground=c["warn"])
        s.configure("Head.TLabel", font=self.font_strong)
        s.configure("Wordmark.TLabel", font=self.font_wordmark)
        s.configure("Drop.TLabel", font=self.font_drop)
        s.configure("Accent.TButton", foreground="#ffffff", font=self.font_strong)
        s.map(
            "Accent.TButton",
            foreground=[("disabled", "#ffffff"), ("pressed", "#d6deef")],
        )
        s.configure("Treeview", rowheight=self.g(3.5), font=self.font_body)
        s.configure("Treeview.Heading", font=self.font_strong, padding=(self.g(1), 0))
        # The list is flat: no expand arrow in front of each file.
        s.layout("Treeview.Item", [
            ("Treeitem.padding", {"sticky": "nswe", "children": [
                ("Treeitem.image", {"side": "left", "sticky": ""}),
                ("Treeitem.focus", {"side": "left", "sticky": "", "children": [
                    ("Treeitem.text", {"side": "left", "sticky": ""}),
                ]}),
            ]}),
        ])  # fmt: skip
        s.map(
            "Treeview",
            background=[("selected", c["sel_bg"])],
            foreground=[("selected", c["sel_fg"])],
        )
        self.root.configure(bg=c["bg"])
        self.dots = {key: self._dot(c[name]) for key, name in DOT_COLOUR.items()}

    def _dot(self, colour: str) -> tk.PhotoImage:
        """A small filled circle that leads a row: its status colour."""
        d = max(8, int(round(9 * self.scale)))
        img = tk.PhotoImage(width=d + self.g(1), height=d)
        r = (d - 1) / 2
        for y in range(d):
            xs = [x for x in range(d) if (x - r) ** 2 + (y - r) ** 2 <= (r + 0.3) ** 2]
            if xs:
                img.put(colour, to=(xs[0], y, xs[-1] + 1, y + 1))
        return img

    # ---------------------------------------------------------------- layout
    def _build(self):
        root, g = self.root, self.g
        outer = ttk.Frame(root, padding=(g(2), g(2), g(2), g(1)))
        outer.pack(fill="both", expand=True)

        # ---- header: logo and wordmark; the version at the right ----------
        header = ttk.Frame(outer)
        header.pack(side="top", fill="x", pady=(0, g(2)))
        self._logo = None
        try:
            logo = tk.PhotoImage(file=str(bundle_dir() / "assets" / "icon-256.png"))
            step = max(1, int(round(256 / (32 * self.scale))))
            self._logo = logo.subsample(step, step)
            ttk.Label(header, image=self._logo).pack(side="left")
        except Exception:
            pass
        ttk.Label(header, text=APP, style="Wordmark.TLabel").pack(
            side="left", padx=(g(1), 0)
        )
        # A click on the version copies one line with the version, Tesseract
        # and the Windows build, ready for a bug report.
        self.version_label = ttk.Label(
            header, text=version_label(), style="Muted.TLabel", cursor="hand2"
        )
        self.version_label.pack(side="right")
        self.version_label.bind("<Button-1>", self.copy_version)
        # Tesseract state beside it: scanned PDFs silently produce no text
        # without it, and that was only discoverable from the output.
        self.tess_label = ttk.Label(header, text="", style="Muted.TLabel")
        self.tess_label.pack(side="right", padx=(0, g(3)))

        # ---- bottom controls FIRST, anchored to the bottom edge -----------
        # Whatever is packed first gets space first. If the window is ever
        # too short, the file list and preview shrink; the buttons never do.
        statusbar = ttk.Frame(outer)
        statusbar.pack(side="bottom", fill="x", pady=(g(1), 0))
        self._statusbar = statusbar
        self.bar = ttk.Progressbar(outer, mode="determinate", maximum=100)
        bar = ttk.Frame(outer)
        bar.pack(side="bottom", fill="x", pady=(g(2), 0))
        opts = ttk.Frame(outer)
        opts.pack(side="bottom", fill="x", pady=(g(2), 0))

        # ---- body: the drop zone while empty, then the list and its tabs ---
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        self.empty = ttk.Frame(body, style="Card.TFrame", padding=g(4))
        self.drop = self.empty
        inner = ttk.Frame(self.empty)
        inner.place(relx=0.5, rely=0.5, anchor="center")
        self.drop_label = ttk.Label(
            inner,
            text="Drop PDFs here, or click to browse"
            if HAVE_DND
            else "Click to browse for PDFs",
            style="Drop.TLabel",
        )
        self.drop_label.pack()
        hint = ttk.Label(
            inner,
            text="Add folder… converts every PDF in a directory",
            style="Muted.TLabel",
        )
        hint.pack(pady=(g(1), 0))
        self._drop_widgets = [self.empty, inner, self.drop_label, hint]
        for w in self._drop_widgets:
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda _e: self.browse())

        self.content = ttk.PanedWindow(body, orient="horizontal")
        left = ttk.Frame(self.content)
        self.content.add(left, weight=5)
        self.tree = ttk.Treeview(
            left,
            columns=("pages", "status", "time"),
            show="tree headings",
            selectmode="extended",
            height=6,
        )
        self.tree.heading("#0", text="File", anchor="w")
        self.tree.heading("pages", text="Pages", anchor="center")
        self.tree.heading("status", text="Status", anchor="w")
        self.tree.heading("time", text="Time", anchor="e")
        self.tree.column("#0", width=g(22), minwidth=g(12), stretch=True)
        self.tree.column(
            "pages", width=g(8), minwidth=g(7), stretch=False, anchor="center"
        )
        self.tree.column(
            "status", width=g(21), minwidth=g(18), stretch=False, anchor="w"
        )
        self.tree.column("time", width=g(8), minwidth=g(7), stretch=False, anchor="e")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Motion>", self._tree_motion)
        self.tree.bind("<Leave>", lambda _e: self._hide_tip())
        self.tree.bind("<Button-3>", self._row_menu)
        self.tree.bind("<ButtonRelease-1>", self._tree_click)
        self.tree.bind("<Return>", self._tree_key)
        self._tip = None
        self._tip_row = None

        self.tabs = ttk.Notebook(self.content)
        self.content.add(self.tabs, weight=4)
        left.configure(width=g(70))
        self.preview = self._text_tab("Preview")
        self.preview.bind("<Button-3>", self._preview_menu)
        self.log_text = self._text_tab("Log")

        # ---- options, collapsed by default ---------------------------------
        self.out_mode = tk.StringVar(value="beside")
        self.out_dir = tk.StringVar(
            value=str(pathlib.Path.home() / "Documents" / "markdown")
        )
        self.opt_images = tk.BooleanVar(value=False)
        self.opt_math = tk.BooleanVar(value=False)
        self.opt_pages = tk.BooleanVar(value=False)
        self.opts_open = False
        head = ttk.Frame(opts)
        head.pack(fill="x")
        self.opts_toggle = ttk.Button(
            head,
            text="▸  Options",
            style="Toolbutton",
            command=self._toggle_options,
        )
        self.opts_toggle.pack(side="left")
        self.opts_summary = ttk.Label(head, text="", style="Muted.TLabel")
        self.opts_summary.pack(side="left", padx=(g(1), 0))

        panel = ttk.Frame(opts, padding=(g(2), g(1), 0, 0))
        self.opts_panel = panel
        out_col = ttk.Frame(panel)
        out_col.pack(side="left", fill="x", expand=True, anchor="n")
        extra_col = ttk.Frame(panel)
        extra_col.pack(side="left", anchor="n", padx=(g(4), 0))
        ttk.Label(out_col, text="Output", style="Head.TLabel").pack(anchor="w")
        for text, value in (
            ("Next to the original PDF", "beside"),
            ("This folder:", "fixed"),
        ):
            ttk.Radiobutton(
                out_col,
                text=text,
                value=value,
                variable=self.out_mode,
                command=self._sync_out,
            ).pack(anchor="w", pady=(g(1), 0))
        path_row = ttk.Frame(out_col)
        path_row.pack(fill="x", pady=(g(1), 0), padx=(g(3), 0))
        self.out_entry = ttk.Entry(path_row, textvariable=self.out_dir, width=44)
        self.out_entry.pack(side="left", fill="x", expand=True)
        self.out_btn = ttk.Button(path_row, text="Change…", command=self.pick_out)
        self.out_btn.pack(side="left", padx=(g(1), 0))
        ttk.Label(extra_col, text="Extras", style="Head.TLabel").pack(anchor="w")
        for text, var in (
            ("Extract images", self.opt_images),
            ("Crop equations for transcription", self.opt_math),
            ("Insert <!-- page N --> markers", self.opt_pages),
        ):
            ttk.Checkbutton(
                extra_col, text=text, variable=var, command=self._sync_out
            ).pack(anchor="w", pady=(g(1), 0))
        # Explorer's Send to entry: Windows app only (it points at this exe).
        self.sendto_var = None
        self.sendto_error = None
        if sys.platform == "win32" and getattr(sys, "frozen", False):
            from markerlite import sendto

            self.sendto_var = tk.BooleanVar(value=sendto.link_path().is_file())
            ttk.Checkbutton(
                extra_col,
                text="Add markerlite to Explorer's Send to menu",
                variable=self.sendto_var,
                command=self._sendto_toggle,
            ).pack(anchor="w", pady=(g(1), 0))
            self.sendto_error = ttk.Label(
                extra_col,
                text="",
                style="Warn.TLabel",
                wraplength=g(40),
                justify="left",
            )
            self.sendto_error.pack(anchor="w")
        self._sync_out()

        # ---- action bar --------------------------------------------------
        self.go = ttk.Button(
            bar, text="Convert", style="Accent.TButton", command=self.start, width=10
        )
        self.go.pack(side="left")
        for text, command in (
            ("Add files…", self.browse),
            ("Add folder…", self.browse_folder),
            ("Clear", self.clear),
        ):
            ttk.Button(bar, text=text, command=command).pack(
                side="left", padx=(g(1), 0)
            )
        self.math_btn = ttk.Button(
            bar, text="Open equation crops", command=self.open_math, state="disabled"
        )
        self.math_btn.pack(side="right")
        self.md_btn = ttk.Button(
            bar, text="Open Markdown", command=self.open_md, state="disabled"
        )
        self.md_btn.pack(side="right", padx=(0, g(1)))
        self.log_btn = ttk.Button(
            bar, text="Open log", command=self.open_log, state="disabled"
        )
        self.log_btn.pack(side="right", padx=(0, g(1)))
        self.open_btn = ttk.Button(
            bar, text="Open output folder", command=self.open_out, state="disabled"
        )
        self.open_btn.pack(side="right", padx=(0, g(1)))

        self.status = ttk.Label(statusbar, text="No files yet", style="Muted.TLabel")
        self.status.pack(side="left")

        if HAVE_DND:
            # tkdnd delivers a drop to the widget under the cursor and does not
            # propagate to parents, so every widget a file can land on is
            # registered: the drop zone and its labels, the list and the tabs.
            for w in self._drop_widgets + [self.tree, self.preview, self.log_text]:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.on_drop)
        self._show_body()

    def _text_tab(self, title: str) -> tk.Text:
        """A read-only text tab in the theme's colours."""
        c, g = self.c, self.g
        frame = ttk.Frame(self.tabs, padding=(0, g(1), 0, 0))
        self.tabs.add(frame, text=title)
        text = tk.Text(
            frame,
            wrap="word",
            bg=c["card"],
            fg=c["ink"],
            insertbackground=c["ink"],
            selectbackground=c["sel_bg"],
            selectforeground=c["sel_fg"],
            inactiveselectbackground=c["sel_bg"],
            relief="flat",
            highlightbackground=c["line"],
            highlightcolor=c["focus"],
            highlightthickness=1,
            font=self.font_mono,
            padx=g(1.5),
            pady=g(1),
            state="disabled",
            height=8,
            width=40,
        )
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return text

    def _show_body(self):
        """The drop zone while the list is empty; the list and tabs after."""
        if self.files:
            self.empty.pack_forget()
            if not self.content.winfo_manager():
                self.content.pack(fill="both", expand=True)
        else:
            self.content.pack_forget()
            if not self.empty.winfo_manager():
                self.empty.pack(fill="both", expand=True)

    def _toggle_options(self):
        self.opts_open = not self.opts_open
        if self.opts_open:
            self.opts_panel.pack(fill="x")
            self.opts_toggle.configure(text="▾  Options")
        else:
            self.opts_panel.pack_forget()
            self.opts_toggle.configure(text="▸  Options")

    def _options_summary(self) -> str:
        folder = safe_display(self.out_dir.get())
        if len(folder) > 48:
            folder = folder[:20] + "…" + folder[-27:]
        where = (
            "next to each PDF" if self.out_mode.get() == "beside" else f"to {folder}"
        )
        extras = [
            name
            for name, var in (
                ("images", self.opt_images),
                ("equation crops", self.opt_math),
                ("page markers", self.opt_pages),
            )
            if var.get()
        ]
        text = f"Markdown {where}"
        return text + (" · with " + ", ".join(extras) if extras else "")

    def copy_version(self, _event=None) -> str:
        """Copy the bug-report line to the clipboard and say so."""
        line = bug_report_line(self.tess_version, windows_build())
        self.root.clipboard_clear()
        self.root.clipboard_append(line)
        self.status.configure(text=f"Copied: {line}")
        return line

    # ---------------------------------------------------------------- files
    def _sync_out(self):
        fixed = self.out_mode.get() == "fixed"
        self.out_entry.configure(state="normal" if fixed else "disabled")
        self.out_btn.configure(state="normal" if fixed else "disabled")
        self.opts_summary.configure(text=self._options_summary())

    def on_drop(self, event):
        self.add(self.root.tk.splitlist(event.data))

    def browse(self):
        paths = filedialog.askopenfilenames(
            title="Choose PDFs",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if paths:
            self.add(paths)

    def browse_folder(self):
        d = filedialog.askdirectory(title="Choose a folder of PDFs")
        if d:
            self.add([d])

    def add(self, raw) -> list:
        found: list[pathlib.Path] = []
        for r in raw:
            p = pathlib.Path(str(r).strip("{}"))
            if p.is_dir():
                found.extend(sorted(p.glob("*.pdf")))
            elif p.suffix.lower() == ".pdf":
                found.append(p)
        added = 0
        for p in found:
            if p in self.files:
                continue
            self.files.append(p)
            self.tree.insert("", "end", iid=str(p), text=" " + safe_display(p.name))
            self._set_row(str(p), "queued")
            added += 1
            self.settings["recent_files"] = recent_files(
                self.settings["recent_files"], [p]
            )
        self._save_settings()
        self._show_body()
        skipped = len(found) - added
        msg = f"{len(self.files)} file(s) ready"
        if skipped:
            msg += f" · {skipped} already listed"
        if not found and raw:
            msg = "Nothing added — those weren't PDFs"
        self.status.configure(text=msg)
        return found

    # ------------------------------------------------------- Send to / launch
    def _receive(self, raw: list):
        """Files from a launch argument or a hand-off (Tk thread only): add
        the PDFs and convert them now, or queue them behind the running
        batch. Anything else is skipped with one app-log line."""
        take, skip = launch_paths([str(r) for r in raw])
        for p in skip:
            app_log(f"skipped (not a PDF): {p}")
        new = self.add(take) if take else []
        self._raise_window()
        if skip and not new:
            self.status.configure(text=f"Skipped {len(skip)} file(s) that are not PDFs")
        if not new:
            return
        now, self.pending = handoff_plan(new, self.running, self.pending)
        if now:
            self.start(only=now)
        else:
            self.status.configure(
                text=f"{len(self.pending)} file(s) queued behind the current batch"
            )

    def _raise_window(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(300, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            pass

    def _sendto_toggle(self):
        from markerlite import sendto

        want = bool(self.sendto_var.get())
        exe = pathlib.Path(sys.executable)
        self.sendto_error.configure(text="")

        def work():
            try:
                if want:
                    sendto.create(exe)
                else:
                    sendto.remove()
                self.events.put(("sendto", want, None))
            except sendto.SendToError as exc:
                self.events.put(("sendto", want, str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _sendto_repair(self):
        from markerlite import sendto

        exe = pathlib.Path(sys.executable)

        def work():
            try:
                old = sendto.repair(exe)
                if old:
                    self.events.put(("sendto-repaired", old, None))
            except sendto.SendToError as exc:
                self.events.put(("sendto-repaired", None, str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def clear(self):
        if self.running:
            return
        self.files.clear()
        self.results.clear()
        self.rows.clear()
        self.tree.delete(*self.tree.get_children())
        self._set_preview("")
        self._set_text(self.log_text, "")
        self._show_body()
        self.open_btn.configure(state="disabled")
        self.log_btn.configure(state="disabled")
        self.md_btn.configure(state="disabled")
        self.math_btn.configure(state="disabled")
        self.log_paths = []
        self.status.configure(text="No files yet")

    def pick_out(self):
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self.out_dir.set(d)

    def outdir_for(self, pdf: pathlib.Path) -> pathlib.Path:
        return output_directory(pdf, self.out_mode.get(), self.out_dir.get())

    # ------------------------------------------------------------ conversion
    def start(self, only=None):
        files = list(only) if only else list(self.files)
        if self.running or not files:
            if not files:
                self.status.configure(text="Add some PDFs first")
            return
        self._check_tesseract()
        self.running = True
        # The token also counts convert()'s per-page checks, which is how
        # a row shows how far its conversion has got.
        self.cancel_token = ProgressToken(
            lambda src, pct: self.events.put(("progress", src, pct))
        )
        # While a batch runs, Convert is Cancel (no confirmation: a
        # cancelled file leaves no output and finished files stay).
        self.go.configure(text="Cancel", command=self.cancel)
        self.batch_total, self.batch_finished = len(files), 0
        for f in files:
            if self.tree.exists(str(f)):
                self._set_row(str(f), "queued", percent=None, elapsed=None)
        self.bar.pack(
            side="bottom", fill="x", pady=(self.g(1), 0), after=self._statusbar
        )
        self.bar.configure(value=0)
        self._set_text(self.log_text, "")
        # Tk variables belong to the main thread: read them here, once, and
        # hand the worker a plain snapshot. Reading them from the worker is a
        # data race, and it also let a mid-run checkbox change alter the batch.
        opts = snapshot_options(
            self.opt_images.get(),
            self.opt_math.get(),
            self.opt_pages.get(),
            self.out_mode.get(),
            self.out_dir.get(),
        )
        threading.Thread(
            target=self._worker,
            args=(files, opts, self.cancel_token),
            daemon=True,
        ).start()

    def cancel(self):
        """Cancel the running batch: the current file is abandoned between
        pages (a running Tesseract is killed), the rest are skipped."""
        act, text, state = cancel_pressed(
            self.running and self.cancel_token is not None
        )
        if not act:
            return
        # Feedback first, on this (Tk) thread, before the worker notices.
        self.status.configure(text=text)
        self.go.configure(state=state)
        if self.current_src and self.current_src in self.rows:
            self._set_row(self.current_src, "cancelling")
        self.cancel_token.cancel()

    def _worker(self, files: list[pathlib.Path], opts: ConversionOptions, token):
        try:
            from markerlite import convert
        except Exception:
            self.events.put(("fatal", traceback.format_exc()))
            return
        import datetime as _dt

        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logs: dict[pathlib.Path, list[str]] = {}

        def log(outdir: pathlib.Path, line: str):
            # One markerlite-run.log per output folder, appended per batch:
            # a batch header, then one line per file with its summary and
            # warnings, so a "why is this file empty" question has an answer
            # after the window is closed.
            path = outdir / "markerlite-run.log"
            try:
                with open(path, "a", encoding="utf-8") as fh:
                    if path not in logs:
                        fh.write(
                            f"=== markerlite run {stamp} ({len(files)} file(s)) ===\n"
                        )
                        logs[path] = []
                    fh.write(line + "\n")
                    logs[path].append(line)
            except Exception:
                pass
            # The same line in the window's Log tab.
            self.events.put(("log", line))

        def page_count(pdf: pathlib.Path) -> int:
            import pymupdf

            with pymupdf.open(pdf) as doc:
                return len(doc)

        outcome = run_batch(
            files, opts, convert, token, self.events.put, log, page_count=page_count
        )
        self.events.put(("finished", sorted(logs), outcome))

    def _drain(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "update-result":
                    self.show_update(ev[1])
                elif kind == "busy":
                    src = ev[1]
                    self.current_src = src
                    self.rows.setdefault(src, {})["t0"] = time.monotonic()
                    cancelling = (
                        self.cancel_token is not None and self.cancel_token.is_set()
                    )
                    self._set_row(src, "cancelling" if cancelling else "converting")
                    self.tree.see(src)
                    self.status.configure(
                        text=busy_status(pathlib.Path(src).name, cancelling)
                    )
                elif kind == "pages":
                    self._set_row(ev[1], pages=ev[2])
                elif kind == "progress":
                    _, src, pct = ev
                    row = self.rows.get(src, {})
                    if row.get("state") == "converting":
                        self._set_row(src, percent=pct, elapsed=self._since(src))
                    self._set_progress(pct)
                elif kind == "log":
                    self._append_text(self.log_text, ev[1])
                elif kind == "done":
                    _, src, md, stats = ev
                    eqs = stats.get("equations", 0)
                    warnings = self._warnings(stats)
                    self.results[src] = {
                        "md": md,
                        "eqs": eqs,
                        "stats": stats,
                        "warnings": warnings,
                        "provenance": self._provenance_of(md),
                    }
                    self._set_row(
                        src,
                        "done",
                        warnings=len(warnings),
                        pages=stats.get("pages") or self.rows.get(src, {}).get("pages"),
                        elapsed=self._since(src),
                    )
                    self._file_finished()
                    if not self.tree.selection():
                        self.tree.selection_set(src)
                elif kind in ("cancelled", "skipped"):
                    src = ev[1]
                    self._set_row(
                        src,
                        kind,
                        elapsed=self._since(src) if kind == "cancelled" else None,
                    )
                    self._file_finished()
                elif kind == "error":
                    _, src, msg = ev
                    self._set_row(src, "failed", elapsed=self._since(src))
                    self.results[src] = {"error": msg}
                    self._file_finished()
                elif kind == "fatal":
                    self._set_preview(
                        "markerlite could not be imported.\n\n"
                        + ev[1]
                        + "\nCheck that markerlite.py and table_recon.py sit next to "
                        "this file, and that pymupdf, scikit-learn, rapidfuzz, "
                        "regex and numpy are installed for this Python."
                    )
                    self._finish()
                elif kind == "handoff":
                    app_log(f"received {len(ev[1])} file(s) from another launch")
                    self._receive(ev[1])
                elif kind == "sendto":
                    _, want, err = ev
                    if err:
                        self.sendto_var.set(not want)
                        self.sendto_error.configure(text=f"Send to unavailable: {err}")
                        verb = "enable" if want else "disable"
                        app_log(f"Send to {verb} failed: {err}")
                    else:
                        app_log(f"Send to entry {'added' if want else 'removed'}")
                        self.status.configure(
                            text="Added to Explorer's Send to menu"
                            if want
                            else "Removed from Explorer's Send to menu"
                        )
                elif kind == "sendto-repaired":
                    _, old, err = ev
                    if err:
                        self.sendto_error.configure(text=f"Send to unavailable: {err}")
                        app_log(f"Send to check failed: {err}")
                    else:
                        app_log(
                            f"Send to shortcut repointed from {old} to {sys.executable}"
                        )
                        self.status.configure(
                            text="Send to entry updated to this markerlite folder"
                        )
                elif kind == "finished":
                    self.log_paths = list(ev[1]) if len(ev) > 1 else []
                    self.outcome = ev[2] if len(ev) > 2 else {}
                    self._finish()
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _finish(self):
        self.running = False
        self.cancel_token = None
        self.current_src = None
        self.go.configure(text="Convert", command=self.start, state="normal")
        self.bar.pack_forget()
        done = [r for r in self.results.values() if "md" in r]
        bad = sum(1 for r in self.results.values() if "error" in r)
        agg = {
            "pages": sum(r.get("stats", {}).get("pages", 0) for r in done),
            "bytes": sum(r.get("stats", {}).get("bytes", 0) for r in done),
            "figures": sum(r.get("stats", {}).get("figures", 0) for r in done),
            "equations": sum(r.get("stats", {}).get("equations", 0) for r in done),
            "ocr_pages": sum(r.get("stats", {}).get("ocr_pages", 0) for r in done),
            "words": sum(r.get("stats", {}).get("words", 0) for r in done),
        }
        parts = []
        if done:
            try:
                from markerlite import summarize

                parts.append(summarize(agg) + f" · {agg['words']:,} words")
            except Exception:
                parts.append(f"{len(done)} converted")
        warned = sum(1 for r in done if r.get("warnings"))
        if warned:
            parts.append(f"\u26a0 {warned} file{'s' * (warned != 1)} with warnings")
        if bad:
            parts.append(f"{bad} failed")
        self.status.configure(
            text=finish_status(self.outcome, " · ".join(parts) or "Nothing converted")
        )
        if done:
            self.open_btn.configure(state="normal")
            self.md_btn.configure(state="normal")
        if self.log_paths:
            self.log_btn.configure(state="normal")
        if any(r.get("eqs") for r in self.results.values()):
            self.math_btn.configure(state="normal")
        if self.pending:
            # Files sent while this batch ran: their batch starts now.
            queued, self.pending = self.pending, []
            self.root.after(100, lambda: self.start(only=queued))

    # ------------------------------------------------------------ rows
    def _set_row(self, src: str, state: str | None = None, **fields):
        """Update a row's state and redraw its Pages, Status and Time cells.
        The text of every state comes from gui_logic.status_cell."""
        if not self.tree.exists(src):
            return
        row = self.rows.setdefault(src, {"state": "queued"})
        if state is not None:
            row["state"] = state
            if state != "converting":
                row["percent"] = None
        row.update(fields)
        text, dot = status_cell(
            row["state"], row.get("percent"), row.get("warnings", 0)
        )
        pages = row.get("pages")
        self.tree.item(
            src,
            image=self.dots[dot],
            values=(pages if pages else "", text, elapsed_text(row.get("elapsed"))),
        )

    def _since(self, src: str):
        t0 = self.rows.get(src, {}).get("t0")
        return None if t0 is None else time.monotonic() - t0

    def _set_progress(self, percent: int):
        self.bar.configure(
            value=overall_progress(self.batch_finished, percent, self.batch_total)
        )

    def _file_finished(self):
        self.batch_finished += 1
        self._set_progress(0)

    def _tree_click(self, event):
        """A click on "Done with N warnings" opens Show warnings."""
        row = self.tree.identify_row(event.y)
        if row and self._on_warnings_cell(row, event.x):
            self._show_warnings(row)

    def _tree_key(self, _event=None):
        """Enter on a row with warnings opens them, like the click."""
        sel = self.tree.selection()
        if sel and self.rows.get(sel[0], {}).get("warnings"):
            self._show_warnings(sel[0])

    def _on_warnings_cell(self, row: str, x: int) -> bool:
        info = self.rows.get(row, {})
        return (
            info.get("state") == "done"
            and bool(info.get("warnings"))
            and self.tree.identify_column(x) == "#2"
        )

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _append_text(self, widget: tk.Text, line: str):
        widget.configure(state="normal")
        widget.insert("end", line + "\n")
        widget.configure(state="disabled")
        widget.see("end")

    # ---------------------------------------------------------------- results
    @staticmethod
    def _warnings(stats: dict) -> list[str]:
        try:
            return warning_lines(stats)
        except Exception:
            return []

    @staticmethod
    def _summary(stats: dict) -> str:
        try:
            return summary_text(stats)
        except Exception:
            return ""

    @staticmethod
    def _provenance_of(md: str) -> list[str]:
        """The <!-- source: ... --> comments convert() wrote at the top."""
        return provenance_comments(pathlib.Path(md))

    def _tree_motion(self, event):
        row = self.tree.identify_row(event.y)
        on_warnings = bool(row) and self._on_warnings_cell(row, event.x)
        self.tree.configure(cursor="hand2" if on_warnings else "")
        if row != self._tip_row:
            self._hide_tip()
            self._tip_row = row
            res = self.results.get(row)
            if res and "stats" in res:
                text = self._summary(res["stats"])
                text += "\n" + row_details(res["stats"])
                for cite in res.get("provenance", []):
                    text += "\n" + cite
                self._show_tip(text, event.x_root + 12, event.y_root + 16)

    def _show_tip(self, text: str, x: int, y: int):
        tip = tk.Toplevel(self.root)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tip,
            text=text,
            justify="left",
            bg=self.c["card"],
            fg=self.c["ink"],
            relief="solid",
            borderwidth=1,
            font=self.font_body,
            padx=8,
            pady=5,
            wraplength=520,
        ).pack()
        self._tip = tip

    def _hide_tip(self):
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None
        self._tip_row = None

    # ------------------------------------------------------------ row menu
    def _row_state(self, src: str) -> dict:
        res = self.results.get(src, {})
        md = res.get("md")
        return menu_state(
            pdf_exists=pathlib.Path(src).is_file(),
            md_exists=bool(md) and pathlib.Path(md).is_file(),
            converted="stats" in res,
            running=self.running,
        )

    def _row_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self._hide_tip()
        state = self._row_state(row)
        actions = {
            "Open Markdown": lambda: self._reveal(
                pathlib.Path(self.results[row]["md"])
            ),
            "Open PDF": lambda: self._reveal(pathlib.Path(row)),
            "Show in folder": lambda: self._show_in_folder(row),
            "Copy Markdown": lambda: self._copy_markdown(row),
            "Show warnings": lambda: self._show_warnings(row),
            "Re-convert": lambda: self._reconvert(row),
            "Remove from list": lambda: self._remove(row),
        }
        menu = tk.Menu(self.root, tearoff=0)
        for label in MENU_ITEMS:
            if label in ("Show warnings", "Remove from list"):
                menu.add_separator()
            menu.add_command(
                label=label,
                command=actions[label],
                state="normal" if state[label] else "disabled",
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_in_folder(self, src: str):
        """Select the Markdown (or, before conversion, the PDF) in the file
        manager. The path is one argument; no shell is involved."""
        md = self.results.get(src, {}).get("md")
        target = (
            pathlib.Path(md) if md and pathlib.Path(md).is_file() else pathlib.Path(src)
        )
        try:
            subprocess.Popen(reveal_command(target))  # noqa: S603
        except Exception as exc:
            self.status.configure(text=f"Could not show folder: {safe_display(exc)}")

    def _copy_markdown(self, src: str):
        try:
            text = pathlib.Path(self.results[src]["md"]).read_text(encoding="utf-8")
        except Exception as exc:
            self.status.configure(text=f"Could not read output: {safe_display(exc)}")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status.configure(
            text=f"Copied Markdown of {safe_display(pathlib.Path(src).name)}"
        )

    def _show_warnings(self, src: str):
        lines = warning_details(self.results.get(src, {}).get("stats", {}))
        win = tk.Toplevel(self.root)
        win.title(f"Warnings — {safe_display(pathlib.Path(src).name)}")
        win.transient(self.root)
        text = tk.Text(
            win,
            wrap="word",
            width=80,
            height=min(20, len(lines) + 2),
            font=self.font_body,
            padx=self.g(1.5),
            pady=self.g(1),
            bg=self.c["card"],
            fg=self.c["ink"],
            relief="flat",
        )
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")  # read-only
        text.pack(fill="both", expand=True)
        win.configure(bg=self.c["bg"])
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=self.g(1))
        win.bind("<Escape>", lambda _e: win.destroy())

    def _reconvert(self, src: str):
        """Convert just this file again with the current settings."""
        if self.running:
            return
        self.start(only=[pathlib.Path(src)])

    def _remove(self, src: str):
        """Take the row off the list. Never touches the disk."""
        if self.running:
            return
        path = pathlib.Path(src)
        if path in self.files:
            self.files.remove(path)
        self.results.pop(src, None)
        self.rows.pop(src, None)
        if self.tree.exists(src):
            self.tree.delete(src)
        self._set_preview("")
        self._show_body()
        self.status.configure(text=f"{len(self.files)} file(s) ready")

    def _preview_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        has_sel = bool(self.preview.tag_ranges("sel"))
        menu.add_command(
            label="Copy",
            command=self._preview_copy,
            state="normal" if has_sel else "disabled",
        )
        menu.add_command(label="Select all", command=self._preview_select_all)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _preview_copy(self):
        try:
            text = self.preview.get("sel.first", "sel.last")
        except tk.TclError:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _preview_select_all(self):
        self.preview.tag_add("sel", "1.0", "end-1c")
        self.preview.focus_set()

    # --------------------------------------------------------------- preview
    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        res = self.results.get(sel[0])
        if not res:
            self._set_preview("Not converted yet.")
            return
        if "error" in res:
            self._set_preview("Conversion failed.\n\n" + res["error"])
            return
        try:
            text = pathlib.Path(res["md"]).read_text(encoding="utf-8")
        except Exception as exc:
            text = f"Could not read output: {safe_display(exc)}"
        if len(text) > 200_000:
            text = text[:200_000] + "\n\n… truncated for preview …"
        self._set_preview(text)

    def _set_preview(self, text: str):
        self._set_text(self.preview, text)

    # ---------------------------------------------------------------- opening
    def _reveal(self, path: pathlib.Path):
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            self.status.configure(text=f"Could not open folder: {safe_display(exc)}")

    def open_out(self):
        """Open each distinct output directory.

        With "next to the original PDF" and inputs drawn from several folders,
        the results are spread across all of them - opening only the first hides
        the rest.
        """
        seen = []
        for res in self.results.values():
            if "md" not in res:
                continue
            d = pathlib.Path(res["md"]).parent
            if d not in seen:
                seen.append(d)
        if not seen:
            return
        for d in seen[:4]:
            self._reveal(d)
        if len(seen) > 4:
            self.status.configure(text=f"Opened 4 of {len(seen)} output folders")

    def open_log(self):
        """Open this batch's markerlite-run.log (one per output folder)."""
        for path in self.log_paths[:4]:
            if pathlib.Path(path).exists():
                self._reveal(pathlib.Path(path))

    def open_md(self):
        """Open the selected file's Markdown in the system default editor."""
        sel = self.tree.selection()
        res = self.results.get(sel[0]) if sel else None
        if not res or "md" not in res:
            res = next((r for r in self.results.values() if "md" in r), None)
        if res:
            self._reveal(pathlib.Path(res["md"]))

    def open_math(self):
        for src, res in self.results.items():
            if res.get("eqs"):
                stem = pathlib.Path(src).stem
                d = pathlib.Path(res["md"]).parent / f"{stem}_math"
                if d.exists():
                    self._reveal(d)
                    return


def write_diagnostics() -> pathlib.Path:
    """`markerlite --diag`: dump what the app can see about its environment.

    A windowed exe has no console, so this goes to a file beside it. Meant for
    exactly one situation: drag-and-drop not working, and needing the actual
    reason rather than a guess.
    """
    import platform
    import traceback

    frozen = getattr(sys, "frozen", False)
    base = pathlib.Path(
        getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent)
    )
    from markerlite import __version__

    lines = [
        f"markerlite {__version__}",
        f"python      {sys.version.split()[0]}  frozen={frozen}",
        f"platform    {platform.system()} {platform.release()} {platform.machine()}"
        f"  PROCESSOR_ARCHITECTURE={os.environ.get('PROCESSOR_ARCHITECTURE')}",
        f"bundle dir  {base}",
        f"HAVE_DND    {HAVE_DND}",
        f"DND_ERROR   {DND_ERROR or '-'}",
    ]
    tesseract = discover_tesseract()
    lines.append(
        f"tesseract   {tesseract_version(tesseract)}  path={tesseract}"
        if tesseract
        else "tesseract   not found"
    )
    try:
        import tkinter

        tcl = tkinter.Tcl()
        lines.append(f"tcl/tk      {tcl.eval('info patchlevel')}")
    except Exception as exc:
        lines.append(f"tcl/tk      failed: {exc!r}")
    tkdnd = base / "tkinterdnd2" / "tkdnd"
    lines.append(f"tkdnd dir   {tkdnd}  exists={tkdnd.is_dir()}")
    if tkdnd.is_dir():
        for sub in sorted(tkdnd.iterdir()):
            files = sorted(p.name for p in sub.iterdir()) if sub.is_dir() else []
            lines.append(f"   {sub.name}: {', '.join(files) if files else '(empty)'}")
    if HAVE_DND:
        try:
            r = TkinterDnD.Tk()
            lines.append(f"TkinterDnD.Tk()  OK  (tkdnd {r.TkdndVersion})")
            r.destroy()
        except Exception:
            lines.append("TkinterDnD.Tk()  FAILED:\n" + traceback.format_exc())
    # The theme as the window would load it: sv-ttk, then the recoloured
    # accent (CI asserts this line for the source run and the frozen exe).
    try:
        r = TkinterDnD.Tk() if HAVE_DND else tk.Tk()
        r.withdraw()
        theme = theme_for(windows_apps_use_light(), os.environ.get("MARKERLITE_THEME"))
        lines.append(f"theme       {load_theme(r, theme)}")
        r.destroy()
    except Exception as exc:
        lines.append(f"theme       FAILED: {type(exc).__name__}: {exc}")
    exe_dir = pathlib.Path(sys.executable).parent if frozen else base
    out = exe_dir / "markerlite-diag.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main():
    if "--diag" in sys.argv[1:]:
        out = write_diagnostics()
        try:
            print(f"wrote {out}")
        except Exception:
            pass
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    events: "queue.Queue[tuple]" = queue.Queue()
    if sys.platform == "win32":
        from markerlite import instance

        single = instance.SingleInstance()
        if not single.primary:
            # A window is open: give it the files and exit. If it does not
            # answer within ~5 s, open a window here with them instead.
            if instance.hand_off(args):
                return
            app_log("hand-off failed; opening a second window with the files")
        else:
            try:
                listener = instance.listen()
            except OSError as exc:
                app_log(f"single-instance listener unavailable: {exc}")
            else:
                threading.Thread(
                    target=instance.serve,
                    args=(
                        listener,
                        lambda paths: events.put(("handoff", paths)),
                        app_log,
                    ),
                    daemon=True,
                ).start()
    root = TkinterDnD.Tk() if HAVE_DND else tk.Tk()
    App(root, events=events, initial=args)
    root.mainloop()


if __name__ == "__main__":
    main()
