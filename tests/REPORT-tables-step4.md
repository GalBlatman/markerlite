# Table recovery report — approved steps 1–4

Completed the four approved steps in separate commits. Stop here for review;
item 8 is next, and no other plan item has been implemented.

## Results

- **6 of the original 36 SBTi fallback regions flipped to reconstruction.**
  The count is now **30 / 55**, with the same 55 detected regions, bounding boxes,
  and source-token identities. The threshold remains **0.9**.
- The six regions are on PDF pages **2, 10, 14, 58, 60, 61**. Their
  reconstructions each have **zero missing and zero duplicated/extra tokens**.
  They recover **505 tokens into reconstruction** (170 + 9 + 38 + 152 + 114 + 22).
  These words were already present in the geometric fallback, so this is not
  a 505-word increase in final Markdown.
- Two previously accepted regions also improve: R22 on p. 26 recovers eight
  tokens, and R35 on p. 42 recovers three. Neither counted as an original fallback.
- **Net SBTi gain from wrapped attachment: 11 content words. Ragins: zero change.**
- `paper.pdf` booktabs and `hard.pdf` ruled tables are **cell-by-cell unchanged**:
  the complete header/body cell matrices have identical hashes. The earlier
  snapshots also have identical table HTML, including row/column order.

## What changed and how it was checked

1. `efaa795`: added `* text=auto eol=lf` and `*.bat text eol=crlf` to the
   existing attributes. Ran `git add --renormalize .`. The committed text was
   already normalized; the only stored change was the three-line attributes
   policy. `git diff --ignore-all-space --stat HEAD^ HEAD` at that commit listed
   only `.gitattributes`; excluding that required policy change gave an empty diff.
2. `9fc5578`: applied exactly the local `(*TEXTISH, "Table")` marginalia
   condition and added `table_only_footer.pdf`. Before the fix, both repeated
   textual footers survived; after it, they disappear and the unique margin
   note stays. All prior fixture outputs and all SBTi table decisions/cells
   were unchanged, including **36/55**.
3. `456091d`: added `<!-- ocr page N -->` independently of `--page-markers`.
   `isolated_ocr_page.pdf` includes digital prose, a raster copyright notice,
   a blank page, and a scanned table. Checks cover both marker settings and
   placement. OCR on the blank page currently sets `ocr_used=True`, so it gets
   a provenance comment without invented text. Existing `scanned.md` changes
   only by the two OCR comments. README and CLAUDE.md explain the marker;
   AGENTS.md was regenerated.
4. The final commit adds markerlite-owned `table_wrap.py`. It reuses the
   vendor's winning column grid and score; it does not edit `table_recon.py`,
   retune the guard, broaden table admission, or add caption/front-matter rules.
   It preserves explicit source-line identities rather than pairing a truncated
   grid with a suffix of source rows. Complete geometric rows or short-key,
   complete row starts establish ownership; partial rows, distant prose,
   unsupported projection assignments, and numeric-transition tables retain
   the original result. An improved result must preserve every input token's
   multiplicity and all old reconstructed content.

The new `all_text_wrapped.pdf` contains ruled and unruled versions, short and
long rows, two-column continuations, a percentage in prose, and a vertically
centered key in the ruled variant. With recovery disabled, the ruled version
falls back and the unruled version loses continuation words and creates a false
extra row. With recovery enabled, both have the same correct five-row cell
matrix (header plus four records), and the ruled region no longer falls back.
Five focused tests cover those cell identities, repeated-word multiplicity,
input immutability, ambiguous partial records, distant prose, and an unchanged
numeric winner. They run through `tests/regress.py` in CI. All **17 PDF fixtures**,
those tests, the OCR marker checks, and the cp1252 console check pass.

## Measurement and reproducibility

Baseline for step 4: `456091d` behavior (after marginalia/OCR, before wrapped
recovery). Reference runtime: `/home/galbl/.markerlite-venv/bin/python`, PyMuPDF
1.28.2. The fixture generator uses fpdf2 2.8.8. New PDFs regenerate byte-identically.

Run these from this checkout with the reference PDFs present locally:

```bash
python tests/audit_table_recovery.py --without-wrapped --output /tmp/before.json
python tests/audit_table_recovery.py --output /tmp/after.json
```

