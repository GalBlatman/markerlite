"""Cell ownership and conservative rejection controls for wrapped recovery."""

import copy
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import markerlite
import markerlite.api as markerlite_api
import table_recon
from table_wrap import recover_wrapped_lines


class WrappedCellsTests(unittest.TestCase):
    def test_ruled_and_unruled_cells(self):
        """The centered Gamma key and two-column Alpha wrap retain ownership."""
        tables = []
        original_render = markerlite_api.render

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
            with patch.object(markerlite_api, "render", record):
                _, info = markerlite.convert(pdf, pathlib.Path(directory), grids=True)
        expected = [
            ["Record", "Requirement", "Assessment"],
            [
                "Alpha",
                "Include the whole reporting boundary and retain every subsidiary "
                "without dropping any exception from the account.",
                "Accepted Review continues",
            ],
            ["Beta", "Report the short independent entry.", "Pending"],
            [
                "Gamma",
                "Cover at least 7% of relevant activity without treating the percentage "
                "as a new row. Publish all checks and name their owners.",
                "Reviewed",
            ],
            ["Delta", "Keep the final independent record.", "Complete"],
        ]
        self.assertEqual(tables, [expected, expected])
        self.assertEqual(info["stats"]["tables_fallback"], 0)

    def test_wrapped_record_fixture_keeps_printed_rows(self):
        tables = []
        original_render = markerlite_api.render

        def record(pages, **kwargs):
            for page in pages:
                for block in page.blocks:
                    if block.btype == "Table" and not block.ignore_for_output:
                        self.assertFalse(block.fallback_paragraphs)
                        parser = markerlite._TableParser()
                        parser.feed(block.html)
                        tables.append([parser.header, *parser.rows])
            return original_render(pages, **kwargs)

        pdf = pathlib.Path(__file__).parent / "fixtures" / "wrapped_record_rows.pdf"
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(markerlite_api, "render", record):
                markerlite.convert(pdf, pathlib.Path(directory), grids=True)
        self.assertEqual(
            tables,
            [
                [
                    ["Record", "Description", "Status"],
                    [
                        "North- east",
                        "Opening fragment continued fragment retained ending",
                        "Accepted with checks",
                    ],
                    ["South- west", "Second fragment final fragment", "Pending review"],
                ]
            ],
        )

    def lines(self):
        return [
            (
                [("Record", 0, 30), ("Description", 100, 145), ("Status", 300, 330)],
                0,
                10,
            ),
            (
                [
                    ("Alpha", 0, 25),
                    ("Opening statement", 100, 170),
                    ("Approved", 300, 340),
                ],
                12,
                22,
            ),
            ([("Opening statement", 100, 170)], 24, 34),
            (
                [("Beta", 0, 20), ("Second entry", 100, 160), ("Pending", 300, 330)],
                36,
                46,
            ),
            (
                [("Gamma", 0, 30), ("Third entry", 100, 160), ("Reviewed", 300, 340)],
                48,
                58,
            ),
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

    def test_hanging_hyphenated_key_is_one_record(self):
        lines = [
            (
                [("Record", 0, 30), ("Description", 100, 150), ("Status", 300, 330)],
                0,
                10,
            ),
            (
                [
                    ("North-", 0, 27),
                    ("Opening fragment", 100, 170),
                    ("Accepted", 300, 345),
                ],
                14,
                24,
            ),
            (
                [
                    ("east", 4, 22),
                    ("continued fragment", 100, 180),
                    ("with checks", 300, 350),
                ],
                26,
                36,
            ),
            ([("", 0, 0), ("retained ending", 100, 170)], 38, 48),
            (
                [
                    ("South-", 0, 27),
                    ("Second fragment", 100, 170),
                    ("Pending", 300, 340),
                ],
                62,
                72,
            ),
            (
                [("west", 4, 22), ("final fragment", 100, 170), ("review", 300, 335)],
                74,
                84,
            ),
        ]
        lines[3] = ([lines[3][0][1]], 38, 48)
        old = table_recon.reconstruct_table_html(lines)
        new = recover_wrapped_lines(lines, old)
        parser = markerlite._TableParser()
        parser.feed(new[0])
        self.assertEqual(parser.header, ["Record", "Description", "Status"])
        self.assertEqual(
            parser.rows,
            [
                [
                    "North- east",
                    "Opening fragment continued fragment retained ending",
                    "Accepted with checks",
                ],
                ["South- west", "Second fragment final fragment", "Pending review"],
            ],
        )
        self.assertEqual(new[1], old[1])

    def test_complete_independent_keys_are_not_merged(self):
        lines = [
            (
                [("Record", 0, 30), ("Description", 100, 150), ("Status", 300, 330)],
                0,
                10,
            ),
            (
                [
                    ("North-", 0, 27),
                    ("Independent entry", 100, 180),
                    ("Accepted", 300, 345),
                ],
                14,
                24,
            ),
            (
                [("east", 0, 20), ("Another entry", 100, 170), ("Pending", 300, 340)],
                26,
                36,
            ),
            (
                [("South", 0, 27), ("Final entry", 100, 160), ("Reviewed", 300, 345)],
                38,
                48,
            ),
        ]
        old = table_recon.reconstruct_table_html(lines)
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
