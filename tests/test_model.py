from markerlite.model import Block, Line, Span


def test_empty_and_mixed_blocks_report_geometry_and_font_ratios():
    empty = Block(lines=[], bbox=(1, 2, 6, 10), page_idx=0, char_pos=0)
    assert empty.text == ""
    assert empty.width == 5
    assert empty.height == 8
    assert empty.line_height() == 0
    assert empty.max_size() == 0
    assert empty.font_ratio("bold") == 0

    bold = Span("Bold", (0, 0, 20, 10), 10, "Times-Bold", 0, 0)
    plain = Span("text", (20, 0, 40, 10), 10, "Times", 0, 1)
    line = Line([bold, plain], (0, 0, 40, 10), 0)
    block = Block([line], line.bbox, 0, 0)
    assert line.text == "Boldtext"
    assert line.height == 10
    assert line.width == 40
    assert block.spans == [bold, plain]
    assert block.line_height() == 10
    assert block.max_size() == 10
    assert block.font_ratio("bold") == 0.5
