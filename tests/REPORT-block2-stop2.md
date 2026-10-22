# Block 2, stop 2: rotated pages and the table-confidence gate

Date 2026-10-22. Item 1 is committed (8ec41af). The gate was committed
after two owner rulings (f9d8cc5), followed by the grid evidence labels
(01ebb9f) and the drawn-box test (8a2584e). The final numbers for the
v0.1.18 release candidate are in the last section; the sections before it
are the record of how the thresholds were chosen. Baseline:
tests/golden/v0.1.16.json. Pipeline documents were read in place.

## Item 1: rotated pages (8ec41af)

### Diagnosis

| Page | Rotation detected by | Upright pass | Table path after | Cause |
| --- | --- | --- | --- | --- |
| R00077 p32 | stored /Rotate 90 | rotation removed; 2.5% vertical chars left | find_tables grid 10x3 | A |
| R00087 p10 | /Rotate 90 | removed | three 3x2 text proposals | A |
| R00087 p12, p13, p15 | /Rotate 90 | removed | one 3x2 text proposal each | A |
| R00112 p14, p15 | 98.7-98.8% vertical characters | turned in memory | find_tables grids 33x5, 33x3 | A |
| R00160 p12 | 98% vertical | turned in memory | find_tables grid 18x20 | A |
| R00263 p15, p20 | /Rotate 90 | removed | find_tables grids 3x4 | A |
| R00373 p13 | 100% vertical | turned in memory | find_tables grid 4x9 | A |
| R00443 p14, p16 | not turned (9.5% / 57.5% vertical) | none; hidden OCR layer kept | none; fragments | B |
| R02027 p30, p31, p36 | not turned (0% vertical) | none | none; fragments | B |

The upright pass itself loses nothing: on the turned pages the only text
it drops is the perpendicular running head (e.g. "The Academy of
Management Annals"), recorded as tilt_filter furniture.

**Mechanism A (11 pages): rotation is right; the table pipeline is
wrong.** e419550 never read these pages upright and emitted prose. Turned
upright, their tables reach detection and get wrong grids: row-band text
proposals on R00087 (M04), find_tables reconstructions elsewhere
(M06-M09). Fix: the confidence gate (item 2), not a rotation change.

**Mechanism B (5 pages): sideways scans whose hidden OCR layer was made
without orientation.** Tesseract's orientation detection answers "Rotate:
90" on all five, confidence 4.04-19.56. Fix (committed): when a
raster-covered page's text layer reads as fragments, OCR a turned copy
and keep it only if it reads as words.

### Effect (76 documents swept)

Only R00443 and R02027 change. Fragment warnings that change: R00443 p14,
p16; R02027 p30, p31, p36, all cleared; no other page. The fixture
`fragment_text` keeps its warning (it is not a scan). R00443 p14 now opens
"TABLE 1 Descriptive Statistics and Correlation Matrix", p16 "TABLE 3
Interaction of Executive Migration…". Words: R00443 16,304 -> 16,089 (the
pieces had counted as words), R02027 17,953 -> 18,042. No lossy page.
Golden audit of 8ec41af: exactly R02027 and R00443 differ. Gold set: no
change (no gold table is on these pages). Fixture `sideways_scan`.

## Item 2: the table-confidence gate (measured, not committed)

Implemented as specified (markerlite/gate.py, parked outside the repo):
row/column evidence, >= 3 rows and >= 2 columns, no curves, prose share
< 0.35, token identity within 0.05, continuation rows < 0.15. Applied to
find_tables grids (below the gate: prose plus the existing marker, then
the B2 release rule) and to text proposals (below the gate: the block
stays a paragraph). Every decision is recorded with its measures.

Measured on 47 documents: the golden corpus, the 42 documents behind
the 245 region labels (which include every v0.1.14 audit page) and Packet
A's sources.

### Acceptance

| Criterion | Result |
| --- | --- |
| Zero exact or near gold tables lost | **met**: EXACT 1 and NEAR 4 unchanged |
| False grids on controls reduced, target 0 | reduced 5 -> 4 (Kostova p7 clean) |
| No audit page worse | **not met**: 7 labelled good grids on 6 pages become prose |
| No source word lost on a changed page | **met**: no page emits fewer words |

The 7 good grids and the test that stopped each:

| Page | Label | Path | Test | Measure |
| --- | --- | --- | --- | --- |
| R00531 p6 (2 grids) | CORRECT | proposal | identity (+ prose on one) | 0.087, 0.061 |
| R00894 p8 | MINOR | find_tables | continuation | 0.25 |
| R02027 p34 | MINOR | proposal | identity | 0.073 |
| R02611 p18 | MINOR | find_tables | continuation | 0.20 |
| Target-Validation-Protocol p42 | CORRECT | find_tables | prose | 0.364 |
| Jay 2013 p6 | MINOR | proposal | identity | 0.074 |

