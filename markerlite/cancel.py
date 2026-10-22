"""Cooperative cancel for a running conversion.

The GUI's Cancel button (and Esc) sets a :class:`CancelToken` from the main
thread; the worker checks it between pages and between files and raises
:class:`Cancelled`. A Tesseract process that is running when the token is
set is killed at once, so a slow OCR page does not hold the cancel up.

``Cancelled`` derives from BaseException, like KeyboardInterrupt: the
pipeline's ``except Exception`` guards (a figure that will not render, an
OCR page that fails) must never swallow a cancel. convert() discards its
staged output on any exception, so a cancelled document leaves nothing
behind (markerlite/output.py).
"""

from __future__ import annotations

import subprocess
import threading
from typing import Optional


class Cancelled(BaseException):
    """The user cancelled the conversion."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._procs: set = set()

    def cancel(self) -> None:
        """Ask the conversion to stop; kill any running subprocess."""
        self._event.set()
        with self._lock:
            procs = list(self._procs)
        for proc in procs:
            try:
                proc.kill()
            except OSError:
                pass

    def is_set(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        """Raise Cancelled if a cancel was asked for."""
        if self._event.is_set():
            raise Cancelled()

    def run(self, args, *, timeout: float, **kwargs) -> int:
        """subprocess.run for a cancellable child: returns its exit code,
        raises Cancelled if the token was set while it ran, and
        subprocess.TimeoutExpired after ``timeout`` seconds."""
        self.check()
        proc = subprocess.Popen(args, **kwargs)
        with self._lock:
            self._procs.add(proc)
        try:
            if self._event.is_set():  # cancelled between check() and add()
                proc.kill()
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise
        finally:
            with self._lock:
                self._procs.discard(proc)
        self.check()
        return code


def check(token: Optional[CancelToken]) -> None:
    """Raise Cancelled if ``token`` is set; no-op without a token."""
    if token is not None:
        token.check()
