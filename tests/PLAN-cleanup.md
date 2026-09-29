# Cleanup plan after v0.1.14

Status: **Phase 0 plan only. No production files have been moved, deleted, or
refactored.** The behavioral baseline is annotated tag `v0.1.14`, which peels
to commit `a19f287df68556255e5bd10e9d8c46b275f06854`.

This plan turns the current single-file implementation into a maintainable
package without changing PDF-to-Markdown behavior. Each phase begins from a
hash-locked v0.1.14 baseline and ends with the same fixture and real-document
results. A behavioral difference stops the cleanup until it is explained and
approved.

## 0. Evidence used for this plan

The coverage survey exercised:

- all 37 generated PDFs through `tests/regress.py`, including the OCR cases;
- all five `table_wrap` unit tests;
- all 11 PDFs under `tests/real/`;
- all 79 Packet A cases and all 44 Packet B cases, representing 25 unique
  source PDFs read in place from the downstream corpus;
- 36 unique non-fixture PDFs in total, without copying any into this repo.

The survey used Python coverage 7.10.7 with branch coverage. The core result
was:

| File | Statements | Missed | Branches | Partial branches | Coverage |
|---|---:|---:|---:|---:|---:|
| `markerlite.py` | 2,533 | 179 | 1,314 | 80 | 92% |
| `markerlite_gui.py` | 578 | 569 | 144 | 0 | 1% |
| `table_wrap.py` | 105 | 10 | 60 | 8 | 89% |
| **Total** | **3,216** | **758** | **1,518** | **88** | **78%** |

The GUI could not import under the local WSL coverage interpreter because it
does not have `tkinter`. That is a test-coverage gap, not evidence that the GUI
is dead. `check_gui.py` remains the static guard, and Windows executable smoke
tests remain required.

The source baseline has 5,756 lines across `markerlite.py`,
`markerlite_gui.py`, `table_wrap.py`, `tests/regress.py`, and `check_gui.py`.

## 1. Golden-output safety suite

Before the first move, add a machine-readable v0.1.14 baseline. It must freeze
behavior without checking copyrighted PDFs or extracted document text into
the repository.

### Manifest format

Create `tests/golden/v0.1.14.json` with one entry per input and mode. Each
entry contains only:

- a stable logical document ID;
- the source PDF SHA-256 and page count;
- the conversion mode and behavior-changing flags;
- the PyMuPDF version and, for OCR entries, the Tesseract version;
- the emitted Markdown SHA-256;
- a SHA-256 of `stats` serialized as canonical JSON with sorted keys and
  compact separators;
- hashes of any flag-math or flag-figures manifests and crops.

The generated-fixture entries run in CI. A second ignored local manifest,
produced by the same command, covers the 11 `tests/real/` PDFs and the 25
unique Packet A/B source PDFs in place. When those files are unavailable, the
runner reports each missing logical ID and skips that corpus; it must never
silently substitute a fixture. Neither the PDFs nor their Markdown enter the
repository.

The suite covers default conversion, the existing page-marker checks, OCR,
`--images`, `--flag-figures`/`--apply-figures`, and
`--flag-math`/`--apply-math`. It compares the complete stats object as well as
Markdown. Existing readable expected Markdown stays in place because it gives
useful review diffs; hashes add a single command that proves byte identity
across a large corpus.

Native-text entries compare on every supported environment. OCR entries
compare only when the running Tesseract version exactly matches the version in
the manifest; a mismatch is reported explicitly rather than accepted as a
hash difference or silently skipped. The PyMuPDF version is always reported
with a verification result so extraction-library drift is visible.

Proposed commands:

```text
pytest -q
pytest -q --corpus-root /home/galbl/unknown-knowns
python tests/golden.py verify tests/golden/v0.1.14.json
```

The first cleanup commit records the baseline from the tagged code. Later
commits may regenerate hashes only for an approved behavior change, never to
make a refactor pass.

## 2. Coverage gaps and their disposition

Every function or branch not executed by the survey is listed below. “Test”
means reachable behavior that needs a named test before it moves. “Keep” means
a defensive path whose triggering library or OS failure must be simulated.
No production function is classified as dead from coverage alone.

