# Gold tables set: protocol

The gold tables set measures table structure against cell matrices read off
the printed page. Its content is third-party (journal articles, a standards
document, a licensed export), so it lives only in the git-ignored
`tests/gold-tables/` beside `tests/real/`. What is committed is this protocol
and the scorer, `tests/score_gold_tables.py`, with its unit test.

Every item was transcribed by one agent from rendered pages and the PDF text
layer, never from converter output, and then re-checked cell by cell by a
second, independent agent (`transcribed_by`, `checked_by`, `check_notes`).
The set as of 2026-10-02 holds 29 tables, 8 non-table controls and 1
ambiguous item; its composition and the v0.1.15 baseline are in
tests/PLAN-tables.md, block 2.

Owner rulings (block 2, stop 1):

- S0009 p. 17 (a numbered reference list under a "Table 6" caption, between
  rules) is `"kind": "ambiguous"`: scored like a control but reported on its
  own line, outside the table and control totals. The control target, zero
  false grids, applies to the remaining 8 controls.
- York 2018 Table 2 continues across the page break by columns (p. 14: the
  variables and models 1-4; p. 15: models 5-12, no row labels). It carries
  `segments` and is scored per page segment. **Known limitation:** joining
  the two halves into one grid is not attempted, not credited and stays
  ranked low; a converter that emits two correct grids scores EXACT.

Run, from WSL where the pipeline PDFs are:

```bash
python tests/score_gold_tables.py --corpus-root /home/galbl/unknown-knowns
```

`--regions DIR` scores recorded region dumps (`<stem>.tables.json` and
`<stem>.md`) instead of converting; `--json OUT` writes per-item results.

## 1. Transcription conventions

You are writing GOLD cell matrices for real tables in PDFs, so that a PDF converter
can be scored against them. The gold must describe what the PRINTED PAGE shows.
You must work independently of the converter: never run markerlite, never open any
markerlite output (.md, region dumps, labels), never look at
tests/expected. Your evidence is (1) the rendered page image and (2) the PDF's own
text layer for exact spelling.

### Tools

Use WSL Python with PyMuPDF: `wsl -e bash -c "~/.markerlite-venv/bin/python script.py"`.
Windows paths are under /mnt/c/... in WSL. Pipeline PDFs live in WSL under
/home/galbl/...; read them in place, never copy a PDF anywhere.
Render pages at 150-200 dpi to PNG files in your own scratch folder,
then LOOK at them with the Read tool. Crop and zoom (render with a `clip=` rectangle at
300 dpi) whenever cells are small. Use `page.get_text("words")` to get exact strings
and their positions; the IMAGE decides the structure (which words share a cell, which
row and column a cell is in). If the text layer and the image disagree (OCR errors,
missing glyphs), the image wins: write what is printed.

A scanned page may have no text layer or an imperfect hidden OCR layer: transcribe from
the image, and say so in `notes`.

### Matrix rules

- One matrix row per printed row of the grid. A cell whose text wraps onto several
  printed lines is ONE cell; join its lines with single spaces. Join a word broken by a
  line-end hyphen ("legiti-" + "macy" -> "legitimacy"); keep genuine hyphens.
- If a table prints standard errors, t-values or intervals on their own line under the
  coefficient (a new line of values, row label empty), that line is its own row with
  an empty first cell. If the interval is printed on the SAME line as the value, it is
  part of the same cell ("5.16 [4.96, 5.37]").
- Header cells that wrap are one cell. A multi-level header is several rows. A header
  cell that spans several columns appears once, in the leftmost column of its span;
  the other spanned positions are "". Same for a row label that spans several rows:
  it appears in the first row only.
- Every row has the same number of cells (pad with ""). Include the row-label column.
- Excluded from the matrix: the caption/title ("Table 2 ..."), notes and sources under
  the table, significance legends, running heads, page numbers. Put the caption text in
  `caption` and the first words of the notes in `notes`.
