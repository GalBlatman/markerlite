# Source-line suppression audit

Baseline: `81b7ca9`. Packet B is read in place from
`/home/galbl/unknown-knowns-markerlite-v0112/upstream/`; source PDFs and evidence
images are not copied into this repository. Packet A is structural evidence for
batch C, not part of this fix. All counts use `content_words`.

## Step 0: reconcile SBTi's fallback gains

All **+80 content words** present at `81b7ca9` are source-member tokens the
geometric fallback omitted. None is an unrelated addition. The implementation
landed in `2103350`; `81b7ca9` did not change SBTi output.

The earlier **83** in REPORT-tables-step4.md is 80 actual missing tokens plus
three tokens falsely counted as missing by that audit's old HTML-stripping
regex: **`is`, `not`, `<1%` on PDF p. 12 (region 6)**. Re-running the historical
`f1f0d16` converter in memory reproduces its 28-token p. 12 deficit with
`<[^>]+>`; the standard real-tag normalization gives 25. The literal `<1%`
was mistaken for the start of a tag and the intervening text disappeared from
the audit comparison. Those three already survive the geometric grid. They
are not new recovered words or a remaining three-word loss.

The following exact gained multisets match the missing fallback-member tokens;
all other fallback regions gain zero. Successful reconstructed cells are
unchanged. The full before/after source audit remains in
`tests/batchC-fallback-audit.json`.

| PDF page | Recovered count | Exact multiset (token: multiplicity) |
| --- | ---: | --- |
| 11 | 1 | `{"Scope": 1}` |
| 12 | 25 | `{"of": 2, "scope": 1, "●": 1, "and": 3, "reported": 2, "excluded": 1, "near-term": 1, "reduction": 1, "customer": 1, "at": 2, "least": 2, "two-thirds": 1, "(67%)": 1, "total": 2, "cover": 1, "target": 1, "33%": 1, "Criterion": 1}` |
| 16 | 27 | `{"the": 3, "and": 2, "with": 1, "should": 1, "boundary": 1, "a": 1, "CO2": 2, "emissions": 1, "from": 1, "processing": 1, "land": 1, "associated": 1, "alongside": 1, "these": 1, "scopes": 1, "1,": 1, "2": 1, "progress": 1, "report": 2, "biogenic": 1, "i.e.,": 1, "also": 1}` |
| 34 | 11 | `{"●": 1, "Subsidiaries": 1, "of": 1, "fossil": 1, "fuel": 1, "companies": 1, "may": 1, "join": 1, "is": 1, "not": 1, "SBTi’s": 1}` |
| 36 | 6 | `{"●": 1, "The": 1, "company’s": 1, "base": 1, "year": 1, "emissions": 1}` |
| 43 | 3 | `{"2030": 1, "100%": 1, "temperature": 1}` |
| 45 | 2 | `{"is": 1, "data.": 1}` |
| 62 | 5 | `{"and": 1, "year].": 1, "to": 1, "1,2": 1, "be": 1}` |

## Step 1: visible suppression, unchanged Markdown

Added `stats["suppressed"]` records with stable `page`, `bbox`, `text`, and
`reason` fields. Whole-block removal records each source line separately;
merged running-head removal records the removed line. Native provenance pages,
OCR notice pages, provenance stamps and the extraction tilt filter are covered.
Relocation into captions/footnotes is not suppression. summarize() reports the
number of records. CLAUDE.md documents the contract; AGENTS.md is regenerated.

The full fixture regression passes without updating any expected Markdown.
Additional contract assertions cover field names, page numbering, bboxes,
summary counts and the watermark, provenance, line-number and footer passes.
Real-document suppression traces are captured before changing the rules for
Packet B and the reference set; they are evidence for the subsequent fix,
not a claim that the current suppressed lines are all furniture.

## Step 2: historical bisection

Historical converter revisions were loaded directly from Git into memory and run
on the original PDFs. The working converter was not replaced and no PDF was
copied. Binary searches over converter-changing commits trace the first new
furniture suppression; adjacent tested converter revisions bracket each change.
Rendered-output checks on `7945428` and `a891dda` expose an important earlier
loss: **20 rotated-page cases became entirely blank at a891dda**. The later
`ab57a91` rotation repair made their text readable again but exposed it to the
furniture passes. Reporting ab57a91 alone as the first loss would be misleading.
All 20 affected page outputs at a891dda are empty after their page marker.