The shape test also removes 4 unlabelled 2-row Capital IQ grids. (An
earlier version of this report also counted "about 14 SBTi criteria
grids" as 2-row grids. That was wrong: those SBTi grids have one column
and 4-10 rows, and every setting removes them for having fewer than two
columns.)

### What each test costs (172 gate decisions matched to a label)

| Gate variant | Good grids kept (of 74) | Bad grids removed (of 98) |
| --- | --- | --- |
| Evidence, figure and >= 2 columns only | 74 | 19 |
| As specified | 67 | 44 |
| Continuation 0.30 | 69 | 42 |
| Identity 0.10 on text proposals | 70 | 43 |
| Prose 0.40 | 68 | 44 |
| Continuation 0.30 + proposal identity 0.10 | 72 | 40 |
| All of: continuation 0.30, proposal identity 0.10, prose 0.40, rows >= 2 | 74 | 40 |

Not applied: a choice of thresholds is the owner's.

### Gold set, before (8ec41af) and with the gate as specified

| | Before | With gate |
| --- | --- | --- |
| EXACT / NEAR / WRONG / PROSE | 1 / 4 / 18 / 6 | 1 / 4 / 15 / 9 |
| Mean cell association | 0.512 | 0.442 |
| Mean adjacency F1 | 0.369 | 0.335 |
| Controls CLEAN / FALSE-GRID / FALSE-MARKER | 3 / 5 / 0 | 4 / 4 / 0 |
| Ambiguous (S0009 p17) | FALSE-GRID | FALSE-GRID |

To prose: R00030 p75, R02611 p18, S0004 p6. Partly gated (one of several
grids), still wrong: R00087 p9, R00112 p14, Jay p6. Mean association falls
because prose scores 0; tokens kept rise on every changed table.

### Simulated against measured

The plan's offline simulation predicted WRONG 12 and controls CLEAN 7.
Measured: WRONG 15, CLEAN 4. Reasons:

- **Drawn boxes count as rules.** R00860 pp60/61 (figures of ruled boxes)
  show 3 horizontal and 9 vertical rules and no curves; the simulation's
  features counted only free-standing strokes. They pass test 1.
- **Proposals were not in the simulation's scope as built.** R02055 p7
  (figure labels in three aligned columns), Wry p37 (endnotes) and S0009
  p17 (bibliography) are text proposals with recurring columns, no rules,
  no curves, little sentence punctuation, exact tokens. Nothing in tests
  1-6 separates them from a table.
- **Identity is computed on the members' own tokens** (as the plan asked)
  rather than the page, so it is stricter on proposals than the offline
  0.20 estimate: it stops grids that differ from their source by 6-9%,
  which the labels call minor-error grids.

## Remaining wrong grids by cause

The 18 GRID-WRONG gold tables before the gate, by their main mechanism
(tests/REPORT-block2-evidence.md):

| Cause | Tables |
| --- | --- |
| Row association (wrapped lines as rows, detached or collapsed rows: M06, M07, M11) | R00077 p8, R00087 p9, R00263 p15, R00373 p13, R00639 p28, R05732 p4, S0004 p6, R00030 p75 |
| Column association (row labels fused into a data column, stacked panels: M09) | R00112 p14, R00112 p17 |
| Header (band outside the candidate, flattened spanners: M08) | R01114 p8, R02027 p25, R02611 p18 |
| Cross-page (M12) | York T2, Capital IQ p87 |
| Not yet classified | R00077 p28, R00315 p14, Jay p6 |

## Proposed stop-3 ranking (the v0.2.0 association work)

1. **Row association**: wrapped-line rows and collapsed rows (8 gold
   tables, the M06 class across 15 audit pages). Highest count; it is
   also what the continuation test detects, so a fix here would let that
   test stay strict.
2. **Header band**: header outside the candidate or flattened (3 gold
   tables, 26 audit pages under M08).
3. **Column association**: fused label columns and stacked panels (2).
4. **Cross-page joining** (2): stays last, as ruled at stop 1.
5. Figure and list proposals that pass every gate test (R02055 p7, Wry
   p37, S0009 p17): a proposal-side check rather than a gate threshold.

## For the owner

1. Choose the gate thresholds (table above), or keep them as specified
   and accept the 7 good grids as prose.
2. Whether 2-row grids should pass the shape test (Capital IQ key-value
   tables, SBTi criteria pairs).
3. Then the gate is committed with fixtures (figure_grid, endnote_list,
   ruled_table control, split_rows_table, lossy_grid) and re-measured.

## Owner ruling 1 (third setting): overfitting check, not passed

