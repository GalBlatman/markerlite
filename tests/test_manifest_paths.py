"""--apply-figures and --apply-math write only <outdir>/<stem>.md."""

import json
import pathlib
import sys

import pytest

from markerlite import cli
from markerlite.paths import ManifestPathError, manifest_target, plain_stem

REJECTED = [
    "/etc/passwd",  # absolute, POSIX
    "C:\\Windows\\win",  # absolute with drive
    "C:win",  # drive-relative
    "C:",  # bare drive
    "..",  # parent
    ".",  # current
    "../outside",  # relative escape, forward slash
    "..\\outside",  # relative escape, backslash
    "sub/paper",  # any forward separator
    "sub\\paper",  # any backslash
    "a/..\\b",  # mixed separators
    "\\\\server\\share\\paper",  # UNC
    "//server/share/paper",  # UNC, forward slashes
    "paper:stream",  # alternate data stream
    "paper\x00",  # NUL
    "pa\nper",  # control character
    " paper",  # leading space
    "paper.",  # trailing dot, stripped by Windows
    "",  # empty
]


@pytest.mark.parametrize("stem", REJECTED)
def test_plain_stem_rejects(stem):
    with pytest.raises(ManifestPathError):
        plain_stem(stem)


@pytest.mark.parametrize("stem", [None, 3, ["paper"], {"a": 1}])
def test_plain_stem_rejects_non_strings(stem):
    with pytest.raises(ManifestPathError):
        plain_stem(stem)


def test_manifest_target_stays_in_outdir(tmp_path):
    assert manifest_target(tmp_path, "paper") == (tmp_path / "paper.md").resolve()
    assert (
        manifest_target(tmp_path, "my paper (v2)")
        == (tmp_path / "my paper (v2).md").resolve()
    )


class _Result:
    def __init__(self, code, stderr):
        self.returncode, self.stderr = code, stderr


def _run(*args):
    """Run the CLI in-process: sys.exit messages land in SystemExit."""
    old = sys.argv
    sys.argv = ["markerlite", *args]
    try:
        cli.main()
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, str):
            return _Result(1, code)
        return _Result(code or 0, "")
    finally:
        sys.argv = old
    return _Result(0, "")


def _setup(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.md"
    victim.write_text("<!-- figure: p. 1; caption: x -->\n", encoding="utf-8")
    return out, victim


@pytest.mark.parametrize("mode", ["--apply-figures", "--apply-math"])
@pytest.mark.parametrize(
    "stem", REJECTED + ["../victim", str(pathlib.Path("..") / "victim")]
)
def test_cli_refuses_every_escaping_stem(tmp_path, mode, stem):
    out, victim = _setup(tmp_path)
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "stem": stem,
                "regions": [
                    {"id": "fig_p1_1", "page": 1, "description": "X"},
                    {"id": "page1_eq0", "latex": "x"},
                ],
            }
        ),
        encoding="utf-8",
    )
    before = victim.read_text(encoding="utf-8")
    proc = _run(mode, str(manifest), "-o", str(out))
    assert proc.returncode != 0
    assert "markerlite:" in proc.stderr
    assert victim.read_text(encoding="utf-8") == before
    assert list(out.iterdir()) == []


def test_valid_figure_manifest_applies_to_outdir_stem_only(tmp_path):
    out, victim = _setup(tmp_path)
    target = out / "paper.md"
    target.write_text("<!-- figure: p. 1; caption: x -->\n", encoding="utf-8")
    manifest = tmp_path / "paper_figures.json"
    manifest.write_text(
        json.dumps(
            {
                "stem": "paper",
                "regions": [{"id": "fig_p1_1", "page": 1, "description": "A box."}],
            }
        ),
        encoding="utf-8",
    )
    proc = _run("--apply-figures", str(manifest), "-o", str(out))
    assert proc.returncode == 0, proc.stderr
    assert "> A box." in target.read_text(encoding="utf-8")
    assert "A box." not in victim.read_text(encoding="utf-8")


def test_valid_math_manifest_applies_to_outdir_stem_only(tmp_path):
    out, _victim = _setup(tmp_path)
    target = out / "paper.md"
    target.write_text(
        "$$\nx\n$$\n\n<!-- markerlite:eq page1_eq0 -->\n", encoding="utf-8"
    )
    manifest = tmp_path / "paper_math.json"
    manifest.write_text(
        json.dumps({"stem": "paper", "regions": [{"id": "page1_eq0", "latex": "y"}]}),
        encoding="utf-8",
    )
    proc = _run("--apply-math", str(manifest), "-o", str(out))
    assert proc.returncode == 0, proc.stderr
    assert target.read_text(encoding="utf-8") == "$$\ny\n$$\n"


def test_missing_target_is_a_clear_error(tmp_path):
    out, _victim = _setup(tmp_path)
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"stem": "absent", "regions": []}), encoding="utf-8")
    proc = _run("--apply-math", str(manifest), "-o", str(out))
    assert proc.returncode != 0
    assert "no Markdown file" in proc.stderr