Thus 23 new cases first lose source content at **a891dda**, and seven at
**5506fe7**. At the current furniture-pass level, 20 are exposed by ab57a91,
seven by 5506fe7, and three by a891dda. The fourteen pre-existing cases all
come from `proc_ignore_common` / `_filter_common`: repeated boundary text is
suppressed regardless of caption/table context or edge position.

- `a891dda`: removes the footer stream-order guard (axis tick `-1`, `5`, `0`);
  removes tilted native lines (20 entire landscape-page cases); extends the
  increasing-integer detector to a single multiline block (the Year column).
- `5506fe7`: strips digit-bearing edge tokens from repetition keys. Numeric
  fragments collapse to an empty key; content fragments falsely match other
  edge text. R00160's second tick, `-4.5`, also joins the loss here; `-1` was
  already lost at a891dda.
- `ab57a91`: normalizes sideways pages, restoring their text into the normal
  pipeline; unprotected repeated headers/captions and page-edge final rows
  are then removed by the furniture passes.

| Case | Document | PDF page | First source loss (or old rule) | Current furniture-path introduction | Suppressed distinct target strings: e419550 → HEAD |
| --- | --- | ---: | --- | --- | ---: |
| B01 | R02659 | 8 | 5506fe7 | 5506fe7 | 0 → 9 |
| B02 | S0004 | 7 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 8 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 9 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 10 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 11 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 12 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 18 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B02 | S0004 | 19 | a891dda (tilt; entire page) | ab57a91 | 0 → 6 |
| B03 | R00263 | 10 | a891dda (tilt; entire page) | ab57a91 | 0 → 3 |
| B03 | R00263 | 15 | a891dda (tilt; entire page) | ab57a91 | 0 → 3 |
| B03 | R00263 | 17 | a891dda (tilt; entire page) | ab57a91 | 0 → 3 |
| B04 | S0004 | 36 | 5506fe7 | 5506fe7 | 0 → 1 |
| B05 | R00153 | 26 | 5506fe7 | 5506fe7 | 0 → 5 |
| B06 | R00373 | 20 | 5506fe7 | 5506fe7 | 0 → 6 |
| B07 | R00860 | 47 | 5506fe7 | 5506fe7 | 0 → 1 |
| B07 | R00860 | 48 | 5506fe7 | 5506fe7 | 0 → 1 |
| B08 | R00032 | 66 | 5506fe7 | 5506fe7 | 0 → 1 |
| B09 | S0004 | 7 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0004 | 8 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0004 | 9 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0004 | 10 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0004 | 11 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0004 | 12 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0009 | 18 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0009 | 19 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0009 | 20 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | S0009 | 21 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B09 | R00263 | 11 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 12 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 16 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 17 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 18 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 19 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B09 | R00263 | 20 | a891dda (tilt; entire page) | ab57a91 | 1 → 2 |
| B10 | S0004 | 6 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B10 | S0004 | 7 | a891dda (tilt; entire page) | ab57a91 | 0 → 1 |
| B10 | S0004 | 8 | a891dda (tilt; entire page) | ab57a91 | 0 → 1 |
| B10 | S0004 | 17 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B10 | S0004 | 18 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B10 | S0004 | 19 | e419550: unpositioned repeated first/last block | already present | 1 → 1 |
| B11 | R00160 | 17 | a891dda | a891dda | 0 → 2 |
| B11 | R00443 | 9 | a891dda | a891dda | 0 → 2 |
| B12 | R00446 | 10 | a891dda | a891dda | 0 → 8 |

Counts in this history table are distinct exact target strings, not content-word counts; repeated cells such as “Strong” count once. They describe the bisection predicate only. Validation below checks every source occurrence and its rendered evidence.

## Step 3: preserve content, constrain furniture

The change protects admitted tables (including fallback prose), source regions
bounded by matching internal rules, and repeated numeric record layouts. Table
attachments must align as a whole block; one header fragment coincidentally
above a table rule does not protect a page-wide running head. These protection
regions do not admit new tables or change reconstruction. `table_recon.py` is
untouched.

