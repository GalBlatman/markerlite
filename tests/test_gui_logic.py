import dataclasses
import pathlib

from markerlite.gui_logic import (
    output_directory,
    provenance_comments,
    snapshot_options,
    summary_text,
    warning_lines,
)
from markerlite.model import Page
from markerlite.stats import build_stats

ROOT_VERSION = pathlib.Path(__file__).resolve().parents[1] / "markerlite" / "VERSION"


def test_output_directory_uses_fixed_or_source_parent(tmp_path):
    pdf = tmp_path / "source" / "paper.pdf"
    assert output_directory(pdf, "beside", str(tmp_path / "chosen")) == pdf.parent
    assert output_directory(pdf, "fixed", str(tmp_path / "chosen")) == (
        tmp_path / "chosen"
    )


def test_option_snapshot_is_plain_and_immutable():
    options = snapshot_options(1, 0, True, "fixed", pathlib.Path("out"))
    assert dataclasses.asdict(options) == {
        "images": True,
        "math": False,
        "page_markers": True,
        "mode": "fixed",
        "directory": "out",
    }
    try:
        options.images = False
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover - documents the immutability contract
        raise AssertionError("option snapshot is mutable")


def test_warning_and_summary_helpers_use_the_shared_policy():
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    page.tables_emitted = page.tables_fell_back = 1
    stats = build_stats([page], "Text\n", {}, [], 0, 0)
    assert warning_lines(stats) == ["1 of 1 table kept as prose"]
    assert summary_text(stats).endswith("1 of 1 table kept as prose")


def test_provenance_reads_source_comments_from_the_initial_window(tmp_path):
    md = tmp_path / "paper.md"
    md.write_text(
        "<!-- source: Journal; DOI 10.1/example -->\n"
        "<!-- source: Stable URL -->\n\nBody\n<!-- source: too late -->\n",
        encoding="utf-8",
    )
    assert provenance_comments(md) == [
        "source: Journal; DOI 10.1/example",
        "source: Stable URL",
        "source: too late",
    ]
    assert provenance_comments(tmp_path / "missing.md") == []


def test_title_and_label_come_from_the_single_version_source():
    import markerlite
    from markerlite.gui_logic import version_label, window_title

    version = markerlite.__version__
    assert version == (ROOT_VERSION.read_text(encoding="ascii").strip())
    assert window_title() == f"markerlite {version}"
    assert version_label() == f"v{version}"
    # nothing hard-coded: another version gives another title
    assert window_title("9.9.9") == "markerlite 9.9.9"
    assert version_label("9.9.9") == "v9.9.9"


def test_bug_report_line_names_version_tesseract_and_windows():
    import markerlite
    from markerlite.gui_logic import bug_report_line

    v = markerlite.__version__
    assert bug_report_line("tesseract 5.5.0", "Windows 10.0.26300") == (
        f"markerlite {v} \u00b7 Tesseract 5.5.0 \u00b7 Windows 10.0.26300"
    )
    assert bug_report_line("tesseract v5.4.0.20240606", "Windows 10.0.22631") == (
        f"markerlite {v} \u00b7 Tesseract v5.4.0.20240606 \u00b7 Windows 10.0.22631"
    )
    assert bug_report_line(None, "Windows 10.0.26300") == (
        f"markerlite {v} \u00b7 Tesseract not found \u00b7 Windows 10.0.26300"
    )
