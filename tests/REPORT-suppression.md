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
