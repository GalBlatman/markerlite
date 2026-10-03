"""Write the release notes for the version in markerlite/VERSION.

The notes are that version's section of CHANGELOG.md followed by the
download instructions. The Windows build job runs this and ships the file
with the zip, so the release job, which checks out nothing, can publish
it. A version without a CHANGELOG section fails the build: every release
says what changed.

usage: python tools/release_notes.py OUT
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (
    "**Windows:** download `markerlite-windows.zip`, unzip, and run "
    "`markerlite.exe` from inside the folder. Windows SmartScreen will warn "
    "once: click More info, then Run anyway. Scanned PDFs need Tesseract "
    "installed separately; digital PDFs do not."
)


def section(changelog: str, version: str) -> str:
    """The body under ``## v<version>``, up to the next ``## `` heading."""
    pattern = rf"^## v{re.escape(version)}(?=[ \t]|$)[^\n]*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, changelog, flags=re.S | re.M)
    if not m or not m.group(1).strip():
        raise SystemExit(f"CHANGELOG.md has no section for v{version}")
    return m.group(1).strip()


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    version = (ROOT / "markerlite" / "VERSION").read_text(encoding="ascii").strip()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = INSTALL + "\n\n" + section(changelog, version) + "\n"
    pathlib.Path(argv[0]).write_text(notes, encoding="utf-8", newline="\n")
    print(f"release notes for v{version}: {len(notes)} characters")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
