# Verification for v0.1.12

Converter at 7bbc066. All document runs in WSL (Tesseract 5.5.0). The metric
is content words from `content_words()`. Pipeline documents were read in place
under /home/galbl/unknown-knowns/ and never copied into this repository. No tag
was created.

Three converter states are compared:

| Label | Commit | Meaning |
| --- | --- | --- |
| before block 0 | 59423bf | v0.1.11 plus the conservation check |
| after block 0 | 97a3995 | block 0, step F and the design rule; no converter change since 1e7af01 |
| release | 7bbc066 | step 1 and step 2 on top |

## Commits in this release

| Step | Commit | What |
| --- | --- | --- |
| block 0 (a) | be93af7 | garbled text layer goes to OCR |
| block 0 (b) | 5e5354c | WRAP repository cover |
| block 0 (c) | d2b45c8, 1e7af01 | figure placeholders, marked once |
| block 0 report | 8a577b7 | tests/REPORT-batch3.md |
| F.i | b4035ad | fixture `figure_dedup` |
| F.iii | 043a8d5 | PLAN item 12, evidence only |
| 0 | 97a3995 | design rule in CLAUDE.md |
| 1 | 897e892 | caption isolation and row extent (PLAN item 7) |
| 2 | 7bbc066 | bibliography symbols are not footnote markers |

F.ii is a report item and is recorded below.

## Content words

| Document | Before block 0 | After block 0 | Release | Cause of change |
| --- | --- | --- | --- | --- |
| Peng 2009 | 12,046 | 12,046 | 12,046 | |
| Greenwood 2006 | 14,777 | 14,777 | 14,777 | |
| Wry 2013 | 18,441 | 18,441 | 18,441 | |
| Jay 2013 | 16,377 | 16,377 | 16,377 | |
| York 2018 | 19,930 | 19,930 | 19,930 | |
| Kitchener 2002 | 13,256 | 13,256 | 13,256 | |
| Suchman 1995 | 16,458 | 16,458 | 16,458 | |
| Kostova 1999 | 11,297 | 11,297 | 11,297 | |
| SBTi protocol | 18,345 | 18,345 | 18,345 | |
| Ragins 2012 | 6,625 | 6,625 | 6,625 | |
| R02611 | 15,307 | 15,307 | 15,307 | |
| R00315 | 17,709 | 17,709 | 17,703 | step 2 |
| R01285 | 23,062 | 23,062 | 23,062 | |
| S0009 | 21,480 | 21,480 | 21,480 | |
| R00443 | 16,026 | 16,026 | 16,026 | |
| R00030 | 21,484 | 21,335 | 21,335 | block 0 (b) |

Two documents change their count.

- **R00030, -149, block 0 (b).** The words are the WRAP cover sheet, now a
  `<!-- source: ... -->` comment.
- **R00315, -6, step 2.** Token by token: 40 note labels left the text and 33
  marks containing a dagger took their place as words. The 8 labels that were
  a bare star, `[^*]:`, `[^**]:` and `[^***]:`, leave no word behind because the
  metric ignores stars. That is -7. "Sociological", hyphenated across a line
  inside an italic title, is now two tokens, "Sociolog-" and "ical". That is
  +1. No word of any reference was lost.

Documents whose Markdown changed without a change in count:

- **Block 0 (c)**, figure placeholders: every document that has figures. The
  placeholders are comments and are not counted.
- **Step 1**: R02611 p. 18 and R01285 p. 8, described below.

Between "after block 0" and the release, 13 of the 16 documents have
byte-identical Markdown. The three that differ are R02611, R01285 and R00315.

## SBTi: 55 region decisions

| | After block 0 | Release |
| --- | --- | --- |
| Tables emitted | 55 | 55 |
| Fell back to cell text | 30 | 30 |
| Table HTML, by hash | | all 55 identical |
| Markdown | | byte-identical |
| Captions isolated | | 0 |
| Lines excluded | | 0 |

A first version of step 1 did change SBTi. It cut boxed tables at an inner
rule: 54 tables, 113 lines excluded, 18,399 words. Row bounding is therefore
limited to candidates made of rules only, with no other stroke inside the
grid. That version was never committed.

## Flags

| Document | lossy_pages | low-yield | garbled |
| --- | --- | --- | --- |
| SBTi protocol | none | p. 1 | none |
| R00443 | p. 16, 163 of 336 | none | none |
| the other 14 | none | none | none |

This is the expected set. There is no further finding.

## Step 1: R02611 p. 18, cell matrix

Before, 6 rows by 7 columns:

| Row | Cells |
| --- | --- |
| header | Table 1. Study Condition (N = / 1 734). / Descriptive Statistics / of Model Variables / by / Experimental / empty |
| 1 | Variable / empty / For-profit core hybrid (N = 187) / For-profit business (N = 185) / Nonprofit core hybrid (N = 176) / empty / Nonprofit organization (N = 186) |
| 2 | all three variable names in one cell; the twelve values in five cells, each interval broken between two cells |
| 3 | Note. Mean [95% / confidence / interval]. |
| 4 | empty / Hybrid / -0.003 .019 / Cognitive Legitimacy / .087** / Intent to Transact / empty |
| 5 | empty / empty / empty / (.024) / empty / empty / empty |

