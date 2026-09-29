<!-- GENERATED from CLAUDE.md by tools/sync_agents.py - do not edit -->
# markerlite — project context for coding agents

Read this before touching anything. It is the handoff from the sessions that
built the project and it records decisions, defects, and rules that are not
obvious from the code.

## What this is

A PDF→Markdown converter that runs offline, on CPU, with no model downloads.
It reimplements the weight-free half of Marker (github.com/datalab-to/marker)
on PyMuPDF's text layer, plus deterministic stand-ins for Marker's five
model-backed stages. Audience: researchers converting journal articles for LLM
use. A blog post about it is planned; the README is written for that audience
and its claims have been deliberately made honest — do not inflate them.

Public repo: github.com/GalBlatman/markerlite · Apache-2.0 · current release
v0.1.13 (`/releases/latest` is the download link the README and blog use).

## Layout

```
markerlite.py        the converter (CLI + `convert()` API). ~2000 lines.
markerlite_gui.py    Tk drag-and-drop front end. Runs from source or as the exe.
table_wrap.py        markerlite-owned wrapped-cell attachment around the winning grid.
table_recon.py       VENDORED from Marker (Apache-2.0). Table grid reconstruction.
                     Do not "improve" it; treat as third-party.
check_gui.py         static check: every `self.x()` in App resolves to a method.
                     RUN IT after any edit to markerlite_gui.py.
assets/              icon.ico / icon.svg / icon-256.png / logo-wordmark.png.
                     icon.svg is the vector source; the others are supplied
                     files. Do not redraw or regenerate them.
build_exe.bat        local PyInstaller onedir build (Windows)
.github/workflows/build-windows.yml   CI: builds the exe; on a v* tag publishes
                     a GitHub Release with markerlite-windows.zip (idempotent -
                     replaces the zip if the release already exists)
README.md            public landing page. INSTALL.md (WSL), WINDOWS-GUI.md (app).
LICENSE, NOTICE      Apache-2.0 for markerlite; NOTICE carries Marker attribution.
third_party/marker/LICENSE   Marker's license text (kept OUT of root so GitHub
                     detects exactly one license).
```

## Pipeline (markerlite.py `convert()`)

1. `extract_page` — PyMuPDF `rawdict`, **unsorted**: block order = PDF
   character-stream order. This IS the reading-order algorithm; Marker itself
   prefers stream order over its learned head on text-layer pages. Never sort
   blocks geometrically. OCR runs when a page has < 20 native chars, OR when
   one raster covers >= `OCR_RASTER_MIN_FRAC` (0.8) of the page and the native
   layer is < `OCR_MAX_NATIVE_CHARS` (500) and confined to the top/bottom 15%
   (a ProQuest/ResearchGate stamp or banner); the native layer is then
   discarded. Such pages carry `Page.image_only`; if none was OCR'd,
   summarize() says "N image-only pages, 0 OCR'd — check Tesseract".
   Before extraction, `detect_provenance` recognises JSTOR / ResearchGate /
   ProQuest cover pages and banners by their boilerplate text (never by
   position), drops them, and writes the citation they carried as
   `<!-- source: ... -->` comments at the top of the Markdown.
2. `detect_tables` — `find_tables` cascade (ruling lines, then
   `vertical_strategy="text", horizontal_strategy="lines"` for booktabs), then
   `reconstruct_table_html` from table_recon on word tokens re-split at gaps.
   Journal front matter with an Abstract label, long prose, a larger preceding
   title and publication metadata stays in its original blocks for heading/prose
   classification (`journal_front_matter`); page-1 data tables remain eligible.
   `_table_sane` rejects absurd grids. Never use the whole-page `text/text`
   strategy: it matches every page.
3. `classify` — order matters: Equation → Code → Caption → **Footnote before
   ListItem** (numbered notes match the list pattern) → SectionHeader → List.
   Then `_split_list_blocks`, `_unmark_lone_lists`, `_demote_toc`.