Repetition now requires the same edge band and height within
`FURNITURE_HEIGHT_TOL = 0.015` of page height, on distinct pages, with a
nonempty normalized key. The common-boundary pass retains its conservative
four-page minimum; marginalia uses two-page evidence in its narrower bands.
Already recorded running heads still supply repetition evidence for a split
header on another page. A bare page number can be removed from a merged header
without removing the body/citation line below it. Generic table/figure captions
are protected, including continuation captions and appendix figure numbers.

Line-number removal requires mostly consecutive values (increments 1–2 for
at least 80% of a run of eight), down a substantial body-margin extent, outside
protected table/figure regions. A repeated numeric record layout protects an
undetected table's Year column without calling the table structurally correct.

Figure labels/ticks move to `<!-- figure text: … -->` after their placeholder.
They remain source text, not model transcriptions. The unchanged standard
`content_words()` excludes comments: this intentionally lowers that metric
where existing prose becomes figure text. Per-page conservation includes the
retained source labels. Rotated figure labels/captions are recovered from the
tilt trace. Orthogonal text on a raster-covered native-text page is retained;
diagonal overlays remain filtered. This preserves mixed-direction hidden OCR
on sideways tables without claiming to repair their structure.

The complete-log review also found a provenance bug: the old matcher treated
any substring of any stamp word as provenance. Complete native stamp pieces
may still join into an OCR line, but arbitrary substrings and incomplete word
bags no longer qualify. R00443 pp. 14/16 and Suchman p. 14 supplied the real
negative cases; their source text is retained. This is suppression work, not
Packet A table reconstruction.

Fixtures and checks:

- `continued_table_header.pdf`: three repeated table headers, continuation
  captions and table-foot markers survive; the real running head/page numbers
  are removed with records.
- `edge_content.pdf`: both footer-band references and final table rows survive;
  real footer/page numbers disappear. Partial stamp strings survive while the
  complete stamp is recorded and removed.
- `year_column.pdf`: the eight years in a native-text table with raster rules
  survive; the separate manuscript page still loses its 40 genuine line
  numbers. The pre-fix converter loses all eight years.
- `figure_source_labels.pdf`: rotated axis text, a negative tick, and a rotated
  caption outside the crop survive as figure-text comments.
- Existing figure goldens reflect label relocation. The caption fixture's
  merged bare page number is now removed; its journal name remains because
  position alone cannot establish a running head in a one-page document.

The following step records the complete real-document acceptance results.

### Real-document result before the implementation commit

All 44 Packet B page cases pass: their exact target strings, including repeated
cell occurrences, survive; none remains in the suppression log. Every boxed
zoom was inspected in place. Document and image SHA-256 values match the packet.
The complete fixture regression (including OCR fixtures) passes. No source PDF
or supplied evidence image has been copied here.

The table reports the ten references first, then all eleven Packet B document
IDs, then the two controls. York and R00160 are the same PDF and are intentionally
shown under both names; totals must not be summed as independent documents.
All figures below use the unchanged standard `content_words()`. Figure comments
contribute zero. No alternate word metric is used to improve a result.