- Keep cell text as printed: significance stars attached ("0.53***"), daggers, signs,
  decimals, percent signs, brackets, parentheses. Footnote letters attached to a word
  are written directly after it ("Incomea"). Use the text layer's characters where it
  agrees with the image (a Unicode minus stays a Unicode minus).
- Bullets inside a cell: write the bullet character if printed, then the item text;
  several bullet items in one cell are joined with single spaces.
- Indentation is not text: an indented row label is written without leading spaces.
- Multi-page table: ONE gold item, `pages` lists all pages, the matrix holds all rows in
  page order. A table that continues by COLUMNS on the next page (side by side) is
  one matrix too, plus `"segments": [{"page": P, "cols": [...]}, ...]` naming which
  matrix columns are printed on which page. A repeated header on a continuation page is NOT repeated in the matrix;
  say "continued header omitted" in `notes`.
- A "table" that the page shows only as a figure (boxes and arrows) is NOT a table.

### Output: one JSON file per item in tests/gold-tables/

. This folder is git-ignored;
never `git add` it, never write anywhere else in the repo.

Table item, file `<id>.json`:

```json
{"id": "R02611-p18-t1", "kind": "table", "doc": "R02611",
 "sha256": "<sha256 of the source PDF>", "source_path": "<path you read>",
 "pages": [18], "label": "Table 1",
 "layout": ["booktabs", "wrapped-header"],
 "caption": "...", "notes": "...",
 "matrix": [["", "col A", ...], ["row label", "1.23", ...]],
 "transcribed_by": "transcriber-<batch>", "method": "image + text layer",
 "uncertain_cells": [[row, col, "why"]]}
```

`layout` uses these words where they apply: ruled (full grid lines), booktabs (only
horizontal rules: top, under the header, bottom), borderless (no rules), shaded-row
(alternating or banded fills), boxed (a frame around the table), multi-page,
wrapped-cell (body cells wrap over several lines), wrapped-header, landscape (printed
sideways), scanned (raster page), numeric, text.

Control item (a page area that is NOT a table, where a converter might wrongly make
one), file `<id>.json`:

```json
{"id": "R02055-p7-c1", "kind": "control", "doc": "R02055", "sha256": "...",
 "source_path": "...", "pages": [7], "bbox": [x0, y0, x1, y1],
 "description": "two figure boxes side by side; no table on the page area",
 "transcribed_by": "..."}
```

`bbox` is in PDF points of the (unrotated) page, covering the area in question.

### Before you finish

Re-read every matrix against the image row by row. Count rows and columns against the
picture. Check every number. List anything you are unsure of in `uncertain_cells`.
Return a short report: items written (id, rows x cols), items you decided are not
tables (and why), and every uncertainty.

## 2. Independent re-check

Another agent transcribed gold cell matrices from rendered PDF pages. You check them
independently. Read the transcription conventions (section 1) first; the gold must
follow them.

Rules for you:
- Never run the markerlite converter and never open its outputs (Markdown
  conversions, region dumps, labels, tests/expected). Your evidence is
  the rendered page and the PDF text layer.
- For each item: render every page in `pages` (PyMuPDF via WSL, 150 dpi, plus 300 dpi
  crops), LOOK at it, and compare it with the JSON matrix row by row and cell by cell:
  the number of rows and columns; each cell's text, including every digit, sign, star,
  bracket and decimal; which row and column each cell is in; wrapped cells joined into
  one cell; header handling; that the caption and notes are not in the matrix.
- Where the matrix is definitely wrong, correct the JSON file in place. Where it is a
  judgement call under the conventions, leave it and record it.
- Add to each JSON file: `"checked_by": "checker-<batch>"`, and `"check_notes"`: a list
  of strings, one per change you made ("[r,c] '5.1' -> '5.17' (image)") or per open
  doubt. An empty list means you found nothing.
- Keep the JSON valid (load it with Python after writing).
- Scratch renders go to your own scratch folder, never the repository.
- Licensed content (doc capiq_keydev): never quote its text in your report.
- Do not modify anything else in the repo; do not run git.

Return a short report: per item, the number of cells checked, the number of
corrections, and the kinds of error found.
