import json

from markerlite.figures import apply_math


def test_apply_math_handles_text_picture_blank_and_missing_anchors(tmp_path):
    markdown = tmp_path / "paper.md"
    markdown.write_text(
        "$$\napproximation\n$$\n\n<!-- markerlite:eq page1_eq0 -->\n\n"
        "<!-- equation: p. 2; set as an image; number (2) -->\n\n"
        "![](paper_math/page2_eq0.png)\n\n"
        "<!-- markerlite:eq page2_eq0 -->\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "paper_math.json"
    manifest.write_text(
        json.dumps(
            {
                "stem": "paper",
                "regions": [
                    {"id": "page1_eq0", "latex": "x + y"},
                    {"id": "page2_eq0", "latex": "z^2"},
                    {"id": "blank", "latex": ""},
                    {"id": "missing", "latex": "q"},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert apply_math(markdown, manifest) == 2
    assert markdown.read_text(encoding="utf-8") == "$$\nx + y\n$$\n\n$$\nz^2\n$$\n"
    assert apply_math(markdown, manifest) == 0
