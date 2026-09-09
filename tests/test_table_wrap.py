"""Cell ownership and conservative rejection controls for wrapped recovery."""

import copy
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import markerlite
import table_recon
from table_wrap import recover_wrapped_lines


class WrappedCellsTests(unittest.TestCase):
    def test_ruled_and_unruled_cells(self):
        """The centered Gamma key and two-column Alpha wrap retain ownership."""
        tables = []
        original_render = markerlite.render

        def record(pages, **kwargs):
            for page in pages:
                for block in page.blocks:
                    if block.btype == "Table" and not block.ignore_for_output:
                        parser = markerlite._TableParser()
                        parser.feed(block.html)
                        tables.append([parser.header, *parser.rows])
            return original_render(pages, **kwargs)

        pdf = pathlib.Path(__file__).parent / "fixtures" / "all_text_wrapped.pdf"
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(markerlite, "render", record):
                _, info = markerlite.convert(pdf, pathlib.Path(directory))
        expected = [
            ["Record", "Requirement", "Assessment"],
            ["Alpha", "Include the whole reporting boundary and retain every subsidiary "
             "without dropping any exception from the account.", "Accepted Review continues"],
            ["Beta", "Report the short independent entry.", "Pending"],
            ["Gamma", "Cover at least 7% of relevant activity without treating the percentage "
             "as a new row. Publish all checks and name their owners.", "Reviewed"],
            ["Delta", "Keep the final independent record.", "Complete"],
        ]
        self.assertEqual(tables, [expected, expected])
        self.assertEqual(info["stats"]["tables_fallback"], 0)

    def lines(self):
        return [
            ([("Record", 0, 30), ("Description", 100, 145), ("Status", 300, 330)], 0, 10),
            ([("Alpha", 0, 25), ("Opening statement", 100, 170), ("Approved", 300, 340)], 12, 22),
            ([("Opening statement", 100, 170)], 24, 34),
            ([("Beta", 0, 20), ("Second entry", 100, 160), ("Pending", 300, 330)], 36, 46),
            ([("Gamma", 0, 30), ("Third entry", 100, 160), ("Reviewed", 300, 340)], 48, 58),
        ]

    def test_repeated_words_retained_once_per_occurrence(self):
        lines = self.lines()
        before = copy.deepcopy(lines)
        old = table_recon.reconstruct_table_html(lines)
        new = recover_wrapped_lines(lines, old)
        self.assertNotEqual(new, old)
        self.assertEqual(new[1], old[1])  # winning score is not retuned
        self.assertEqual(new[0].count("Opening statement"), 2)
        self.assertEqual(lines, before)

    def test_partial_new_record_is_ambiguous(self):
        lines = self.lines()
        lines[2] = ([("Uncertain record", 0, 45)], 24, 34)
        old = table_recon.reconstruct_table_html(lines)
        self.assertIsNotNone(old)
        self.assertEqual(recover_wrapped_lines(lines, old), old)

    def test_distant_prose_is_not_attached(self):
        lines = self.lines()
        lines.append(([("Unrelated paragraph below the table", 100, 240)], 100, 110))
        old = table_recon.reconstruct_table_html(lines)
        self.assertIsNotNone(old)
        self.assertEqual(recover_wrapped_lines(lines, old), old)

    def test_numeric_winner_is_unchanged(self):
        lines = self.lines()
        for i in (1, 3, 4):
            spans, y0, y1 = lines[i]
            lines[i] = ([spans[0], (str(i), 100, 110), (str(i + 1), 300, 310)], y0, y1)
        old = table_recon.reconstruct_table_html(lines)
        self.assertIsNotNone(old)
        self.assertEqual(recover_wrapped_lines(lines, old), old)


if __name__ == "__main__":
    unittest.main()
