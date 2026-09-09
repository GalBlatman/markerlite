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

### 6. Reject journal-front-matter pseudo-tables (report 1)

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

### 7. Isolate captions and constrain membership before reconstruction (report 3)

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

### 8. Parse footnote labels before inline formatting (remaining report 7)

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