The first command disables only wrapped recovery within that diagnostic process;
it does not edit or copy source. Snapshots contain counts, region identities,
source digests, and per-cell hashes, not third-party PDF text. Compare all region
page/bbox/source-digest triples and the full `paper`/`hard` cell-hash matrices.
The two audit runs reproduced the earlier pre-change snapshot's table decisions.
`detect_tables` statistics exclude second-chance text proposals; the denominator
here is the same original 55, not every Table block in the document.

For each region, source tokens come from its original member lines. Normalize
with Unicode NFKC, HTML entity decoding, and whitespace splitting; retain case,
punctuation, and repeated occurrences. Compare multisets, not just lengths or
unique vocabulary. **M** is source occurrences missing from HTML. **D** is excess
occurrences, including duplicates or foreign tokens. An absent reconstruction
has M equal to the source count. Final M/D refer to the emitted table HTML,
including fallback, and are distinct from reconstruction M/D.

Content-word totals below use `markdown_words()` in the audit script: remove
comments, pipe-table separator rows, HTML tags, heading prefixes, pipes, emphasis
asterisks, and display-math delimiters, then apply the same normalization and
whitespace split. This is a fixed comparison metric, not the historical
18,685/18,884 gross-word metric from commit `62c3ff8`; the denominators must not
be mixed. It does not guess missing mathematical notation or deduplicate prose.

| Document | Before steps 1–4 | After marginalia/OCR, before attachment | After attachment | Attachment delta | Total delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| SBTi | 16,321 | 16,255 | 16,266 | +11 | -55 |
| Ragins | 6,625 | 6,625 | 6,625 | 0 | 0 |

SBTi's total reduction is explained by **66 repeated-footer content words
removed**, offset by **11 newly retained content words**. Ragins' Markdown is
unchanged. Original totals were captured before the marginalia edit; the
repeatable `--without-wrapped` command isolates the attachment delta.

## All 36 original fallback regions

IDs are their positions among the original 55 detected regions, not renumbered
successes. Pages are one-based PDF pages; SBTi's printed number is one lower.
Bboxes are `(x0, y0, x1, y1)` in points, rounded here to one decimal; comparison
used the full coordinates plus source digests. “Now reconstructs” means the
reconstruction is emitted rather than the fallback, not a claim that the entire
parent table or page is structurally solved. Baseline reconstruction D was zero
for every region below.

