"""Spanning labels move without reassigning ordinary table cells."""

import pathlib
import tempfile
from unittest.mock import patch

import markerlite
import markerlite.api as api
from markerlite.render import _TableParser
from markerlite.table_columns import recover_spanning_columns


def test_spanning_column_fixture():
    tables = []
    original = api.render

    def record(pages, **kwargs):
        for page in pages:
            for block in page.blocks:
                if block.btype == "Table" and not block.ignore_for_output:
                    assert not block.fallback_paragraphs
                    parser = _TableParser()
                    parser.feed(block.html)
                    tables.append([parser.header, *parser.rows])
        return original(pages, **kwargs)

    pdf = pathlib.Path(__file__).parent / "fixtures" / "spanning_column_labels.pdf"
    with tempfile.TemporaryDirectory() as out:
        with patch.object(api, "render", record):
            markerlite.convert(pdf, pathlib.Path(out), grids=True)
    assert tables == [
        [
            ["FIRST", ""],
            ["Alpha", "Accepted after review of every record"],
            ["Beta", "Pending confirmation of all source fields"],
            ["Gamma", "Reviewed with all original entries retained"],
            ["SECOND", ""],
            ["Delta", "Complete after checking the full inventory"],
            ["Epsilon", "Open until independent review is complete"],
            ["Zeta", "Closed with every source record retained"],
        ]
    ]


def test_duplicate_label_is_not_arbitrarily_removed():
    html = "<table><thead><tr><th></th><th>GROUP</th></tr></thead><tbody><tr><td>Alpha</td><td>GROUP</td></tr><tr><td>Beta</td><td>Kept</td></tr></tbody></table>"
    lines = [
        ([("GROUP", 80, 120)], 10, 20),
        ([("Alpha", 0, 30), ("GROUP", 140, 180)], 40, 50),
        ([("Beta", 0, 25), ("Kept", 140, 170)], 60, 70),
    ]
    graphics = {"h": [(0, 0, 200), (30, 0, 200), (100, 0, 200)], "v": []}
    assert recover_spanning_columns(lines, html, graphics, (0, 0, 200, 100)) == html


def test_vertical_divider_protects_an_individual_cell():
    html = "<table><thead><tr><th></th><th>GROUP</th></tr></thead><tbody><tr><td>Alpha</td><td>Kept</td></tr></tbody></table>"
    lines = [
        ([("GROUP", 80, 120)], 10, 20),
        ([("Alpha", 0, 30), ("Kept", 140, 180)], 40, 50),
    ]
    graphics = {"h": [(0, 0, 200), (30, 0, 200), (100, 0, 200)], "v": [(100, 0, 30)]}
    assert recover_spanning_columns(lines, html, graphics, (0, 0, 200, 100)) == html
