# Block 2 stop 3 — B1 diagnosis

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
