"""Tesseract status and override validation without Tk or network access."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

WINDOWS_DOWNLOAD_URL = "https://github.com/UB-Mannheim/tesseract/wiki"


@dataclass(frozen=True)
class OcrStatus:
    path: str | None
    version: str | None
    message: str
    outdated: bool = False


def ocr_status(path: str | None, version: str | None) -> OcrStatus:
    if not path:
        return OcrStatus(
            None,
            None,
            "Tesseract was not found. Install Tesseract 5 or later, then use Detect in Preferences, or choose its tesseract.exe path.",
        )
    match = re.match(r"tesseract\s+v?(\d+)\.(\d+)", version or "", re.IGNORECASE)
    if not match:
        return OcrStatus(
            path,
            version,
            "Tesseract was found, but its version could not be read. Check its installation or choose a different executable in Preferences.",
        )
    outdated = int(match[1]) < 5
    return OcrStatus(
        path,
        version,
        "Outdated: install Tesseract 5 or later."
        if outdated
        else "Tesseract is ready for OCR.",
        outdated,
    )


def validate_override(path: str, *, run=subprocess.run, is_file=None) -> str:
    """Validate an explicit local executable by running --version, never a shell."""
    candidate = pathlib.Path(path.strip().strip('"')).expanduser()
    exists = candidate.is_file() if is_file is None else is_file(candidate)
    if not path.strip() or not exists:
        raise ValueError("Choose an existing Tesseract executable.")
    try:
        flags = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if sys.platform == "win32"
            else {}
        )
        result = run(
            [str(candidate.resolve()), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            **flags,
        )
        lines = (result.stdout or result.stderr or "").strip().splitlines()
        version = lines[0] if lines else ""
        if result.returncode != 0 or not re.match(
            r"tesseract\s+v?\d+\.\d+", version, re.IGNORECASE
        ):
            raise ValueError("The executable did not report a Tesseract version.")
        return str(candidate.resolve())
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"Could not run Tesseract: {exc}") from exc
