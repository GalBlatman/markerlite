# markerlite — project context for Claude Code

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
v0.1.7 (`/releases/latest` is the download link the README and blog use).

## Layout

```
markerlite.py        the converter (CLI + `convert()` API). ~2000 lines.
markerlite_gui.py    Tk drag-and-drop front end. Runs from source or as the exe.
table_recon.py       VENDORED from Marker (Apache-2.0). Table grid reconstruction.
                     Do not "improve" it; treat as third-party.
check_gui.py         static check: every `self.x()` in App resolves to a method.
                     RUN IT after any edit to markerlite_gui.py.
assets/              icon.ico / icon.svg / icon-256.png
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
   blocks geometrically.
2. `detect_tables` — `find_tables` cascade (ruling lines, then
   `vertical_strategy="text", horizontal_strategy="lines"` for booktabs), then
   `reconstruct_table_html` from table_recon on word tokens re-split at gaps.
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
   `extract_images`, `proc_captions`, `flag_math`.
6. `render` — Markdown. Footnotes as `[^N]:` with the detected label;
   superscript body refs become `[^N]` only when note N exists (else `<sup>`).

### Decisions that look wrong but aren't

- **Marginalia requires repetition evidence.** Position alone deleted page-top
  headings and titles. A running head is suppressed only if its text (page
  numbers stripped, fuzzy) recurs on 2+ pages, or is a bare page number.
  Headers are judged by position only (they are often drawn LAST in the
  stream); footers additionally require being last in reading order (protects
  the foot of column 1 on two-column pages).
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

## Workflow rules

- Commit messages: imperative subject, body explains WHY. Every commit ends
  with the Co-Authored-By / Claude-Session trailer.
- Only the user pushes (`git push`) and tags. Tags: `vX.Y.Z`, patch bump per
  release. Tag push triggers the build and publishes the Release. Never
  force-move a published tag; if a tag exists, bump.
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
`paper.pdf` (real pdflatex: display equations, booktabs table) is still
missing: `tests/generators/paper.tex` + `make_paper.sh` build it, but no TeX
was installed on the dev machine. Add it and run `regress.py --update paper`.

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
   found). README lists tables under "partial" for this reason.
2. Heading recovery on journals that style all headings identically with no
   numbering: some headings render as paragraphs.
3. ScholarOne cover sheets (rotated/clipped submission metadata) produce junk
   tables at the top of some manuscripts.
4. OCR path: Tesseract lets a page number through mid-text; misreads large
   display type.
5. References section: bold "REFERENCES" heading sometimes merges with first
   entry.
6. Inline math is not detected (Marker needs an LLM for this too).

## Open items

- Add `paper.pdf` (needs pdflatex) and its expected output; see above.
- Real-document validation: the user's Ragins 2012 (AMR manuscript PDF) and
  SBTi standards PDFs are the reference cases. Ask for them; do not assume
  the synthetic fixtures cover them.
- Code signing (Azure Trusted Signing) if the blog gets traction —
  SmartScreen warns on every unsigned build.
