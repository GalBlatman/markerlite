import pathlib
import tempfile

from markerlite import convert

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_sectioned_running_heads_emit_once_and_alternating_pair_stays_furniture():
    with tempfile.TemporaryDirectory() as directory:
        output, info = convert(
            ROOT / "tests" / "fixtures" / "sectioned_running_heads.pdf",
            pathlib.Path(directory),
        )
        markdown = output.read_text(encoding="utf-8")

    assert [item["page"] for item in info["stats"]["section_heads_emitted"]] == [
        1,
        3,
        5,
    ]
    assert markdown.count("## Section ") == 3
    assert "Journal Author" not in markdown
    assert "Article Title" not in markdown
