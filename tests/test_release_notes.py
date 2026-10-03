"""tools/release_notes.py: the release notes are this version's CHANGELOG
section, and a version without one fails the build."""

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "release_notes", ROOT / "tools" / "release_notes.py"
)
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)

LOG = "# Changelog\n\n## v0.2.0\n\nnew\n\n## v0.1.9\n\nold\n"


def test_section_is_the_version_body_only():
    assert rn.section(LOG, "0.2.0") == "new"
    assert rn.section(LOG, "0.1.9") == "old"


def test_missing_version_fails():
    with pytest.raises(SystemExit):
        rn.section(LOG, "0.1.1")
    with pytest.raises(SystemExit):
        rn.section(LOG, "0.2")


def test_current_version_has_notes(tmp_path):
    out = tmp_path / "notes.md"
    assert rn.main([str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("**Windows:**") and "###" in text
