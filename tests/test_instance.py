"""Single instance and file hand-off (markerlite/instance.py), launch
arguments and queueing (gui_logic), and the Send to shortcut's failure
path (markerlite/sendto.py)."""

import json
import pathlib
import subprocess
import sys
import threading
import uuid

import pytest

from markerlite import instance, sendto
from markerlite.gui_logic import handoff_plan, launch_paths

ABS = str(
    pathlib.Path("C:/papers/a.pdf") if sys.platform == "win32" else "/papers/a.pdf"
)


# ---------------------------------------------------------------- messages
def test_message_round_trip_is_json_of_absolute_paths():
    msg = instance.encode_paths(["a.pdf", ABS])
    value = json.loads(msg)
    assert all(pathlib.Path(p).is_absolute() for p in value)
    assert instance.decode_paths(msg) == value


@pytest.mark.parametrize(
    "data",
    [
        b"\x80\x04K\x01.",  # a pickle, never accepted
        b"not json",
        json.dumps({"paths": [ABS]}).encode(),
        json.dumps([ABS] * (instance.MAX_PATHS + 1)).encode(),
        json.dumps(["relative/a.pdf"]).encode(),
        json.dumps([ABS + "\x00x"]).encode(),
        json.dumps([1]).encode(),
        json.dumps(["C:/" + "a" * instance.MAX_PATH_CHARS]).encode(),
        b"[" + b" " * instance.MAX_MESSAGE_BYTES + b"]",
    ],
    ids=[
        "pickle",
        "text",
        "dict",
        "too-many",
        "relative",
        "nul",
        "int",
        "too-long",
        "too-big",
    ],
)
def test_invalid_messages_are_refused(data):
    with pytest.raises(instance.HandoffError):
        instance.decode_paths(data)


# ------------------------------------------------------------------- retry
class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def test_hand_off_retries_while_the_window_starts():
    calls = []

    class Conn:
        def send_bytes(self, b):
            calls.append(b)

        def recv_bytes(self, maxlength):
            return instance.ACK

        def close(self):
            pass

    attempts = {"n": 0}

    def client(address, family, authkey):
        attempts["n"] += 1
        if attempts["n"] < 4:
            raise FileNotFoundError("pipe not there yet")
        return Conn()

    clock = FakeClock()
    assert instance.hand_off(
        [ABS], "addr", b"k" * 32, client=client, sleep=clock.sleep, clock=clock
    )
    assert attempts["n"] == 4 and len(calls) == 1


def test_hand_off_gives_up_after_about_five_seconds():
    def client(address, family, authkey):
        raise FileNotFoundError

    clock = FakeClock()
    ok = instance.hand_off(
        [ABS], "addr", b"k" * 32, client=client, sleep=clock.sleep, clock=clock
    )
    assert not ok and 5.0 <= clock.t <= 5.5  # the caller then opens a window


# ------------------------------------------------------------- real pipe
needs_windows = pytest.mark.skipif(sys.platform != "win32", reason="named pipes")


def _server(key):
    addr = instance.pipe_address("test" + uuid.uuid4().hex[:12])
    listener = instance.listen(addr, key)
    got, log = [], []
    lock = threading.Lock()

    def deliver(paths):
        with lock:
            got.append(paths)

    threading.Thread(
        target=instance.serve, args=(listener, deliver, log.append), daemon=True
    ).start()
    return addr, listener, got, log


@needs_windows
def test_pipe_hand_off_and_wrong_key():
    key = b"k" * 32
    addr, listener, got, log = _server(key)
    try:
        assert instance.hand_off([ABS], addr, key, retry_seconds=2)
        assert got == [[ABS]]
        assert not instance.hand_off([ABS], addr, b"z" * 32, retry_seconds=0.5)
        assert got == [[ABS]]
    finally:
        listener.close()


@needs_windows
def test_concurrent_launches_lose_no_file():
    key = b"k" * 32
    addr, listener, got, _log = _server(key)
    paths = [str(pathlib.Path(f"C:/papers/p{n}.pdf")) for n in range(12)]
    results = []
    threads = [
        threading.Thread(
            target=lambda p=p: results.append(
                instance.hand_off([p], addr, key, retry_seconds=5)
            )
        )
        for p in paths
    ]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(results) and len(results) == 12
        assert sorted(p for batch in got for p in batch) == sorted(paths)
    finally:
        listener.close()


@needs_windows
def test_mutex_decides_one_primary():
    name = "Local\\markerlite-test-" + uuid.uuid4().hex[:12]
    first = instance.SingleInstance(name)
    second = instance.SingleInstance(name)
    assert first.primary and not second.primary


# ------------------------------------------------------- launch and queue
def test_launch_paths_split_pdfs_from_the_rest(tmp_path):
    folder = tmp_path / "dir"
    folder.mkdir()
    take, skip = launch_paths(
        [str(tmp_path / "a.PDF"), str(tmp_path / "b.docx"), str(folder), "--diag"]
    )
    assert [p.name for p in take] == ["a.PDF", "dir"]
    assert [p.name for p in skip] == ["b.docx"]


def test_handoff_queues_behind_a_running_batch():
    a, b, c = (pathlib.Path(f"C:/{n}.pdf") for n in "abc")
    assert handoff_plan([a], running=False, pending=[]) == ([a], [])
    now, pending = handoff_plan([a, b], running=True, pending=[b])
    assert now == [] and pending == [b, a]
    now, pending = handoff_plan([c], running=True, pending=pending)
    assert pending == [b, a, c]


# ------------------------------------------------------- Send to failures
def _fake_run(returncode=0, stdout=b"", stderr=b""):
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    return run, calls


def test_powershell_blocked_gives_a_clear_error(tmp_path):
    run, calls = _fake_run(
        1, stderr=b"Cannot create the COM object: blocked by policy\r\n"
    )
    with pytest.raises(sendto.SendToError, match="blocked"):
        sendto.create(
            pathlib.Path("C:/m/markerlite.exe"), tmp_path / "markerlite.lnk", run
        )
    args, kwargs = calls[0]
    assert args[:3] == ["powershell", "-NoProfile", "-NonInteractive"]
    # paths travel in the environment, never in the command text
    assert "markerlite.exe" not in " ".join(args)
    assert kwargs["env"]["ML_TARGET"].endswith("markerlite.exe")


def test_powershell_missing_gives_a_clear_error(tmp_path):
    def run(args, **kwargs):
        raise FileNotFoundError("powershell")

    with pytest.raises(sendto.SendToError, match="could not run"):
        sendto.create(
            pathlib.Path("C:/m/markerlite.exe"), tmp_path / "markerlite.lnk", run
        )


def test_remove_is_a_plain_delete_and_idempotent(tmp_path):
    link = tmp_path / "markerlite.lnk"
    link.write_bytes(b"x")
    sendto.remove(link)
    sendto.remove(link)
    assert not link.exists()


def test_repair_only_when_the_target_moved(tmp_path):
    link = tmp_path / "markerlite.lnk"
    exe = tmp_path / "new" / "markerlite.exe"
    assert (
        sendto.repair(exe, link, _fake_run()[0]) is None
    )  # no shortcut: nothing to do
    link.write_bytes(b"x")
    same, calls = _fake_run(stdout=str(exe).encode())
    assert sendto.repair(exe, link, same) is None and len(calls) == 1
    moved, calls = _fake_run(stdout=b"C:\\old\\markerlite.exe")
    assert sendto.repair(exe, link, moved) == "C:\\old\\markerlite.exe"
    assert calls[1][1]["env"]["ML_TARGET"] == str(exe)
