# Changelog

Changes that affect output or use, newest first. Every release's golden
audit (tests/golden.py) lists which reference documents changed and why.

## v0.2.0 (unreleased)

### Windows app

- Sun Valley light/dark interface in the logo's blue, monitor-aware sizing,
  a large empty drop zone, per-file pages/status/time and conversion progress,
  warning details, Preview and Log tabs, and collapsible Options.
- Native File, Edit, View, Tools and Help menus with keyboard shortcuts and
  shared handlers. Recent files, About, diagnostics and Check OCR.
- Preferences for output, Explorer integration, OCR override, theme and the
  startup Table grids choice. Older settings migrate with grids off.
- Check for updates is user-initiated only: one GitHub release request,
  ten-second timeout, graceful offline handling; no startup polling.

### Tables

- **Grids are now opt-in.** Default CLI/API/GUI output keeps table source
  lines as ordered prose under a marker. --grids, convert(..., grids=True),
  or Options → Table grids enables grids; Preferences saves the GUI default.
  The fresh held-out baseline from the author's own Zotero library was only
  2/60 correct (95% interval 0.9–11.4%). The frozen-sample final measurement
  and reason-code breakdown are in tests/REPORT-v0.2.0-rc.md.
- Wrapped record rows, ruled multiline headers, spanning-label column
  ownership, and conservative explicit same-schema vertical continuations.
  York's column-wise and Capital IQ's split-record continuations remain
  unresolved. The proposed B3.5 prose guard was discarded after regressing
  Wry's genuine continuation table; its idea is in the backlog.
- Grid-off source prose recovers some printed tokens grids dropped; every
  count increase is checked against rendered pages and recorded by token
  class, without source text. No metric change or threshold relaxation.
- The new v0.2.0 golden manifest covers both modes, excludes confidential
  files, and records PyMuPDF/Tesseract versions. Earlier manifests remain.

![The refreshed window](docs/images/markerlite-window.png)

## v0.1.18

Tables: a confidence gate, evidence labels and a drawn-box test. Scans:
sideways scans re-OCRed upright. Headings: per-page body size. The golden
baseline is now tests/golden/v0.1.18.json; every change against v0.1.16
is listed in tests/REPORT-block2-stop2.md and the commit messages.

### Tables

- **Table-confidence gate.** A reconstructed grid is emitted only when
  the page and the grid show it is a table. The page needs ruling lines or
  recurring column starts, the grid at least two rows and two columns, no
  curve drawn inside it, and fewer than 40% of its lines ending a sentence.
  Its cells must hold the source's words (token identity within 5%), and
  fewer than 15% of its rows may be wrapped continuation lines. Below the
  gate the region is kept as marked prose with every word. The removed
  grids are recorded in stats `tables_gated` with the failing test.
  Measured effect: on 142 held-out documents the gate removed 95 grids,
  82 of them wrong (a bad grid or not a table) and 13 correct. Correct
  grids turned into prose are the accepted cost (19 across the training
  and held-out sets). Gold set: wrong grids 18 -> 15, false grids on
  controls 5 -> 2. The kept-grid precision did not move measurably:
  0.34 (95% interval 0.22-0.48) before, 0.33 (0.21-0.47) after, on
  held-out samples of about 50 grids. Most remaining errors are rows and
  columns misassigned inside real tables, which a gate cannot catch.
- **Evidence labels.** Every emitted grid has a comment immediately before
  it: `<!-- table p. N: grid from ruling lines; verify before use -->` or
  `<!-- table p. N: grid from aligned text; verify before use -->`. The
  label states what the grid stands on, not how reliable it is: on the
  held-out sample, ruling-line grids were correct in 11 of 36 cases and
  aligned-text grids in 5 of 13, so both carry the same caution.
- **Drawn-box test.** Three or more stroked boxes in a region, none
  touching another, are a diagram (a model or flow figure), not table
  cells. On the labelled sets it removes 4 grids, all figures or
  non-tables, and no correct one.

### Scans

- **Sideways scans re-OCRed upright.** A raster page whose hidden OCR
  layer reads as fragments because it was made without orientation is
  OCRed again turned upright, and the result is kept only if it reads as
  words (R00443 pp. 14, 16; R02027 pp. 30, 31, 36).

### Headings and paragraphs

- **Per-page body size.** A page with enough text of its own is judged
  against its own body size, never a smaller one, so a 12 pt manuscript
  bound with a 9.5 pt letter no longer turns every line into a heading.