4. `propose_tables_from_text` — second-chance table detection for pages with
   no vector rules (scans). Guarded by `_columns_align`: token x-starts must
   recur across rows, otherwise justified prose becomes a "table".
5. Processors, in this order (each is a port of a Marker processor; the
   docstrings name the source file): `proc_line_numbers`, `proc_reflow`,
   `proc_ignore_common`, `proc_footnotes` (must run BEFORE marginalia),
   `proc_marginalia`, `proc_section_levels`, `proc_continuation`,
   `proc_merge_equations`, `proc_blockquote`, `proc_list_indent`, `proc_code`,
   `place_figures`, `_promote_figure_captions`, `proc_captions`,
   `_figures_from_captions`, `_route_raster_equations`, then the hand-offs
   `flag_math` (--flag-math) and `flag_figures` (--flag-figures).
6. `render` — Markdown. Footnotes as `[^N]:` with the detected label;
   superscript body refs become `[^N]` only when note N exists (else `<sup>`).
   Pages with `ocr_used` emit `<!-- ocr page N -->` independently of
   `--page-markers`, so recognized text keeps its provenance. A paragraph
   that opens like a list item and is not one has its marker escaped.
7. Hand-offs for a vision pass. markerlite does not read equations or
   figures; it crops them and takes the answers back. `--flag-math` writes
   `<stem>_math/` and `<stem>_math.json`, `--apply-math` splices LaTeX.
   `--flag-figures` writes `<stem>_figures/fig_p<N>_<M>.png` at 200 dpi and
   `<stem>_figures.json` ({stem, regions: [{id, page, bbox, caption, file,
   description}]}), one entry per placeholder in placeholder order;
   `--apply-figures` inserts each non-empty description under the M-th
   placeholder of page N as a block quote opening with
   `<!-- figure description: model-transcribed -->`. Both flags are off by
   default and change nothing in the Markdown when absent.

### Decisions that look wrong but aren't

- **Marginalia requires repetition evidence.** Position alone deleted page-top
  headings and titles. A running head is suppressed only if its text (page
  numbers stripped, fuzzy) recurs on 2+ pages, or is a bare page number.
  Headers and footers are both judged by position plus repetition; the old
  last-in-reading-order guard for footers was dropped (PDFMaker draws the
  footer first). Page-number tokens are stripped before matching, including
  tokens that merely contain a digit ("1995 Suchman $79" from OCR).
- **Reflow only joins single-line blocks.** Double-spaced manuscripts make
  PyMuPDF emit one block per line. Multi-line blocks are PyMuPDF's own
  paragraph grouping and must not be merged — the first version welded
  block-style paragraphs together.
- **Heading levels come from section numbering when present** (`3.1` → h3),
  else KMeans over line heights. Two bugs in Marker's own sectionheader.py
  are fixed here (axis=0 sort scrambling pairs; forced 4 clusters).
- **Equation detection uses glyphs + placement, not just font names**, so
  Symbol+Times equations are caught. Equations are NOT converted to LaTeX;
  `--flag-math` crops them for a vision pass, `--apply-math` splices results.
- **Token preservation ≠ structural correctness.** A table can keep every
  word and still be unusable if words land in the wrong cells. Word ratios
  (the 0.9 guards, conservation) catch loss; only per-cell token identity
  catches misassignment. Never certify a table change on counts alone.
- **Vendored table_recon is imported first**, marker-pdf second, and a missing
  file WARNS instead of silently setting the function to None. v0.1.0 shipped
  with that import reversed and lost borderless tables. Don't regress it.

## GUI facts

- tkinterdnd2 provides drag-and-drop and it DOES load inside the PyInstaller
  exe (verified with `--diag`). A native WM_DROPFILES fallback was tried,
  crashed on first drop, and was removed. Don't re-add it.
- Every widget in the drop zone is registered as a drop target (tkdnd does not
  propagate drops to parents).