Phase 1 also audits **unobservable code**: code that executes but whose result
cannot reach either rendered Markdown or serialized stats. Candidates include
compute-then-discard locals, the unused `detect_tables` score, and grid/HTML
construction reachable only through output paths that fallback-to-prose no
longer emits. For each candidate, create a temporary scratch branch, delete
only that candidate, and run the fixture and full-corpus golden suite. The
Phase 1 report records the candidate, why it is unobservable, the hash result,
and estimated lines saved. Only candidates with every hash unchanged become
Phase 2 deletions; the scratch branches are not merged.

### Extraction, OCR, and document setup

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `Block.font_ratio` | 278, 281; origins 277, 280 | Test unusual empty and mixed-span blocks in `test_model.py`. |
| `_page_raster_covered` | 456-457, 461; origin 460 | Test multiple partial images and the exception path in `test_ocr_gates.py`. |
| `_page_is_image_only` | 610-611, 615; origins 614, 617 | Test native edge stamps against `scanned_with_stamp.pdf`. |
| `_ocr_page` | 646, 661-662; origin 645 | Keep timeout/error handling; mock Tesseract failure in `test_defensive_paths.py`. |
| `_attach_drop_caps` | 751; origin 750 | Test a rejected, non-adjacent initial beside `dropcap.pdf`. |
| `extract_page` | 822, 836; origins 813, 821, 835 | Test empty spans, tilted lines, and OCR replacement in `test_extraction.py`. |
| module import fallback | 61-67 | Keep compatibility with installed Marker; simulate both import paths. |
| `_normalise_rotation` related branches | exercised but threshold edges remain implicit | Parameterize `rotated_pages.pdf`, Wry, and York at either side of the rotation gates. |

### Table detection and reconstruction

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `_tokens_for_recon` | 927; origins 913, 915, 926 | Test orphan tokens and overlapping cells in `test_table_members.py`. |
| `_grid_from_members` | 992-995; origins 991, 993 | Test no-row/no-column defensive inputs and boundary tokens. |
| `_table_sane` | 1057-1058, 1061, 1065, 1072; origins 1060, 1064, 1071 | Parameterize absurd header, empty-cell, and skinny-grid rejection. |
| `_page_graphics` | 1104-1105 | Keep PyMuPDF exception fallback; mock `get_drawings()` failure. |
| `_isolate_table` | 1204, 1206, 1208, 1211; origins 1203, 1205, 1207, 1209 | Extend `caption_inside_table.pdf` with punctuation, interrupted rules, and boxed controls. |
| `_split_members` | 1282; origins 1276, 1279, 1281, 1284 | Test tokens on candidate and exclusion boundaries. |
| `_journal_front_matter` | 1304, 1307, 1315; origins 1303, 1306, 1314 | Cover with `journal_front_matter.pdf`, R01285 p. 1, R02611 p. 1, and Ragins p. 1. |
| `detect_tables` | 1346-1347, 1418-1419, 1424, 1445-1446, 1455-1456; origins 1423, 1429 | Test missing reconstruction dependency, overlapping candidates, and reconstruction exceptions in `test_defensive_paths.py`; use SBTi for fallback decisions. |
| `_columns_align` | 1521; origin 1520 | Add ragged and exactly aligned controls beside `justified_scan.pdf`. |
| `propose_tables_from_text` | 1564-1565 | Test candidate-construction failure and proposal conservation. |
| `_ruled_bounds` | `table_wrap.py` 32, 38; origins 31, 37 | Add incomplete outer-rule cases to `all_text_wrapped.pdf`. |
| `recover_wrapped_lines` | `table_wrap.py` 58-59, 66, 74, 77, 93, 104, 107; origins 65, 73, 76, 92, 103, 106 | Parameterize missing HTML, no anchors, ambiguous assignment, and conservation failure. |

