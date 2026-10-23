# Block 2 stop 3 — diagnosis, held-out study and repairs

No converter changes. Sources were read in place. Original rendered pages were
reviewed at 2x: R00077 pp. 28–32, R00315 p. 14, R00258 (Jay 2013) p. 6.
Historical comparison uses archived commit 8ec41af; current baseline is v0.1.18.
No source PDF or document text is committed.

## The three remaining diagnoses

- **R00077, Table 2 pp. 28–32:** wrapped row/header association, with incomplete
  continuation coverage. The rendered table has 35 records plus its header.
  Only p. 32 becomes a grid (10 × 3); its wrapped header becomes two rows and
  each of the four records becomes two rows. Earlier continuation pages stay
  prose. Historical and current output agree: association .203, adjacency F1 .009.
- **R00315 p. 14:** glyph decoding, not cell association. The rendered 14 × 8
  grid retains its positions. Eight cells differ: header cells (0,4)–(0,7)
  and body cells (5,6), (7,6), (9,6), (10,6), using zero-based coordinates.
  Printed pi/rho/chi/minus become control characters U+0002/U+0001/U+0003/U+0004.
  Both outputs have association .940, adjacency F1 .886. Structural repair
  would not address this cause.
- **R00258 (Jay 2013) p. 6:** partial-region fragmentation, missing true header,
  and wrapped continuations. The rendered right-column table has a shared
  Source/Number header and three groups with a different column layout in the
  last group. The historical output emits Interviewees and Observations as
  separate grids, treating their first records as headers; Archival records
  is outside both. The existing gate leaves only the Interviewees grid;
  Observations stays prose. Association/F1 change .683/.604 to .412/.391
  predates this task and is part of stop 2's accepted cost.

## All eighteen pre-gate wrong tables

The first fifteen causes carry forward the stop-2 report; only the final
three were newly diagnosed here. These are structural labels, not content-word
counts. Machine-readable records, with review provenance and no document text,
are in tests/labels/stop3-gold-causes.json.

| Document | Page | Cause |
| --- | --- | --- |
| R00077 | 8 | row association |
| R00087 | 9 | row association |
| R00263 | 15 | row association |
| R00373 | 13 | row association |
| R00639 | 28 | row association |
| R05732 | 4 | row association |
| S0004 | 6 | row association |
| R00030 | 75 | row association |
| R00112 | 14 | column association |
| R00112 | 17 | column association |
| R01114 | 8 | header association |
| R02027 | 25 | header association |
| R02611 | 18 | header association |
| York | 14 | cross-page joining |
| capiq_keydev | 87 | cross-page joining |
| R00077 | 28 | wrapped row/header association; incomplete continuation coverage |
| R00315 | 14 | glyph decoding; cell positions intact |
| R00258 | 6 | partial-region fragmentation; missing header; wrapped continuations |

No Markdown or stats change is expected or accepted for this evidence-only item.

## B2 — fresh-sample blocker (owner's amended exclusion rule)

All 47 training and 142 held-out documents from stop 2 are excluded, including
aliases of the same PDF. The lost held-out labels were not reconstructed.
The inventory below is source identity metadata, not inferred labels.

The surviving corpus identifies **45 unique training PDFs and 139 unique
held-out PDFs** by SHA256. These have multiple pipeline/reference aliases;
all aliases are excluded. Five historical identities (two training, three
held-out) cannot be certified from the surviving inventory. This discrepancy
is explicit rather than filling missing IDs with guesses. Complete identified
IDs, aliases and hashes are in tests/labels/stop3-exclusions.json.

Conservative exclusions leave just one candidate, pilot/pdf/S0001.pdf
(SHA256 7e2a1ea34a901d63b2a77cf33d0be9bce788dd10eda62c90e33be9ca294b1aaa).
Its baseline conversion produces **zero detected regions and zero emitted
grids**. Its untouched status is not certified while the five historical
identities remain unresolved. Thus **zero available untouched documents
produce grids**, below the owner's approximately 30-document / 60-grid
minimum. No B2 labels, precision estimate or independent agreement is claimed.
No sample was used. New PDFs are required; B3–B5 were not started.

### Identifiable exclusion set by document ID

IDs in parentheses are aliases of the same PDF, not extra documents.