| Document | Before | After | Change | Attribution |
| --- | ---: | ---: | ---: | --- |
| Target-Validation-Protocol | 18,425 | 18,425 | +0 | Byte-for-byte identical Markdown; all 25 reconstructed grids unchanged, 55 regions / 30 fallbacks. |
| Ragins craft of clear writing 2012 | 6,625 | 6,621 | -4 | −4 words from the genuine running head above the submission cover; all key/value metadata remains. |
| peng2009 | 12,046 | 12,011 | -35 | 28 existing diagram words move to comments; −7 words/numbers in the genuine p. 1 running head. The p. 2 head remains suppressed. |
| greenwood2006 | 14,777 | 14,777 | +0 | Unchanged metric; the two rotated Figure 1 caption lines (seven words) are restored in figure-text comments. |
| wry2013 | 18,441 | 18,441 | +0 | No content-word change. |
| jay2013 | 16,377 | 16,377 | +0 | No content-word change. |
| york2018 | 19,930 | 19,383 | -547 | Same source PDF as R00160: −547 existing figure words moved to comments, with the 199 suppressed words restored there too. |
| kitchener2002 | 13,256 | 13,256 | +0 | No content-word change. |
| suchman1995 | 16,458 | 16,459 | +1 | One native OCR fragment (“itima”, inside Figure 1 on p. 14) no longer matches a provenance substring. Printed folio 571 remains suppressed under the bare-number rule. |
| kostova1999 | 11,297 | 11,291 | -6 | −6 words in the genuine repeated copyright footer on p. 19. |
| R02659 | 19,575 | 19,475 | -100 | +9 column-header words; 109 existing figure words move to comments. Six more words in three tilted labels are retained in comments (zero metric contribution). |
| S0004 | 18,516 | 18,606 | +90 | +64 repeated header words, +18 continuation-caption words, +6 table-foot markers, +2 reference words. |
| R00263 | 17,410 | 17,444 | +34 | +13 final-row words and +21 continuation-caption words. |
| R00153 | 23,801 | 23,779 | -22 | +5 reference words; 27 existing figure words move to comments. Four tilted axis-label words are recovered in comments. |
| R00373 | 13,745 | 13,751 | +6 | +6 reference-continuation words. |
| R00860 | 18,126 | 18,125 | -1 | +3 reference words; −4 words from the genuine ScholarOne running head on PDF p. 2 (the journal field inside the submission table remains). |
| R00032 | 29,827 | 29,755 | -72 | +2 citation words on p. 66; −74 previously leaking bare page numbers from merged page-top blocks. |
| S0009 | 21,480 | 21,492 | +12 | +12 continuation-caption words. |
| R00160 | 19,930 | 19,383 | -547 | 547 existing figure words move to comments; 199 previously suppressed figure words (34 tilted lines plus two ticks) also survive in comments. |
| R00443 | 16,026 | 16,308 | +282 | +273 native OCR tokens from 191 tilted lines and 73 false provenance matches; −48 existing figure words moved to comments; +58 literal formatting tokens (52 code fences and six blockquote markers), −1 existing hyphen-reflow join. Net +282 under the unchanged metric; see qualification below. |
| R00446 | 13,067 | 13,069 | +2 | +8 years; −6 words in the genuine p. 9 running head (OCR “lio” for printed 110, journal name, February). |
| paper | 304 | 304 | +0 | Byte-for-byte identical Markdown and reconstructed cells. |
| hard | 1,021 | 1,021 | +0 | Byte-for-byte identical Markdown and reconstructed cells. |

R00443's +282 is **not 282 newly legible words**. The recovered native OCR is
still damaged on its sideways tables (PDF pp. 14 and 16, checked against the
rendered pages). Its 273 restored source tokens cause existing code/blockquote
classification to emit 58 additional formatting tokens, which the standard
metric counts. Existing reflow joins `r-` with the restored `.28` into `r.28`
(one fewer token). The remaining −48 is figure-text relocation on pp. 9–10.
These effects account exactly for +282; the audit retains the complete diff.
Table reconstruction/OCR repair remains Packet A work. Likewise Suchman's
Figure 1 still lacks a resolved crop on the page-sized scan: its recovered
OCR fragment remains in the existing unstructured output, not a claimed
reconstruction of the figure.

SBTi is still **18,425 content words, 55 regions, 30 fallbacks**. Its full
Markdown, not merely the count, is identical. All 25 reconstructed regions
retain their exact HTML and every cell hash. No restored row changes any SBTi
region; the region-by-region change list is empty. `paper.pdf` and `hard.pdf`
are also byte-identical and keep every cell hash. The 0.9 guard is unchanged.

## Step 4: complete acceptance evidence

Implementation: `702607d`. The frozen logging baseline is `cfcb630`, whose
Markdown is unchanged from `81b7ca9`. [suppression-audit.json](suppression-audit.json)
contains both suppression lists for every document, source hashes, complete
before/after Markdown for each Packet B page case, per-document output diffs,
and both sides of the reconstructed-cell hash comparisons. Source/evidence
files remain at their original paths. The audit used page markers solely to
locate excerpts; the standard metric removes them.

### Suppression-log review and furniture checks

Every final record was reviewed by source text, pass, page and bbox. The final
lists contain running heads/feet, bare numeric furniture, manuscript line
numbers, provenance notices/stamps, and tilted watermark/running-head text.
**No remaining genuine-content suppression was found.** The extra findings in
the draft were closed before committing: 191 orthogonal table-text lines on
R00443 pp. 14/16; 73 false provenance matches there; the “itima” OCR fragment in
Suchman p. 14; two rotated Greenwood p. 15 caption lines; and the R00153 p. 36
axis label. R02659 and York also retain their formerly tilted figure labels.
The full lists make these conclusions inspectable, rather than hiding them in
an aggregate count.