### Classification

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `body_font_size` | 1598; origin 1597 | Test a page with no eligible body spans. |
| `_split_list_blocks` | origin 1722 | Add a one-line list and an unsplittable multiline block. |
| `_is_equation` | 1782; origin 1781 | Add a centered non-equation control to `repro.pdf`. |
| `_symbol_is_notation` | 1839, 1846, 1850-1859; origins 1838, 1845, 1849, 1851, 1852, 1855, 1857 | Extend `bibliography_symbols.pdf` and `table_legend.pdf` for every contextual exemption. |
| `_is_heading` | 1909; origin 1908 | Test an empty-span candidate and OCR/body controls. |
| `_demote_toc`, `_unmark_lone_lists`, footnote helpers, `_title_case` | functions executed, some predicate combinations not isolated | Add focused parameterized units while preserving their fixture checks. |

### Processors and furniture suppression

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `proc_line_numbers` | origin 2232 | Extend `year_column.pdf` for a near-consecutive non-margin control. |
| nested `_increasing` | 2199; origin 2198 | Unit-test empty, singleton, broken, and descending runs. |
| `proc_marginalia` | 2322; origin 2321 | Add a repeated block just outside the furniture band to `edge_content.pdf`. |
| `proc_section_levels` | origin 2487 | Test a document with no surviving headings. |
| `_bucket_headings` | origins 2538, 2544 | Test one-size, two-size, and tied-size heading sets. |
| `proc_continuation` | origin 2665 | Test an empty next page and a rejected cross-page merge. |
| `proc_list_indent` | origin 2731 | Test list items lacking geometry. |
| `proc_code` | origin 2751 | Test empty and mixed-font code blocks. |
| `_protect_numeric_records`, `_furniture_band`, `_furniture_protected`, `_positional_repeat`, suppression recording | major paths executed by Packet B | Add direct predicate tests so all Packet B rules remain visible after moves. |

### Rendering and stats

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `_TableParser.handle_data` | origin 2858 | Test data outside a cell and nested inline markup. |
| `table_html_to_markdown` | 2867; origin 2866 | Test empty tables and uneven rows. |
| `_inline` | origin 2897 | Parameterize every inline style combination and escaping. |
| `render` | 3086, 3157, 3159, 3165, 3190; origins 3085, 3156, 3158, 3162, 3167, 3179, 3189 | Test absent pages, pending list flushes, table leads, page markers, and terminal footnotes. |
| `summarize` | 4129-4130; origin 4128 | Test empty stats and all warning clauses through typed stats. |

### Figures, equations, and handoffs

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `_attach_figure_source_text` | 2107, 2114; origins 2106, 2113, 2117 | Extend `figure_source_labels.pdf` with empty, distant, and multiple label groups. |
| `_vector_regions` | 3230-3231, 3265; origin 3264 | Test drawing API failure and a rejected page-sized vector region. |
| `_figure_regions` | 3329; origin 3328 | Test a page with no eligible image or vector candidate. |
| `_equation_neighbourhood` | origin 3476 | Test a raster with neither announcement, number, nor definition. |
| `_route_raster_equations` | origin 3506 | Test no figure blocks and an already classified equation. |
| `place_figures` | 3534-3541, 3543, 3546-3550; origins 3533, 3536, 3538 | Test missing image bytes and save failures; keep the latter as defensive paths. |
| `_locate_caption_figure` | 3586-3587, 3592, 3643; origins 3591, 3642 | Use Peng p. 2 plus rejected left/right and page-edge candidates. |
| `flag_figures` | 3689, 3691; origins 3680, 3688, 3694 | Test crop failure, duplicate placeholder IDs, and empty regions. |
| `apply_figures` | 3729, 3736; origins 3726, 3735 | Test missing and blank descriptions. |
| `flag_math` | 3755-3769, 3777-3780; origins 3757, 3759, 3763, 3778 | Entirely reachable and untested: add `math_handoff.pdf`, crop hashes, and manifest assertions. |
| `apply_math` | 3786-3793, 3796, 3799-3800, 3803, 3806-3810; origins 3789, 3791, 3800, 3807 | Entirely reachable and untested: apply a filled manifest and cover blank/missing answers. |

### Provenance, API, and CLI

