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
import time
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

    def capture(self, args, *, timeout, max_bytes):
        return capture_capped(args, timeout=timeout, max_bytes=max_bytes, cancel=self)


def capture_capped(args, *, timeout, max_bytes, cancel=None):
    """Bound stdout, kill on overflow, and reap even if the reader cannot start."""
    check(cancel)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = bytearray()
    errors = []
    reader = None

    def read():
        try:
            while len(data) <= max_bytes:
                chunk = proc.stdout.read(min(65536, max_bytes + 1 - len(data)))
                if not chunk:
                    return
                data.extend(chunk)
            proc.kill()
        except BaseException as exc:
            errors.append(exc)
            try:
                proc.kill()
            except OSError:
                pass

    try:
        if cancel is not None:
            with cancel._lock:
                cancel._procs.add(proc)
        reader = threading.Thread(target=read, name="markerlite-capped-stdout")
        reader.start()
        deadline = time.monotonic() + timeout
        while True:
            check(cancel)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                code = proc.wait(timeout=min(0.05, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
        reader.join(timeout=5)
        if reader.is_alive():
            raise RuntimeError("stdout reader did not finish")
        check(cancel)
        if errors:
            raise errors[0]
        return code, bytes(data[:max_bytes]), len(data) > max_bytes
    finally:
        try:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            if reader is not None and reader.ident is not None:
                reader.join(timeout=5)
            proc.stdout.close()
        finally:
            if cancel is not None:
                with cancel._lock:
                    cancel._procs.discard(proc)


def check(token: Optional[CancelToken]) -> None:
    """Raise Cancelled if ``token`` is set; no-op without a token."""
    if token is not None:
        token.check()
