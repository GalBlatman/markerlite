"""Explorer's "Send to" menu entry for the Windows app.

A shortcut named markerlite.lnk in the user's SendTo folder
(shell:sendto, %APPDATA%\\Microsoft\\Windows\\SendTo) that points at the
running markerlite.exe. Explorer starts it with the chosen files as
arguments. No registry change, no administrator rights; removing the
shortcut removes the entry.

The shortcut is written and read through PowerShell's WScript.Shell COM
object (-NoProfile -NonInteractive, no window). Paths reach PowerShell as
environment variables, never inside the command text. When PowerShell or
COM is blocked by policy, SendToError carries a message for the checkbox
and nothing else in the app is affected.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Callable, Optional

LINK_NAME = "markerlite.lnk"
TIMEOUT = 30

_CREATE = (
    "$ErrorActionPreference = 'Stop'; "
    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:ML_LINK); "
    "$s.TargetPath = $env:ML_TARGET; "
    "$s.WorkingDirectory = $env:ML_WORKDIR; "
    "$s.IconLocation = $env:ML_ICON; "
    "$s.Description = 'Convert PDFs to Markdown with markerlite'; "
    "$s.Save()"
)
_READ = (
    "$ErrorActionPreference = 'Stop'; "
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
    "(New-Object -ComObject WScript.Shell).CreateShortcut($env:ML_LINK).TargetPath"
)


class SendToError(Exception):
    """Send to could not be changed; the message is for the user."""


def sendto_folder() -> pathlib.Path:
    appdata = os.environ.get("APPDATA") or str(
        pathlib.Path.home() / "AppData" / "Roaming"
    )
    return pathlib.Path(appdata) / "Microsoft" / "Windows" / "SendTo"


def link_path() -> pathlib.Path:
    return sendto_folder() / LINK_NAME


def _powershell(script: str, env_extra: dict, run: Callable = subprocess.run) -> str:
    env = dict(os.environ)
    env.update(env_extra)
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        proc = run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            env=env,
            capture_output=True,
            timeout=TIMEOUT,
            **kwargs,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SendToError(f"PowerShell could not run ({type(exc).__name__})") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        reason = detail[0][:160] if detail else f"exit code {proc.returncode}"
        raise SendToError(f"PowerShell or COM is blocked: {reason}")
    return (proc.stdout or b"").decode("utf-8", "replace").strip()


def create(exe: pathlib.Path, link: Optional[pathlib.Path] = None, run=subprocess.run):
    """Write (or rewrite) the shortcut so it starts ``exe`` with its icon."""
    link = link or link_path()
    link.parent.mkdir(parents=True, exist_ok=True)
    _powershell(
        _CREATE,
        {
            "ML_LINK": str(link),
            "ML_TARGET": str(exe),
            "ML_WORKDIR": str(pathlib.Path(exe).parent),
            "ML_ICON": f"{exe},0",
        },
        run,
    )
    if not link.is_file():
        raise SendToError("the shortcut was not written")


def remove(link: Optional[pathlib.Path] = None) -> None:
    """Delete the shortcut if it is there (a plain file delete)."""
    link = link or link_path()
    try:
        link.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SendToError(f"could not remove the shortcut: {exc.strerror}") from exc


def target(link: Optional[pathlib.Path] = None, run=subprocess.run) -> str:
    return _powershell(_READ, {"ML_LINK": str(link or link_path())}, run)


def repair(exe: pathlib.Path, link: Optional[pathlib.Path] = None, run=subprocess.run):
    """Startup check, only when the shortcut exists: if it points somewhere
    else (the markerlite folder was moved), point it at ``exe``. Returns the
    old target when it was repointed, else None."""
    link = link or link_path()
    if not link.is_file():
        return None
    old = target(link, run)
    if os.path.normcase(os.path.abspath(old)) == os.path.normcase(
        os.path.abspath(str(exe))
    ):
        return None
    create(exe, link, run)
    return old
