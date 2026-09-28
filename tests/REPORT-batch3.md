# Batch 3 report: block 0 of batch C

Converter at 1e7af01. All runs in WSL (Tesseract 5.5.0). The metric is content
words from `content_words()`, as in every earlier report. The four pipeline
documents, and R00077 for step (d), were read in place and never copied into
this repository.

## Where the pipeline documents are

The brief names `/home/galbl/unknown-knowns/pilot/pdf/`. That folder holds only
R00087 of the four. The files used:

| Document | Path under /home/galbl/unknown-knowns/ |
| --- | --- |
| R00443 Kraatz & Moore 2002 | stack/pdf/R00443.pdf |
| R00030 Dacin, Dacin & Kent 2019 | autonomous/run-002/pdf/R00030.pdf |
| R00087 Greenwood et al. 2011 | stack/pdf/R00087.pdf (same checksum as pilot/pdf/) |
| R00639 Elsbach & Sutton 1992 | stack/pdf/R00639.pdf |
| R00077 Bromley & Powell 2012 | stack/pdf/R00077.pdf |

## What the four documents are

| Document | Nature | Expected defect | What was found |
| --- | --- | --- | --- |
| R00443 | Publisher scan, 25 pages, with an invisible OCR text layer (PDFsharp), EBSCO notice on p. 25 | garbled native text | The text layer is readable, with scattered character errors. Rotated lines on pp. 14 and 16. |
| R00030 | Word manuscript, 77 pages, WRAP cover on p. 1, p. 77 image-only | repository cover, table loss | Both confirmed. |
| R00087 | Arbortext typeset, 55 pages, pp. 9-15 rotated, raster figure on p. 8 | raster figure absent | Confirmed: no mark for the figure, caption ran as body text. |
| R00639 | ResearchGate cover and 41 scanned pages | cover, figure, table | Cover already handled. Figure on p. 13 unmarked. All 41 pages OCR'd. |

## (a) Garbled text layer: be93af7

A page whose text layer has at least `GARBLE_MIN_TOKENS` (50) word tokens and a
`readable_ratio` under `GARBLE_MIN` (0.10) is treated as having no usable text
and goes to OCR. The ratio is the share of tokens that are common English
words. Fixture `garbled_font.pdf` has a scrambled ToUnicode map and scores
0.03 on 214 tokens; the regression check `garbled` also asserts that `hard`
and `paper` stay clean.

**The detector does not fire on R00443, and it should not.** Its lowest page
scores 0.26, the same as clean reference pages. Compared against a fresh
Tesseract reading of three pages, about 1.4% of its tokens are wrong (17 of
1,254). That is a scan whose hidden OCR layer has isolated character errors,
not a broken font map. The pipeline's own note says the same: "localized
native-text character errors outside the existing ligature trigger".
Content words are 16,026 before and after. A trigger for this class would need
a per-token dictionary test or a sampled OCR comparison, and it would have to
decide when re-OCR of a whole scanned article is worth the cost. That is a
decision for you; nothing was built for it.

Lowest readable ratios, three pages per document:

| Document | Pages judged | Lowest three |
| --- | --- | --- |
| Peng 2009 | 19 of 19 | 0.32 p. 18; 0.33 p. 19; 0.34 p. 16 |
| Greenwood 2006 | 21 of 23 | 0.28 p. 21; 0.31 p. 19; 0.35 p. 22 |
| Wry 2013 | 47 of 49 | 0.31 p. 42; 0.33 p. 45; 0.34 p. 20 |
| Jay 2013 | 23 of 24 | 0.26 p. 22; 0.26 p. 23; 0.33 p. 21 |
| York 2018 | 32 of 32 | 0.31 p. 29; 0.32 p. 31; 0.33 p. 30 |
| Kitchener 2002 | 0 of 30 | scan, no native text to judge |
| Suchman 1995 | 0 of 40 | scan, no native text to judge |
| Kostova 1999 | 1 of 19 | 0.46 p. 1 (the cover) |
| SBTi protocol | 62 of 63 | 0.28 p. 51; 0.33 p. 50; 0.35 p. 54 |
| Ragins 2012 | 21 of 22 | 0.43 p. 20; 0.46 p. 21; 0.55 p. 6 |
| R00443 | 24 of 25 | 0.26 p. 23; 0.27 p. 22; 0.27 p. 24 |
| R00030 | 76 of 77 | 0.21 p. 2; 0.23 p. 74; 0.26 p. 71 |
| R00087 | 55 of 55 | 0.30 p. 12; 0.31 p. 51; 0.31 p. 53 |
| R00639 | 1 of 42 | 0.43 p. 1 (the cover) |

No page of any document is under 0.10. The lowest pages are reference lists
and title pages, which are mostly names. The nearest real page is 0.21, so the
threshold has a margin of about two to one.

## (b) Repository covers: 5e5354c

R00030 carries the Warwick WRAP cover sheet, which was a new signature. It
needs two of the sheet's phrases to match. R00639 carries a ResearchGate cover,
which the existing signature already handled; no change was needed for it.
Fixture: `provenance_pages.pdf` page 7.

Citation lines written:

```
R00030: <!-- source: WRAP (University of Warwick); Manuscript version: Author’s Accepted Manuscript; Persistent WRAP URL: http://wrap.warwick.ac.uk/147367; CC BY-NC-ND 4.0 -->
R00639: <!-- source: ResearchGate; Acquiring Organizational Legitimacy Through Illegitimate Actions: A Marriage of Institutional and Impression Management Theories; Article in Academy of Management Journal · October 1992; DOI: 10.2307/256313 -->
```