- Options are snapshotted on the main thread before the worker starts; never
  read Tk variables from the worker thread.
- Window sizing: per-monitor DPI awareness (v2), sized against the work area
  of the monitor it opens on, then measured and shrunk if off-screen. Bottom
  controls are packed first with side=bottom so they can never be clipped.
  The user has two monitors with different scaling — test both.
- `markerlite.exe --diag` writes markerlite-diag.txt beside the exe.
- The status bar shows Tesseract's version (or a warning) at startup and on
  every Convert. After a batch each row shows pages / content words / OCR
  pages / tables (fallbacks); a row with any `stat_warnings()` entry gets a
  warning glyph and a hover tooltip with the summarize() line and the
  provenance citation. Every batch appends to `markerlite-run.log` in each
  output folder ("Open log"). Warning text comes from markerlite.stat_warnings
  so CLI, GUI and log agree; do not phrase warnings in the GUI.
- Per-page conservation: every page's emitted words are compared with its
  source words (native layer, or Tesseract's at every confidence). Below
  `CONSERVATION_MIN` (0.5), with at least `CONSERVATION_MIN_SOURCE` (20)
  source words, the page is listed in stats["lossy_pages"] with both numbers
  and shows in summarize(), the GUI glyph and the run log. regress.py's
  `conservation` check switches the sideways-page fix off and expects
  rotated_pages pp. 2-3 flagged. Closest clean page in the reference set:
  Ragins p. 2 at 0.57 (its line numbers are 40% of the page's words).
- Low-yield pages: a raster-covered page emitting < `LOW_YIELD_WORDS` (15)
  words. A report cover with a full-page picture and a short title trips it
  (SBTi p1); that is a known false positive, not a bug in the count.

### Suppression audit contract

`info["stats"]["suppressed"]` is always a list. Each record has stable fields:
`page` (one-based PDF page), `bbox` ([x0,y0,x1,y1] in points in the normalized
page orientation), `text` (unformatted source-line text), and `reason` (pass
name: `proc_line_numbers`, `proc_ignore_common`, `proc_marginalia`,
`provenance`, or `tilt_filter`). Every removed furniture/provenance/tilted line
is recorded, including lines cut from a retained block. Caption/footnote or
paragraph relocation is not suppression. summarize() reports the list length.
The downstream bump protocol consumes these field names; keep them stable.

## Workflow rules

- After editing CLAUDE.md, run python tools/sync_agents.py and commit AGENTS.md
  with it. Never edit AGENTS.md directly.
- Commit messages: imperative subject, body explains WHY. Every commit ends
  with the Co-Authored-By / Claude-Session trailer.
- Push after committing (`git pull --rebase` first if the remote is ahead).
  Create and push a version tag ONLY when the user explicitly writes
  "tag vX.Y.Z" in a message - never on your own initiative and never as part
  of another task. Tags are `vX.Y.Z`, patch bump per release; the tag push
  builds and publishes the Release. Never force-move a published tag; if a
  tag exists, bump.
- A fix motivated by a real document is verified on that document, not only
  its fixture. Every commit that claims to fix a real-document defect reports
  the before/after on that file.
- After editing markerlite_gui.py: `python check_gui.py`. After editing
  markerlite.py: `python tests/regress.py`; if the diff is intended,
  `--update` and commit the expected files with the change.
- Never slice code out of the App class by cutting to a section-comment
  anchor — two methods were deleted that way. Cut to the next `def`.
- Two bugs came from having two copies of a file and copying the wrong way.
  There is ONE copy now: this repo. Do not work from a scratch copy.

## Test fixtures and regression

`tests/fixtures/*.pdf` are generated by `tests/generators/make_fixtures.py`
(fpdf2, deterministic: a rerun reproduces the bytes). Each exists to
reproduce a specific fixed bug: `hard.pdf` (two-column, running head,
hyphenation across column, ruled table, footnotes), `repro.pdf` (3 pages,
page-top headings, raster figure + caption, vector chart, Symbol+Times
equations), `repro_tight.pdf` (same, 11mm top margin - header and heading
share one PyMuPDF block), `footnote_repro.pdf` (note wrapped across two
blocks, superscript refs, an exponent), `scanned.pdf` (raster of hard.pdf,
OCR path), `manuscript.pdf` (double-spaced, margin line numbers drawn as a
separate pass, first-line indents, running head drawn last).
`paper.pdf` is real pdflatex output (two-column, fancyhdr running head,
amsmath display equations, booktabs table, itemize, two footnotes); it is
rebuilt from `tests/generators/paper.tex` by `make_paper.sh`.

`python tests/regress.py` converts every fixture and diffs against
`tests/expected/`; non-zero on any difference. `--update` rewrites the
expected files - only for an intended behaviour change, committed together
with the code change. `scanned` needs Tesseract and is SKIPPED (not failed)
without it; regenerate its expected output from WSL, where Tesseract 5.5.0
is installed, not from Windows. CI runs `check_gui.py` and `regress.py`
before the PyInstaller build.

## Known defects, in priority order

1. Tables with tall multi-line cells assign content to wrong rows
   (`_attach_wrapped_lines` only fires when a numeric header transition is
   found). README lists tables under "partial" for this reason. Since the
   text-loss guard (below) a failed reconstruction keeps the original source
   paragraphs instead of a geometric grid. The words are retained but the
   table layout is lost (SBTi pp. 26, 34).
2. Heading recovery on journals that style all headings identically with no
   numbering: some headings render as paragraphs.
3. ScholarOne cover sheets (rotated/clipped submission metadata) produce junk
   tables at the top of some manuscripts.
4. OCR path: Tesseract lets a page number through mid-text; misreads large
   display type. Rule-less scanned tables and boxed figures are not
   recovered (Suchman Table 1 / Figure 1); superscript footnote references
   are lost (no superscript flag from Tesseract). See tests/REPORT-jstor.md.
5. References section: bold "REFERENCES" heading sometimes merges with first
   entry.
6. Inline math is not detected (Marker needs an LLM for this too).
7. Publisher scans with an invisible OCR layer (Jay 2013) are read from that
   layer, errors and all: footnote marks come through as "^". Re-OCR would
   be an OCR-gate decision and has not been taken.
8. Numbered footnotes on some two-column digital pages are not emitted as
   definitions (York 2018: 3 of 8); stage not yet traced.

Fixed and covered by the regression (do not reintroduce; the fixture in
parentheses fails if the fix is undone):
- a hyphenated last line joins across a column break even for a one-line
  block (`hard.pdf`, "bef-" / "ore"; Marker skips one-line blocks).
- a line-number column that arrives as ONE block is stripped, and reflow's
  column edges come from body-sized, non-margin blocks (`manuscript_numcol`).
  This was the Ragins "every line its own paragraph" failure.
- footers are judged by position + repetition only; no reading-order guard
  (`hard_footer_first`; Acrobat PDFMaker draws the footer before the body).
- rotated rawdict lines (|dy| > 0.1) are dropped in extract_page
  (`watermark`; a diagonal "RETIRED" seeded fake tables).
- a footnote is sized by its text, not its label (`footnote_biglabel`; Word
  labels are body-size glyphs).
- a bulleted line is never a heading, whatever its weight (`bold_bullets`).
- every figure leaves `<!-- figure: p. N; caption: ... -->` at its reading
  position, with or without --images (the link follows it when saved):
  rasters that are content, vector clusters, and any figure caption no region
  claimed, which is the only evidence on a scanned page (`repro`,
  `images_inline`). Figure interiors are never OCR'd. Page-sized rasters are
  ignored. This replaced the `<!-- image omitted ... -->` marker.
  An unclaimed figure caption first goes to an uncaptioned region within
  `FIGURE_CAPTION_REACH` (0.25 of page height), so a chart is marked once; a
  table never claims a caption that opens with a figure label. A caption
  without a delimiter ("FIGURE 1" alone, or followed by a capitalised title)
  is a caption even when its weight made it a heading.
- a text layer that extracts as nonsense is OCR'd instead (`garbled_font`;
  `readable_ratio` under `GARBLE_MIN` 0.10 on >= `GARBLE_MIN_TOKENS` 50
  tokens). This catches a broken ToUnicode map. It does NOT catch a scan whose
  hidden OCR layer has scattered character errors (R00443: lowest page 0.26,
  about 1.4% of tokens wrong); that needs a different trigger.
- the WRAP (Warwick) repository cover sheet is dropped and recorded
  (`provenance_pages` p. 7); two of its phrases must be present.
- the CLI reconfigures stdout/stderr with errors="replace" and prints an
  ASCII arrow; regress.py's `cli-cp1252` check runs it under a cp1252 console.
- aggregator scans with a native copyright stamp are OCR'd (`scanned_with_stamp`;
  the 20-char gate alone converted Suchman 1995 to 185 words of 17,550).