| Function or branch | Uncovered lines/origins | Disposition and proposed test |
|---|---|---|
| `detect_provenance` | origins 3882, 3936 | Extend `provenance_pages.pdf` with competing signatures and no citation. |
| `_ebsco_comment` | 3952; origin 3949 | Test an EBSCO notice lacking one optional field. |
| `_drop_ocr_notice` | origin 3970 | Test a partial OCR notice that must survive. |
| `_drop_provenance_lines.is_prov` | 3988; origin 3987 | Test an ordinary sentence containing one provenance word. |
| `convert` | 4065; origin 4064 | Test invalid/empty paths and all public option combinations. |
| `main` | 4145-4193; origins 4145, 4146, 4173, 4181, 4188 | Entirely reachable and untested under coverage: add subprocess tests for help, success, bad input, output selection, summaries, and cp1252. |
| module `__main__` guard | 4197 | Covered by the CLI subprocess test. |

### GUI

All GUI methods were unexecuted because `tkinter` was unavailable in the WSL
interpreter. GUI automation is deliberately limited to pure logic plus a real
Windows executable smoke test:

| Methods | Disposition and proposed test |
|---|---|
| `outdir_for`, `_warnings`, `_summary`, `_provenance_of` | Test as pure functions/helpers without constructing widgets. |
| `start` option capture | Extract or call the option-snapshot logic without a live widget tree and assert the worker receives immutable values. |
| `write_diagnostics`, GUI `main`, icon loading | Cover with a packaged Windows `markerlite.exe --diag` launch and assert its diagnostics and embedded icon resources. |
| Widget layout, tooltips, dialogs, monitor fitting, drag/drop and shell-open methods | No fake-widget tests. Preserve `check_gui.py`, the Windows launch smoke test, and focused manual checks when these methods change. |

`check_gui.py` remains mandatory after every GUI edit. The Windows smoke test
must also assert that the executable contains the seven icon resources that
match `assets/icon.ico`; v0.1.14 contains 16, 24, 32, 48, 64, 128, and 256 px
images with byte-identical resource payloads.

## 3. Dead and stale-code inventory

This is the complete static inventory found by AST reference analysis, Ruff,
and blame. Removal waits for the golden suite.

| Item | Evidence | Proposed action |
|---|---|---|
| `FOOTNOTE_START` in `markerlite.py` | No reference remains; `FOOTNOTE_MARKER` superseded it in `9bde71e`. | Delete in the dead-code phase. |
| `page = pages[blk.page_idx]` in `proc_continuation` | Local is never read; present since `e419550`. | Delete. |
| `score = 0.0` and its later binding in `detect_tables` | The local score is never consumed by this function. | Delete after a focused table regression proves no side effect was hidden in the expression. |
| `foot_notes = {1: [], 2: []}` in `make_fixtures.py` | Local is never read; present since fixture commit `e1ef3328`. | Delete. |
| comments near the table fallback and tall-cell fixture | They say the geometric grid/cell text is emitted, but since `2103350` failed reconstructions emit ordered prose. | Rewrite comments only; behavior stays fixed. |
| repeated stats-key initialization and warning lookups | New fields arrived in several feature commits, leaving the same string keys created and read in multiple stages. This is duplicated schema knowledge, not duplicate behavior. | Centralize construction in the typed-stats phase while preserving the returned dictionary exactly. |

No unreferenced production function was found. `recover_wrapped_lines` is
imported by `markerlite.py`; the Marker import fallback is public defensive
compatibility. The removed native `WM_DROPFILES` experiment is already absent.
No second implementation of a current algorithm was found that is safe to
delete. Similar word counters have deliberately different semantics (source
token multisets, HTML-stripped table words, and public content words) and must
stay separate or gain explicit names rather than be merged casually.

Ruff 0.13.2 with `E4,E7,E9,F,I` also reports import sorting, two semicolon
statements in `markerlite.py`, one in `markerlite_gui.py`, the two unused
locals above, and one test lambda assignment. These are mechanical cleanup,
not evidence of dead behavior.

## 4. Proposed package and function ownership

Keep the public command and imports stable through a thin root shim. The
vendored `table_recon.py` remains at the repository root, byte-for-byte
unchanged.

### `markerlite/model.py`

Own the `Span`, `Line`, `Block`, and `Page` dataclasses and their current
properties. `Span` keeps `bold`, `italic`, `mono`, `math`, and `superscript`;
`Line` keeps `text`, `height`, `x_start`, `x_end`, and `width`; `Block` keeps
`text`, `x_start`, `x_end`, `y_start`, `y_end`, `width`, `height`, `spans`,
`line_height`, `max_size`, and `font_ratio`.

