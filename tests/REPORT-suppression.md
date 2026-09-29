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
