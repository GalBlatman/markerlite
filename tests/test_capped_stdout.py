"""Bounded pipes cannot fill RAM or disk, and always reap their producer."""

import subprocess
import sys
import threading
import time

import pytest

from markerlite.cancel import Cancelled, CancelToken, capture_capped


def test_stdout_overflow_kills_producer_and_keeps_bounded_prefix():
    script = "import sys,time; sys.stdout.buffer.write(b'x'*1000000);sys.stdout.flush();time.sleep(60)"
    start = time.monotonic()
    code, data, capped = capture_capped(
        [sys.executable, "-c", script], max_bytes=1024, timeout=5
    )
    assert capped and data == b"x" * 1024 and code != 0
    assert time.monotonic() - start < 5
    assert not any(t.name == "markerlite-capped-stdout" for t in threading.enumerate())


def test_stdout_at_exact_cap_is_not_overflow():
    code, data, capped = capture_capped(
        [sys.executable, "-c", "print('abc',end='')"], max_bytes=3, timeout=5
    )
    assert (code, data, capped) == (0, b"abc", False)


def test_capped_stdout_timeout_reaps_and_joins_reader():
    with pytest.raises(subprocess.TimeoutExpired):
        capture_capped(
            [sys.executable, "-c", "import time;time.sleep(60)"],
            max_bytes=100,
            timeout=0.1,
        )
    assert not any(t.name == "markerlite-capped-stdout" for t in threading.enumerate())


def test_capped_stdout_cancel_reaps_and_joins_reader():
    token = CancelToken()
    timer = threading.Timer(0.1, token.cancel)
    timer.start()
    try:
        with pytest.raises(Cancelled):
            token.capture(
                [sys.executable, "-c", "import time;time.sleep(60)"],
                max_bytes=100,
                timeout=5,
            )
    finally:
        timer.cancel()
        timer.join()
    assert not token._procs
    assert not any(t.name == "markerlite-capped-stdout" for t in threading.enumerate())