| Historical set | Document ID | Other source IDs |
| --- | --- | --- |
| held_out | AR0002 | — |
| held_out | AR0006 | — |
| held_out | AR0017 | — |
| held_out | AR0020 | — |
| held_out | AR0021 | — |
| held_out | AR0024 | — |
| held_out | AR0026 | — |
| held_out | AR0027 | — |
| held_out | AR0028 | — |
| held_out | AR0030 | — |
| held_out | AR0033 | — |
| held_out | AR0034 | S0002 |
| held_out | AR0035 | — |
| held_out | AR0036 | — |
| held_out | AR0042 | — |
| held_out | AR0043 | — |
| held_out | AR0044 | — |
| held_out | AR0046 | — |
| held_out | AR0048 | — |
| held_out | AR0049 | — |
| held_out | AR0050 | — |
| held_out | AR0051 | — |
| held_out | AR0052 | S0003 |
| held_out | AR0063 | — |
| held_out | AR0065 | — |
| held_out | AR0068 | — |
| held_out | AR0071 | — |
| held_out | AR0073 | — |
| held_out | AR0077 | — |
| held_out | AR0080 | — |
| held_out | AR0081 | — |
| held_out | AR0082 | — |
| held_out | AR0084 | — |
| held_out | AR0085 | — |
| held_out | AR0086 | — |
| held_out | AR0087 | — |
| held_out | AR0089 | — |
| held_out | AR0090 | — |
| held_out | AR0097 | — |
| held_out | AR0098 | — |
| held_out | AR0099 | — |
| held_out | AR0100 | — |
| held_out | AR0102 | — |
| held_out | AR0103 | — |
| held_out | AR0109 | — |
| held_out | AR0110 | — |
| held_out | AR0113 | — |
| held_out | AR0114 | — |
| held_out | AR0115 | — |
| held_out | AR0116 | — |
| held_out | AR0117 | — |
| held_out | AR0118 | — |
| held_out | AR0121 | — |
| held_out | AR0122 | — |
| held_out | AR0124 | — |
| held_out | AR0125 | — |
| held_out | AR0127 | — |
| held_out | AR0128 | — |
| held_out | AR0129 | — |
| held_out | AR0135 | — |
| held_out | AR0136 | — |
| held_out | AR0137 | — |
| held_out | AR0138 | — |
| held_out | AR0139 | — |
| held_out | AR0140 | — |
| held_out | AR0141 | — |
| held_out | AR0142 | — |
| held_out | AR0143 | — |
| held_out | AR0144 | — |
| held_out | AR0145 | — |
| held_out | AR0146 | — |
| held_out | AR0147 | — |
| held_out | AR0148 | — |
| held_out | AR0149 | — |
| held_out | AR0150 | — |
| held_out | AR0152 | — |
| held_out | AR0153 | — |
| held_out | AR0154 | — |
| held_out | AR0155 | — |
| held_out | AR0156 | — |
| held_out | AR0157 | — |
| held_out | AR0158 | — |
| held_out | AR0159 | — |
| held_out | AR0160 | — |
| held_out | AR0161 | — |
| held_out | AR0162 | — |
| held_out | AR0163 | — |
| held_out | AR0164 | — |
| held_out | AR0165 | — |
| held_out | AR0166 | — |
| held_out | AR0167 | — |
| held_out | AR0168 | — |
| held_out | AR0169 | — |
| held_out | R00052 | AR0091 |
| held_out | R00096 | AR0010 |
| held_out | R00249 | AR0001 |
| held_out | R00443 | AR0047 |
| held_out | R00446 | AR0038 |
| held_out | R00476 | AR0031 |
| held_out | R00538 | AR0037 |
| held_out | R00828 | AR0003 |
| held_out | R00862 | — |
| held_out | R00884 | AR0018 |
| held_out | R01002 | AR0075 |
| held_out | R01073 | AR0078 |
| held_out | R01341 | AR0029 |
| held_out | R01342 | AR0130 |
| held_out | R01346 | AR0131 |
| held_out | R01410 | — |
| held_out | R01473 | AR0096 |
| held_out | R01497 | AR0014 |
| held_out | R01668 | — |
| held_out | R01668 | AR0055 |
| held_out | R01991 | AR0045 |
| held_out | R02682 | — |
| held_out | R04854 | AR0123 |
| held_out | R05947 | AR0126 |
| held_out | R07341 | AR0032 |
| held_out | R07385 | AR0066 |
| held_out | R07399 | AR0079 |
| held_out | R07416 | AR0008 |
| held_out | R07591 | AR0111 |
| held_out | R07672 | AR0108 |
| held_out | R07718 | AR0025 |
| held_out | R07730 | AR0060 |
| held_out | R07749 | AR0004 |
| held_out | R09566 | — |
| held_out | R09567 | AR0009 |
| held_out | R09608 | AR0106 |
| held_out | R09678 | AR0132 |
| held_out | R09704 | AR0119 |
| held_out | R09764 | AR0040 |
| held_out | R10096 | AR0005 |
| held_out | R10097 | AR0039 |
| held_out | R10100 | AR0023 |
| held_out | R10102 | — |
| held_out | R10104 | AR0007 |
| held_out | R10105 | AR0041 |
| held_out | S0001 | — |
| training | AR0011 | S0008 |
| training | AR0076 | S0009 |
| training | R00014 | — |
| training | R00014 | — |
| training | R00023 | — |
| training | R00030 | AR0151 |
| training | R00032 | AR0070 |
| training | R00063 | AR0133, wry2013 |
| training | R00077 | AR0013 |
| training | R00087 | — |
| training | R00112 | AR0092 |
| training | R00153 | AR0105 |
| training | R00160 | AR0112, york2018 |
| training | R00219 | AR0022 |
| training | R00258 | AR0061, jay2013 |
| training | R00263 | AR0101 |
| training | R00293 | AR0015 |
| training | R00315 | AR0053 |
| training | R00359 | AR0064, greenwood2006 |
| training | R00373 | AR0093 |
| training | R00531 | AR0104 |
| training | R00639 | AR0019 |
| training | R00717 | AR0059 |
| training | R00754 | AR0134, peng2009 |
| training | R00831 | AR0120 |
| training | R00860 | AR0069 |
| training | R00894 | — |
| training | R01025 | AR0016, kostova1999 |
| training | R01078 | AR0012, suchman1995 |
| training | R01114 | — |
| training | R01285 | AR0054 |
| training | R02027 | — |
| training | R02055 | — |
| training | R02190 | — |
| training | R02611 | AR0056 |
| training | R02659 | — |
| training | R04077 | AR0057 |
| training | R05732 | — |
| training | R07771 | AR0058 |
| training | R07771 | — |
| training | R07804 | AR0062, kitchener2002 |
| training | Ragins craft of clear writing 2012 | — |
| training | S0004 | — |
| training | Target-Validation-Protocol | — |
| training | capiq_keydev | — |