### `markerlite/extraction.py`

Own `_bbox_of`, `readable_ratio`, `_normalise_rotation`,
`_page_raster_covered`, `_remap_pi_fonts`, `_page_is_image_only`, `_ocr_page`,
`_attach_drop_caps`, and `extract_page`. Keep provenance close to extraction:
`_lines_of`, `detect_provenance`, `_ebsco_comment`, `_drop_ocr_notice`, and
`_drop_provenance_lines`.

### `markerlite/tables.py` and `markerlite/table_wrap.py`

Own `_overlap_frac`, `_tokens_for_recon` and nested `place`,
`_grid_from_members`, `_grid_to_html`, `_html_word_count`, `_table_sane`,
`_page_graphics`, `_rules_in`, `_one_run`, `_line_size`, `_isolate_table` and
its nested helpers, `_split_members` and its nested helpers,
`_journal_front_matter`, `detect_tables`, `_columns_align`, and
`propose_tables_from_text`.

Move `_words`, `_html_words`, `_ruled_bounds`, and `recover_wrapped_lines`
with its nested assignment helper into the package's `table_wrap.py`. The root
`table_wrap.py` remains a temporary compatibility re-export until downstream
imports have had one release to migrate.

### `markerlite/classification.py`

Own `body_font_size`, `classify`, `_demote_toc`, `_split_list_blocks`,
`_unmark_lone_lists`, `_is_equation`, `_symbol_is_notation`,
`footnote_label`, `note_text_size`, `_is_footnote`, `_is_heading`, and
`_title_case`.

### `markerlite/processors.py`

Own `_protect_numeric_records`, `_furniture_band`, `_furniture_protected`,
`_positional_repeat`, `_record_suppressed`, `_suppress_block`,
`proc_line_numbers` and its nested predicate, `proc_ignore_common`,
`_clean_text`, `proc_marginalia`, `proc_footnotes`, `proc_section_levels`,
`_levels_from_numbering`, `_bucket_headings`, `proc_reflow`,
`proc_continuation`, `_flat_text_blocks`, `proc_blockquote`,
`proc_list_indent`, `proc_code`, `proc_merge_equations`, and `proc_captions`.
Declare processor order once in an explicit tuple or driver function and test
that order.

### `markerlite/figures.py`

Own `_prepare_figure_zones`, `_attach_figure_source_text`, `_insert_pos`,
`_vector_regions`, `_content_images`, `_insert_block`, `_figure_regions`,
`_promote_figure_captions`, `_figures_from_captions`,
`_equation_neighbourhood`, `_route_raster_equations`, `place_figures`,
`_locate_caption_figure`, `flag_figures`, `apply_figures`, `flag_math`, and
`apply_math`, including their current nested geometry helpers.

### `markerlite/render.py`

Own `_TableParser` and its `__init__`, `handle_starttag`, `handle_endtag`, and
`handle_data` methods; `table_html_to_markdown`; `_inline`,
`_strip_source_label`, `_footnote_groups`, `block_text`,
`_escape_list_start`, `_is_list_line`, `fallback_prose`, and `render`, with
their current nested padding and flush helpers.

### `markerlite/stats.py`

Own `_emitted_words`, `content_words`, `stat_warnings`, and `summarize`, plus
the typed stats records described below.

### `markerlite/api.py`, `markerlite/cli.py`, and compatibility shims

`api.py` owns `convert` with its exact v0.1.14 signature and return shape.
`cli.py` owns `main`. `markerlite/__init__.py` exports `convert` and the small
set of helpers already used by tests and downstream callers. Root
`markerlite.py` becomes a thin import/re-export shim and calls `cli.main()`
under its main guard. Root `markerlite_gui.py` stays the GUI entry point and
imports the package.

