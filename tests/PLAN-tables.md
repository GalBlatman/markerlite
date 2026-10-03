# Table recovery plan — v0.1.8 baseline

Planning only. No converter, vendored reconstruction, fixture, or expected-output
changes are part of this commit. Review this plan before implementation.

## Evidence and baseline

Read the downstream report **in place** at
`/home/galbl/unknown-knowns/pilot/markerlite-stage-a/issues.md` (the Ubuntu path
behind the supplied UNC path). It concerns initial commit `e419550`, not the
current converter. Also read CLAUDE.md defect 1 and commit `62c3ff8`, and inspected
the PDFs in `tests/real/`. The report and third-party PDFs are not copied here.

All page references below are **one-based PDF pages**. SBTi's printed page number
is one less: PDF pp. 10, 13, 26 correspond to printed pp. 9, 12, 25.

Reran the current core, which matches v0.1.8 ignoring existing line-ending-only
changes, through its normal `convert()` pipeline, with page markers and no
downstream wrapper hooks. Used `/home/galbl/.markerlite-venv/bin/python`, PyMuPDF
1.28.2, with Tesseract available. Temporary Markdown, source text, and block
diagnostics stayed under `/tmp/markerlite-plan-audit/`. Inspected source page
renderings as well as extracted text; word retention alone cannot verify cells.

Full-document runs: SBTi (63 pages), Ragins (22), and pilot PDFs R02611, R01285,
S0009, R05732, S0008, R00014, R02027, R00315, R01114 from
`/home/galbl/unknown-knowns/pilot/pdf/`. These are representative reruns for all
nine issues, not a claim to have revalidated every document in the 25-PDF pilot.
All 14 existing regression fixtures and the cp1252 CLI check pass in this runtime.

SBTi reproduces **36 fallbacks / 55 detected tables** exactly. This counter only
covers `detect_tables`: it does not count tables from `propose_tables_from_text`.
For example, S0009 reports zero detected tables but still emits reference-page
tables. Do not interpret the stats as a count of every rendered table.

Commit `62c3ff8` records SBTi retention improving to 18,685 / 18,884 words. That
is the prior audit's metric, not a newly reproduced token-identity measurement.
The current page-2 table has 241 source-member whitespace words; rerunning its
reconstruction yields 71. The geometric fallback keeps 241. These counts use a
different source unit from the commit's 71 / 248 example; do not mix denominators.
Ragins still emits its page-1 submission metadata as a two-column table, but the
clipped duplicate is gone. Its body and page-22 writing-advice list are useful
negative controls against over-detecting tables.

## Nine-issue triage against v0.1.8

Statuses describe the complete reported behavior, not just disappearance of its
original string signature. There are **0 CLOSED, 2 PARTIAL, and 7 OPEN** items.

| Report item | Status | Current evidence and what remains |
| --- | --- | --- |
| 1. Journal front matter captured as tables | OPEN | R01285 p. 1 still splits title/authors across cells; R02611 p. 1 still puts title and abstract into a table. No front-matter admission check was added. Ragins p. 1 is a related submission-metadata case, not evidence that all front matter is fixed. |
| 2. Reconstruction silently drops tokens | PARTIAL | The 0.9 geometric fallback protects many `detect_tables` cases: SBTi's 36 fallbacks demonstrate that improvement. The proposal path remains unguarded. S0009 p. 17 emits 502 HTML whitespace words from 761 source-member words, and pp. 17–22 still become reference tables. R05732 p. 6 remains structurally wrong despite similar aggregate source/output counts. Loss below 10%, omitted membership, and replacement by unrelated words are not excluded by a count ratio. |
| 3. Caption inside a table block | OPEN | R02611 p. 18 now retains the caption words, but shreds them into a seven-column header instead of separating the caption. The same block includes labels from the diagram below, and numeric rows are collapsed. The old wrapper-triggered prose fallback is not the exact current symptom; caption isolation is still absent. |
| 4. Run-together words | OPEN | S0008 p. 1 still contains `legitimacyhasbeenthesubject` and `searchersadoptasomewhatbroaderlensthatexamines`. The raw text layer already glues them; `extract_page` copies character strings without body-text gap recovery. The report's 1.98/1k rate is historical, not remeasured here. |
| 5. Wrapped titles/headings split | OPEN | R00014 p. 1 still emits two consecutive `##` headings for “AN INTELLECTUAL HISTORY OF INSTITUTIONAL” and “THEORY: LOOKING BACK TO MOVE FORWARD”. No adjacent-heading merge exists. |
| 6. Bold seams and failed dehyphenation | OPEN | R02027 has 1,609 literal `** **` seams in this run; p. 1 contains `lati-** **tude`. `_inline` merges spans within a line, but `block_text` formats each line before joining/dehyphenating. |
| 7. Unlabeled, fragmented footnotes | PARTIAL | The labeled-definition, continuation, and reference fixes work on the existing fixtures and many R01285 notes; literal `[^]:` is gone. But R02027 p. 3 emits separate `[^**]:` definitions for bold continuation lines of notes 3 and 4. The renderer calls `footnote_label` on already formatted strings, treating Markdown `**` as a source note marker. R00315 also has italic-marker misidentification. This is not CLOSED merely because labels are nonempty. |
| 8. Control characters leak | OPEN | R00315 still contains 217 C0 controls, including 27 on p. 10 and 48 on p. 12. Dropping rotated lines does not sanitize surviving horizontal glyph strings. Some are unmapped mathematical glyphs: deletion removes controls, not reconstructs their intended symbols. |
| 9. Isolated OCR page lacks provenance | OPEN | R01114 p. 36 still emits “Copyright of Academy of MManagement Review…” as ordinary prose. Stats correctly say one OCR page, but Markdown has no OCR provenance marker. This is a raster copyright page, not a visually blank page; skipping all text-empty pages would destroy legitimate scans. |

Only OPEN/PARTIAL work appears below. In particular, do not redo the working
plain-text footnote implementation under the guise of fixing issue 7.

## Goal, measurement, and constraints

- Keep `TABLE_FALLBACK_MIN_KEEP = 0.9` unchanged. Improve reconstruction before
  applying the guard; do not lower the threshold, suppress accounting, or count
  a rejected table as a successful reconstruction.
- Proposed first table milestone: convert at least **12 of the original 36
  fallback regions** into verified reconstructions, leaving at most 24 fallback
  regions among the original 55. Track original regions by page/bbox and member
  identity. This is an acceptance target, not a predicted result. Report the new
  document-wide totals too; splitting/merging regions must not game the target.
- Measure words restored to **reconstruction before fallback**, separately from
  net words restored to final Markdown. The guard already saves much of that
  text, so a large reconstruction gain can produce little net document gain.
- Record source-token identities/multiplicities, assigned row/column, missing
  tokens, duplicated tokens, caption membership, rejection/fallback reason, and
  detection strategy per region. A word count cannot catch swapped cells or
  duplicated words masking omissions. Explicitly retain AND/OR, negations,
  percentages, and units. Use a consistent documented normalization for HTML,
  whitespace, and dehyphenation, not a vocabulary-only set comparison.
- Preserve vendored `table_recon.py`. Put any new orchestration/attachment logic
  in markerlite-owned code, using the existing candidate/scoring helpers to
  retain the winning grid and source-row identities before HTML serialization.
  Do not patch private helpers globally or infer column boundaries from final
  HTML. Reliance on private vendor helpers is an integration risk to test.