### Verification and stop

Part A's final app commit a1b31f0 matches all 89 archived golden entries,
zero OCR skips. B1 and this inventory change no converter code; their own
archived-commit runs must also pass before push. There is no default change,
version change, tag, or table_recon.py modification. Content-word delta is
zero wherever Markdown/stats hashes are identical.

Every future training or held-out label must be committed under tests/labels/
with document ID, page, region, label and labeller agreement, without source
text, before it is used. No ephemeral labels may support a claimed result.

## B2 resumed — Zotero source (selection frozen before conversion)

This supersedes the pipeline-only sampling blocker above. The owner supplied
Zotero storage as a new source, read in place. No PDFs, source text, titles or
file names from this source are committed. Documents use 16-hex SHA-256 prefixes.

Pool: 1,230 PDF attachments, representing 1,208 unique document hashes.
Exclusion by exact hash against the entire pipeline corpus, packet upstream
tree, tests/real, tests/fixtures and gold-source metadata removes 147 unique
documents, leaving **1,061 eligible documents**. All 238 exclusion fingerprints
were obtained without read errors; no unresolved historical identity is treated
as eligible merely because its old label record was lost. Duplicates count
once so each document has equal selection probability.

First draw: 80 documents, without replacement, from the sorted eligible hashes,
using Python random.Random(2026102202).sample. Seed, eligible hash-prefix pool
and selected prefixes are frozen in tests/labels/b2-zotero-selection.json before
conversion. There is no replacement of unreadable or failed PDFs. If these
80 yield fewer than 60 emitted grids, a separately seeded batch of 40 will
be drawn from the remaining eligible hashes. Converted text and rendered
review images stay outside the repository. Labels must be committed before
they support any measurement; held-out labels are never tuning inputs.

### B2 review completed and frozen

All 80 drawn documents opened and converted successfully; 219 emitted grids.
No replacement draw or second batch was made. A uniform sample of 60 grids
from the complete 219-grid population uses random.Random(2026102203).sample
after sorting by document hash prefix, page and region. The selected region
locators and all 80 conversion outcomes are committed in
tests/labels/b2-zotero-grid-sample.json.