The comparison also reviews records that stopped being suppressed, not just
the final list. **No previously removed running head or page number returns.**
The draft's Peng p. 2 head and Suchman's folio 571 were caught by this check and
fixed before the implementation commit. New removals are genuine furniture:
R00032's 74 leaking folios, R00446 p. 9's printed header, the ScholarOne banners
above the Ragins/R00860 submission covers, Peng p. 1's head, and Kostova p. 19's
copyright footer. Their source pages were rendered and inspected. Submission
metadata inside the Ragins/R00860 cover tables remains intact.

Spot checks of all ten references used SBTi PDF p. 45 (footer), Ragins p. 2,
Peng p. 2, Greenwood p. 2, Wry p. 2, Jay p. 2, York p. 2, Kitchener p. 2,
Suchman p. 2, and Kostova p. 3. The visible running heads/feet and page numerals
on those pages remain suppressed. Additional rendered checks cover the newly
removed furniture listed above. Counts below are **source-line records by
pass**, not a second word metric. Numeric records in running heads can include
a publication year as well as a page number; they are not mislabeled as a
count of pages.

| Document | Before records | After records | Line numbers | Repeated boundary | Marginalia | Provenance | Tilt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R00032 | 22 | 95 | 0 | 20 | 75 | 0 | 0 |
| R00153 | 116 | 110 | 0 | 105 | 1 | 4 | 0 |
| R00160 | 130 | 94 | 0 | 84 | 1 | 0 | 9 |
| R00263 | 82 | 55 | 0 | 54 | 1 | 0 | 0 |
| R00373 | 62 | 56 | 0 | 52 | 0 | 4 | 0 |
| R00443 | 333 | 67 | 0 | 64 | 0 | 3 | 0 |
| R00446 | 60 | 55 | 0 | 52 | 0 | 3 | 0 |
| R00860 | 3708 | 3707 | 3529 | 177 | 1 | 0 | 0 |
| R02659 | 99 | 87 | 0 | 56 | 1 | 0 | 30 |
| Ragins craft of clear writing 2012 | 1323 | 1324 | 1260 | 63 | 1 | 0 | 0 |
| S0004 | 96 | 35 | 0 | 23 | 0 | 0 | 12 |
| S0009 | 124 | 120 | 0 | 30 | 90 | 0 | 0 |
| Target-Validation-Protocol | 174 | 174 | 0 | 75 | 36 | 0 | 63 |
| greenwood2006 | 67 | 65 | 0 | 61 | 0 | 4 | 0 |
| hard | 6 | 6 | 0 | 2 | 4 | 0 | 0 |
| jay2013 | 70 | 70 | 0 | 66 | 1 | 3 | 0 |
| kitchener2002 | 77 | 77 | 0 | 29 | 17 | 31 | 0 |
| kostova1999 | 58 | 58 | 0 | 33 | 9 | 16 | 0 |
| paper | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| peng2009 | 54 | 58 | 0 | 54 | 4 | 0 | 0 |
| suchman1995 | 83 | 82 | 0 | 38 | 0 | 44 | 0 |
| wry2013 | 52 | 52 | 0 | 44 | 0 | 4 | 4 |
| york2018 | 130 | 94 | 0 | 84 | 1 | 0 | 9 |

### Packet B: 44/44 page cases restored

All boxed zooms were inspected in place, and their hashes and source-PDF hashes
match Packet B. Every target occurrence survives, including duplicated “Strong”
cells; no target source line remains in `stats["suppressed"]`. Figure ticks are
checked in the figure-text comments, not confused with a different numeric
occurrence in surrounding prose.

Each diff below compares the actual Markdown lines that contain the case's
target strings. Unchanged matches elsewhere on the page may appear as context;
the boxed source-position lines were absent before. Full before/after pages
and per-target occurrence counts are in the JSON. The literal escape in
`2006\.` is Markdown syntax; standard normalization gives `2006.`.

#### B01 — R02659, PDF p. 8

table column-header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B01-R02659-p008-zoom.png>).