- on OCR pages `_is_heading` treats line height as shape evidence only, and a
  numbered opener must be short (`scanned`, `scanned_with_stamp`; Tesseract
  line boxes made ~60 body lines headings in one article).
- running heads match across pages after dropping digit-bearing edge tokens
  (`scanned_with_stamp`, "1995 Suchman 579" vs "1995 Suchman S81").
- provenance pages/banners (JSTOR, ResearchGate, ProQuest) are dropped by
  content signature and recorded as `<!-- source: ... -->` (`provenance_pages`;
  the control title page must survive).
- `propose_tables_from_text` keeps a block as prose when the proposed grid
  keeps < `TABLE_FALLBACK_MIN_KEEP` of the block's words (`justified_scan`;
  interim, PLAN items 4/5 remain the real fix). stats: `proposals_kept_prose`.
- footnote labels and continuation boundaries come from raw spans, never from
  formatted Markdown (`footnote_bold_wrapped`; "**3During" gave `[^**]:`).
  Note numbers must increase down the page.
- sideways pages are turned upright before extraction: `/Rotate` is baked in
  and a page with >= `ROTATED_PAGE_MIN_FRAC` (0.8) vertical characters is
  rotated in memory (`rotated_pages`). The tilt filter alone deleted seven
  table pages in two articles. Do not "simplify" it back to a filter.
