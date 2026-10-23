# v0.2.0 release-candidate verification

Status: candidate prepared; post-push verification follows below. No tag.
Grid default OFF by owner ruling.

## Accepted table work

B3.1 f0eceec (wrapped record rows), B3.2 b27aae7 (ruled header bands),
B3.3 84cf752 (spanning-label column ownership), B3.4 8b743f3 (explicit,
compatible vertical continuations). B3.5 was discarded, not shipped. Its
Wry p. 47 regression and the idea are in PLAN-tables.md's backlog.

## B4 frozen held-out measurement

Reconvert the original 80-document Zotero draw; do not replace documents or
regions. Compare the original 60 sampled grids by PDF hash, page, source box,
cell matrix and continuation identity. Reuse unchanged B2 labels; changed
grids receive two independent rendered-page/crop checks. Labels are committed
before computing final precision. Final: 2/60 correct (3.33%); 95% Wilson interval 0.919–11.364%.
59 matrices/labels are unchanged; the sole changed grid remains WRONG in
both new independent passes. Labels were committed in 13d991b before this
calculation. All 80 sources match the frozen hashes and converted successfully.

B2 reason-code breakdown (union of the two existing reviewers; categories
are nonexclusive):

| Category | Regions |
| --- | ---: |
| Header errors | 36 |
| Wrong rows | 22 |
| Not a table | 17 |
| Wrong extent / included material | 15 |
| Cell text / cell association | 11 |
| Wrong columns | 10 |

Of 58 wrong grids, one has only cell-text/association codes; 57 have at least
one other category. Severity was not graded, so "cell-only" does not mean
"minor". Raw reason-code counts and the exact mapping are preserved in
labels/b4-b2-reason-breakdown.json; no source text is included.

## B5 grid modes

CLI --grids / --no-grids and API grids=False; GUI Options → Table grids,
with a saved Preferences startup default. Default OFF. Settings schemas 1–2
migrate with grids off; schema 3 records the preference. Per-batch choices
are snapshotted on the main thread. Detection, furniture protection and the
existing reconstruction guard remain active in both modes. Off mode renders
ordered original source lines, not flattened reconstructed cells, under
"grids disabled; text kept as prose" markers. Stats keep the original guard
counts and add tables_grids_disabled when nonzero.

Both modes pass on 93 conversion specifications covering 84 unique PDFs.
Markdown changes for 54 unique documents (60 specifications). No page count
decreases; six source-verified recovery pages gain 29 tokens altogether.
Full hash-only page counts: labels/b5-mode-audit.json.
Every source table line is checked in the off output. The standard
content_words implementation is unchanged. No decrease is permitted; an
increase needs rendered-page proof for every recovered source token.

Verified recoveries (token classes only):

| Document | PDF page | Page words on → off | Recovered class |
| --- | ---: | ---: | --- |
| SBTi | 54 | 330 → 333 | Three bullet tokens |
| Greenwood | 11 | 651 → 655 | Four spanning-subheader tokens |
| Jay | 6 | 670 → 671 | One wrapped-cell proper-noun token |
| York | 22 | 331 → 344 | Thirteen spanning-header tokens |
| R00373 | 12 | 395 → 401 | Six wrapped-row-label tokens |
| R05732 | 7 | 509 → 511 | Two wrapped-cell tokens (numeric/acronym) |

All additions are visible in the rendered original and absent from the grid;
normalized token subtraction finds no removed token on these pages. The
hash-only records are labels/b5-prose-recoveries.json.

## Pre-tag checks

- WSL pytest: 283 passed, 3 Windows-only skips; one existing homogeneous-font
  clustering warning in the synthetic continuation fixture.
- All readable structural fixture regressions pass with explicit grids on.
- Ruff and check_gui.py pass (85 methods; 56 self-calls resolve).
- Clean environment: 28 installed production files match the candidate exactly.
  pip install -c requirements-lock.txt . succeeds;
  markerlite --version reports 0.2.0; default conversion of hard.pdf succeeds
  and reports one table kept as prose (grids off).
- New golden manifest recorded: 186 entries (93 specifications in both
  grid modes), exclude list respected; PyMuPDF 1.28.2, Tesseract 5.5.0.
  Archived verification of this new manifest follows the candidate commit.
- Windows build, real frozen window title, --diag first line, icon resources,
  source GUI screenshots and Ubuntu CI on final main: pending.
- No tag. Final worker/process audit: pending.
