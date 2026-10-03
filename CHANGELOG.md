# Changelog

Changes that affect output or use, newest first. Every release's golden
audit (tests/golden.py) lists which reference documents changed and why.

## v0.1.16

### Output changes

- **Fallback marker only after a real table candidate.** `<!-- table p. N:
  reconstruction failed; text kept as prose -->` now appears only where the
  failed candidate shows table evidence: a ruling line, or column starts that
  recur across its rows, and no curves. Elsewhere (body prose behind Word's
  white line boxes, reference lists, figures) the text is emitted as ordinary
  text with no marker. On the 68 reference documents: 78 markers -> 50; the
  28 removed are 27 non-tables and one real table (Peng 2009 p. 2), whose
  words are all kept. New stats key `table_candidates_released` (only when
  non-zero). Released text is not offered to the text-table proposal pass.
- **Running heads need matching position and type size.** A line is
  suppressed as a repeated running head only if the repetition also agrees
  on alignment and, on digital pages, on type size; on OCR pages only
  position decides. R00014 p. 1 keeps its journal-name masthead; no other
  reference document changes.
- **A dash between two numbers survives a line break.** "3370-" / "3381" is
  now "3370-3381" (was "33703381"); the same for en and em dashes and year
  ranges. 94 joins change across 23 reference documents, all ranges or
  numbers.

### New warnings (flag only; no text removed)

- **Fragment pages.** A page whose emitted words are mostly one or two
  letters long (>= 30 letter tokens, >= 0.7 of them) is listed in
  `stats["fragment_pages"]` and warned about: "N pages emit text as
  fragments". Typical cause: a sideways scanned table read from a hidden OCR
  layer. Word conservation cannot see this, since pieces still count as words.
- **Resource limits.** A pathological PDF no longer stalls or exhausts memory:
  table projection, ruling lines, code indentation, provenance pieces, vector
  drawings per page, image pixels, OCR render size and Tesseract output are
  bounded, each at 10x or more the largest value measured on the reference
  set. A tripped limit keeps the content, adds `stats["resource_limits"]` and
  the warning "N resource limits reached ... content kept, see stats".

### App

- The version is visible: window title `markerlite 0.1.16`, a `v0.1.16`
  label in the status bar (click to copy version, Tesseract and Windows
  versions for a bug report), and the first line of `--diag`.
- File names and errors shown in the app, the run log and the console have
  control and bidirectional characters escaped.

### Security and build

- `--apply-math` / `--apply-figures` refuse manifest paths that leave the
  output folder.
- CI runs with read-only permissions; a separate release job, on `v*` tags
  only, is the one job that can write, and checks the tag against the
  version inside the zip. Actions are pinned to commit SHAs.
- `build_exe.bat` works from a folder whose path has spaces or `&`.
- SECURITY.md: threat model, scope and how to report.

### Measured, not improved: tables

Gold tables set (29 tables, 8 non-table controls, 1 ambiguous item):

| | v0.1.15 | v0.1.16 |
| --- | --- | --- |
| Tables exact / near / wrong grid / prose | 1 / 4 / 18 / 6 | 1 / 4 / 18 / 6 |
| Exact-match rate | 0.034 | 0.034 |
| Mean cell association | 0.512 | 0.512 |
| Mean adjacency F1 | 0.369 | 0.369 |
| Controls clean / false grid / false marker | 0 / 5 / 3 | 3 / 5 / 0 |
| Ambiguous item (a captioned reference list) | false grid | false grid |

Both columns use the current scoring rules (a table split across two pages
side by side is scored per page; the ambiguous item is reported apart), so
v0.1.15 reads 0.512 here rather than the 0.514 in the block 2 plan.

Table structure is unchanged in this release. Verify any table you intend
to read as data.
