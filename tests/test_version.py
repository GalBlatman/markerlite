import pathlib
import subprocess
import sys
import tempfile

import markerlite
from markerlite import convert

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_source_cli_reports_the_package_version():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "markerlite.py"), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == f"markerlite.py {markerlite.__version__}"


def test_source_cli_help_is_available():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "markerlite.py"), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--flag-figures" in proc.stdout
    assert "--apply-math" in proc.stdout


def test_conversion_metadata_uses_the_package_version_without_changing_stats():
    with tempfile.TemporaryDirectory() as directory:
        _out, info = convert(
            ROOT / "tests" / "fixtures" / "table_only_footer.pdf",
            pathlib.Path(directory),
        )
    assert info["version"] == markerlite.__version__
    assert "version" not in info["stats"]