- **Heading-density guard.** A page where more than a third of the lines
  became headings is judged again by weight and shape alone, and listed
  in stats `heading_guard_pages` with a warning.
- A justified paragraph that ends a hair short of the column edge now
  joins its continuation on the next page; cells of one table row are
  never joined that way.

### Testing

- `tests/golden.py record` skips any `tests/real` file named in the local,
  git-ignored `tests/real/.golden-exclude`.

## v0.1.17

An interim release for the Windows app. Conversion output is unchanged:
every reference document converts to the same Markdown and stats as in
v0.1.16 (golden audit 85/85 after every commit).

### App

- **Cancel.** While a batch runs, Convert becomes Cancel; Esc does the
  same. "Cancelling…" shows at once. The current file is abandoned between
  pages (a running Tesseract is stopped) and leaves no output; finished
  files stay; the rest are skipped. The run log names the cancelled and
  skipped files.
- **Right-click menu** on file rows: Open Markdown, Open PDF, Show in
  folder, Copy Markdown, Show warnings, Re-convert, Remove from list
  (entries enabled only when they apply; nothing is deleted from disk).
  The preview pane has Copy and Select all.
- **Explorer "Send to".** An option, off by default, adds markerlite to
  Explorer's Send to menu (a shortcut in your own SendTo folder; no
  registry change, no admin rights). Files sent while markerlite is open
  go to that window and queue behind a running batch. Untick the option
  before deleting the markerlite folder.
- **One window.** A second launch hands its files to the open window over
  a local, per-user, authenticated pipe instead of opening another.

### Output

- **Atomic output.** Every output file and folder is written under a
  `.part` name and renamed into place only when the whole conversion
  succeeds. A failure, a cancel or Ctrl+C on the command line leaves no
  `.part` behind and the previous complete output intact.

### Command line

- Ctrl+C cancels with the same cleanup, lists the cancelled and skipped
  files, and exits with status 130.

### Build

- The zip no longer ships the CI runner's `markerlite-diag.txt`; the
  build log prints the zip's SHA-256; artifact actions moved to versions
  on Node 24, still pinned to commit SHAs.

### Measured cancel latency, as is

Time from Cancel to idle on every reference document, cancelling at
10/30/50/70/90% of its conversion, with Tesseract available and hidden.
Worst case 6.63 s. Long cancels happen inside whole-document steps that
check for a cancel only before and after; a worker-process design that
would make cancel immediate is recorded in tests/PLAN-cleanup.md.

| Document | OCR | Conversion | Worst cancel |
| --- | --- | --- | --- |
| capiq_keydev.pdf | yes | 57.5 s | 0.39 s |
| greenwood2006.pdf | yes | 10.4 s | 0.27 s |
| jay2013.pdf | yes | 20.7 s | 0.23 s |
| kitchener2002.pdf | yes | 116.1 s | 3.48 s |
| kostova1999.pdf | yes | 63.7 s | 0.04 s |
| peng2009.pdf | yes | 6.5 s | 0.28 s |
| R02027.pdf | yes | 35.2 s | 0.22 s |
| Ragins craft of clear writing 2012.pdf | yes | 2.6 s | 0.19 s |
| suchman1995.pdf | yes | 110.9 s | 0.34 s |
| Target-Validation-Protocol.pdf | yes | 57.3 s | 6.63 s |
| wry2013.pdf | yes | 8.9 s | 0.16 s |
| york2018.pdf | yes | 10.0 s | 0.28 s |
| capiq_keydev.pdf | hidden | 44.1 s | 0.28 s |
| greenwood2006.pdf | hidden | 7.8 s | 0.23 s |
| jay2013.pdf | hidden | 15.2 s | 0.53 s |
| kitchener2002.pdf | hidden | 22.5 s | 2.21 s |
| kostova1999.pdf | hidden | 6.2 s | 0.51 s |
| peng2009.pdf | hidden | 4.9 s | 0.22 s |
| R02027.pdf | hidden | 29.1 s | 3.72 s |
| Ragins craft of clear writing 2012.pdf | hidden | 2.4 s | 0.06 s |
| suchman1995.pdf | hidden | 6.2 s | 0.09 s |
| Target-Validation-Protocol.pdf | hidden | 45.1 s | 1.73 s |
| wry2013.pdf | hidden | 6.4 s | 0.12 s |
| york2018.pdf | hidden | 7.5 s | 0.41 s |

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
  ranges. 94 joins change across 24 reference documents, all ranges or
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
