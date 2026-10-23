"""Continuation joins retain physical page words and reject schema changes."""

import copy
import pathlib
import tempfile
from html.parser import HTMLParser
from unittest.mock import patch

import markerlite
import markerlite.api as api
from markerlite.render import render
from markerlite.stats import content_words
from markerlite.table_joins import link_continued_tables


class TableBalance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.opened = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.depth += 1
            self.opened += 1

    def handle_endtag(self, tag):
        if tag == "table":
            self.depth -= 1
            assert self.depth >= 0


def test_row_continuations_join_without_moving_page_words():
    captured = []
    original = api.render

    def record(pages, **kwargs):
        captured.extend(copy.deepcopy(pages))
        return original(pages, **kwargs)

    source = pathlib.Path(__file__).parent / "fixtures" / "cross_page_tables.pdf"
    with tempfile.TemporaryDirectory() as out:
        with patch.object(api, "render", record):
            path, _info = markerlite.convert(
                source, pathlib.Path(out), page_markers=True, grids=True
            )
        md = path.read_text()
    tables = [
        [b for b in page.blocks if b.btype == "Table" and not b.ignore_for_output]
        for page in captured
    ]
    assert all(len(group) == 1 for group in tables)
    assert [group[0].table_join_prev for group in tables] == [
        False,
        True,
        True,
        False,
        False,
        False,
        False,
    ]
    assert [group[0].table_join_next for group in tables] == [
        True,
        True,
        False,
        False,
        False,
        False,
        False,
    ]
    assert (
        tables[0][0].table_join_id
        == tables[1][0].table_join_id
        == tables[2][0].table_join_id
    )
    assert tables[3][0].table_join_id is None
    assert tables[4][0].table_join_id is None
    assert tables[5][0].table_join_id is None
    assert tables[6][0].table_join_id is None
    link_continued_tables(captured)
    assert render(captured, page_markers=True) == md
    balance = TableBalance()
    balance.feed(md)
    assert balance.opened == 1 and balance.depth == 0
    assert md.count('class="continued-header"') == 2
    for page in captured:
        joined_words = content_words(render([page]))
        unlinked = copy.deepcopy(page)
        for block in unlinked.blocks:
            block.table_join_prev = block.table_join_next = False
            block.table_join_id = None
            block.table_join_caption_columns = 0
        assert joined_words == content_words(render([unlinked]))
    assert (
        md.count("Page 1 Alpha")
        == md.count("Page 2 Alpha")
        == md.count("Page 3 Alpha")
        == 1
    )
