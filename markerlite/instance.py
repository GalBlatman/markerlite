"""One markerlite window per user: later launches hand their files over.

Explorer's "Send to" starts a new markerlite.exe with the chosen files as
arguments. If a window is already open, that process gives the files to it
and exits instead of opening a second window.

- Which process is the window is decided by a per-user named mutex
  (``Local\\markerlite-<user id>``), so two launches at the same moment
  cannot both become it.
- Files travel over a local named pipe (multiprocessing.connection,
  family AF_PIPE) whose name carries the same user id, authenticated with
  a random per-user key kept in %LOCALAPPDATA%\\markerlite. Messages are
  JSON bytes (send_bytes/recv_bytes), never pickle: a list of absolute
  paths, capped in count and size and validated before anything is queued.
- A sender retries for up to HANDOFF_RETRY_SECONDS while the window starts
  its listener; if the hand-off still fails it opens a normal window with
  the files, so a sent file is never dropped.

Pipe access (measured, Windows 11): Python's Listener creates each pipe
instance with the default descriptor "(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;<user>)
(A;;FR;;;WD)(A;;FR;;;AN)": SYSTEM, Administrators and the user have full
access, Everyone and Anonymous read access. It cannot be narrowed through
multiprocessing.connection: the handle lacks WRITE_DAC, so SetSecurityInfo
fails with access denied, and passing a descriptor would mean creating the
pipe outside that API. Why the authkey alone is acceptable here:

- Python's Client opens the pipe read/write; another account gets read only,
  so it cannot complete the handshake or send a message.
- Every connection must answer an HMAC challenge keyed with the per-user
  secret in %LOCALAPPDATA%\\markerlite, which other accounts cannot read.
  Without it nothing is accepted.
- The pipe is local: Python sets PIPE_REJECT_REMOTE_CLIENTS.
- Nothing secret is ever written to the pipe (a random challenge, then
  "ok"). What another local account can do is occupy the listening instance
  with a read-only open; hand-offs then time out and the new launch opens
  its own window with its files, so nothing is lost.

A message that is not a valid path list is dropped and nothing is queued.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import secrets
import sys
import time
from typing import Callable, List, Optional

MAX_PATHS = 1000
MAX_PATH_CHARS = 32767  # the longest path Windows accepts
MAX_MESSAGE_BYTES = 4 * 1024 * 1024
HANDOFF_RETRY_SECONDS = 5.0
ACK = b"ok"


class HandoffError(Exception):
    """A message that is not a valid list of paths."""


def user_id() -> str:
    """A short stable id for the current Windows user (domain, name and
    profile folder), used in the mutex and pipe names."""
    who = "|".join(
        os.environ.get(k, "")
        for k in ("USERDOMAIN", "USERNAME", "LOCALAPPDATA", "USERPROFILE")
    )
    return hashlib.sha256(who.encode("utf-8")).hexdigest()[:16]


def pipe_address(uid: Optional[str] = None) -> str:
    return rf"\\.\pipe\markerlite-{uid or user_id()}"


def mutex_name(uid: Optional[str] = None) -> str:
    return f"Local\\markerlite-{uid or user_id()}"


def key_path() -> pathlib.Path:
    base = os.environ.get("LOCALAPPDATA") or str(pathlib.Path.home())
    return pathlib.Path(base) / "markerlite" / "instance.key"


def authkey(path: Optional[pathlib.Path] = None) -> bytes:
    """The per-user secret, created on first use. %LOCALAPPDATA% is readable
    by the user (and administrators) only."""
    path = path or key_path()
    try:
        data = path.read_bytes()
        if len(data) >= 32:
            return data
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    data = secrets.token_bytes(32)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path.read_bytes()


def encode_paths(paths: List[str]) -> bytes:
    msg = json.dumps([str(pathlib.Path(p).absolute()) for p in paths]).encode("utf-8")
    decode_paths(msg)  # never send what the receiver would refuse
    return msg


def decode_paths(data: bytes) -> List[str]:
    """Validate a hand-off message: JSON, a list of at most MAX_PATHS
    absolute paths, each a string without NUL of at most MAX_PATH_CHARS."""
    if len(data) > MAX_MESSAGE_BYTES:
        raise HandoffError("message too large")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HandoffError("not JSON") from exc
    if not isinstance(value, list) or len(value) > MAX_PATHS:
        raise HandoffError("not a list of at most %d paths" % MAX_PATHS)
    out = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or len(item) > MAX_PATH_CHARS
            or "\x00" in item
            or not pathlib.PureWindowsPath(item).is_absolute()
            and not pathlib.PurePosixPath(item).is_absolute()
        ):
            raise HandoffError("not an absolute path")
        out.append(item)
    return out


class SingleInstance:
    """Owns the per-user mutex while the window is open (Windows only)."""

    def __init__(self, name: Optional[str] = None):
        self.name = name or mutex_name()
        self.handle = None
        self.primary = True
        if sys.platform != "win32":
            return
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        self.handle = kernel32.CreateMutexW(None, False, self.name)
        # ERROR_ALREADY_EXISTS: another process created it first.
        self.primary = ctypes.get_last_error() != 183


def serve(listener, deliver: Callable[[List[str]], None], log=lambda line: None):
    """Accept hand-offs forever (run on a daemon thread). ``deliver`` must
    only queue: it is called on this thread, and the window takes the paths
    off its queue on the Tk thread."""
    from multiprocessing import AuthenticationError

    while True:
        try:
            conn = listener.accept()  # answers the HMAC challenge first
        except AuthenticationError:
            log("hand-off refused: authentication failed")
            continue
        except OSError:
            return  # listener closed
        try:
            paths = decode_paths(conn.recv_bytes(maxlength=MAX_MESSAGE_BYTES))
            deliver(paths)
            conn.send_bytes(ACK)
        except (HandoffError, OSError, EOFError) as exc:
            log(f"hand-off refused: {exc}")
        finally:
            conn.close()


def hand_off(
    paths: List[str],
    address: Optional[str] = None,
    key: Optional[bytes] = None,
    retry_seconds: float = HANDOFF_RETRY_SECONDS,
    client=None,
    sleep=time.sleep,
    clock=time.monotonic,
) -> bool:
    """Give ``paths`` to the running window. True only once the window has
    acknowledged them; False after ``retry_seconds`` of failures."""
    if client is None:
        from multiprocessing.connection import Client as client
    address = address or pipe_address()
    key = key if key is not None else authkey()
    msg = encode_paths(paths)
    deadline = clock() + retry_seconds
    while True:
        try:
            conn = client(address, family="AF_PIPE", authkey=key)
            try:
                conn.send_bytes(msg)
                if conn.recv_bytes(maxlength=16) == ACK:
                    return True
            finally:
                conn.close()
        except (OSError, EOFError, ValueError):
            pass
        except Exception:  # AuthenticationError and the like: retry, then give up
            pass
        if clock() >= deadline:
            return False
        sleep(0.2)


def listen(address: Optional[str] = None, key: Optional[bytes] = None):
    from multiprocessing.connection import Listener

    return Listener(
        address or pipe_address(),
        family="AF_PIPE",
        authkey=key if key is not None else authkey(),
    )