- EBSCOhost notice pages, native or OCR'd, are provenance (`provenance_pages`
  p6, `ebsco_notice_scan`).
- a significance legend ("* p < .05") is not a footnote (`table_legend`).
- pi fonts: minus and "<" that extract as "2" and "," are repaired from the
  document's font inventory, BEFORE tables are built (`pi_minus`). convert()
  therefore extracts all pages first and runs detect_tables second.
- drop capitals are reattached to their paragraph; a lone capitalised word with
  real bold/size evidence is a heading (`dropcap`).
- a block of single letters is never a heading (`panel_letters`).
- `content_words` strips real tags only; a bare "<" is content. The old
  pattern undercounted SBTi by 2,079 words (16,266 vs 18,345).
- a table candidate gives up its caption and what stands under its bottom
  rule BEFORE reconstruction (`caption_inside_table`; regress.py's
  `cell-matrix` check asserts which token is in which cell). Caption: leading
  line with a table label, alone in its row, one run of text, plus its
  continuation lines; no punctuation needed after the number. Row extent:
  only for rule-only (second pass) candidates with no stroke inside the grid
  other than rules, and only when a note or a diagram stands under the last
  rule. Boxed tables are never cut (SBTi lost rows when they were). Caption
  words are counted apart: stats `table_captions_isolated`,
  `table_caption_words`, `table_lines_excluded`. The isolated caption is
  emitted before its table (`Block.leads`); other captions stay after.