Before: 9 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Variables** **N** **Min** **Max** **Mean** **SD** **p25** **Median** **p75**
```

#### B02 — S0004, PDF p. 7

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p007-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 •• Unintended signals •• Signal temporal duration
```

#### B02 — S0004, PDF p. 8

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p008-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 •• Signal inconsistency weakens signaling effectiveness depending on signaler status Seong & Godart (2018) AMJ Global high-end
```

#### B02 — S0004, PDF p. 9

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p009-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 •• Signal ambiguity
```

#### B02 — S0004, PDF p. 10

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p010-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 Shareholders •• Signaler performance influences receiver signal response •• Signal credibility Janney & Gove (2011) JMS Firms •• Corporate social responsibility Shareholders •• Identifies corporate social responsibility as a signal following signaler wrong-doing Okhmatovskiy & David
```

#### B02 — S0004, PDF p. 11

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p011-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 | James & Vaaler (2018) | OS | Host countries | Noncontrolling but substantial | Shareholders | Signal dominance occurs when the value of one signal |
```

#### B02 — S0004, PDF p. 12

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p012-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 | Wu & Reuer (2021) | JMS | Acquisition targets | Alliance partner prominence | Shareholders | Receiver experience shapes their attention to signals |
```

#### B02 — S0004, PDF p. 18

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p018-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 | Ramaswami, Dreher, Bretz, | PP | Proteges | Mentor status | Prospective | Signal strength and visibility shape the benefits derived from a signal |
```

#### B02 — S0004, PDF p. 19

repeated continuation-table header row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B02-S0004-p019-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
+Authors Journal Signaler Signal Receiver Key Signaling Concepts
 •• Receiver-specific reputation shapes signal influence •• Receiver accountability increases signal attention and response to signal consistency Kilduff, Crossland, Tsai, &
```

#### B03 — R00263, PDF p. 10

table final row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B03-R00263-p010-zoom.png>).

Before: 5 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -2 +2,2 @@
 *Memorialized communication*: Evidence of formal communication documents such as memos, manuals, internal circulars, and instructions (archival data). *Absence of lateral* *communication*: “The process is quite straightforward. Basically, I work independently until I present the case to [the fund manager] . . . no, I think I have already mentioned that there is not much need to consult other case execs.” (SCE3)
+Evidence Strong Strong Moderate Strong
```

#### B03 — R00263, PDF p. 15

table final row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B03-R00263-p015-zoom.png>).

Before: 4 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Evidence Strong Moderate Strong
```

#### B03 — R00263, PDF p. 17

table final row. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B03-R00263-p017-zoom.png>).

Before: 4 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Evidence Strong Strong Moderate
```

#### B04 — S0004, PDF p. 36

reference-list line. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B04-S0004-p036-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+39: 432-478.
```

#### B05 — R00153, PDF p. 26

reference-list line. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B05-R00153-p026-zoom.png>).

Before: 5 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -12,3 +12,3 @@
 camp: The dual identification of contract workers. Administrative Science Quarterly, 50: 68–99.
-persistence and change: A framing perspective. Academy of Management Review, 31: 347–365.
+2006\. Cognitive underpinnings of institutional persistence and change: A framing perspective. Academy of Management Review, 31: 347–365.
 K. G. 2013. Organizational identity formation and change. The Academy of Management Annals, 7: 123–193.
```

#### B06 — R00373, PDF p. 20

reference-list line. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B06-R00373-p020-zoom.png>).

Before: 6 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -6 +6,2 @@
 Staw, B. M., McKechnie, P. I., & Puffer, S. M. 1983. The
+Useem, M. 1993. ***Executive*** ***defense:*** ***Shareholder***
```

#### B07 — R00860, PDF p. 47

reference-list line. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B07-R00860-p047-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+39(4): 1024-1039.
```

#### B07 — R00860, PDF p. 48

reference-list line. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B07-R00860-p048-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+653-669.
```

#### B08 — R00032, PDF p. 66

body / citation fragment. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B08-R00032-p066-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+al., 2000).
```

#### B09 — S0004, PDF p. 7

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p007-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0004, PDF p. 8

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p008-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0004, PDF p. 9

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p009-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0004, PDF p. 10

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p010-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0004, PDF p. 11

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p011-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0004, PDF p. 12

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0004-p012-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**Table 1  (continued)**
```

#### B09 — S0009, PDF p. 18

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0009-p018-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Table 6 (Continued)
```

