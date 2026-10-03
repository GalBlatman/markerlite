"""Names and messages from outside are displayed as one inert line."""

import pathlib
import shutil
import sys

import pytest

from markerlite import cli
from markerlite.display import safe_display
from markerlite.gui_logic import (
    failure_log_line,
    failure_message,
    run_log_line,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIL = "report\nFAKE: forged line\r\x1b[31mred\x07\x7f\x85\u2028\u202e.pdf"


def _inert(line: str) -> None:
    assert "\n" not in line and "\r" not in line
    assert not any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in line)
    assert "\u2028" not in line and "\u202e" not in line


def test_safe_display_escapes_every_control_visibly():
    shown = safe_display(EVIL)
    _inert(shown)
    assert shown == (
        "report\\nFAKE: forged line\\r\\x1b[31mred\\x07\\x7f\\x85\\u2028\\u202e.pdf"
    )


def test_ordinary_names_are_unchanged():
    for name in (
        "paper.pdf",
        "Müller – Ünïcode (2019).pdf",
        "C:\\out\\a & b.md",
        "tab-free",
    ):
        assert safe_display(name) == name


def test_run_log_lines_are_one_inert_line():
    ok = run_log_line(EVIL, "3 pages", ["1 lossy page (2)"])
    _inert(ok)
    assert ok.startswith("report\\nFAKE: forged line")
    err = failure_log_line(EVIL, failure_message(ValueError("bad\nnews\x1b[0m")))
    _inert(err)
    assert err.endswith("FAILED ValueError: bad\\nnews\\x1b[0m")


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows file names cannot hold controls"
)
def test_cli_status_for_a_control_character_file_name(tmp_path, capsys):
    pdf = tmp_path / "evil\nname\r\x1b[2J.pdf"
    shutil.copy(ROOT / "tests" / "fixtures" / "table_only_footer.pdf", pdf)
    old = sys.argv
    sys.argv = ["markerlite", str(pdf), "-o", str(tmp_path / "out")]
    try:
        cli.main()
    finally:
        sys.argv = old
    # PyMuPDF may print its own advisory line; every other line is ours.
    lines = [
        ln
        for ln in capsys.readouterr().out.splitlines()
        if not ln.startswith("Consider using the pymupdf_layout")
    ]
    assert len(lines) == 2
    _inert(lines[0])
    assert lines[0].startswith("evil\\nname\\r\\x1b[2J.pdf -> ")
