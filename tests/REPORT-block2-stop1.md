# Block 2, stop 1: report

Date 2026-10-02. Covers the owner rulings and items B1-B3 of block 2 stop 1
(tests/PLAN-tables.md, block 2). Measured on the 77-entry golden corpus
(68 distinct source documents) and the gold tables set (29 tables, 8
controls, 1 ambiguous item; tests/GOLD-TABLES.md). No document text from
third-party sources is quoted here beyond running-head strings already
recorded in the suppression audit.

## Summary

| Item | Status | Commits |
| --- | --- | --- |
| Rulings: S0009 p17 ambiguous; York T2 per page segment | done | 03ac0a2 |
| Label re-check (34 labels) | done, 1 flip, does not affect the gate | - |
| B1 masthead | **BLOCKED, not committed** (3 running heads stop being suppressed) | - |
| B2 marker rule | done | 91057e7, 1c7bf0c |
| B3 R00443 fragments | recorded with a measured detector proposal | f2fdd1e |
| Stop-2 ranking note (rotated pages first) | recorded in the plan | f2fdd1e |

## Label re-check before stop 2

The 32 grids labelled non-table and the 2 real-table markers that the
marker rule was expected to remove were re-labelled independently
against the rendered pages. One label flips:

- **R00293 p8, region 1: OTHER -> TABLE.** The region mixes body prose
  with the grid of the article's Table 3. It is a real table captured
  together with prose, so it is GRID-WRONG under either label. It does not
  change the gate's decision.

Peng 2009 p2 and SBTi p43 are confirmed as real tables (each region also
holds other material: Peng a figure strip, SBTi surrounding text).

## B1: R00014 masthead (BLOCKED)

**Change tried:** repetition evidence must also agree on alignment (left
edge, right edge or centre within 0.03 of the page width) and on type
size (ratio at most 1.2). Fixture `first_page_masthead` (synthetic, R00014
geometry): masthead suppressed before, kept after; every running head
still suppressed.

**R00014 p1:** before, "Academy of Management Annals" (the citation-block
masthead) was recorded as `proc_marginalia` and the page opened with the
volume line. After, the masthead is kept; only the folio "1" is
suppressed. Records 89 -> 88.

**Suppression records per golden document, before -> after:** 65 of the 68
documents are unchanged. Three change:

| Document | Records | Change |
| --- | --- | --- |
| R00014 | 89 -> 88 | p1 masthead kept (the intended fix) |
| Kitchener 2002 | 77 -> 76 | **p22 running head "Martin Kitchener" no longer suppressed** |
| Kostova 1999 | 58 -> 56 | **p4 running head "66 . Academy of Management Review" and its "January" no longer suppressed**; pp13, 16, 18 heads move from `proc_ignore_common` to `proc_marginalia` (still suppressed) |

Under the ruling, a running head that stops being suppressed is a blocker,
so B1 is not committed. The patch and its fixture are parked outside the
repository.

**Cause.** Both pages are OCR pages (Kitchener and Kostova are scans). On
an OCR page the "type size" is Tesseract's line-box height, which varies
with descenders and noise: the Kitchener p22 head measures 8.6 pt against
6.2-6.5 pt for the same head on every other even page; the Kostova p4
head 10.3 pt against 7.7-8.2 pt. The size test rejects every match. The
alignment test passes in both cases. This is the same fact CLAUDE.md
already records for headings: on OCR pages line height is shape evidence,
not type size.

**Measured option for the owner (not committed):** apply the size test
only when neither line is on an OCR page. Measured on the three changed
documents: Kitchener 77, Kostova 58 (both identical to before, all heads
suppressed again), R00014 88 (masthead still kept). The 65 unchanged
documents were not re-run with this variant. It would need the full
before/after sweep again before a commit.

## B2: fallback marker only after a real table candidate

**Rule.** A failed candidate keeps "table p. N: reconstruction failed;
text kept as prose" only if a rule touches its region (horizontal over
half its width, or vertical over 0.3 of its height) or at least two column
starts recur across half its rows, and no curve is drawn there. Otherwise
the candidate is dropped and its blocks are classified as ordinary text.
A candidate rejected by the projection limit (A5a) keeps its marker.
`stats["table_candidates_released"]` counts releases (only when non-zero).
1c7bf0c adds that released blocks are not proposed as tables again (see
Peng below).

**Mechanism found on R00023 p3:** Word draws a white filled box behind each
line of text; their edges are "lines" to find_tables' second pass, which
made a 45 x 8 candidate over double-spaced prose. Fixture
`no_table_marker` reproduces this geometry with synthetic text.

**Markers on the golden corpus: 78 -> 50.** Removed 28:

| Document | Markers | Pages released | Label |
| --- | --- | --- | --- |
| R00023 | 18 -> 2 | 3, 7, 9, 11, 12, 22, 24, 27, 28, 34 / 38-42, 45 | prose / references |
| R00032 | 5 -> 1 | 85-88 | references |
| R00153 | 3 -> 1 | 17, 21 | figures |
| R00293 | 4 -> 2 | 15, 17 | figures |
| R05732 | 1 -> 0 | 11 | figure |
| R00030 | 1 -> 0 | 70 | references |
| S0004 | 3 -> 2 | 1 | prose |
| Peng 2009 | 1 -> 0 | 2 | **real table** |

By label: 11 prose, 11 reference lists, 5 figures, 1 real table.