After, 6 rows by 5 columns, checked cell by cell against the rendered page:

| | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| header | | For-profit | For-profit | Nonprofit | Nonprofit |
| 1 | | core hybrid | business | core hybrid | organization |
| 2 | Variable | (N = 187) | (N = 185) | (N = 176) | (N = 186) |
| 3 | Intent to transact | 5.16 [4.96, 5.37] | 4.91 [4.72, 5.10] | 5.19 [5.01, 5.37] | 5.40 [5.21, 5.59] |
| 4 | Cognitive legitimacy | 4.64 [4.42, 4.86] | 4.66 [4.47, 4.86] | 4.43 [4.22, 4.63] | 4.41 [4.17, 4.64] |
| 5 | Moral legitimacy | 5.64 [5.46, 5.82] | 5.35 [5.18, 5.53] | 5.62 [5.45, 5.80] | 5.89 [5.73, 6.04] |

- One intact caption of 15 words stands before the table: "Table 1. Study 1
  Descriptive Statistics of Model Variables by Experimental Condition
  (N = 734)."
- The three numeric rows are intact. All twelve values and intervals match
  the page.
- No diagram label is in any cell. The note and the five diagram labels
  follow the table as text, then the Figure 3 placeholder.
- **Not fixed:** the wrapped column header is three rows, one per printed
  line. Each fragment is in the right column.
- The document's other four tables are unchanged by hash.

R01285 p. 8 also changed. "Table 3" was the header row of a two-column table
and is now its caption. The 53 body rows are identical.

Controls: the expectations of `paper` and `hard` are byte-identical to the
previous commit.

```
5e1511d7f65bc611e05f2bfb54b3bdd5c686b63dec548c2719a5f1cea0bb93a2  tests/expected/paper.md
5c7c089448082c63eb3ad6a65f33f9238d6483fc8002b3aa9bd86114635d51ab  tests/expected/hard.md
```

## Step 2: R00315 footnotes

| | Before | After |
| --- | --- | --- |
| Definitions | 49 | 9 |
| Numbered notes | 1, 3-10 | 1, 3-10 |
| Legend lines as notes (p. 15) | 4 | 0 |
| References as notes (pp. 18-25) | 36 | 0 |
| In-text references, numbered | 15 | 15, same order |
| In-text `[^†]` | 1 | 0, a superscript dagger again |

No in-text citation is broken. The 36 references are back in the list in
reading order and whole; several had been cut after their first line.

Two defects are visible in R00315 and are not changed by this release. Note 2
has no definition, and exponents "2" are emitted as references to it. Entries
whose first character is a star begin a Markdown line with `* `, which a
renderer may read as a bullet. This was already so for marked entries in the
upper part of a page.

Controls: York 2018 is byte-identical, with 3 definitions and 3 references.
The expectations of `footnote_repro`, `footnote_biglabel`,
`footnote_bold_wrapped` and `table_legend` are unchanged.

## Step F

**F.i** Fixture `figure_dedup` has a chart over its raster export with text
between chart and caption, and a figure caption directly under a table. The
converter of d2b45c8 gives two placeholders on page 1 and none on page 2. The
current one gives one captioned placeholder on each. Wry 2013 has 7
placeholders and York 2018 has 4.

**F.ii** Three of SBTi's eight caption-less placeholders, against the rendered
pages:

| Page | Region | What it is | Verdict |
| --- | --- | --- | --- |
| 8 | full-width band near the top | the ruled tail of a criteria table continued from the previous page | false positive |
| 40 | two bands, 52 pt high each | the two minimum-ambition formulas, set as pictures | real content, an equation and not a figure |
| 59 | large region, a quarter of the page | the flowchart "Figure 1. Target classification procedure" | real figure |

On p. 59 the caption exists on the page in italics. It is not found because it
is extracted inside the preceding paragraph block. The placeholder also stands
before that paragraph instead of after it. Nothing was fixed.

**F.iii** PLAN item 12 records R00443 p. 16 as evidence.

## Fixtures and checks

| Check | Windows | WSL |
| --- | --- | --- |
| tests/regress.py | all fixtures match, 6 OCR fixtures skipped | all fixtures match, none skipped |
| check_gui.py | OK, 33 methods, 18 self-calls | not run |

New fixtures: `figure_dedup`, `caption_inside_table`, `bibliography_symbols`.
New check: `cell-matrix`, which asserts which token stands in which cell of
`caption_inside_table`.

## Open after this release

1. Wrapped column headers stay one row per printed line (R02611 p. 18).
2. R00443: scattered character errors in the hidden OCR layer are not detected.
3. R00443 p. 16: a sideways table on an upright page loses 173 words. PLAN item 12.
4. R00030 p. 75: 16 of 261 tokens dropped under the 0.9 decision. PLAN item 4.
5. Kostova Figure 1 has no placeholder.
6. SBTi p. 8 false figure, and p. 59 caption swallowed by a paragraph.
7. R00315: note 2 undefined, exponents read as references to it.