All `App` methods listed in the GUI coverage table, plus
`write_diagnostics()` and GUI `main()`, remain in `markerlite_gui.py`; this
split does not invent a GUI framework layer. `check_gui.py` remains a
standalone static check. The current regression helpers — `convert_to_string`,
`check_ocr_markers`, `check_source_suppression`,
`check_journal_front_matter`, `check_fallback_prose`,
`check_proposal_guard`, `check_conservation`, `check_garbled`, `table_cells`,
`check_cell_matrix`, `check_flag_figures`, `check_low_yield`,
`check_cli_console`, and its `main` — move by responsibility into pytest
modules under `tests/`, with `tests/regress.py` retaining a compatibility
`main` until the migration is complete.

## 5. Threshold inventory and calibration

Move behavioral constants and unexplained numeric gates into
`markerlite/thresholds.py`. Each constant gets a one-line rationale and a
test on both sides of its boundary. Defaults that are part of the API stay in
their public signatures and refer to the named constant.

| Area | Current thresholds to name | Calibration evidence |
|---|---|---|
| Native/OCR gate | native text `<20`; max native `500`; raster fraction `0.8`; edge band `15%`; OCR 300 dpi, PSM 1, timeout 180 s, confidence 30 | `scanned.pdf`, `scanned_with_stamp.pdf`, Suchman, Kostova, and Kitchener. |
| Garbled text | readable ratio `0.10` with at least 50 tokens | `garbled_font.pdf` as positive; R00443 as the known hidden-layer negative. |
| Rotation and tilt | minimum 100 chars; vertical fraction `0.8`; direction tolerances `0.1/0.9`; tilt cutoff `0.1` | `rotated_pages.pdf`, `watermark.pdf`, Wry, and York. |
| Page diagnostics | low-yield 15 words; conservation `0.5` with at least 20 source words | SBTi cover, `rotated_pages.pdf`, and Ragins p. 2 at 0.57. |
| Pi-font repair/drop caps | font count 5, suspicious-two count 3, glued ratio `0.8`; drop-cap scale/geometry gates | `pi_minus.pdf`, `dropcap.pdf`, and ordinary bold initials as negatives. |
| Reconstruction tokens | gap at `0.8` glyph height; row tolerance `0.5` height; fallback keep `0.9` | SBTi, `tall_cell.pdf`, R00030 p. 75, `paper.pdf`, and `hard.pdf`. |
| Grid sanity | header ratio `1.4`; empty-cell ratio `0.45`; candidate area 200 and `0.60` page; overlap `0.60` | SBTi's 55-region baseline, `paper.pdf`, `hard.pdf`, and boxed-prose controls. |
| Rules and caption isolation | rule cover `0.60`; physical-edge `0.95/0.08`; bounds 12 pt, `0.9` height, `0.15` width, 4 pt; member overlap `0.5`; caption size delta `0.6`, gap `0.8` | `caption_inside_table.pdf`, SBTi, and `all_text_wrapped.pdf`. |
| Front matter/table proposals | title scale `1.25`; journal title `0.95`; alignment needs 3 recurrences at `0.60`; proposal score `0.62`; 2-12 columns | `journal_front_matter.pdf`, R01285 p. 1, R02611 p. 1, Ragins p. 1, and `justified_scan.pdf`. |
| Classification | mono ratio `0.8`; TOC run 5; equation center `0.12`, width `0.75`, math-font/math-char gates; footnote y `0.70`, size `0.95`; heading bold/title-case `0.60` | `repro.pdf`, `paper.pdf`, `footnote_repro.pdf`, `bibliography_symbols.pdf`, `dropcap.pdf`, and `panel_letters.pdf`. |
| Furniture bands/repetition | fuzzy threshold `0.015`; top/bottom `0.10/0.87`; touch 2 pt, x alignment 3 pt; line-number margin `0.14`, run 8, increasing ratio `0.8`, body geometry gates; marginalia `0.08/0.13/0.035`, max length 150 | `hard.pdf`, `manuscript.pdf`, SBTi, and Packet B's `continued_table_header.pdf`, `edge_content.pdf`, and `year_column.pdf`. |
| Reflow/continuation/layout | line gap `2.4`, size delta `0.15`, x tolerance `0.015`, column margin `0.14`, body scale `0.9`; continuation `0.02`; blockquote/list tolerances; equation gap `1.8`; caption gap `0.05` | `hard.pdf`, `manuscript.pdf`, `repro_tight.pdf`, lists, footnotes, and Packet B continuation pages. |
| Figures/equations | vector minimum 8 segments/60 pt; page-line `0.98`; area `0.01-0.70`; image minimum 40 pt, page max `0.90`, span `0.95`; table overlaps `0.5/0.4`; text density `0.35`; caption 60 words/reach `0.25`; raster equation height `0.20`, gap `0.06`; crop 200 dpi | `repro.pdf`, Peng p. 2, R00153, R00443, `figure_source_labels.pdf`, and SBTi pp. 40-44. |

