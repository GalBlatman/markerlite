"""proc_continuation: a justified paragraph cut by a page break joins the
next page even when its last line ends a fraction of a point short."""

from markerlite.model import Block, Line, Page, Span
from markerlite.processors import proc_continuation


def _line(x0, y, x1, text):
    return Line(
        spans=[
            Span(
                text=text,
                bbox=(x0, y, x1, y + 12),
                size=12.0,
                font="T",
                flags=0,
                char_pos=0,
            )
        ],
        bbox=(x0, y, x1, y + 12),
        char_pos=0,
    )


def _pages(last_x_end):
    a = Block(
        lines=[
            _line(72, 650, 543.21, "first full line of the paragraph runs"),
            _line(72, 678, last_x_end, "and the last line on the page also"),
        ],
        bbox=(72, 650, 543.21, 690),
        page_idx=0,
        char_pos=0,
        btype="Text",
    )
    b = Block(
        lines=[
            _line(72, 72, 543.2, "continues here on the following page"),
            _line(72, 100, 300, "and ends."),
        ],
        bbox=(72, 72, 543.2, 112),
        page_idx=1,
        char_pos=1,
        btype="Text",
    )
    return [
        Page(page_idx=0, width=612, height=792, blocks=[a]),
        Page(page_idx=1, width=612, height=792, blocks=[b]),
    ], a


def test_full_line_a_fraction_short_still_continues():
    pages, a = _pages(542.97)  # floor(543.21) = 543 used to reject this
    proc_continuation(pages)
    assert a.has_continuation


def test_a_short_last_line_ends_the_paragraph():
    pages, a = _pages(400.0)
    proc_continuation(pages)
    assert not a.has_continuation


def test_tolerance_does_not_join_numbers_sentences_or_captions():
    pages, a = _pages(542.97)
    a.lines[-1].spans[0].text = ".26 -.03"  # a column of numbers
    proc_continuation(pages)
    assert not a.has_continuation
    pages, a = _pages(542.97)
    a.lines[-1].spans[0].text = "and the sentence ends here."
    proc_continuation(pages)
    assert not a.has_continuation
    pages, a = _pages(542.97)
    pages[1].blocks[0].lines[0].spans[0].text = "Table 2"
    proc_continuation(pages)
    assert not a.has_continuation


def test_tolerance_does_not_join_two_cells_of_one_row():
    a = Block(
        lines=[
            _line(72, 300, 300.2, "first cell of a row in a table"),
            _line(72, 314, 299.9, "and its second line goes here"),
        ],
        bbox=(72, 300, 300.2, 326),
        page_idx=0,
        char_pos=0,
        btype="Text",
    )
    b = Block(
        lines=[
            _line(340, 300, 540, "the next cell in the same row"),
            _line(340, 314, 500, "of the same table"),
        ],
        bbox=(340, 300, 540, 326),
        page_idx=0,
        char_pos=1,
        btype="Text",
    )
    pages = [Page(page_idx=0, width=612, height=792, blocks=[a, b])]
    proc_continuation(pages)
    assert not a.has_continuation