Two independent agents each visually reviewed all 60 original full pages and
crops and checked all emitted cells, headers and table extents against them.
Both completed the full pass before reconciliation, never reading each other's
labels. Agreement: 60/60; unresolved uncertainties: zero. Both individual
passes and the reconciled records are committed in
tests/labels/b2-zotero-labels.json, containing only hash-prefix identities,
region locators, generic structural reason codes and review/agreement metadata.
No source words, titles, file names or PDFs enter the repository.

These records are committed before computing baseline precision or beginning
B3 implementation. The held-out cases are reserved for baseline/final evaluation;
only the earlier gold set and training evidence may inform B3 changes.

The seeded-selection commit 9dec1f6 passes the full archived audit: 89/89
Markdown/stats hashes match v0.1.18, zero OCR skips, exit status 0.

### B2 baseline precision (computed after label commit f672892)

Correct kept grids: **2/60 = 0.0333**. Two-sided 95% Wilson interval:
**0.0092–0.1136** (0.9%–11.4%). The sample spans 24 documents. This is
grid-weighted precision on a uniform 60-grid sample from the 219 emitted
grids in the uniform 80-document draw; it is not document-weighted precision.
The interval is the same binomial Wilson metric used in stop 2; grids within
a document can be dependent. Both independent passes agreed on all 60 labels.
No held-out defect examples are used to choose B3 changes.

## B3.1 — wrapped record rows

Training evidence: R00077 PDF p. 8, visually checked against the rendered page.
Its two short record keys each wrap after a dash; the following printed line
also fills all four columns. Treating each complete line as a fresh record
split each printed row in two. The repair requires the preceding key to end
in a hyphen/dash, an adjacent hanging-indent continuation, short record keys,
and complete independent row starts. It reuses the winning grid's column
assignment and score. A header box plus one undivided booktabs body box gives
no internal row evidence; independently delimited rows retain their geometry.
Numeric tables retain their existing path. This changes cell ownership only,
not word dehyphenation, glyph decoding, gate thresholds or table_recon.py.
The full source-token multiset must match before a repaired grid is accepted.

Synthetic fixture: wrapped_record_rows.pdf. The immutable pre-fix converter
collapses its two records into one body row (2 × 3 including the header);
the repair produces the printed 3 × 3 table with every source token. It is
rendered and visually checked. The focused tests also protect independently
aligned complete keys, numeric winners, distant prose and ambiguous records.

| Gold table metric | Before | After |
| --- | ---: | ---: |
| EXACT | 1 | 1 |
| GRID-NEAR | 4 | 4 |
| GRID-WRONG | 15 | 15 |
| PROSE | 9 | 9 |
| Mean cell association | 0.441828 | 0.442931 |
| Mean adjacency F1 | 0.334621 | 0.336379 |
| Controls: false grids | 2 | 2 |
| Controls: false markers | 2 | 2 |
| Controls: clean | 4 | 4 |

The ambiguous item remains a false grid, scored separately. Every exact/near
item's complete score record is unchanged. The sole changed gold item is
R00077 p. 8: 5 × 4 becomes 3 × 4; association .751 → .783, adjacency F1
.125 → .176. It remains GRID-WRONG because pre-existing source bullet decoding
and spacing differ from printed gold; no exact/near gain is claimed.

All 42 documents behind the 245 surviving training labels were converted
before and after. Forty-one Markdown outputs and all their regions are
identical; R00077 p. 8 is the only changed region in the remaining document.
Its bounding box, table decision and normalized cell-token multiset are
unchanged. Every page in all 42 documents has the same standard content-word
count. R00077 remains 19,014 content words. The all-document counts, region
comparison and single-review provenance are committed in
tests/labels/b3-row-audit.json. No lost stop-2 labels were reconstructed and
no new held-out examples supplied the repair.

All fixtures match, including paper.pdf and hard.pdf. Unit tests: 274 passed,
three Windows-only named-pipe skips; the final focused table suite passes
8 tests. Ruff checks and formatting pass. The only intended existing-golden
change is the R00077 packet conversion: row ownership/Markdown and its byte
count, with all content words conserved. The new synthetic fixture is
covered by its expected Markdown and focused test; the released v0.1.18
manifest is retained for archived comparisons rather than rewritten.
The full archived-commit output is retained after this commit as required.