R00030 content words: 21,484 before, 21,335 after. The 149 words are the cover
sheet.

## (c) Figure placeholders: d2b45c8, 1e7af01

Every figure leaves `<!-- figure: p. N; caption: ... -->` at its position in
the stream, with or without `--images`. With `--images` the link follows the
comment. A figure is a content raster, a cluster of vector drawing, or a figure
caption that no region claimed. Figure interiors are not OCR'd.

| Document | Figures in the document | Before | After |
| --- | --- | --- | --- |
| R00087 | 1 (p. 8, raster) | no mark, caption as body text | 1 placeholder with its caption |
| R00639 | 1 (p. 13, in the scan) | no mark | 1 placeholder with its caption |

Both sentences in R00639 that open "Figure 1 ..." remain prose. Content words
are unchanged in both files.

The second commit came from reading the placeholders across the whole set. A
chart with axis labels between it and its caption was marked twice, and a
table next to a figure caption took the caption. Both are fixed.

Placeholders per document after both commits:

| Document | Placeholders | Without caption | Note |
| --- | --- | --- | --- |
| Peng 2009 | 2 | 0 | Figures 1 and 2 |
| Greenwood 2006 | 1 | 1 | p. 15: raster figure, no caption in the text layer |
| Wry 2013 | 7 | 0 | Figures 1-7 |
| Jay 2013 | 4 | 0 | Figures 1-4 |
| York 2018 | 4 | 0 | Figures 1-4 |
| Kitchener 2002 | 1 | 0 | caption is "Figure 1."; the title follows as a separate paragraph |
| Suchman 1995 | 1 | 0 | caption absorbs the figure's own words (OCR page) |
| Kostova 1999 | 0 | 0 | **miss**: Figure 1 sits inside a proposed table on an OCR page |
| SBTi protocol | 8 | 8 | none of the eight has a caption the converter recognises |
| Ragins 2012 | 0 | 0 | no figure mentioned in the text |
| R00443 | 3 | 0 | Figures 1-3 |
| R00030 | 0 | 0 | no figure mentioned in the text |
| R00087 | 1 | 0 | |
| R00639 | 1 | 0 | |
| R00077 | 2 | 0 | Figures 1-2 |

Known limits. Kostova's figure is unmarked because a text-table proposal
swallowed its label; that belongs to the table work (PLAN items 5 and 7). With
`--images`, a vector figure gets a placeholder but no saved image, as before
(`repro`: 2 figures, 1 saved). The eight SBTi placeholders were counted, not
inspected one by one against the rendered pages.

## (d) Table token loss: evidence only, nothing fixed

From `tests/audit_table_recovery.py`:

| Document | Page | Source tokens | Reconstruction | Fallback | Output missing |
| --- | --- | --- | --- | --- | --- |
| R00030 | 70 | 29 | 0 kept, 29 missing | yes | 2 |
| R00030 | 75 | 261 | 245 kept, 16 missing | no | 16 |
| R00077 | 8 | 153 | 153 kept | no | 0 |
| R00077 | 32 | 183 | 183 kept | no | 0 |

R00030 p. 75 is the important case. The reconstruction keeps 0.94 of the
tokens, passes the 0.9 decision, and drops 16 tokens with no fallback and no
warning. It is recorded under PLAN item 4. Page 70 is recorded under item 2.

R00077 does not lose tokens inside a detected grid. Its two text-table
proposals are kept as prose, so the words survive and the structure does not.
It is recorded under item 4 as evidence for the proposal path's accounting.

## Content words

Reference set, against the figures of the previous report:

| Document | Before block 0 | After block 0 | Change |
| --- | --- | --- | --- |
| Peng 2009 | 12,046 | 12,046 | 0 |
| Greenwood 2006 | 14,777 | 14,777 | 0 |
| Wry 2013 | 18,441 | 18,441 | 0 |
| Jay 2013 | 16,377 | 16,377 | 0 |
| York 2018 | 19,930 | 19,930 | 0 |
| Kitchener 2002 | 13,256 | 13,256 | 0 |
| Suchman 1995 | 16,458 | 16,458 | 0 |
| Kostova 1999 | 11,297 | 11,297 | 0 |
| SBTi protocol | 18,345 | 18,345 | 0 |
| Ragins 2012 | 6,625 | 6,625 | 0 |

Pipeline documents:

| Document | Before block 0 | After block 0 | Change | Cause |
| --- | --- | --- | --- | --- |
| R00443 | 16,026 | 16,026 | 0 | |
| R00030 | 21,484 | 21,335 | -149 | WRAP cover dropped (b) |
| R00087 | 21,235 | 21,235 | 0 | |
| R00639 | 16,859 | 16,859 | 0 | |
| R00077 | 19,014 | 19,014 | 0 | |

Placeholders are comments and do not count as content words.

## Warnings raised on these documents

- R00443: 1 lossy page, p. 16, 163 of 336 words emitted. The page holds a
  partly sideways table below the 0.8 share that turns a page upright, so the
  sideways lines are dropped. The warning is correct; the loss is open.
- SBTi: 1 low-yield page, p. 1, the known false positive.

## Open after block 0

1. R00443's character errors are not detected. Needs a decision on a trigger.
2. R00443 p. 16: sideways table on a mostly upright page loses 173 words.
3. R00030 p. 75: 16 tokens dropped silently under the 0.9 decision.
4. Kostova Figure 1 has no placeholder.

Regression: all fixtures match on Windows and in WSL. No tag was created.
