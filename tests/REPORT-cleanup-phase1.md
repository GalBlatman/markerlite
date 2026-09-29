# Cleanup Phase 1 — safety net, coverage, and unobservable-code audit

Baseline: `v0.1.14` production code (`a19f287`). Environment: Python 3.14,
PyMuPDF 1.28.2, Tesseract 5.5.0, coverage.py 7.10.7. This phase changes no
converter behavior.

## Golden safety net

`tests/golden.py` records and verifies SHA-256 values without storing extracted
third-party text. `tests/golden/v0.1.14.json` contains 77 entries:

| Set | Entries | Modes |
|---|---:|---|
| generated fixtures | 37 | default |
| fixture option controls | 4 | page markers, images, flag-figures, flag-math |
| `tests/real/` | 11 | default |
| Packet A/B logical sources | 25 | default |

The 25 packet entries come directly from the two upstream packet JSON files.
They are resolved by the packets' recorded source SHA-256 across the supplied
corpus roots. This preserves both logical R00087 inputs even though their PDF
bytes are identical, and finds R00030/R00258 in the current run-002 tree
without copying them into this repository.

Each entry records the logical ID, source hash, page count, mode, Markdown
hash, canonical sorted-stats hash, OCR status, and hashes of generated JSON or
image artifacts. The manifest records PyMuPDF and Tesseract versions. OCR
entries compare only under the recorded Tesseract version; a different version
produces an explicit skip. Native entries continue to compare, with the
PyMuPDF version printed for every run.

Commands used:

```text
python tests/golden.py verify --scope fixtures
python tests/golden.py verify --scope full \
  --corpus-root /home/galbl/unknown-knowns-markerlite-v0112 \
  --corpus-root /home/galbl/unknown-knowns
```

Result before the audit: **41/41 fixture/mode entries and 77/77 full entries
matched; zero OCR entries skipped.** Markdown bytes, complete canonical stats
(including `suppressed`), figure/math manifests, and crop hashes matched.

## Branch coverage

The complete fixture regression, five wrapped-table unit tests, 11 real PDFs,
and all 25 Packet A/B logical PDFs were run under branch coverage. The two
packet manifests contain 79 Packet A cases and 44 Packet B cases.

| File | Statements | Missed | Branches | Partial branches | Coverage |
|---|---:|---:|---:|---:|---:|
| `markerlite.py` | 2,533 | 179 | 1,314 | 80 | 92% |
| `markerlite_gui.py` | 578 | 569 | 144 | 0 | 1% |
| `table_wrap.py` | 105 | 10 | 60 | 8 | 89% |
| **Total** | **3,216** | **758** | **1,518** | **88** | **78%** |

The GUI import is the reason for its low number: this WSL Python lacks
`tkinter`. No GUI method is therefore called dead. The approved test boundary
is pure helpers and option snapshots plus the packaged Windows `--diag`, icon,
and launch smoke test; widget-layout fakes are excluded.

The complete unexecuted-function/branch disposition remains in
`tests/PLAN-cleanup.md` section 2. The measured origins are reproduced here so
the Phase 1 result is independent of the plan:

- extraction/model: `Block.font_ratio` 278/281; `_page_raster_covered`
  456-457/461; `_page_is_image_only` 610-611/615; `_ocr_page` 646/661-662;
  `_attach_drop_caps` 751; `extract_page` 822/836; import fallback 61-67;
- tables: `_tokens_for_recon` 927; `_grid_from_members` 992-995;
  `_table_sane` 1057-1058/1061/1065/1072; `_page_graphics` 1104-1105;
  `_isolate_table` 1204/1206/1208/1211; `_split_members` 1282;
  `_journal_front_matter` 1304/1307/1315; `detect_tables`
  1346-1347/1418-1419/1424/1445-1446/1455-1456; `_columns_align` 1521;
  `propose_tables_from_text` 1564-1565;
- wrapped tables: `_ruled_bounds` 32/38 and `recover_wrapped_lines`
  58-59/66/74/77/93/104/107 in `table_wrap.py`;
- classification: `body_font_size` 1598; partial `_split_list_blocks` at
  origin 1722; `_is_equation` 1782; `_symbol_is_notation`
  1839/1846/1850-1859; `_is_heading` 1909;
