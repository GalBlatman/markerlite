"""Capture real Windows menus/dialogs with synthetic fixtures only.

A manual/CI smoke check, never imported by unit tests. The update dialog
uses the real user-requested handler once per theme. No replies are mocked.
Unavailable desktop states are recorded rather than replaced with images.
"""

from __future__ import annotations

import ctypes
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import tkinter as tk
from ctypes import wintypes

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def frame_bounds(window):
    """Visible frame bounds exclude Windows' invisible resize border."""
    window.update_idletasks()
    hwnd = int(window.wm_frame(), 16)
    rect = wintypes.RECT()
    dwm = ctypes.windll.dwmapi.DwmGetWindowAttribute
    dwm.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    if dwm(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        user = ctypes.windll.user32
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        if not user.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise OSError("window bounds unavailable")
    return rect


def capture(window, destination):
    import numpy as np
    import pymupdf

    user, gdi = ctypes.windll.user32, ctypes.windll.gdi32
    user.GetDC.argtypes, user.GetDC.restype = [wintypes.HWND], wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    gdi.CreateCompatibleDC.argtypes, gdi.CreateCompatibleDC.restype = (
        [wintypes.HDC],
        wintypes.HDC,
    )
    gdi.CreateCompatibleBitmap.argtypes, gdi.CreateCompatibleBitmap.restype = (
        [wintypes.HDC, ctypes.c_int, ctypes.c_int],
        wintypes.HBITMAP,
    )
    gdi.SelectObject.argtypes, gdi.SelectObject.restype = (
        [wintypes.HDC, wintypes.HGDIOBJ],
        wintypes.HGDIOBJ,
    )
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    gdi.BitBlt.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
    ]
    gdi.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.UINT,
    ]

    class Header(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("width", wintypes.LONG),
            ("height", wintypes.LONG),
            ("planes", wintypes.WORD),
            ("bits", wintypes.WORD),
            ("compression", wintypes.DWORD),
            ("image_size", wintypes.DWORD),
            ("xppm", wintypes.LONG),
            ("yppm", wintypes.LONG),
            ("colours", wintypes.DWORD),
            ("important", wintypes.DWORD),
        ]

    if isinstance(window, wintypes.RECT):
        rect = window
    else:
        rect = frame_bounds(window)
    width, height = rect.right - rect.left, rect.bottom - rect.top
    screen = user.GetDC(None)
    memory = gdi.CreateCompatibleDC(screen)
    bitmap = gdi.CreateCompatibleBitmap(screen, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        if not gdi.BitBlt(
            memory, 0, 0, width, height, screen, rect.left, rect.top, 0x00CC0020
        ):
            raise OSError("desktop capture unavailable")
        gdi.SelectObject(memory, old)
        old = None
        header = Header(ctypes.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(width * height * 4)
        if not gdi.GetDIBits(
            memory, bitmap, 0, height, pixels, ctypes.byref(header), 0
        ):
            raise OSError("desktop pixels unavailable")
        image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)[
            :, :, 2::-1
        ]
        if image.std() < 1:
            raise OSError("desktop capture is blank")
        pymupdf.Pixmap(pymupdf.csRGB, width, height, image.tobytes(), False).save(
            destination
        )
    finally:
        if old is not None:
            gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(None, screen)


def pump(root, seconds=0.3):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        root.update()
        time.sleep(0.02)


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows only; other-platform captures are not substitutes.")
    import markerlite_gui as gui

    out = ROOT / "gui-screenshots"
    out.mkdir(exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(
        prefix="markerlite-screenshot-settings-"
    ) as settings:
        os.environ["APPDATA"] = os.environ["LOCALAPPDATA"] = settings
        root = gui.TkinterDnD.Tk() if gui.HAVE_DND else tk.Tk()
        app = gui.App(root)
        from markerlite.gui_logic import window_title

        assert root.title() == window_title()
        assert app.opt_grids.get() is False
        checked_title = root.title()
        app.add([ROOT / "tests/fixtures/hard.pdf"])
        try:
            for theme in ("light", "dark"):
                os.environ["MARKERLITE_THEME"] = theme
                app.theme_choice.set(theme)
                app.change_theme()
                root.lift()
                pump(root)
                if not app.opts_open:
                    app._toggle_options()
                filename = f"{theme}-table-options.png"
                capture(root, out / filename)
                records.append(
                    {"file": filename, "state": "captured; grids default off"}
                )
                for menu_index, (name, menu) in enumerate(app.menus.items()):
                    app._refresh_menus()
                    filename = f"{theme}-menu-{name.lower()}.png"
                    print(f"Capturing {filename}", flush=True)

                    hwnd = int(root.wm_frame(), 16)
                    bounds = frame_bounds(root)
                    user = ctypes.windll.user32
                    user.GetWindowRect.argtypes = [
                        wintypes.HWND,
                        ctypes.POINTER(wintypes.RECT),
                    ]
                    user.PostMessageW.argtypes = [
                        wintypes.HWND,
                        wintypes.UINT,
                        wintypes.WPARAM,
                        wintypes.LPARAM,
                    ]
                    user.GetMenu.argtypes, user.GetMenu.restype = (
                        [wintypes.HWND],
                        wintypes.HMENU,
                    )
                    user.GetMenuItemRect.argtypes = [
                        wintypes.HWND,
                        wintypes.HMENU,
                        wintypes.UINT,
                        ctypes.POINTER(wintypes.RECT),
                    ]
                    item = wintypes.RECT()
                    if user.GetMenuItemRect(
                        hwnd, user.GetMenu(hwnd), menu_index, ctypes.byref(item)
                    ):
                        position = (item.left, item.bottom)
                    else:
                        position = (root.winfo_rootx(), root.winfo_rooty())

                    def snapshot(filename=filename, bounds=bounds, hwnd=hwnd):
                        time.sleep(0.4)
                        try:
                            # No Tk calls from this worker: native menu.post()
                            # owns the main thread until Windows dismisses it.
                            capture(bounds, out / filename)
                            records.append(
                                {
                                    "file": filename,
                                    "state": "captured; requires visual review",
                                }
                            )
                        except Exception as exc:
                            records.append(
                                {"file": filename, "state": f"unavailable: {exc}"}
                            )
                        finally:
                            # Tk menu.unpost() has no effect on Windows. Its
                            # own window receives WM_CANCELMODE instead.
                            user.PostMessageW(hwnd, 0x001F, 0, 0)
                            # The native menu loop consumes Escape before Tk's
                            # window procedure. Post only to our own window;
                            # no global keyboard input is injected.
                            user.PostMessageW(hwnd, 0x0100, 0x1B, 0)
                            user.PostMessageW(hwnd, 0x0101, 0x1B, 0)
                            print(f"Captured/dismissed {filename}", flush=True)

                    worker = threading.Thread(target=snapshot)
                    worker.start()
                    try:
                        menu.post(*position)
                    finally:
                        worker.join(timeout=5)
                        if worker.is_alive():
                            raise RuntimeError("menu capture did not finish")
                    pump(root, 0.1)
                for name, command in (
                    ("preferences", app.preferences),
                    ("ocr", app.check_ocr),
                    ("updates", app.check_updates),
                ):
                    before = set(root.winfo_children())
                    command()
                    deadline = time.monotonic() + 12
                    window = None
                    while time.monotonic() < deadline:
                        pump(root, 0.1)
                        windows = [
                            w
                            for w in root.winfo_children()
                            if w not in before and isinstance(w, tk.Toplevel)
                        ]
                        if windows:
                            window = windows[-1]
                            break
                    filename = f"{theme}-{name}.png"
                    print(f"Capturing {filename}", flush=True)
                    if window is None:
                        records.append(
                            {
                                "file": filename,
                                "state": "unavailable: no dialog within 12 seconds",
                            }
                        )
                        continue
                    window.lift()
                    pump(root)
                    try:
                        capture(window, out / filename)
                        records.append(
                            {
                                "file": filename,
                                "state": "captured; requires visual review",
                            }
                        )
                    except OSError as exc:
                        records.append(
                            {"file": filename, "state": f"unavailable: {exc}"}
                        )
                    finally:
                        window.destroy()
        finally:
            thread = getattr(app, "update_thread", None)
            if thread is not None:
                thread.join(timeout=12)
                if thread.is_alive():
                    raise RuntimeError("update request did not finish")
            root.destroy()
    manifest = {
        "source": "Real Windows source App; only tests/fixtures/hard.pdf; isolated settings; update handler uses its real response, never mocked.",
        "window_title": checked_title,
        "table_grids_default": False,
        "captures": records,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