Threshold extraction is organizational only. Calibration changes are separate
behavior commits with the real-document rule and their own approved baselines.

## 6. Typed stats and warning contracts

Replace the freely shaped internal stats dictionary with typed structures,
while preserving the public dictionary returned by `convert()` byte-for-byte
at the boundary.

Use a `ConversionStats` dataclass or `TypedDict` with every existing field,
including table totals/fallbacks, OCR/image-only pages, lossy and low-yield
pages, provenance, rotations, caption isolation, proposals kept as prose, and
`suppressed`. Use a `SuppressionRecord` with the stable fields `page`, `bbox`,
`text`, and `reason`. Add construction helpers instead of scattered
`setdefault` calls.

Tests must assert:

- the exact v0.1.14 stats keys, value types, and serialized values;
- each suppression reason belongs to the documented finite set;
- `stat_warnings()` is the only warning-policy function consumed by CLI and
  GUI;
- `summarize()` keeps its current wording, including “kept as prose”;
- old callers that index the returned dictionary continue to work.

Only after one compatibility release should a typed object become public, and
then only with an explicit migration path.

## 7. `pyproject.toml`, pytest, Ruff, and CI

Add `pyproject.toml` only after the golden suite exists. It defines the
package, CLI entry point, Python floor, and compatible direct-dependency
ranges. Exact resolved versions belong in `requirements-lock.txt`, used by CI,
the PyInstaller build, and the documented pinned-pipeline installation. The
initial lock records the successful v0.1.14 Windows build versions:

- NumPy 2.5.3
- PyMuPDF 1.28.2
- RapidFuzz 3.14.6
- regex 2026.9.29
- scikit-learn 1.9.1
- tkinterdnd2 0.6.3
- PyInstaller 6.22.3 and pyinstaller-hooks-contrib 2026.7 in the build extra
- pytest, coverage 7.10.7, and Ruff 0.13.2 in the development extra

Expose one version source as `markerlite.__version__`. `--version`, serialized
stats, package metadata, and release checks all read it and require it to
match the release tag. Creating or pushing that tag remains a user action.

Move the regression entry point under pytest without discarding its readable
fixture diffs. Keep a small `tests/regress.py` compatibility wrapper during
the migration. Configure Ruff incrementally: first `E4,E7,E9,F,I`, with
format checking, then enable additional rule families only in dedicated
cleanup commits. Never mix automatic formatting with a module move.

CI becomes:

1. sync check for generated `AGENTS.md`;
2. Ruff check and format check;
3. pytest plus coverage on Ubuntu, including Tesseract OCR fixtures;
4. pytest and `check_gui.py` on Windows;
5. golden fixture hashes on both systems;
6. the existing PyInstaller build, `--diag` smoke test, and embedded-icon
   resource assertion;
7. release publication unchanged on explicit `v*` tags.

GitHub's Ubuntu runner is the portable Linux check; it is not literally WSL.
Each phase report therefore also records the same pytest/golden commands run
locally in WSL, plus the green Windows CI job. A missing local corpus is
reported rather than treated as green.

## 8. README installation for pinned pipelines

Add a short section after the ordinary installation instructions. Proposed
copy:

```markdown
## Pin markerlite in a pipeline

Install an exact released revision so a later table or OCR rule cannot change
an existing corpus unexpectedly:

    curl -O https://raw.githubusercontent.com/GalBlatman/markerlite/v0.1.15/requirements-lock.txt
    python -m pip install -c requirements-lock.txt "markerlite @ git+https://github.com/GalBlatman/markerlite.git@v0.1.15"
    python -c "import markerlite; print(markerlite.__version__)"

Record the tag and keep the generated Markdown and stats hashes with the
pipeline run. Upgrade deliberately, then compare those hashes on a sample
corpus before processing everything again.
```

