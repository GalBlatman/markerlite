# Block 2, stop 2: rotated pages and the table-confidence gate

Date 2026-10-22. Item 1 is committed (8ec41af). Item 2, the gate, is
implemented and measured inside the converter but **not committed**: as
specified it fails one acceptance criterion (labelled good grids removed on
audit pages). The measurements and the options are below for the owner's
ruling. Baseline: tests/golden/v0.1.16.json. Pipeline documents were read
in place.

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

The shape test also removes 2-row grids that carry no label (4 Capital IQ
key-value grids, about 14 SBTi criteria grids); they become prose with all
text.

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
