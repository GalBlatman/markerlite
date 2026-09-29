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