#### B09 — S0009, PDF p. 19

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0009-p019-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Table 6 (Continued)
```

#### B09 — S0009, PDF p. 20

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0009-p020-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Table 6 (Continued)
```

#### B09 — S0009, PDF p. 21

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-S0009-p021-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+Table 6 (Continued)
```

#### B09 — R00263, PDF p. 11

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p011-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+### TABLE 2 Continued
```

#### B09 — R00263, PDF p. 12

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p012-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+### TABLE 2 Continued
```

#### B09 — R00263, PDF p. 16

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p016-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**TABLE 3** **(Continued)**
```

#### B09 — R00263, PDF p. 17

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p017-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**TABLE 3** **(Continued)**
```

#### B09 — R00263, PDF p. 18

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p018-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**TABLE 3** **(Continued)**
```

#### B09 — R00263, PDF p. 19

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p019-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**TABLE 3** **(Continued)**
```

#### B09 — R00263, PDF p. 20

table / caption continuation label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B09-R00263-p020-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+**TABLE 3** **(Continued)**
```

#### B10 — S0004, PDF p. 6

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p006-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+*(continued)*
```

#### B10 — S0004, PDF p. 7

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p007-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1,2 @@
+*(continued)*
+**Table 1  (continued)**
```

#### B10 — S0004, PDF p. 8

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p008-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1,2 @@
+*(continued)*
+**Table 1  (continued)**
```

#### B10 — S0004, PDF p. 17

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p017-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1 @@
+*(continued)*
```

#### B10 — S0004, PDF p. 18

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p018-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
 **Table 2  (continued)**
+*(continued)*
```

#### B10 — S0004, PDF p. 19

table-foot continuation marker. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B10-S0004-p019-zoom.png>).

Before: 1 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
 **Table 2  (continued)**
+*(continued)*
```

#### B11 — R00160, PDF p. 17

figure axis tick label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B11-R00160-p017-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1,2 @@
+<!-- figure text: -1 -->
+<!-- figure text: -4.5 -->
```

#### B11 — R00443, PDF p. 9

figure axis tick label. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B11-R00443-p009-zoom.png>).

Before: 2 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -0,0 +1,2 @@
+<!-- figure text: 5 -->
+<!-- figure text: 0 -->
```

#### B12 — R00446, PDF p. 10

table data column (years) removed as line numbers. [Boxed source evidence](</home/galbl/unknown-knowns-markerlite-v0112/upstream/evidence/packet-B/B12-R00446-p010-zoom.png>).

Before: 8 boxed source-line occurrence(s) suppressed. After: all retained; zero matching suppression records.

```diff
--- before Markdown
+++ after Markdown
@@ -1 +1,2 @@
 ine the adoption of the senior and staff attorney tracks in the principal offices of firms. The empirical analysis of this study thus deals with timevarying conditions that lead up to these adoptions. We used these models for analysis since our main data were collected from annual directories and we therefore did not know the exact time at which each law office adopted an innovation (Allison, 1982). Principal offices that did not adopt the innovation by 1994 were treated as "right-censored." Having adopted an innovation, an office was no longer at risk of adopting the practice, and it did not provide any additional observations.
+1987 1988 1989 1990 1991 1992 1993 1994
```

### SBTi: all 55 region decisions and cell checks

Direct decision traces at the logging baseline and at `702607d` match in
full: page, bbox, source digest, fallback decision, source-token count,
caption/excluded-line counts, and reconstruction/output token diagnostics.
The full trace and both 25-table cell-hash matrices are in the JSON. This is
in addition to the byte-identical whole Markdown check. No restored row joins
or alters a region.