- a star or dagger is a footnote marker only where context allows
  (`bibliography_symbols`; `_symbol_is_notation`). Not a note: a block inside
  a recognised reference list (heading to next heading; the heading may carry
  a raised note letter, "REFERENCESa"); a reference-shaped entry on a page
  that explains its marks or holds several such entries; a significance
  legend, also when its "<" extracted as nothing or as a control character.
  The glyphs are not banned: the star footnote on the fixture's page 2 must
  survive. R00315 emitted 36 references and 4 legend lines as notes.
- a paragraph that opens with `* `, `+ `, `- ` or `N. ` and is not a ListItem
  is escaped in render (`list_lookalikes`; R00315's starred references).
  `content_words` removes the escape, so the metric is unchanged by it.
- an equation set as a picture is an Equation, not a Figure (`repro` p. 3):
  a caption-less raster no taller than `RASTER_EQ_MAX_HEIGHT` (0.2 of the
  page) with an equation number beside it, a "Where:" or definition line
  under it, or a sentence above it that announces a formula. It leaves
  `<!-- equation: p. N; set as an image -->` and is cropped by --flag-math.
  SBTi pp. 40-44: six formulas. The announcing sentence is the only signal
  on p. 40; do not drop it.
- --flag-figures / --apply-figures (regress.py `flag-figures`; the filled
  manifest is tests/fixtures/repro_figures_filled.json, the result
  tests/expected/repro_described.md). A figure known from its caption only
  is located for the crop by `_locate_caption_figure`; inside a false table
  region curves and filled shapes still count as the figure (Peng 2009
  p. 2). With --images too, the Markdown links to the crops and
  `<stem>_images/` is not written. `content_words` leaves a spliced
  description out: it is not the document's text.
- text-loss guard in `detect_tables`: a reconstruction that keeps fewer than
  `TABLE_FALLBACK_MIN_KEEP` (0.9) of the words in PyMuPDF's geometric cells
  keeps its original source paragraphs as prose (`tall_cell` regression also
  disables wrapped recovery to exercise the lossy reconstruction). Existing
  fallbacks for unusable reconstruction do the same. The marker is
  `<!-- table p. N: reconstruction failed; text kept as prose -->`.
  Source block/line stream order and token identity are retained without
  dehyphenation. The geometric grid remains the guard's reference, filled
  from the table's own members, not `tbl.extract()`. Internally the block
  remains Table with `fallback_paragraphs`, so processors cannot consume or
  reclassify it. `tables_fallback` and the GUI column keep counting these
  decisions; summarize() prints "N of M tables kept as prose". This sacrifices
  five usable SBTi fallback grids as well as the shredded grids: measured
  spanned-line shares could not separate them (tests/REPORT-batchC-block1.md).

## Open items

- Table work follows tests/PLAN-tables.md; items 0, 1, 7, 8, 11b done;
  fallback-to-prose done; item 5 not needed after fallback-to-prose (no evidence
  in 44 remaining reference regions); item 6 done; 2,3,4 then 9,10,11a,11c pending review; 12 is evidence only. Items 2 and 5 carry extra
  evidence from five journal articles (tests/REPORT-batch2.md).
- Pipeline documents (R00443, R00030, R00087, R00639, R00077) are read in
  place from /home/galbl/unknown-knowns/ in WSL and never copied here. Four of
  the five are under stack/pdf/ or autonomous/run-002/pdf/, not pilot/pdf/.
  Results: tests/REPORT-batch3.md.
- Real-document validation: the user's Ragins 2012 (AMR manuscript PDF) and
  SBTi standards PDFs are the reference cases. Ask for them; do not assume
  the synthetic fixtures cover them.
- The GUI does not expose --flag-figures or --apply-figures yet (nor the
  math pair). WINDOWS-GUI.md is unchanged for that reason.
- Code signing (Azure Trusted Signing) if the blog gets traction —
  SmartScreen warns on every unsigned build.
