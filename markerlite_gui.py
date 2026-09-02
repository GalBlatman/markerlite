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
import tkinter as tk
import traceback
from tkinter import filedialog, ttk

# Crisp text on high-DPI Windows displays; harmless elsewhere.
if sys.platform == "win32":
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
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
PAD = 10

BG = "#faf9f7"
CARD = "#ffffff"
INK = "#1f1d1b"
MUTED = "#6b6763"
LINE = "#d9d5d0"
ACCENT = "#4a6fa5"
OK = "#2f7d4f"
BAD = "#b3402f"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.files: list[pathlib.Path] = []
        self.results: dict[str, dict] = {}
        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.running = False

        root.title(f"{APP} — PDF to Markdown")
        root.geometry("1000x700")
        root.minsize(820, 560)
        root.configure(bg=BG)

        self._style()
        self._build()
        self._set_icon()
        self.root.after(80, self._drain)

    def _set_icon(self):
        """Title-bar and taskbar icon. Best effort: a missing file is not fatal.

        PyInstaller unpacks bundled data under sys._MEIPASS; from source the
        assets folder sits beside this file.
        """
        base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
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
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=BG, foreground=INK, font=("Segoe UI", 10))
        s.configure("Card.TFrame", background=CARD, relief="flat")
        s.configure("TLabel", background=BG, foreground=INK)
        s.configure("Muted.TLabel", background=BG, foreground=MUTED)
        s.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
        s.configure("Head.TLabel", background=BG, foreground=INK,
                    font=("Segoe UI Semibold", 10))
        s.configure("TButton", padding=(12, 6))
        s.configure("Go.TButton", padding=(18, 8), font=("Segoe UI Semibold", 10))
        s.configure("TCheckbutton", background=BG)
        s.configure("TRadiobutton", background=BG)
        s.configure("Treeview", rowheight=24, fieldbackground=CARD,
                    background=CARD, borderwidth=0)
        s.configure("Treeview.Heading", font=("Segoe UI", 9))
        s.configure("TProgressbar", troughcolor=BG, background=ACCENT,
                    borderwidth=0, thickness=6)

    # ---------------------------------------------------------------- layout
    def _build(self):
        root = self.root

        # ---- drop zone -------------------------------------------------
        drop = tk.Frame(root, bg=CARD, highlightbackground=LINE,
                        highlightthickness=1)
        drop.pack(fill="x", padx=PAD, pady=(PAD, 6))
        self.drop = drop

        inner = tk.Frame(drop, bg=CARD)
        inner.pack(pady=18)
        self.drop_label = tk.Label(
            inner,
            text="Drop PDFs here" if HAVE_DND else "Add PDFs to convert",
            bg=CARD, fg=INK, font=("Segoe UI Semibold", 13),
        )
        self.drop_label.pack()
        hint = tk.Label(
            inner,
            text="or click to browse — use Add folder for a whole directory",
            bg=CARD, fg=MUTED, font=("Segoe UI", 9),
        )
        hint.pack(pady=(3, 0))

        for w in (drop, inner, self.drop_label):
            w.bind("<Button-1>", lambda _e: self.browse())
        for w in (drop, inner):
            w.bind("<Enter>", lambda _e: drop.configure(highlightbackground=ACCENT))
            w.bind("<Leave>", lambda _e: drop.configure(highlightbackground=LINE))

        if HAVE_DND:
            # tkdnd delivers a drop to the widget under the cursor and does not
            # propagate to parents. The zone is mostly covered by the inner
            # frame and its two labels, so register all of them - registering
            # only the outer frame meant a drop on the text went nowhere.
            for w in (drop, inner, self.drop_label, hint):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.on_drop)

        # ---- middle: file list + preview -------------------------------
        mid = ttk.Frame(root)
        mid.pack(fill="both", expand=True, padx=PAD)

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=False)
        ttk.Label(left, text="Files", style="Head.TLabel").pack(anchor="w")

        table = ttk.Frame(left)
        table.pack(fill="both", expand=True, pady=(4, 0))
        self.tree = ttk.Treeview(table, columns=("status",), show="tree headings",
                                 selectmode="browse", height=12)
        self.tree.heading("#0", text="File")
        self.tree.heading("status", text="Status")
        self.tree.column("#0", width=300, stretch=True)
        self.tree.column("status", width=150, stretch=False, anchor="w")
        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("done", foreground=OK)
        self.tree.tag_configure("error", foreground=BAD)
        self.tree.tag_configure("busy", foreground=ACCENT)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.Frame(mid)
        right.pack(side="left", fill="both", expand=True, padx=(PAD, 0))
        ttk.Label(right, text="Preview", style="Head.TLabel").pack(anchor="w")
        pv = ttk.Frame(right)
        pv.pack(fill="both", expand=True, pady=(4, 0))
        self.preview = tk.Text(
            pv, wrap="word", bg=CARD, fg=INK, relief="flat",
            highlightbackground=LINE, highlightthickness=1,
            font=("Consolas", 9), padx=10, pady=8, state="disabled",
        )
        pvsb = ttk.Scrollbar(pv, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=pvsb.set)
        self.preview.pack(side="left", fill="both", expand=True)
        pvsb.pack(side="right", fill="y")

        # ---- options ----------------------------------------------------
        opts = ttk.Frame(root)
        opts.pack(fill="x", padx=PAD, pady=(PAD, 4))

        self.out_mode = tk.StringVar(value="beside")
        self.out_dir = tk.StringVar(value=str(pathlib.Path.home() / "Documents" / "markdown"))
        self.opt_images = tk.BooleanVar(value=False)
        self.opt_math = tk.BooleanVar(value=False)
        self.opt_pages = tk.BooleanVar(value=False)

        # Two independently packed columns, so a long checkbox label can never
        # be clipped by the grid geometry of the output controls.
        left_opts = ttk.Frame(opts)
        left_opts.pack(side="left", fill="x", expand=True)
        right_opts = ttk.Frame(opts)
        right_opts.pack(side="right", anchor="n", padx=(24, 0))

        ttk.Label(left_opts, text="Output", style="Head.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        ttk.Radiobutton(left_opts, text="Next to the original PDF", value="beside",
                        variable=self.out_mode, command=self._sync_out).grid(
            row=1, column=0, sticky="w", columnspan=3)
        ttk.Radiobutton(left_opts, text="This folder:", value="fixed",
                        variable=self.out_mode, command=self._sync_out).grid(
            row=2, column=0, sticky="w")
        self.out_entry = ttk.Entry(left_opts, textvariable=self.out_dir, width=38)
        self.out_entry.grid(row=2, column=1, sticky="w", padx=(6, 4))
        self.out_btn = ttk.Button(left_opts, text="Browse…", command=self.pick_out)
        self.out_btn.grid(row=2, column=2, sticky="w")

        ttk.Label(right_opts, text="Extras", style="Head.TLabel").pack(
            anchor="w", pady=(0, 2))
        ttk.Checkbutton(right_opts, text="Extract images",
                        variable=self.opt_images).pack(anchor="w")
        ttk.Checkbutton(right_opts, text="Crop equations for transcription",
                        variable=self.opt_math).pack(anchor="w")
        ttk.Checkbutton(right_opts, text="Insert <!-- page N --> markers",
                        variable=self.opt_pages).pack(anchor="w")
        self._sync_out()

        # ---- action bar --------------------------------------------------
        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=PAD, pady=(4, 4))
        self.go = ttk.Button(bar, text="Convert", style="Go.TButton",
                             command=self.start)
        self.go.pack(side="left")
        ttk.Button(bar, text="Add folder…", command=self.browse_folder).pack(
            side="left", padx=6)
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left")
        self.open_btn = ttk.Button(bar, text="Open output folder",
                                   command=self.open_out, state="disabled")
        self.open_btn.pack(side="left")
        self.md_btn = ttk.Button(bar, text="Open Markdown",
                                 command=self.open_md, state="disabled")
        self.md_btn.pack(side="left", padx=6)
        self.math_btn = ttk.Button(bar, text="Open equation crops",
                                   command=self.open_math, state="disabled")
        self.math_btn.pack(side="left")

        # The summary line gets its own row: sharing the button row clipped it
        # once the text grew to "5 pages -> 7 KB Markdown - 2 figures - ...".
        self.bar = ttk.Progressbar(root, mode="determinate")
        statusbar = ttk.Frame(root)
        statusbar.pack(fill="x", padx=PAD, pady=(0, PAD))
        self.status = ttk.Label(statusbar, text="No files yet", style="Muted.TLabel")
        self.status.pack(side="left")
        if not HAVE_DND:
            self.status.configure(
                text="Drag-and-drop unavailable (" + (DND_ERROR or "tkinterdnd2 missing")
                + ") — use the drop zone click or Add folder")

    # ---------------------------------------------------------------- files
    def _sync_out(self):
        fixed = self.out_mode.get() == "fixed"
        self.out_entry.configure(state="normal" if fixed else "disabled")
        self.out_btn.configure(state="normal" if fixed else "disabled")

    def on_drop(self, event):
        self.add(self.root.tk.splitlist(event.data))

    def browse(self):
        paths = filedialog.askopenfilenames(
            title="Choose PDFs", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if paths:
            self.add(paths)

    def browse_folder(self):
        d = filedialog.askdirectory(title="Choose a folder of PDFs")
        if d:
            self.add([d])

    def add(self, raw):
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
            self.tree.insert("", "end", iid=str(p), text=p.name, values=("queued",))
            added += 1
        skipped = len(found) - added
        msg = f"{len(self.files)} file(s) ready"
        if skipped:
            msg += f" · {skipped} already listed"
        if not found and raw:
            msg = "Nothing added — those weren't PDFs"
        self.status.configure(text=msg)

    def clear(self):
        if self.running:
            return
        self.files.clear()
        self.results.clear()
        self.tree.delete(*self.tree.get_children())
        self._set_preview("")
        self.open_btn.configure(state="disabled")
        self.md_btn.configure(state="disabled")
        self.math_btn.configure(state="disabled")
        self.status.configure(text="No files yet")

    def pick_out(self):
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self.out_dir.set(d)

    def outdir_for(self, pdf: pathlib.Path) -> pathlib.Path:
        if self.out_mode.get() == "fixed":
            return pathlib.Path(self.out_dir.get())
        return pdf.parent

    # ------------------------------------------------------------ conversion
    def start(self):
        if self.running or not self.files:
            if not self.files:
                self.status.configure(text="Add some PDFs first")
            return
        self.running = True
        self.go.configure(state="disabled")
        self.bar.pack(fill="x", padx=PAD, pady=(0, 6))
        self.bar.configure(maximum=len(self.files), value=0)
        # Tk variables belong to the main thread: read them here, once, and
        # hand the worker a plain snapshot. Reading them from the worker is a
        # data race, and it also let a mid-run checkbox change alter the batch.
        opts = {
            "images": self.opt_images.get(),
            "math": self.opt_math.get(),
            "page_markers": self.opt_pages.get(),
            "mode": self.out_mode.get(),
            "dir": self.out_dir.get(),
        }
        threading.Thread(target=self._worker, args=(list(self.files), opts),
                         daemon=True).start()

    def _worker(self, files: list[pathlib.Path], opts: dict):
        try:
            from markerlite import convert
        except Exception:
            self.events.put(("fatal", traceback.format_exc()))
            return
        for pdf in files:
            self.events.put(("busy", str(pdf)))
            try:
                outdir = (pathlib.Path(opts["dir"]) if opts["mode"] == "fixed"
                          else pdf.parent)
                outdir.mkdir(parents=True, exist_ok=True)
                md, manifest = convert(pdf, outdir, opts["images"], opts["math"],
                                       opts["page_markers"])
                self.events.put(("done", str(pdf), str(md),
                                 manifest.get("stats", {})))
            except Exception as exc:
                self.events.put(("error", str(pdf), f"{type(exc).__name__}: {exc}"))
        self.events.put(("finished",))

    def _drain(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "busy":
                    self.tree.item(ev[1], values=("converting…",), tags=("busy",))
                    self.tree.see(ev[1])
                    self.status.configure(text=f"Converting {pathlib.Path(ev[1]).name}")
                elif kind == "done":
                    _, src, md, stats = ev
                    eqs = stats.get("equations", 0)
                    label = "converted" + (f" · {eqs} eq" if eqs else "")
                    self.tree.item(src, values=(label,), tags=("done",))
                    self.results[src] = {"md": md, "eqs": eqs, "stats": stats}
                    self.bar.step(1)
                    if not self.tree.selection():
                        self.tree.selection_set(src)
                elif kind == "error":
                    _, src, msg = ev
                    self.tree.item(src, values=("failed",), tags=("error",))
                    self.results[src] = {"error": msg}
                    self.bar.step(1)
                elif kind == "fatal":
                    self._set_preview(
                        "markerlite could not be imported.\n\n" + ev[1] +
                        "\nCheck that markerlite.py and table_recon.py sit next to "
                        "this file, and that pymupdf, scikit-learn, rapidfuzz, "
                        "regex and numpy are installed for this Python."
                    )
                    self._finish()
                elif kind == "finished":
                    self._finish()
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _finish(self):
        self.running = False
        self.go.configure(state="normal")
        self.bar.pack_forget()
        done = [r for r in self.results.values() if "md" in r]
        bad = sum(1 for r in self.results.values() if "error" in r)
        agg = {
            "pages": sum(r.get("stats", {}).get("pages", 0) for r in done),
            "bytes": sum(r.get("stats", {}).get("bytes", 0) for r in done),
            "figures": sum(r.get("stats", {}).get("figures", 0) for r in done),
            "equations": sum(r.get("stats", {}).get("equations", 0) for r in done),
            "ocr_pages": sum(r.get("stats", {}).get("ocr_pages", 0) for r in done),
        }
        parts = []
        if done:
            try:
                from markerlite import summarize
                parts.append(summarize(agg))
            except Exception:
                parts.append(f"{len(done)} converted")
        if bad:
            parts.append(f"{bad} failed")
        self.status.configure(text=" · ".join(parts) or "Nothing converted")
        if done:
            self.open_btn.configure(state="normal")
            self.md_btn.configure(state="normal")
        if any(r.get("eqs") for r in self.results.values()):
            self.math_btn.configure(state="normal")

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
            text = f"Could not read output: {exc}"
        if len(text) > 200_000:
            text = text[:200_000] + "\n\n… truncated for preview …"
        self._set_preview(text)

    def _set_preview(self, text: str):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

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
            self.status.configure(text=f"Could not open folder: {exc}")

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
            self.status.configure(
                text=f"Opened 4 of {len(seen)} output folders")

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


def main():
    root = TkinterDnD.Tk() if HAVE_DND else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