| Region | PDF page | Before → after | Cells/source |
| --- | ---: | --- | --- |
| 1 | 2 | reconstructed grid → reconstructed grid | every cell identical |
| 2 | 3 | fallback prose → fallback prose | source identical |
| 3 | 10 | reconstructed grid → reconstructed grid | every cell identical |
| 4 | 11 | fallback prose → fallback prose | source identical |
| 5 | 11 | fallback prose → fallback prose | source identical |
| 6 | 12 | fallback prose → fallback prose | source identical |
| 7 | 13 | fallback prose → fallback prose | source identical |
| 8 | 14 | reconstructed grid → reconstructed grid | every cell identical |
| 9 | 15 | reconstructed grid → reconstructed grid | every cell identical |
| 10 | 16 | reconstructed grid → reconstructed grid | every cell identical |
| 11 | 16 | reconstructed grid → reconstructed grid | every cell identical |
| 12 | 16 | fallback prose → fallback prose | source identical |
| 13 | 17 | fallback prose → fallback prose | source identical |
| 14 | 17 | fallback prose → fallback prose | source identical |
| 15 | 19 | reconstructed grid → reconstructed grid | every cell identical |
| 16 | 20 | fallback prose → fallback prose | source identical |
| 17 | 20 | reconstructed grid → reconstructed grid | every cell identical |
| 18 | 22 | fallback prose → fallback prose | source identical |
| 19 | 24 | reconstructed grid → reconstructed grid | every cell identical |
| 20 | 25 | reconstructed grid → reconstructed grid | every cell identical |
| 21 | 25 | fallback prose → fallback prose | source identical |
| 22 | 26 | reconstructed grid → reconstructed grid | every cell identical |
| 23 | 26 | fallback prose → fallback prose | source identical |
| 24 | 27 | reconstructed grid → reconstructed grid | every cell identical |
| 25 | 29 | fallback prose → fallback prose | source identical |
| 26 | 29 | fallback prose → fallback prose | source identical |
| 27 | 30 | reconstructed grid → reconstructed grid | every cell identical |
| 28 | 31 | reconstructed grid → reconstructed grid | every cell identical |
| 29 | 32 | reconstructed grid → reconstructed grid | every cell identical |
| 30 | 34 | fallback prose → fallback prose | source identical |
| 31 | 35 | reconstructed grid → reconstructed grid | every cell identical |
| 32 | 36 | reconstructed grid → reconstructed grid | every cell identical |
| 33 | 36 | fallback prose → fallback prose | source identical |
| 34 | 40 | reconstructed grid → reconstructed grid | every cell identical |
| 35 | 42 | reconstructed grid → reconstructed grid | every cell identical |
| 36 | 43 | fallback prose → fallback prose | source identical |
| 37 | 44 | fallback prose → fallback prose | source identical |
| 38 | 45 | fallback prose → fallback prose | source identical |
| 39 | 45 | fallback prose → fallback prose | source identical |
| 40 | 46 | fallback prose → fallback prose | source identical |
| 41 | 47 | fallback prose → fallback prose | source identical |
| 42 | 48 | fallback prose → fallback prose | source identical |
| 43 | 49 | fallback prose → fallback prose | source identical |
| 44 | 53 | fallback prose → fallback prose | source identical |
| 45 | 54 | reconstructed grid → reconstructed grid | every cell identical |
| 46 | 55 | fallback prose → fallback prose | source identical |
| 47 | 56 | reconstructed grid → reconstructed grid | every cell identical |
| 48 | 57 | reconstructed grid → reconstructed grid | every cell identical |
| 49 | 58 | reconstructed grid → reconstructed grid | every cell identical |
| 50 | 60 | fallback prose → fallback prose | source identical |
| 51 | 60 | reconstructed grid → reconstructed grid | every cell identical |
| 52 | 61 | fallback prose → fallback prose | source identical |
| 53 | 61 | reconstructed grid → reconstructed grid | every cell identical |
| 54 | 62 | fallback prose → fallback prose | source identical |
| 55 | 63 | fallback prose → fallback prose | source identical |

Validation commands: `python tests/regress.py` (all fixtures and additional
checks pass, with Tesseract available) and the `capture()` function in
`tests/audit_table_recovery.py` for the SBTi decision/cell trace. Baseline
converter code was loaded from Git into memory, never into a scratch checkout;
all PDFs were read from the source paths in the JSON. Historical bisection
results are separately retained in `tests/suppression-history.json`.

## Step 5: context and generated instructions

CLAUDE.md now states the requested source-line decision rule, documents the
positional/table/figure protections, the stable suppression-record contract,
and the figure-text marker and its metric behavior. Its pipeline and fixture
notes reflect the implemented behavior. `tools/sync_agents.py` regenerated
AGENTS.md; it was not edited directly. Packet A remains deferred batch C work.
No version tag was created.
