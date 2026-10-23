"""Printed header-band ownership, including wrapped and spanning labels."""

import pathlib
import tempfile
from unittest.mock import patch

import markerlite
import markerlite.api as api
from markerlite.render import _TableParser


def test_printed_header_bands():
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

    pdf = pathlib.Path(__file__).parent / "fixtures" / "ruled_header_band.pdf"
    with tempfile.TemporaryDirectory() as out:
        with patch.object(api, "render", record):
            markerlite.convert(pdf, pathlib.Path(out))
    assert len(tables) == 2
    assert tables[0][0] == [
        "Variable",
        "Private service (N=12)",
        "Public service (N=13)",
        "Community service (N=14)",
    ]
    assert len(tables[0]) == 4
    assert tables[0][1] == [
        "Alpha",
        "2.1 [2.0, 2.2]",
        "3.1 [3.0, 3.2]",
        "4.1 [4.0, 4.2]",
    ]
    assert tables[1] == [
        ["Record", "Outcome", ""],
        ["", "North", "South"],
        ["Alpha", "12", "24"],
        ["Beta", "13", "25"],
        ["Gamma", "14", "26"],
    ]