- processors: partial `proc_line_numbers` at 2232 and nested `_increasing`
  2199; `proc_marginalia` 2322; partial `proc_section_levels` at 2487;
  `_bucket_headings` origins 2538/2544; partial `proc_continuation` 2665,
  `proc_list_indent` 2731, and `proc_code` 2751;
- rendering: partial `_TableParser.handle_data` at 2858;
  `table_html_to_markdown` 2867; `_inline` origin 2897; `render`
  3086/3157/3159/3165/3190; `summarize` 4129-4130;
- figures/handoffs: `_attach_figure_source_text` 2107/2114;
  `_vector_regions` 3230-3231/3265; `_figure_regions` 3329;
  `_equation_neighbourhood` origin 3476; `_route_raster_equations` origin
  3506; `place_figures` 3534-3541/3543/3546-3550;
  `_locate_caption_figure` 3586-3587/3592/3643; `flag_figures` 3689/3691;
  `apply_figures` 3729/3736; all of `flag_math` 3755-3780 and `apply_math`
  3786-3810;
- provenance/API/CLI: partial `detect_provenance` origins 3882/3936;
  `_ebsco_comment` 3952; partial `_drop_ocr_notice` 3970 and
  `_drop_provenance_lines.is_prov` 3988; `convert` 4065; all CLI `main`
  4145-4193 and the module guard 4197;
- GUI: every `App` method, `write_diagnostics`, and GUI `main`, because import
  stopped before class execution.

These paths are classified as reachable-uncovered or defensive, with named
fixtures/mocks in the plan. None is deleted in Phase 2 merely because coverage
missed it.

## Unobservable-code audit

The audit ran on temporary branch `scratch/unobservable-audit`. Each accepted
candidate was removed and the full 77-entry suite was run. The production tree
was restored after each experiment; the branch was deleted without merging.

| Candidate | Why suspected | Scratch result | Phase 2 action | Lines saved |
|---|---|---|---|---:|
| `detect_tables`: `score = 0.0` and the unused score result | reconstruction score is never read on the ruled-table path | **77/77 matched** | unpack only `res[0]` | 1 |
| `FOOTNOTE_START` | no reference; superseded by contextual `FOOTNOTE_MARKER` in `9bde71e` | **77/77 matched** | delete definition and stale comment | 4 |
| `proc_continuation`: `page = pages[blk.page_idx]` | assigned and never read since `e419550` | **77/77 matched** | delete local | 1 |
| fixture `foot_notes` local | assigned and never read since `e1ef3328` | **77/77 matched** | delete local | 1 |
| `check_proposal_guard` argument `guarded` | call result is never read by the check | **77/77 matched** | remove parameter and argument | 0 whole lines; simpler signature/call |
| fallback `_grid_from_members` → `_grid_to_html` construction | suspected obsolete because fallbacks now render as prose | **failed fixture goldens**: `continued_table_header.pdf` changed Markdown and stats | **retain** | 0 |

The geometric grid is observable even though its HTML is no longer emitted
for a fallback. It supplies the cell-word baseline, sanity/admission result,
and the decision to count and render the region as fallback prose. Removing it
caused `continued_table_header.pdf` to lose that decision. The full corpus was
not run after this fixture failure because the no-change contract had already
failed.

Static reference analysis and Ruff found no other compute-then-discard
production value or unused production helper. The similarly named word
counters are not duplicates: source-token multisets, visible table HTML, and
public Markdown content deliberately use different normalization. Import
fallbacks and exception handlers are defensive code and remain.

Ruff 0.13.2 (`E4,E7,E9,F,I`) also found import ordering, three semicolon
statements, and a test lambda assignment. Those are formatting/tooling work,
not unobservable behavior, and do not enter Phase 2.

## Phase 1 acceptance

- No production file changed.
- The manifest contains hashes only, not extracted third-party text.
- `python tests/regress.py`: all fixtures match.
- `python tests/golden.py verify --scope fixtures`: 41/41 match.
- Full local golden verification: 77/77 match, including all Markdown and
  stats hashes.
- The audit identifies five safe deletions and one required table path.
