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