Use the first packaged release tag available at that phase; `v0.1.15` above
is illustrative and must not be created as part of cleanup. Document the
source checkout command as an alternative until a wheel is published.

## 9. Phased commit sequence

Use exactly one reviewed commit for each phase below. Every phase runs the
fixture suite, golden hashes, the local real/Packet corpus when available,
`check_gui.py` after GUI edits, and the appropriate Windows job. Pull with
rebase before each push. No cleanup phase creates a tag.

### Phase 1 — safety net and coverage report

Add the golden manifest/runner, freeze the v0.1.14 fixture hashes, add the
optional in-place corpus command and local hashes for all 36 documents, and
commit the reproducible coverage report. Add only the minimum tests needed to
make the safety harness itself trustworthy; the report retains every gap in
section 2 for later test work. Run the unobservable-code scratch-branch audit
described in section 2 and include its complete candidate/results table.

Estimated production removal: **0 lines**. Expected test/report addition:
roughly 500-800 lines.

### Phase 2 — delete confirmed dead code

Delete only the items in section 3 that the Phase 1 suite proves inert, and
the unobservable candidates whose scratch deletions left all hashes unchanged;
repair the associated stale comments. Do not format or move surrounding code
in this commit. If any hash moves, restore the code and report the item as
misclassified.

Estimated production removal: **10-20 lines**.

### Phase 3 — mechanical package split

Create the module layout in section 4 and move functions without logic edits.
Preserve the processor sequence explicitly, keep compatibility imports in
root `markerlite.py` and `table_wrap.py`, and keep `table_recon.py` untouched.
Record its SHA-256 before and after. Do not extract thresholds or replace stats
dicts in this phase. Before and after the move, compute a normalized AST hash
for every function and method, excluding source location attributes. Report
every mismatch; the mismatch table must be empty except for explicitly listed
compatibility shim and import lines, which contain no moved function bodies.

Estimated root-file removal: **3,900-4,100 lines moved**, leaving a roughly
30-60 line root compatibility entry point. Estimated actual deletion:
**0-10 lines** of move scaffolding; total behavior code remains similar.

### Phase 4 — thresholds and typed warnings/stats

Move the complete section 5 inventory into `thresholds.py`, adding one-line
calibration comments without altering values. Introduce `ConversionStats` and
`SuppressionRecord`, centralize key construction, and serialize back to the
exact existing dictionary field names and values at the public boundary.

Estimated production removal: **30-60 lines** of repeated key initialization
and local constants, offset by typed declarations and calibration comments.

### Formatting commit — after Phase 3

Run `ruff format` in its own golden-verified commit after the mechanical move.
It is never mixed with moved functions or behavior edits. This commit is
separate from the numbered behavior-preserving phases.

### Phase 5a — tooling, CI, and documentation

Add `pyproject.toml`, pinned dependencies and console entry point; migrate the
runner to pytest while retaining its compatibility wrapper; enable the stated
Ruff rules; and update CI, README, INSTALL, CLAUDE.md, generated AGENTS.md,
and a one-page `ARCHITECTURE.md`. Use compatible dependency ranges in
`pyproject.toml` and the exact lock file everywhere reproducibility matters.

### Phase 5b — coverage-gap tests

Add direct tests for the reachable gaps in section 2, including math handoff,
CLI, the limited GUI pure logic named above, and defensive paths. Do not add
fake-widget tests of layout, tooltips, dialogs, drag/drop, or monitor fitting.
The final report covers imports, CLI output, GUI diagnostics, hashes, stats,
Windows CI, local WSL, executable build/launch, and `check_gui.py`.

Estimated production removal: **20-40 lines** as the hand-rolled runner and
temporary compatibility scaffolding shrink. Across all phases, estimated
actual deletion is **60-100 lines**; most of the 3,900-4,100-line reduction in
root `markerlite.py` is movement into owned modules, not deletion.

## Stop point

This document is the complete Phase 0 deliverable. Implementation, file
moves, deletions, formatting, dependency changes, and CI edits wait for review
and explicit approval of the next phase.