The owner chose the third setting (continuation 0.30, proposal identity
0.10, prose 0.40, 2-row grids allowed) on condition that it survive two
checks. It is not committed: check (b) failed.

**(a) 2-row grids.** Under the third setting the 2-row allowance keeps
exactly 4 grids in the 47 documents, all Capital IQ one-record tables
(header plus one record, four columns). Rendered and compared: all 4 good
(cells hold 8/3/13, 4/3/15, 7/3/12, 5/3/11 words, as printed). No SBTi
2-row grid exists (see the correction above). Clean.

**(b) Held-out check.** 142 documents outside the 47 (the pipeline's
run-001 and stack sets), 89 of which produced grids: 271 gate decisions.
Only 14 differ between the specified and the third setting, so the sample
is all 14 plus 20 random grids kept by the third setting. Each was
labelled from its rendered page against the emitted grid by two
independent labellers (agreement 30 of 34); the 4 disagreements were
adjudicated from the page (D04, K13, K14 bad; K16 good: only its first
two period headers are fused).

| Sample | Good | Bad | Prose |
| --- | --- | --- | --- |
| 14 grids the third setting keeps and the specified one removes | 8 | 5 | 1 |
| 20 random grids the third setting keeps | 9 | 10 | 1 |

By loosened test, for the 14 differing decisions:

| Loosened test | Good kept | Bad or prose kept |
| --- | --- | --- |
| 2-row grids allowed | 4 | 1 (a quadrant figure) |
| Continuation 0.15 -> 0.30 | 3 | 4 |
| Proposal identity 0.05 -> 0.10 | 0 | 1 |
| Prose 0.35 -> 0.40 | 1 | 0 |

On the 172 training labels the continuation and identity loosening cost
nothing (40 bad removed against 44, 5 more good kept). Held out they keep
more bad grids than good: the two thresholds were fitted to the labels.
The 2-row allowance and the prose threshold hold up on both.

Random kept grids are good in 9 of 20: the gate removes non-tables and
the worst grids, but most remaining errors are row and column association
inside real tables, which no gate threshold separates (stop-3 work).

Options for the owner:

1. Third setting without the two fitted loosenings: continuation 0.15 and
   proposal identity 0.05 as specified, prose 0.40, 2-row grids allowed.
   On the training labels this keeps 68 of 74 good (losing R00894 p8,
   R02611 p18 to continuation, R00531 p6 x2, R02027 p34 and Jay p6 to
   identity) and removes 44 of 98 bad; held out, it removes the 4 bad and
   1 bad grids above at the cost of 3 good.
2. The specified setting.
3. Hold the gate until the row-association work (stop 3) lets the
   continuation test stay strict without losing wrapped-header tables.

Not yet done (blocked behind this ruling): item 2 (drawn-box test),
item 3 final numbers, item 4 release candidate.

## Owner ruling 2 and what was committed

The owner took option 1: prose 0.40 and 2-row grids allowed;
continuation 0.15 and proposal identity 0.05 as specified (f9d8cc5). The
acceptance rule was amended: no page loses text, and no page gains a
wrong grid. A correct grid that becomes marked prose is an accepted,
listed cost.

## Final numbers (v0.1.18 release candidate)

Gate as committed in f9d8cc5, with the drawn-box test (8a2584e).

### Gold set

| | Before the gate (8ec41af) | v0.1.18 |
| --- | --- | --- |
| EXACT / NEAR / WRONG / PROSE | 1 / 4 / 18 / 6 | 1 / 4 / 15 / 9 |
| Wrong-grid count (tables) | 18 | 15 |
| Mean cell association | 0.512 | 0.442 |
| Mean adjacency F1 | 0.369 | 0.335 |
| Controls CLEAN / FALSE-GRID / FALSE-MARKER | 3 / 5 / 0 | 4 / 2 / 2 |
| Ambiguous (S0009 p17) | FALSE-GRID | FALSE-GRID |

Prose scores 0 on cell association and adjacency F1 by construction, so
both means fall when a wrong grid becomes prose. The wrong-grid count is
the measure the amended rule uses. The two FALSE-MARKER controls are
R00860 pp60/61: the drawn-box test removed their grids, and the
reconstruction-failed marker stays because ruling lines touch the region.
No gold table changed category because of the drawn-box test.

### Held-out documents: the ship rule

142 documents outside the 47, 271 gate decisions. Every grid the gate
removes was labelled from its rendered page (two independent labellers,
disagreements adjudicated from the page).

| Removed grids | Count |
| --- | --- |
| Wrong (bad grid 62, not a table 20) | 82 |
| Correct | 13 |

Ship rule: the gate stays only if wrong >= 2x correct (>= 26). 82 >= 26,
so the gate stays in v0.1.18. The drawn-box test removes one more held-out
grid (AR0117 p16, two charts, labelled not a table), giving 83 wrong of
96 removed: 0.865, 95% interval 0.782-0.919 (Wilson).