**Real-table markers removed: one, not two.** Peng 2009 p2 (Table 1
"Dimensions of Institutions"; its region also holds a figure strip). Its
text remains: 12,005 content words before the fix commit and after it, and
the gold scorer keeps every token (kept 1.000, PROSE). SBTi p43 keeps its
marker: its region has 8 recurring column starts. The plan's simulation
counted features strictly inside the labelled region box and predicted it
would be removed; the implementation measures column starts on the
candidate's own tokens.

**Text retained.** No source word is lost. Content-word changes are fully
accounted for:

- figure labels that the fallback emitted as prose now sit beside their
  figure placeholder as `<!-- figure text: ... -->` comments, which
  `content_words` excludes (R00153 -141, R00293 -129, R05732 -122);
- the marker's own words;
- "&amp;" that fallback prose emitted literally (R00023, 12-17 per
  reference page) now renders "&";
- ordinary reflow dehyphenation of the released prose, e.g. Peng
  "soci- ologists" -> "sociologists".

**Defect exposed, not introduced:** dehyphenation also joins a page range
broken after its hyphen ("3370-" / "3381" -> "33703381", "Howard-" /
"Grenville" -> "HowardGrenville"). R00023 pp43-44 already showed the
numeric join before B2 (three ranges); B2 extends it to released reference
pages 40-41. This is the open dehyphenation item in CLAUDE.md; a digit on
both sides of the break should never be joined.

**Peng regression found and fixed (1c7bf0c).** With 91057e7 alone, the
gold scorer moved Peng p2 from PROSE to GRID-WRONG (adjacency F1 0.345):
the second-chance proposal pass built a partial grid from the released
blocks. Released blocks are now skipped by that pass. Verified across all
68 golden documents: Peng is the only document whose output changes
between 91057e7 and 1c7bf0c.

**Still marked, labelled non-table (5):** R00293 p10 (kept by four
horizontal strokes inside the region, measured), R02659 p1,
Target-Validation-Protocol p44 and p45 (two regions). For the last four the
label features show recurring columns or rules inside the region; the
deciding test was not traced one by one.

**Golden hash changes, all explained by B2:** 91057e7 changes exactly 8
entries, Markdown and stats: Peng 2009, R00030, R00032, R00153, R00293,
R00023, R05732, S0004, which are the 8 documents in the table above.
1c7bf0c changes only Peng's output relative to 91057e7. B1 changes no
hash (not committed).

## B3: R00443 p16 sideways fragments

Recorded in tests/PLAN-tables.md (E3, owner ruling): no fix now; it belongs
to the rotated-page work. Proposed detector, measured:

| Population | Letter tokens of <= 2 letters | Mean letter-token length |
| --- | --- | --- |
| R00443 body pages (21) | 0.13-0.29 | 5.2-6.1 |
| R00443 p14 / p16 | 0.97 / 0.95 | 1.29 / 1.54 |
| R02027 pp30, 31, 36 | 0.88-0.97 | 1.3-1.5 |
| every other page of tests/real (>= 40 tokens) | <= 0.46 | - |

R00443 p14 is a second page of the same kind that no report had flagged;
R02027 pp30, 31, 36 are fragment output too (a scanned sideways table's
hidden OCR layer). `readable_ratio` cannot detect these pages because it
counts digits as readable: p16 scores 0.77, above its body pages. Proposed:
`stats["fragment_pages"]` for pages with >= 40 letter tokens of which
>= 0.6 are at most two letters, plus a `stat_warnings` line; the text
stays. The sweep must cover the 25 packet documents before a threshold is
committed.

## Gold set re-score

Same gold files throughout. "Old scoring" is the v0.1.15 baseline in the
plan; "new scoring" applies the rulings (S0009 p17 scored apart; York T2
per page segment).

| | v0.1.15, old scoring | 845702f (pre-B2), new scoring | 1c7bf0c (B2), new scoring |
| --- | --- | --- | --- |
| Tables | 29 | 29 | 29 |
| EXACT / NEAR / WRONG / PROSE | 1 / 4 / 18 / 6 | 1 / 4 / 18 / 6 | 1 / 4 / 18 / 6 |
| Exact-match rate | 0.034 | 0.034 | 0.034 |
| Mean cell association | 0.514 | 0.512 | 0.512 |
| Mean adjacency F1 | 0.369 | 0.369 | 0.369 |
| Controls | 9 | 8 | 8 |
| Controls CLEAN / FALSE-GRID / FALSE-MARKER | 0 / 6 / 3 | 0 / 5 / 3 | **3 / 5 / 0** |
| Ambiguous (S0009 p17) | - | FALSE-GRID | FALSE-GRID |

Deltas:

- **Scoring rulings alone:** York T2 per segment: association 0.437 ->
  0.370, adjacency F1 0.346 -> 0.361, still GRID-WRONG (each page's grid
  is wrong on its own page; the old whole-matrix match let page-14 cells
  match page-15 output). Mean association 0.514 -> 0.512. S0009 p17 leaves
  the control count (FALSE-GRID 6 -> 5).
- **B2:** false markers on controls 3 -> 0 (R00023 p3, R00023 p9, R00032
  p85 all CLEAN). Tables unchanged; Peng p2 stays PROSE after 1c7bf0c.
- **Not met:** zero false grids on the 8 controls. Five remain: R00860 p60
  and p61, R02055 p7, Kostova p7 (figures) and Wry p37 (endnotes). These
  are the gate's work (stop 2, gate tests 1-4); stop 1 did not target them.

## Open for the owner

1. B1: accept the OCR-page exemption from the size test (measured above),
   or another approach. B1 stays parked until then.
2. The dehyphenation join across a digit-hyphen-digit break (pre-existing;
   now on more pages).
3. GitHub private vulnerability reporting is still disabled on the
   repository (Part A6); enabling it is an account setting.