- Never geometrically sort document blocks. Local cell geometry is appropriate;
  recovered captions/prose retain their original stream positions.
- Every implementation item needs a deterministic synthetic fixture that fails
  before the fix, plus a rerun of its named real pages. `paper.pdf` booktabs and
  `hard.pdf` ruled-table contents and cell associations must remain unchanged.
  Run all regressions before committing intended expected-output changes.

## Implementation order

Item 0 is the requested isolated housekeeping fix. Items 1–4 are ordered by
estimated SBTi words restored to reconstruction / implementation risk. The
estimates are ordinal: overlap between fixes prevents credible additive word
forecasts. Items 5–11 have small or unmeasured SBTi gains and follow the main
recovery work; ties favor localized changes. Safety fixtures from items 5 and 6
must exist before broadening admission in item 2, even though those fixes rank
lower for word recovery.

### 0. Include tables when establishing marginalia body bounds — ship alone first

**Observed mechanism:** SBTi pp. 3, 45, 54–55, 62–63 retain the repeated
“Target Validation Protocol…” footer. On p. 3 the active content is one Table
and one footer Text block. `TEXTISH` excludes Table, so `len(text_blocks) < 2`
skips the page; the later `if not body` guard also excludes pages whose only
body content is a table. Bare page numbers may already have been removed by
`proc_ignore_common`; it is the repeated textual footer that demonstrates this.

**Exact one-line condition change:** in `proc_marginalia`'s local
`text_blocks` comprehension, replace

```python
if b.btype in TEXTISH and not b.ignore_for_output and b.text.strip()
```

with

```python
if b.btype in (*TEXTISH, "Table") and not b.ignore_for_output and b.text.strip()
```

This includes table body geometry and fixes both early-skip cases without
removing their guards, inventing default body bounds, or changing global
`TEXTISH`. Existing height/position/repetition checks still decide marginalia.

**Fixture:** add `table_only_footer.pdf`: two pages containing a body table and
the same short footer, drawn before the table; one control page has a unique
margin note. Check repeated footers disappear, unique text and all cells stay.
Existing `hard_footer_first.pdf` is a regression control but does **not** cover
the table-only case by itself. No new fixture has been created in this plan.

**Risk:** a short table located in a margin can become a candidate. Test that
unique short tables survive and normal `hard.pdf`/`paper.pdf` tables are neither
suppressed nor changed. Repetition remains mandatory for non-numeric content.

**First commit alone:** this condition change plus its reproducer and expected
output. It is independently reviewable and must leave the 36/55 count unchanged.

### 1. Attach wrapped lines in all-text cells using the winning grid

**Observed mechanism:** SBTi p. 2's document-history cell falls from 241 member
words to 71 in reconstruction; p. 48's accepted region has 243 member words
but a reconstruction rerun retains 76. On pp. 26 and 34, nominally cleaner
reconstructions lose content and the fallback can shred it into many columns.
`_find_header_band` returns no numeric transition for these examples. More
precisely than the old diagnosis, the vendor has a sparse-header alternative;
attachment runs only when `first_data_y` becomes non-None, and still excludes
span-rich lines, numeric-looking fragments, and some wide text. Merely deleting
the numeric-transition check is insufficient.

**Proposed fix:** retain the winning `cut_xs`, each source line's y interval,
and explicit source-to-grid row mapping. For every unassigned continuation,
choose the cell whose x interval contains it (bounded by table edges), then
attach within that logical row in y order. Establish rows from real horizontal
separators or independent row starts, not every physical text baseline. Reject
ambiguous cross-column/row assignments and keep their text through the existing
fallback. Do not append tokens already represented in a row. Handle all-text
tables without requiring numeric data; distinguish a new all-text row from a
wrapped line using separators, shared row starts, and gaps. Do not use the
vendor's positional `data[-len(grid):]` assumption as proof of row identity.

**Fixture:** extend the `tall_cell` coverage with `all_text_wrapped.pdf`: header
in first row, three text columns, alternating one-/four-line cells, sparse
continuations, a percentage embedded in prose, and a continuation sharing a
baseline with another column's new row. Include an unruled variant. Assert every
word appears once in its correct cell and the reconstruction wins the 0.9 guard.

**Risk and rank:** high recovery / medium risk, first table commit after item 0.
Blind merge-up shifts labels or numeric observations into the previous row.
Verify `paper.pdf` numeric booktabs rows and `hard.pdf` ruled rows individually,
including empty cells and real row transitions; matching total words is not enough.

### 2. Recover Table 1's alternating fragments and Table 2's logical rows

**Additional batch C evidence:** fallback-to-prose sacrifices five usable SBTi
grid layouts: regions 2 (PDF p. 3), 43 (p. 49), 44 (p. 53), 52 (p. 61), and
55 (p. 63). Their words survive; recovering their cell relationships remains
structural work. Kostova Figure 1 (PDF p. 7) still becomes a successful false
table proposal, swallowing its label with no figure placeholder. See
REPORT-batchC-block1.md for rendered evidence and matrices.

Packet A (79 table-structure cases) is additional batch C evidence, read in
place at `/home/galbl/unknown-knowns-markerlite-v0112/upstream/markerlite-v0.1.12-PACKET-A-table-structure.md`
and its JSON twin. In particular, R00087 PDF p. 10 loses **“U.S.”** from
“Standard & Poor's 1500 in / U.S.” inside a text-table proposal; no furniture
pass suppresses it. This is structural recovery, outside Packet B's
source-line suppression task. Do not conflate the two packets.

**Capital IQ continuation evidence (tests/REPORT-capiq.md, B5):** the export
contains 47 company sections, each one logical four-column table spanning a
contiguous page run. Current detection emits only one page-local region per
section: 45 reconstructed grids (306 body rows) and two prose fallbacks. Future
cross-page work should join the page-local pieces into one table per section
and merge repeated `DATE / COMPANY / TYPE / HEADLINE` rows without changing
cell text or treating the section banner as a row.