### Kept-grid precision on held-out documents

A random sample of 50 grids each version keeps, labelled the same way.

| Version | Good / kept sample | Precision | 95% interval (Wilson) |
| --- | --- | --- | --- |
| v0.1.17 (no gate) | 17 / 50 | 0.34 | 0.224-0.478 |
| v0.1.18 gate (f9d8cc5) | 16 / 50 | 0.32 | 0.208-0.458 |
| v0.1.18 with the drawn-box test | 16 / 49 | 0.327 | 0.212-0.466 |

The intervals overlap almost entirely. The gate removes non-tables and the
worst grids (the removed set is 86% wrong). Precision on what it keeps
does not move measurably, because most remaining errors are row and column
association inside real tables.

By evidence label (v0.1.18 sample with the drawn-box test):

| Label | Good / kept | Precision | 95% interval |
| --- | --- | --- | --- |
| grid from ruling lines | 11 / 36 | 0.306 | 0.180-0.469 |
| grid from aligned text; verify before use | 5 / 13 | 0.385 | 0.177-0.645 |

Ruling lines do not make a grid more trustworthy on this sample. The
label says what the grid stands on; it is not a confidence score.

### Drawn-box test (8a2584e)

Three or more stroked boxes inside the region, none sharing an edge with
another, fail the gate. Cells drawn one box each touch, and a frame or row
band spanning 90% of the region is not counted.

| Set | Test fires | Newly removed | Labels of the newly removed | Good grids lost |
| --- | --- | --- | --- | --- |
| 172 labelled training decisions | 7 | 3 (R00263 p8, R00860 p60, p61) | all figure | 0 |
| 271 held-out decisions | 4 | 1 (AR0117 p16) | not a table | 0 |

No page loses a source word. On AR0117 p16 the chart axis labels move
from grid cells to figure-text comments beside the two figure placeholders.
Fixture: `drawn_boxes` (R00860 p60 geometry, synthetic text, plus a table
drawn cell by cell as the control).

### Correct grids turned into prose (19, the accepted cost)

| Set | Page | Test |
| --- | --- | --- |
| training | R00531 p6 (2 grids) | identity |
| training | R00894 p8 | continuation 0.25 |
| training | R02027 p34 | identity |
| training | R02611 p18 | continuation 0.20 |
| training | Jay 2013 p6 | identity |
| held out | AR0024 p58, AR0044 p26, AR0080 p10, AR0115 p22, p24, AR0138 p23, R07385 p13 | identity |
| held out | AR0117 p18, AR0157 p38, AR0163 p9 | continuation |
| held out | AR0121 p11 | prose 0.44 |
| held out | R02682 p8, p9 | figure |

Each keeps every word as marked prose.

### Grid evidence labels (01ebb9f)

Every emitted grid has a comment immediately before it:
`<!-- table p. N: grid from ruling lines -->` or
`<!-- table p. N: grid from aligned text; verify before use -->`.
Golden changes from the labels alone: Markdown and the stats byte count,
on every entry that emits a grid. Against 06307a1, 29 entries changed:
19 fixture entries (all_text_wrapped, caption_inside_table, edge_content,
figure_dedup, hard, hard_footer_first, isolated_ocr_page and its
page-markers mode, journal_front_matter, justified_scan, paper, pi_minus,
rotated_pages, scanned, scanned_with_stamp, table_legend,
table_only_footer, tall_cell, watermark), four real entries
(Ragins, greenwood2006, kitchener2002, peng2009) and six packet entries
(R00293, R00359, R00373, R00639, R00860, S0009). capiq_keydev, which
already differed in its stats, now differs in its Markdown too. The other
25 differing entries already differed from v0.1.16 because of earlier
commits; the grids in them carry the labels too.

## Stop-3 list

1. Row association (wrapped-line rows, collapsed rows): 8 gold tables.
2. Header band: 3 gold tables.
3. Column association: 2 gold tables.
4. Cross-page joining: 2, last.
5. Text proposals with aligned columns that pass every gate test: R02055
   p7 (figure labels), Wry p37 (endnotes), S0009 p17 (bibliography). A
   proposal-side check, not a gate threshold.
6. Option measured alongside 1-3: tables emitted as marked prose by
   default, with grids behind an opt-in flag (`--grids` on the command
   line, an option in the GUI). Chosen if stop 3 cannot raise held-out
   kept-grid precision well above the current ~0.33.

   Ruled out (owner ruling at the v0.1.18 tag): emitting grids only where
   ruling lines prove the structure. On the held-out sample ruled grids
   were correct in 11 of 36 cases and aligned-text grids in 5 of 13, so
   ruling lines do not separate reliable grids.
