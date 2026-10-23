"""Launch the real Windows exe and check its versioned Tk window title."""

from __future__ import annotations

import ctypes
import pathlib
import subprocess
import sys
import time
from ctypes import wintypes

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from markerlite.gui_logic import window_title

    executable = pathlib.Path(sys.argv[1]).resolve()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(
        [str(executable)], cwd=executable.parent, startupinfo=startup
    )
    user = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    titles = []

    @callback_type
    def inspect_window(hwnd, _param):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid:
            text = ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd) + 1)
            user.GetWindowTextW(hwnd, text, len(text))
            if text.value:
                titles.append(text.value)
        return True

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"exe exited before its window opened: {process.returncode}"
                )
            user.EnumWindows(inspect_window, 0)
            if window_title() in titles:
                time.sleep(2)
                if process.poll() is not None:
                    raise RuntimeError("exe exited during startup")
                print(f"Frozen window title: {window_title()}")
                return
            time.sleep(0.2)
        raise RuntimeError(
            f"expected {window_title()!r}; observed window titles: {titles!r}"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