**Unknown Knowns v0.1.14 audit evidence (PR #8, read in place):** 17 Run-2
pages have new grid regressions against e419550: R00063 p. 37; R00077 pp. 8,
32; R00087 pp. 10, 12, 13, 15; R00112 pp. 14, 15, 17; R00160 pp. 12, 14, 15;
R00263 pp. 15, 20; R00373 p. 13; and R00860 p. 58. R00087 p. 10 loses
“U.S.”, while R02055 p. 7 merges phrases from two figure boxes into a false
3×3 grid. The fallback marker appears on 27 pages with no table; the words are
safer as prose, but the false structural claim remains evidence for admission
and representation work.

**Observed mechanism:** SBTi Table 1 begins on p. 7. Pages 7–9 emit no detected
table; pp. 10–11 alternate prose/list runs and reconstructed fragments instead
of retaining the three-column criterion/requirement/assessment relationship.
This is not evidence that every second logical row is literally deleted.
On pp. 10, 13, 26, 34, full candidates cover about 0.61–0.63 of the page and
are rejected by `area > 0.6 * page_area`; fragment candidates survive. PyMuPDF
also proposes spurious 13–19-column grids on these visually three-column pages.
Table 2 on pp. 38–39 has no emitted Table at all despite detected candidates;
its six columns and wrapped/merged cells flatten into text. Page 40 resumes as
a four-column fragment, losing the six-column relationship.

**Proposed fix:** distinguish genuine long table rules from text/fill-derived
candidate edges, and validate connected column separators and logical row bands
before accepting a large region. Add a narrow structural-evidence exception to
the 60% area rejection, not a larger blanket limit or a whole-page `text/text`
strategy. Investigate which candidate edges arise from decoration versus actual
rules using the rendered page; the raw text rotation filter does not filter
PyMuPDF's drawing-based table detection. Apply item 1 within validated rows.
Preserve spanning section bands and Table 2's shared “Absolute targets” and
“Intensity targets” cells without collapsing all methods into one cell. Keep
page-local tables first; cross-page joining is not required for this milestone.

**Fixture:** `criteria_alternating_rows.pdf`, a three-column landscape table
covering just over 60% of the page, with full-width section bands and alternating
short/tall criteria; add a decorated/diagonal-watermark twin. Add
`methods_multiline.pdf`, six columns with shared target-type cells, ten numbered
methods over multiple pages, and uneven wrapped descriptions. Assert every
method/criterion maps to the expected cells, not merely a pipe-table appearance.

**Risk and rank:** high recovery / high risk, second. Broad admission can swallow
front matter or boxed prose; items 5/6 negative fixtures gate this work. Edge
filtering can destroy `paper.pdf`'s sparse booktabs rules; aggressive row merging
can collapse `hard.pdf`'s real rows. Keep those exact baseline grids intact.

**Evidence added by batch 2 (tests/REPORT-batch2.md, journal articles):**
Greenwood & Suddaby 2006 p. 7 (Table 1, three columns of wrapped text, emitted
as one 13-column fallback row), p. 10 (Table 2, 10 columns, one row), p. 11
(Table 3, 14 columns); York et al. 2018 p. 12 (Table 1, correlation matrix
turned upright since ab57a91: all 17 row labels merged into one cell), pp.
14-15 (Table 2 split into five tables, coefficient and standard-error lines
stacked in one cell), pp. 22-23 (Table 3, same shape); Jay 2013 p. 6 (Table 1
split in two, header row lost). These are ruled or booktabs tables in
two-column journal pages, not compliance tables: batch C starts with both kinds.

**Evidence added by batch 3 (tests/REPORT-batch3.md, pipeline documents read
in place):** R00030 Dacin et al. 2019 p. 70 (Word manuscript, a ruled region of
29 tokens: the reconstruction returns 0 tokens, the region falls back, and the
fallback output still lacks 2 of the 29).

### 3. Keep criterion lead-ins with the following bullets

**Observed mechanism:** SBTi p. 10 places “Criterion not met if:” at the end of
the preceding positive ListItem, while p. 13 turns that lead-in and its bullets
into a spurious six-column mini-table. Page 26 splits longer met/not-met lead-ins
across a ten-column fallback and even reverses a wrapped header's text order.
These are cell/group ownership failures, not just bullet formatting defects.

**Proposed fix:** assign lines to the validated parent cell before list splitting
or header promotion. A standalone lead-in ending in a colon belongs with the
following list in that same cell; split it from the previous list block when
the text layer has grouped them. Preserve all qualifiers, AND/OR, formulas, and
explicit negation. Use geometry plus lead-in structure, not a global rule that
every colon starts a heading. Where the parent is rejected, retain the same
lead-in/list grouping as prose rather than fabricate a table header.

**Fixture:** `criteria_leadins.pdf`, modeled on pp. 10, 13, 26: two assessment
groups in one cell, a two-line qualifier, met and not-met clauses, and bullets
containing AND/OR. A second column contains a separate list at overlapping y
positions. Assert each lead-in precedes only its own bullets in its own cell.

**Risk and rank:** moderate recovery / medium risk, third; depends on item 1's
cell ownership. Avoid attaching the next real row or neighboring column. Keep
`paper.pdf` caption/list handling and `hard.pdf` row headers unchanged.

### 4. Close the remaining token-conservation gaps (report 2)

**Observed mechanism:** S0009 pp. 17–22 still pass aligned reference numbers as
two-column tables; p. 17 loses 259 whitespace words in its emitted HTML. The
alignment check is satisfied by a bibliography, and this path has no geometric
fallback. SBTi p. 26's left reconstruction retains 112/120 member words, enough
to pass 0.9, but omits “lead to at least a 7% physical intensity”. R05732 p. 6
illustrates why similar aggregate counts cannot establish correct membership.

**Evidence added by batch 3 (tests/REPORT-batch3.md):** R00030 p. 75 (landscape
table, 261 source tokens): the reconstruction keeps 245, which is 0.94 and
passes the 0.9 decision, so 16 tokens are dropped without a fallback and
without a warning. Same shape as SBTi p. 26. R00077 Bromley & Powell 2012 is
listed by the pipeline under table token loss, but its two detected regions
(pp. 8 and 32, 153 and 183 tokens) conserve every token; its two text-table
proposals are kept as prose, so the words survive and the structure does not.
It is evidence for the proposal path's accounting, not for loss inside a grid.

**Proposed fix:** track token identities across both detection paths, including
candidate membership and rejected captions. For accepted grids, recover leftover
tokens to a proven cell using item 1; if location remains uncertain, preserve
the source region as prose or emit the unassigned source text explicitly, rather
than silently discard it. Keep the existing geometric 0.9 decision unchanged.
Before unruled table proposals, reject the specific numbered-reference pattern
(citation syntax, hanging wraps, publication/year context), without banning every
two-column numeric-label table. Add separate proposal-path accounting.

**Fixture:** `references_not_table.pdf` with six numbered, wrapped bibliography
entries; a genuine two-column numbered-data control; `table_token_identity.pdf`
with repeated values and a missing negation/percentage below 10% of the total.
Assert multiset conservation and positions, including no duplicated padding.

**Risk and rank:** small demonstrated net SBTi gain / medium risk, fourth; large
pilot gain but do not count that as SBTi gain. Bibliography heuristics may reject
`paper.pdf`-style unruled tables; exact-token checks must tolerate legitimate
dehyphenation and HTML escaping. `hard.pdf` numeric duplicates must remain distinct.

### 5. Separate boxed prose from one-column tables

**Status: not needed after fallback-to-prose, no evidence.** After commit
2103350, checked all 44 remaining reconstructed/proposed regions across the
ten reference documents against their source-page crops and emitted cells.
No standalone bordered paragraph remained. SBTi narrative cells belong to
parent tables; remaining false proposals in Wry, Kitchener, and Kostova are
unboxed notes/references/proposition or a diagram. No prose detector was added.
See the step 3 evidence table in tests/REPORT-batchC-block1.md. The mechanism,
proposed fix, and fixture below are historical, not an outstanding implementation
instruction.


**Observed mechanism:** SBTi p. 48's Table 4 contains boxed narrative continuation
text in its upper-right cell. The real page is a two-column table; a `text/lines`
candidate instead invents **nine columns** through the prose. This is a verified
boxed-cell example, not a separately verified standalone nine-column text box.
SBTi p. 45 additionally turns unboxed explanatory prose into a four-column table.
The plan must test the requested standalone bordered-paragraph case explicitly,
without misclassifying the whole p. 48 parent table as prose.

**Proposed fix and distinguishing test:** an outer rectangle alone is not table
evidence. A single flowing paragraph with no internal row rules, no repeated
record starts, and no header/body distinction stays prose. A one-column table
must have independent row evidence (internal horizontal separators or repeated
record layout with a distinct header), not just wrapped baselines. Ambiguous
single-cell boxes remain text. Within a real multi-column table, boxed prose
remains in its parent cell. Do not use a minimum-column-count rule.

**Fixture:** `boxed_prose_vs_one_column.pdf` containing the same paragraph with
and without an outer border, a justified-text box whose word gaps suggest nine
columns, a ruled one-column header plus three records, and a two-column parent
table containing that paragraph. Expect prose/prose/prose/table/table respectively,
all words preserved. This paired test isolates structure from typography.

**Risk and rank:** little net word gain while fallback works / medium risk.
Over-rejection erases legitimate one-column tables; requiring vertical rules
breaks `paper.pdf` booktabs. Verify `hard.pdf`'s ruled table stays a table.

**Evidence added by batch 2 (tests/REPORT-batch2.md):** Peng et al. 2009 p. 2
(two-column body prose beside Figure 1 emitted as a 6-column table of line
fragments, "| the ity and mal 1). use well | last three (North, 1990; ..."),
from detect_tables; Wry et al. 2013 p. 37 (six numbered endnotes emitted as a
2-column table "| 1. | Note that the data for 2011 ...", from
propose_tables_from_text, which also costs the document its footnotes).

### 6. Reject journal-front-matter pseudo-tables (report 1) — DONE

Verified on R01285 and R02611 p. 1, with original blocks preserved;
`journal_front_matter.pdf` covers both layouts and page-1 data-table controls.
All ten references and hard/paper outputs remain byte-identical to the
fallback-to-prose step. See tests/REPORT-batchC-block1.md, step 4.

**Observed mechanism:** R01285 and R02611 p. 1 still merge title, journal metadata,
authors, and abstract into grids. Ragins p. 1's legitimate-looking key/value
submission metadata shows why “every page-1 table is false” is too broad.

**Proposed fix:** use front-matter evidence (title typography, authors, DOI/journal
metadata, Abstract/Keywords and long prose) to reject a candidate before consuming
its blocks. Preserve those original blocks for heading/paragraph classification;
do not revert the entire candidate into one run-on paragraph. Leave a genuine
page-1 data table and Ragins' isolated metadata readable and complete.

**Fixture:** `journal_front_matter.pdf`, inspired by both pilot p. 1 layouts,
plus a lower-page real table and a page-1 booktabs-only control. Verify the title
is intact, abstract label remains with text, and real table cells survive.

**Risk and rank:** no demonstrated SBTi word gain / medium risk. A page-position
ban could delete `hard.pdf`'s or `paper.pdf`'s first-page table. This is a safety
prerequisite for item 2, not a shortcut for raising the area threshold.

**Evidence added by batch 2 (tests/REPORT-batch2.md):** no new case. The first
pages of Peng 2009, Greenwood & Suddaby 2006, Wry et al. 2013, Jay 2013 and
York et al. 2018 all stay prose; none is captured as a table. Recorded as a
negative result so the item is not assumed to affect every journal.

### 7. Isolate captions and constrain membership before reconstruction (report 3) - DONE in v0.1.12

Implemented in `_isolate_table` / `_split_members` (markerlite.py). Row bounding
is limited to rule-only candidates without strokes inside the grid; boxed
tables are untouched. Verified on R02611 p. 18 by cell matrix
(tests/REPORT-v0.1.12.md). Not done: a wrapped header stays one row per line.

**Observed mechanism:** R02611 p. 18's two-line caption becomes a seven-column
header; diagram labels below the table also enter the candidate. `proc_captions`
only attaches neighboring Caption blocks after reconstruction, too late to repair
either mistake. Full-member source/output counts are both 96 in this run; that
does not mean the table is correct.

**Proposed fix:** split a leading table-caption band from source lines before
reconstruction, even when it shares a block with the grid. Use label plus
layout separation, handling a caption's continuation line; do not require every
caption to have punctuation after its number. Limit membership to the actual
table rows using the bottom rule/row extent so nearby figure text is excluded.
Reinsert and attach the caption in stream order, and account for its tokens
separately so a preserved caption cannot mask missing data.

**Fixture:** `caption_inside_table.pdf`: two-line “Table 1 Study…” caption in
the same extraction block, a five-column grid with three observations, note
below, and an adjacent diagram with text. Expect one intact caption, correct
numeric rows, and no diagram labels in any cell.

**Risk and rank:** small/unmeasured SBTi gain / medium-high risk. Header cells can
start with “Table”; excessive clipping loses notes or tall rows. Protect the
caption, header band, and sparse rules of `paper.pdf`, and all `hard.pdf` cells.

### 8. Parse footnote labels before inline formatting (remaining report 7) - DONE 699c4f3

**Observed mechanism:** R02027 p. 3's bold notes 3/4 become multiple `[^**]:`
definitions. The source-label logic works earlier, but `render` reparses the
`_inline` result, where emphasis markers resemble symbol footnotes.

**Proposed fix:** determine labels and continuation boundaries from raw spans
before Markdown, remove only the actual source label, then format the merged
note body. Preserve genuine star/dagger notes and in-text superscript references.

**Fixture:** `footnote_bold_wrapped.pdf`: bold numbered notes over several lines
and blocks, an italic continuation, and a genuine star note. Expect one correctly
numbered definition per note, unique labels, and correct references. Retain
`footnote_repro` and `footnote_biglabel` expectations.

**Risk and rank:** no measured SBTi gain / low localized risk. Keep table-local
asterisks/significance markers out of footnotes; both `paper.pdf` footnotes and
`hard.pdf` notes/cells must remain unchanged. Ship separately from table geometry.

### 9. Merge emphasis across soft breaks before dehyphenation (report 6)

**Observed mechanism:** R02027 p. 1 has `lati-** **tude`; per-line Markdown
prevents `HYPHEN_END` from seeing the actual trailing hyphen.

**Proposed fix:** join compatible raw formatting runs across soft line breaks,
perform existing dehyphenation on text, then emit emphasis. Preserve intentional
paragraph breaks and changes between bold, italic, superscript, and plain text.

**Fixture:** `bold_soft_breaks.pdf`: a bold wrapped paragraph with a hyphenated
word, a real compound hyphen, and a style change at a line break. No artificial
seams; legitimate boundaries and compounds survive.

**Risk and rank:** unmeasured SBTi gain / medium risk. Never merge across table
cells or hard row breaks. Protect `paper.pdf` emphasis/equations and `hard.pdf`'s
existing column-break dehyphenation. Shared rendering warrants full regression.

### 10. Merge only genuine wrapped headings (report 5)

**Observed mechanism:** R00014 p. 1's two title lines are separate SectionHeader
blocks, and rendering emits a heading for each without testing continuation.

**Proposed fix:** merge adjacent same-page, same-column headings with matching
font/size/level and a wrap-sized vertical gap, unless numbering, punctuation,
or layout signals an independent heading. Same level alone is insufficient.

**Fixture:** `wrapped_heading.pdf`: the reported two-line title shape, plus two
distinct adjacent numbered headings with identical styling and two columns.
Assert one title, separate sections, and original reading order.

**Risk and rank:** no measured SBTi word gain / medium risk. Do not fuse table
captions or section bands. `paper.pdf` numbered hierarchy and `hard.pdf` table
heading/caption placement must remain unchanged.

### 11. Extraction hygiene: controls, OCR provenance, and tight text (reports 8, 9, 4)

These are separate future commits, grouped here because their measured SBTi
word-recovery benefit is zero/unknown, not because they share a safe code change.

**11a — controls (report 8).** R00315 pp. 10–16 carries unmapped C0 characters
through `Span.text` and raw `chars`; table tokenization may consult the latter.
Filter C0/C1 controls other than tab/newline consistently in both representations,
after recognizing known symbol-font list markers so sanitization does not erase
legitimate bullets. Do not claim this transcribes missing mathematical symbols.
Fixture `control_glyphs.pdf`: embedded controls in prose/citations/table cells,
a symbol-font bullet, and valid Unicode/superscript controls. Assert no forbidden
controls and retained word separation/known bullets. Risk: `paper.pdf` uses a
control-range bullet glyph, and filtering only one representation causes table
text to diverge. Recheck its list and `hard.pdf` cell contents.

**11b — OCR provenance (report 9).** R01114 p. 36 has zero text-layer characters
but visible copyright text; the `<20` rule legitimately invokes OCR, whose output
is unmarked. Emit a page-associated OCR comment whenever `ocr_used`, including
when ordinary page markers are disabled. Do not delete isolated raster pages
or boilerplate in this first fix. Fixture `isolated_ocr_page.pdf`: digital page,
raster copyright notice, genuinely blank page, and a real scanned table control.
Assert provenance follows the OCR page and no digital page is mislabeled. Risk:
no geometry change to `paper.pdf`/`hard.pdf`; ensure scanned table content remains
present and existing `scanned` output changes only as intentionally documented.

**11c — tight text (report 4).** S0008 p. 1's body contains the glued examples
above. Recover spaces from character geometry before creating text runs, starting
with a calibrated gap around 0.2 em relative to the line's median character
advance. This number is a hypothesis to validate, not a universal threshold.
Do not insert spaces across ligatures, kerning pairs, decimals, or a column gap;
share the normalized representation with table tokenization. Fixture
`tight_body_spacing.pdf`: the same sentence at several explicit inter-word gaps,
with true tight kerning, ligatures, numbers, and a nearby numeric table. Assert
known words recover without splitting true words. Risk: highest of these three;
global geometry changes can alter `paper.pdf` math/numeric tokens and `hard.pdf`
column boundaries. Defer until the targeted gap examples are measured visually.

### 12. Sideways region on an upright page - evidence only

**Observed mechanism:** R00443 Kraatz & Moore 2002 p. 16 emits 163 of its 336
source words (tests/REPORT-batch3.md). The page is upright prose with a table
set sideways on part of it. Its vertical characters are under
`ROTATED_PAGE_MIN_FRAC` (0.8), so the page is not turned, and the rotated-line
filter in `extract_page` then drops every sideways line. The conservation check
reports the page as lossy, which is correct; the words are still lost.

**Proposed fix:** rotate the region, not the page. Group the rotated lines into
a connected region, extract that region through a rotated clip so its lines
come out upright, and hand it to table detection as its own candidate, placed
in the stream where the region stands. The page-level rule stays as it is for
pages that are sideways as a whole. A diagonal watermark must stay dropped:
only quarter-turn text, in a region with several parallel lines, qualifies.

**Fixture:** `sideways_region.pdf`: an upright page with two paragraphs and a
quarter-turned table between them, plus the `watermark` control. Assert the
cell matrix of the turned table, not word counts, and that the page is no
longer in `lossy_pages`.

**Risk and rank:** medium. `watermark` and `rotated_pages` must not change.
Not ranked against items 2-7 until reviewed. No implementation in v0.1.12.

**Downstream contradiction to investigate:** the v0.1.14 audit classifies
R00443 p. 16 as a known, still-unusable content loss but reports zero
`lossy_pages` for the Run-2 set. The earlier markerlite audit measured 163 of
336 source words emitted and did flag the page. Reconcile the wrapper's source
word denominator and page association before changing the conservation rule.

### 13. First-page citation masthead suppression — small independent item

**Observed mechanism:** the Unknown Knowns v0.1.14 audit finds that R00014
p. 1 loses the journal name from the article's own citation line through
`proc_marginalia`. It is unique first-page content, not a running head, and
e419550 retained it.

**Proposed fix:** trace the normalized repetition evidence and block grouping
on p. 1, then protect a citation-line masthead that does not repeat in the same
header/footer band. Keep the general positional-plus-repetition rule and do
not add journal-name vocabulary.

**Traced 2026-10-02 (block 2, E1):** still present at v0.1.15; the even-page
running head has the same text in the same band but a different position, font
and size. The fix adds horizontal-position and size agreement to the
repetition evidence.

**Fixture and risk:** add a first-page citation line with a journal masthead
and later genuine repeated running heads. Assert the masthead survives and the
heads remain suppressed. This is suppression work, independent of item 2's
table admission changes.

## Block 2: table structure — plan (2026-10-02, for review)

This section is a plan. No converter code changes until it is reviewed.

**Governing principle.** A wrong grid is worse than no grid. The Unknown
Knowns v0.1.14 audit preferred e419550 on tables mainly because e419550
rarely attempted one. markerlite emits a grid only when row and column
structure is supported by evidence. Otherwise it emits ordered prose, with
the existing marker only where the region really is a table. The design
rule in CLAUDE.md applies throughout: token preservation is not structural
correctness, so every table step is judged by which token lands in which
cell (gold set, A) and never by word counts alone.

Evidence files: tests/REPORT-block2-evidence.md (inventory by mechanism and
the v0.1.15 region labels), tests/block2-region-labels.json (labels and gate
features, no document text), tests/GOLD-TABLES.md (gold protocol),
tests/score_gold_tables.py (scorer).

### A. Gold tables set: design and v0.1.15 baseline

**Content and storage.** 29 tables and 9 non-table controls from 27
documents, stored as one JSON per item in the git-ignored
`tests/gold-tables/` beside `tests/real/`. Third-party content never enters
the repository; the scorer and protocol do.

| Source group | Tables | Items |
| --- | ---: | --- |
| Reference set | 10 | Greenwood 2006 T1 p7, T3 p11; Jay 2013 T1 p6; Peng 2009 T1 p2; Wry 2013 Appendix pp46-47; York 2018 T1 p12, T2 pp14-15; SBTi pp3, 53, 61 (Kostova p7 proved to be a figure: control) |
| Packet A and audit pages | 17 | R00030 T3 pp75-76; R00077 T1 p8, T2 pp28-32; R00087 T1 pp9-15; R00112 T3 pp14-15, T4 p17; R00263 T3 pp15-20; R00315 T3 p14; R00373 T2 p13; R00639 T4 p28; R01114 T2 p8; R01285 T1 p6; R02027 T2 p25; R02611 T1 p18, T2 p25; R05732 T1 p4; S0004 T1 pp6-12 |
| Capital IQ | 2 | one company section over pp87-88; the p9 rows of a section v0.1.15 does not detect |
| Controls | 9 | R02055 p7 and R00860 pp60, 61 (figures); Kostova p7 (figure); Wry p37 (endnotes); R00023 pp3, 9 (body prose); R00032 p85 (references); S0009 p17 (numbered bibliography captioned "Table 6") |


Layouts covered (an item can have several): booktabs 22, wrapped-cell 17,
landscape 9, multi-page 9, wrapped-header 9, numeric 10, ruled 4, scanned 4,
borderless 3, shaded-row 2. Thin spots: only 4 fully ruled tables and 2
shaded-row tables; both should grow before v0.2.0 (see F).

**How each item was made.** One agent transcribed the cell matrix from 150
to 300 dpi renders, with the PDF text layer for spelling only, never from
converter output. A second agent re-checked every cell independently. The
checks covered 3,464 cells and found no matrix error; they corrected three
control boxes and recorded every judgement call (`check_notes`). One
overlap was resolved: R00087 Table 1 runs pp9-15 and is one item; a
page-10-only duplicate was retired. Conventions: tests/GOLD-TABLES.md.

**Metric** (`tests/score_gold_tables.py`):

- *per-table exact match*: the emitted grid equals the gold matrix after
  normalisation (NFKC, dashes and minus signs unified, bullets as layout,
  empty rows and columns dropped);
- *per-cell association*: the mean, over gold cells, of the token Jaccard
  with the best-matching emitted cell (merged or split cells lose credit;
  prose scores 0);
- *adjacency F1* (ICDAR 2013): right and down neighbour relations between
  non-empty cells;
- *tokens kept*: the table's tokens present on its pages in any form.

Outcomes: EXACT; GRID-NEAR (adjacency F1 >= 0.9); GRID-WRONG; PROSE (no
grid, >= 0.95 of tokens kept); LOST. Controls: CLEAN, FALSE-GRID,
FALSE-MARKER.

**v0.1.15 baseline** (converter at 328af5d, identical conversion path to
v0.1.15):

| Measure | v0.1.15 |
| --- | --- |
| Tables: EXACT / GRID-NEAR / GRID-WRONG / PROSE / LOST | 1 / 4 / 18 / 6 / 0 |
| Exact-match rate | 1 of 29 (3.4%) |
| Mean cell association | 0.514 |
| Mean adjacency F1 | 0.369 |
| Tables with >= 0.95 of tokens kept | 25 of 29 |
| Controls: CLEAN / FALSE-GRID / FALSE-MARKER | 0 / 6 / 3 |

The four tables under 0.95 tokens kept lose source glyphs, not words: the
text layers of R00373 and York drop or substitute minus signs, and Jay and
R00315 lose a few symbols. Per item:

| Item | Outcome | Assoc. | Adj. F1 | Kept |
| --- | --- | ---: | ---: | ---: |
| R01285-p6-t1 | EXACT | 1.000 | 1.000 | 1.000 |
| greenwood2006-p11-t3 | GRID-NEAR | 0.988 | 0.983 | 0.968 |
| R02611-p25-t1 | GRID-NEAR | 0.976 | 0.902 | 1.000 |
| wry2013-p46-t1 | GRID-NEAR | 0.990 | 0.984 | 1.000 |
| york2018-p12-t1 | GRID-NEAR | 0.998 | 0.994 | 1.000 |
| R00315-p14-t1 | GRID-WRONG | 0.940 | 0.886 | 0.942 |
| R00112-p17-t1 | GRID-WRONG | 0.943 | 0.712 | 0.979 |
| R02611-p18-t1 | GRID-WRONG | 0.910 | 0.605 | 1.000 |
| R02027-p25-t1 | GRID-WRONG | 0.776 | 0.722 | 0.959 |
| R01114-p8-t1 | GRID-WRONG | 0.742 | 0.694 | 0.989 |
| R00077-p8-t1 | GRID-WRONG | 0.751 | 0.125 | 0.978 |
| capiq-p87-t1 | GRID-WRONG | 0.713 | 0.595 | 0.997 |
| jay2013-p6-t1 | GRID-WRONG | 0.683 | 0.604 | 0.932 |
| R00112-p14-t1 | GRID-WRONG | 0.586 | 0.068 | 0.975 |
| R00263-p15-t1 | GRID-WRONG | 0.576 | 0.049 | 0.978 |
| R05732-p4-t1 | GRID-WRONG | 0.569 | 0.039 | 0.989 |
| S0004-p6-t1 | GRID-WRONG | 0.455 | 0.178 | 0.963 |
| york2018-p14-t2 | GRID-WRONG | 0.437 | 0.346 | 0.775 |
| R00030-p75-t1 | GRID-WRONG | 0.255 | 0.000 | 0.960 |
| R00077-p28-t1 | GRID-WRONG | 0.203 | 0.009 | 0.998 |
| R00373-p13-t1 | GRID-WRONG | 0.177 | 0.199 | 0.761 |
| R00639-p28-t1 | GRID-WRONG | 0.129 | 0.000 | 0.988 |
| R00087-p9-t1 | GRID-WRONG | 0.107 | 0.000 | 0.999 |
| capiq-p9-t1, greenwood2006-p7-t1, peng2009-p2-t1, sbti-p3-t1, sbti-p53-t1, sbti-p61-t1 | PROSE | 0 | 0 | 1.000 |

Controls: FALSE-GRID on R02055 p7, R00860 pp60 and 61, Kostova p7, Wry p37
and S0009 p17; FALSE-MARKER on R00023 pp3 and 9 and R00032 p85.

Limits of the baseline: the set was chosen to cover known failure pages,
so it over-represents hard tables and is not a random sample of tables in
the corpus. Two gold matrices keep the printed layout where a reader might
want another: York Table 1 prints its header one column left of the data,
and York Table 2 continues its columns side by side on p15, so a
page-by-page converter cannot reach EXACT there without joining columns.

### B. Evidence inventory, deduplicated by mechanism

Full table with every page and source: tests/REPORT-block2-evidence.md.
Twenty mechanisms; page counts are from the audited versions (v0.1.12 and
v0.1.14); the v0.1.15 column is from the region labels.

| ID | Mechanism | Class | Pages | Status at v0.1.15 |
| --- | --- | --- | ---: | --- |
| M01 | Figure or diagram admitted as a table | false grid | 14 | 13 figure grids emitted |
| M02 | List-like text proposed as a 2-column grid | false grid | 7 | 12 reference-list grids (6 are S0009's captioned bibliography) |
| M03 | Body prose or layout captured into a table region | false grid | 6 | R00293 p8 still a merged grid |
| M04 | Single-row grids from a text proposal (R00087 Table 1) | false grid | 4 | 6 grids on R00087 pp10-15, all wrong |
| M05 | Fallback marker on non-table content | false marker | 31 | 32 of 78 markers |
| M06 | Wrapped lines emitted as separate grid rows | wrong association | 15 | open |
| M07 | Rows collapsed into one row, or columns fused | wrong association | 15 | open (York, R00373, R02659 regression tables) |
| M08 | Header misplaced | wrong association | 26 | open |
| M09 | Stacked panels merged; label column fused | wrong association | 7 | open (R00112) |
| M10 | One table split into several partial grids plus prose | wrong association | 15 | 74 of 135 table grids cover part of a table |
| M11 | Cells or rows detached from the table | wrong association | 11 | open |
| M12 | Cross-page table not joined | wrong association | 13 + Capital IQ's 47 sections | open |
| M13 | Caption displaced or fused | wrong association | 16 | open (minor) |
| M14 | Failed reconstruction kept as prose: layout lost | missed table | 43 | 46 real-table fallbacks |
| M15 | Real table not detected | missed table | 30 + about 135 Capital IQ pages | open |
| M16 | Large candidate rejected by the page-area rule | missed table | 7 | open (SBTi) |
| M17 | Lossy reconstruction accepted (passes the 0.9 guard) | lost text | 30 | 39 grids drop printed words |
| M18 | Sideways region on an upright page | lost text | 1 | now kept as unreadable fragments (E3) |
| M19 | Table rows lost as furniture | lost text | 14 | fixed (Packet B, 702607d) |
| M20 | Glyph loss in cells (pi fonts, OCR layers) | lost text | 19 | open, source layer |

Pages per class (a page counts once per class): false grid 31, wrong
association 76, missed table 77, lost text 57, false marker 31.

Cross-cutting findings:

- **Stop-2 ranking note (owner, stop 1):** 11 of the 17 regressions are on
  pages turned upright; investigate rotated-page handling as a shared cause
  first, before gate tests 1-4 are tuned on those pages. R00443 p14/p16
  (E3) belong to the same investigation.
- Eleven of the 17 pages that were new regressions against e419550 are on
  pages the converter turns upright (ab57a91). e419550 left them sideways
  and emitted prose; once upright, detection runs and M04, M06, M07 and M09
  fire. Turning pages upright stays (it recovered seven table pages of
  text), but those pages are where the gate matters most.
- Text proposals are not worse than `find_tables` candidates per grid
  (36 good of 64 against 38 good of 103), but they produce most list and
  reference false grids (M02, M04).
- Disagreements between sources are listed in the evidence report, part 1,
  section 4. None changes the ranking below.

### C. Remaining items, re-ranked by gold-set impact over risk

Items that remove false grids or fix association come first; items that
only add grids come after them.

| Rank | Item | Removes / fixes | Gold-set impact (estimate) | Risk |
| ---: | --- | --- | --- | --- |
| 1 | E2: marker only on real table regions | false markers (M05) | 3 FALSE-MARKER controls clean | low |
| 2 | D: table-confidence gate (new item 14) | false grids (M01-M04), worst wrong grids (M06, M07, M10) | FALSE-GRID 6 to 2; GRID-WRONG 18 to 12, no EXACT/NEAR lost | medium |
| 3 | E1: R00014 masthead (item 13) | lost text | none on the gold set | low |
| 4 | E3: sideways fragments warning (interim item 12) | silent unreadable text | none on the gold set | low |
| 5 | Item 1 extended: wrapped-line rows for all row-banded tables | M06 | R02611 p18, R05732 p4, R00077 p8, S0004 | medium |
| 6 | New: row-collapse repair or refusal | M07 | York T2, R00373, R02659 | medium |
| 7 | Item 4: per-cell token identity on both paths | M17, and the gate's identity test | jay, R00315, York T2 | medium |
| 8 | Header band and panel spanners | M08, M09 | R00112, R02611 p25 | medium |
| 9 | Cross-page joining and repeated headers | M12 | Capital IQ, Wry, York, S0004, R00077, R00087 | high: adds grids |
| 10 | Item 2: area rule exception | M16 | SBTi p53, p61 | medium: adds grids |
| 11 | Item 12: rotate the region | M18 | none on the gold set | medium: adds text |
| 12 | Item 3: criterion lead-ins | SBTi only | none | low |
| 13 | Items 9, 10, 11a, 11c | text hygiene | none | as before |

### D. Table-confidence gate (new item 14)

A grid is emitted only when all of these hold. Each is measurable on the
source page or the candidate, without trusting the reconstruction it
judges:

1. **Row and column evidence.** At least two horizontal rules spanning the
   region or one vertical rule, OR at least two column starts that recur
   (within 4 pt) in at least half of the multi-column printed rows.
2. **Consistent shape.** At least three grid rows and at least two columns.
3. **Not a figure.** No curve drawing operators inside the region (boxes
   with arrows, path diagrams).
4. **Not prose.** Fewer than 35% of printed lines end in a word followed
   by sentence punctuation.
5. **Per-cell token identity.** The grid's tokens equal the members'
   tokens as a multiset, within tolerance: nothing missing and nothing
   duplicated beyond `GATE_IDENTITY_MAX` (start at 0.05 inside the
   converter, where the comparison uses the members' own tokens after
   glyph repair; the offline estimate below had to use 0.20 because it
   compares against the page).
6. **No continuation rows.** Fewer than 15% of body rows have an empty
   first cell and lower-case continuation text in the others (the
   signature of wrapped lines emitted as rows, M06).

Below the gate the region becomes ordered prose. It keeps the marker only
if it passes test 1 or has a rule near it (E2); otherwise its blocks return
to normal classification with no marker.

**Estimate on the 167 labelled v0.1.15 grids:**

| Gate | Good grids kept | Bad grids removed | Non-table grids removed |
| --- | --- | --- | --- |
| Tests 1-5 | 71 of 77 | 53 of 90 | 19 of 29 |
| Tests 1-6 (proposed) | 70 of 77 | 58 of 90 | 19 of 29 |

"Good" is a correct or minor-error grid of a real table or a cover-sheet
box; "bad" is any other grid. The seven good grids the gate costs are R00263
pp5, 15 and 20, R02611 p18, R01285 p7, R02027 p34 and R00894 p8, six of
them minor-error grids, so they become prose rather than wrong. The 32 bad
grids it still lets through are mostly ruled tables whose rows are split or
collapsed (SBTi criteria pages, York T2, R00315 p12, R00112 p14), the R07771
reference lists and S0009's captioned bibliography, and the R02055 figure,
which has no curves. Those need items 5-8, not a stricter gate.

**Estimate on the gold set** (same gate, simulated on the v0.1.15 regions):

| Measure | v0.1.15 | With the gate |
| --- | --- | --- |
| Tables EXACT / NEAR / WRONG / PROSE / LOST | 1 / 4 / 18 / 6 / 0 | 1 / 4 / 12 / 11 / 1 |
| Controls CLEAN / FALSE-GRID / FALSE-MARKER | 0 / 6 / 3 | 7 / 2 / 0 |

The one LOST is R00373, whose text layer has no minus signs; it moves from
a wrong grid to prose and is scored on tokens. The two controls still
failing are R02055 p7 (a figure drawn without curves) and S0009 p17 (the
bibliography captioned as a table).

These are estimates: the region labels are one pass each, and the features
are an offline reimplementation. The implementation step re-measures on the
gold set and the audit pages before it is committed.

### E. Three small isolated items, each with a fixture, done first

**E1. R00014 p1: the journal name in the article's own citation line is
suppressed as furniture (PLAN item 13).** Still present at v0.1.15: p1's
first line, "Academy of Management Annals", is recorded as
`proc_marginalia` and the Markdown opens with "2023, Vol. 17, No. 1". The
mechanism: the even-page running head is the same text in the same top band
(y 51.9-60.8 pt against 48.6-55.3 pt on p1, inside `FURNITURE_HEIGHT_TOL`),
so repetition evidence matches. But it is a different object: the masthead
sits at x = 47 in 6.3 pt Arial as the first of three citation lines; the
running head is centred at x = 236 in 8.3 pt Times Italic. *Fix:* repetition
evidence must also agree on horizontal position (centre within a tolerance)
and on type size, and a line is not cut out of a block whose other lines are
not furniture. *Fixture* `first_page_masthead.pdf`: a page-1 citation block
with the journal name at the left in small type; later pages with the same
name as a centred running head. Assert the masthead survives and the heads
are suppressed. Verify on R00014 p1 and on the suppression audit pages.

**E2. The "reconstruction failed" marker only follows a real table.** At
v0.1.15, 32 of 78 markers sit on body prose (14), reference lists (11),
figures (5) and an equation's "Where:" key (2). The mechanism: the second
`find_tables` pass (columns from text, rows from lines) makes candidates on
pages with no ruling lines at all (R00023 p3: no rules, a 45 x 8 candidate
over double-spaced prose). Reconstruction fails, the geometric grid passes
`_table_sane`, and the region becomes a marked fallback. *Fix:* a failed
candidate keeps the marker only if a rule spans or borders it or it has at
least two recurring column starts, and it has no curves. Otherwise its
blocks return to the page unmarked and are classified like any other text,
so a prose page reads as prose with its headings. On the 78 fallbacks this
unmarks 28 of the 32 non-tables and 2 of the 46 real tables (Peng p2, whose
region also holds a figure strip, and SBTi p43). *Fixture*
`no_table_marker.pdf`: a double-spaced prose page, a reference list, and a
box-and-arrow figure, none with a marker; `tall_cell` keeps its marker.
Verify on R00023, R00032 pp85-88 and SBTi.

**E3. The R00443 p16 lossy-page contradiction.** Both reports are right
for the version each measured. At v0.1.12 the tilt filter dropped the
page's sideways lines and the page emitted 163 of 336 words, so it was
flagged. Commit 702607d (2026-09-29) began keeping orthogonal native text
on raster-covered pages, because mixed-direction hidden OCR can hold real
sideways table data. Since then p16 emits 382 content words, above the 0.5
conservation ratio, and is not flagged. Converting R00443 at 702607d~1 and
at 702607d reproduces the switch exactly. The words it now emits are the
hidden OCR layer's sideways fragments in column order (numbers and
two-letter pieces), unreadable as a table. So the check is right about the
count and blind to order. *Fix:* record pages whose emitted text includes
orthogonal lines that were not turned upright in
`stats["sideways_text_pages"]` and warn "N pages keep sideways text as
fragments" through `stat_warnings`, so CLI, GUI and log say so; item 12
remains the real fix. *Fixture:* a raster-covered page with an upright
paragraph and a quarter-turned table in its hidden text layer; assert the
warning and that conservation is unchanged. Verify on R00443 p16.

*Owner ruling (stop 1): recorded, not fixed now.* Sideways native text kept
since 702607d produces unreadable fragments that word conservation cannot
see; the fix belongs to the rotated-page work (item 12 and the stop-2
investigation below). What follows is the detector proposed for that work.

*Proposed detector: fragment share, not word count.* Conservation counts
words, and a word split into its letters still counts. The signal that
does separate R00443 p16 is the shape of the emitted tokens. Measured per
page on the emitted Markdown (comments removed, pages with >= 40 tokens):

| R00443 page | tokens | `readable_ratio` | letter tokens of <= 2 letters | mean letter-token length |
| --- | --- | --- | --- | --- |
| body pages (21) | 183-858 | 0.26-0.62 | 0.13-0.29 | 5.18-6.06 |
| p14 | 542 | 0.51 | **0.97** | **1.29** |
| p16 | 300 | 0.77 | **0.95** | **1.54** |

p14 is a second page of the same kind that no report had flagged.
`readable_ratio` (the `garbled_font` trigger) is no help: digits count as
readable, so the fragment pages score higher than the body. A page whose
letter tokens are mostly one or two letters long is a page of fragments,
whatever its word count. Proposed: `stats["fragment_pages"]` lists pages
with at least `FRAGMENT_MIN_TOKENS` letter tokens of which at least
`FRAGMENT_SHORT_SHARE` are <= 2 letters long, with both numbers, and
`stat_warnings` says "N pages emit text as fragments". It is a report,
not a removal: the text stays.

First sweep (all 12 `tests/real` documents, pages with >= 40 tokens): the
short share reaches 0.88-0.97 on exactly three more pages, R02027 pp. 30,
31 and 36, which are themselves fragment output (a scanned sideways table's
hidden OCR layer emitted as one- and two-character pieces) and not flagged
today either. The next highest page anywhere is R02027 p. 46 at 0.46; every
other page stays below 0.4. So a share of 0.6 on >= 40 letter tokens
separates the two populations in this sample with margin on both sides.
Before implementation the sweep must cover the 25 packet documents of the
golden corpus (tables of abbreviations and statistics are the risk).

### F. Acceptance for v0.2.0

Measured with `tests/score_gold_tables.py` on the gold set, extended first
with at least four fully ruled and two more shaded-row tables, and at least
six more non-table controls drawn from pages the gate has not been tuned on.

1. **Zero false grids and zero false markers on every gold control.**
2. **No wrong grid where v0.1.15 had a good one:** every v0.1.15 EXACT or
   GRID-NEAR table stays EXACT or GRID-NEAR.
3. **GRID-WRONG at most 4 of the original 29 tables** (from 18). A table
   may reach that by becoming PROSE.
4. **EXACT plus GRID-NEAR at least 8 of 29** (from 5), and mean cell
   association not below 0.514.
5. **Tokens kept at least 0.95 on every table** whose source layer holds
   its glyphs; the source-glyph losses (R00373, York minus signs) are
   reported, not excused silently.
6. **No audit page worse than v0.1.15**: the 17 v0.1.14 regression pages,
   the 13 B-KNOWN structure pages, the 6 B-KNOWN content-loss pages and
   the 27 false-marker pages, judged visually against v0.1.15 output.
7. The 77-entry golden audit runs; every hash change is explained by a
   step of this block.
8. **README tables paragraph rewritten from the measured numbers**: how
   many gold tables are exact or near, how many become prose, and what a
   reader gets on a non-table page. "Verify any table you intend to read as
   data" stays unless criteria 2-4 hold on the extended set with GRID-WRONG
   at zero.

### G. Commit sequence and stop points

Each step is one commit with its fixture, the regression and golden checks,
the gold-set scores before and after, and the R rule on the real pages
named.

1. E2 marker rule. Fixture `no_table_marker`. Before/after on R00023,
   R00032, SBTi fallbacks.
2. E1 masthead. Fixture `first_page_masthead`. Before/after on R00014 p1
   and the suppression audit list.
3. E3 sideways-fragments warning. Fixture `sideways_fragments`.
   Before/after on R00443 p16.
   **STOP 1:** report E1-E3; user review.
4. Gate tests 1-4 (evidence, shape, figure, prose), with the gold-set
   simulation re-run inside the converter. Fixtures: `figure_grid` (box and
   arrows), `endnote_list`, `ruled_table` control (must stay a grid).
5. Gate tests 5-6 (token identity, continuation rows). Fixtures:
   `split_rows_table`, `lossy_grid`.
   **STOP 2:** gold-set and audit-page report; user review. No further
   step if any v0.1.15 EXACT or NEAR table regressed.
6. Item 1 extension (wrapped-line rows). 7. Row-collapse repair. 8. Item 4
   token identity on the proposal path. 9. Header band and panel spanners.
   **STOP 3** after each of 6-9 if a gold table moves from NEAR to WRONG.
10. Cross-page joining. 11. Item 2 area rule. 12. Item 12 region rotation.
    **STOP 4:** v0.2.0 acceptance report against F; README rewrite.
    No tag until the user writes "tag v0.2.0".

## Review and shipment gates

Ship item 0 alone first after approval, then item 1 as the first reconstruction
change. Re-rank later items using measured recovered-token counts and fixture
results; do not bundle admission, row attachment, and rendering into one patch.

For each table commit, compare original and new region membership, all recovered
words, row associations, and fallback decisions on the named SBTi pages. Preserve
the guard and rerun both real references, all synthetic fixtures, and affected
pilot documents. Include Table 1's prose-only pages and Table 2 pp. 38–40 in
review; a lower fallback count must not conceal newly flattened tables. Reject a
change that improves counts by duplication, loses negations/numbers, or regresses
`paper.pdf` booktabs, `hard.pdf` ruled cells, or Ragins' paragraph flow.

This commit contains the plan only. No implementation starts until review.