| ID | PDF page | Bbox | Source tokens | Before rec. M | Now reconstructs | Rec. M | Rec. D | Final M | Final D |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| R01 | 2 | 54.2, 173.7, 572.8, 713.1 | 241 | 170 | yes | 0 | 0 | 0 | 0 |
| R02 | 3 | 54.2, 126.2, 572.8, 642.3 | 201 | 201 | no | 201 | 0 | 0 | 0 |
| R03 | 10 | 546.1, 349.6, 788.2, 526.1 | 75 | 9 | yes | 0 | 0 | 0 | 0 |
| R04 | 11 | 546.1, 117.8, 788.2, 515.9 | 170 | 91 | no | 91 | 0 | 0 | 0 |
| R05 | 11 | 316.6, 117.8, 781.8, 538.7 | 187 | 130 | no | 130 | 0 | 1 | 0 |
| R06 | 12 | 55.6, 117.7, 781.8, 521.1 | 251 | 109 | no | 109 | 0 | 28 | 0 |
| R07 | 13 | 546.1, 117.8, 788.2, 228.0 | 47 | 8 | no | 8 | 0 | 0 | 0 |
| R08 | 14 | 298.6, 141.3, 536.2, 320.0 | 71 | 38 | yes | 0 | 0 | 0 | 0 |
| R12 | 16 | 55.6, 117.8, 781.8, 531.8 | 235 | 73 | no | 73 | 0 | 27 | 0 |
| R13 | 17 | 298.6, 117.8, 536.1, 516.2 | 165 | 105 | no | 105 | 0 | 0 | 0 |
| R14 | 17 | 55.6, 117.8, 781.8, 523.4 | 218 | 97 | no | 97 | 0 | 0 | 0 |
| R16 | 20 | 546.1, 117.9, 788.2, 515.1 | 207 | 126 | no | 126 | 0 | 0 | 0 |
| R18 | 22 | 50.5, 117.8, 793.1, 520.1 | 252 | 66 | no | 66 | 0 | 0 | 0 |
| R21 | 25 | 55.6, 117.9, 788.1, 528.1 | 220 | 88 | no | 88 | 0 | 0 | 0 |
| R23 | 26 | 316.6, 117.8, 788.1, 538.4 | 190 | 22 | no | 22 | 0 | 0 | 0 |
| R25 | 29 | 546.1, 117.9, 788.2, 254.2 | 51 | 27 | no | 27 | 0 | 0 | 0 |
| R26 | 29 | 55.6, 117.9, 788.1, 527.1 | 246 | 139 | no | 139 | 0 | 0 | 0 |
| R30 | 34 | 55.6, 133.6, 788.1, 531.8 | 297 | 53 | no | 53 | 0 | 11 | 0 |
| R33 | 36 | 55.6, 133.6, 788.1, 524.4 | 240 | 54 | no | 54 | 0 | 6 | 0 |
| R36 | 43 | 53.0, 151.0, 558.1, 719.5 | 306 | 306 | no | 306 | 0 | 3 | 0 |
| R37 | 44 | 54.1, 661.4, 557.8, 710.6 | 19 | 19 | no | 19 | 0 | 0 | 0 |
| R38 | 45 | 54.2, 127.7, 557.7, 194.8 | 42 | 42 | no | 42 | 0 | 0 | 0 |
| R39 | 45 | 53.0, 142.1, 553.2, 295.1 | 69 | 69 | no | 69 | 0 | 2 | 0 |
| R40 | 46 | 55.1, 218.1, 788.6, 532.6 | 235 | 177 | no | 177 | 0 | 0 | 0 |
| R41 | 47 | 60.5, 117.3, 783.3, 529.2 | 365 | 302 | no | 302 | 0 | 0 | 0 |
| R42 | 48 | 60.5, 276.5, 783.2, 529.7 | 243 | 167 | no | 167 | 0 | 0 | 0 |
| R43 | 49 | 55.1, 117.2, 788.7, 515.5 | 307 | 202 | no | 202 | 0 | 0 | 0 |
| R44 | 53 | 54.2, 285.9, 557.8, 731.9 | 296 | 63 | no | 63 | 0 | 0 | 0 |
| R46 | 55 | 59.6, 126.2, 545.2, 723.4 | 350 | 97 | no | 97 | 0 | 0 | 0 |
| R49 | 58 | 54.2, 126.2, 557.8, 630.8 | 265 | 152 | yes | 0 | 0 | 0 | 0 |
| R50 | 60 | 54.1, 151.7, 562.5, 302.1 | 76 | 22 | no | 22 | 0 | 0 | 0 |
| R51 | 60 | 54.1, 415.9, 562.5, 718.9 | 216 | 114 | yes | 0 | 0 | 0 | 0 |
| R52 | 61 | 54.1, 126.2, 562.6, 366.3 | 224 | 108 | no | 108 | 0 | 0 | 0 |
| R53 | 61 | 54.1, 613.7, 562.6, 720.1 | 54 | 22 | yes | 0 | 0 | 0 | 0 |
| R54 | 62 | 59.6, 126.2, 541.4, 711.7 | 410 | 274 | no | 274 | 0 | 5 | 0 |
| R55 | 63 | 54.2, 126.2, 562.6, 419.2 | 198 | 198 | no | 198 | 0 | 0 | 0 |

## Remaining limitations and review boundary

The original 36 regions' reconstruction deficit falls from **3,940 to 3,435
source tokens**; all reconstruction/final D counts are zero. Their final table
outputs still omit **83 source-member tokens**, all in unchanged fallback
regions. These deficits predate this attachment change: the geometric fallback
itself does not necessarily cover every member token. A successful 0.9 count
check is not a guarantee of complete extraction or correct parent-table layout.

The six changed regions were checked against rendered source pages. In particular,
p. 2's wrapped descriptions stay with their version/date cells despite vertically
centered keys; pp. 60–61 retain the matching target formulations and descriptions.
Some inherited structural limitations remain: p. 14's first bullet is still
promoted to a header, p. 58's first continuation row still acts as a header, and
pp. 10/14 are still fragments of the larger criteria table. These are not fixes
for the deferred header/parent-table/lead-in work. The remaining 30 fallbacks
retain their original result; no region disappeared to improve the count.

No acceptance target was imposed on item 1 alone. The actual result is six
flips. CLAUDE.md and its generated AGENTS.md now point to the approved plan and
record **0, 1, 11b done; 8 next; 5,6,2,3,4 then 7,9,10,11a,11c pending review**.
Stop here before item 8 until the user has read this report.
