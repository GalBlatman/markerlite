# Batch 2: PLAN item 8, then five more PDFs read as a set

Files copied to `tests/real/` (gitignored): `peng2009.pdf`, `greenwood2006.pdf`,
`wry2013.pdf`, `jay2013.pdf`, `york2018.pdf`, plus `R02027.pdf` for item 8.
Zotero originals untouched. All word counts are **content words**
(`markerlite.content_words`, the metric fixed in REPORT-kitchener.md; see the
note on its tag pattern in section 6).

## 0. PLAN item 8 (commit 699c4f3)

Footnote labels and continuation boundaries are read from the raw spans, the
source label alone is removed, and the merged note body is formatted once.
Fixture `footnote_bold_wrapped`. `footnote_repro`, `footnote_biglabel`,
`paper`, `hard` unchanged.

R02027, the case the plan names: before, 123 definitions, 121 of them `[^**]:`
and 2 `[^***]:`; page 3's note 3 was six definitions. After, 28 definitions,
27 distinct labels, none `[^**]`; page 3 has one `[^3]: **During the 1960s and
early 1970s, a number of EEO/AA laws ...`.

## 1. Characterisation

| | peng2009 | greenwood2006 | wry2013 | jay2013 | york2018 |
| --- | --- | --- | --- | --- | --- |
| Journal | Acad. Mgmt Perspectives | Acad. Mgmt Journal | Acad. Mgmt Annals | Acad. Mgmt Journal | Acad. Mgmt Journal |
| Producer / creator | XPP | XPP | Acrobat Distiller 10 / Arbortext APP 9.1 | PDFsharp 0.9.653 | Acrobat Distiller 10 / Arbortext APP 9.1 |
| Pages | 19 | 23 | 49 | 24 | 32 |
| Text layer | native, all pages | native pp. 1-22; p. 23 raster only | native, all pages | **scan with an invisible OCR text layer** pp. 1-23 (render mode 3 over a 1-bit raster); p. 24 native | native, all pages |
| Native chars / page (min, median, max) | 2337, 4427, 5694 | 0, 4989, 5418 | 182, 2930, 3279 | 301, 5012, 5321 | 1266, 4888, 5545 |
| Cover / banner, aggregator | none | **EBSCOhost notice as a raster**, p. 23 | **EBSCOhost notice**, p. 49 (native) | **EBSCOhost notice**, p. 24 (native) | none |
| Columns | 2 (p1 mixed) | 2 | 1 | 2 | 2 |
| Rotated text | none | p. 15: two vertical lines (Figure 1 printed sideways; its boxes are vector) | **pp. 18-21 stored with /Rotate 90**: 98-99% of characters vertical in unrotated coordinates | none | **pp. 12, 22, 23 printed sideways** (97-99% vertical); pp. 16, 17, 19, 20: 13-16% (figure axis labels) |
| OCR gate fires | no page | p. 23 (0 native chars, the < 20 rule) | no page | no page | no page |
| Should it | no | yes | no | no: a text layer exists, 5,000 chars per page, so the raster rule correctly stays out | no |

No miss and no false fire of the gate in this set. Jay is the instructive
case: every page is covered by a raster, which is what the gate looks at, but
the native layer is a full OCR layer, far above 500 characters, so the page is
read from that layer. The quality of that layer is the publisher's (section 3, H).

Classes: Peng and Greenwood are the same class (XPP, native, two-column AOM
layout). Wry and York are the same class (Arbortext/Distiller, native, pi
fonts, sideways tables). Jay is a class of its own here (publisher scan with
an OCR layer). Greenwood, Wry and Jay share the EBSCOhost aggregator.

## 2. Conversion with HEAD (item 8 in), `--page-markers`

| | peng | greenwood | wry | jay | york |
| --- | --- | --- | --- | --- | --- |
| summarize() | 19 pages -> 83 KB · 1 of 2 table fell back | 23 pages -> 103 KB · 1 OCR'd · 2 of 3 tables fell back | 49 pages -> 121 KB | 24 pages -> 110 KB · 1 text-table proposal kept as prose | 32 pages -> 128 KB |
| Content words | 12,053 | 14,825 | 17,400 | 16,425 | 19,080 |
| PyMuPDF raw words | 12,483 | 15,388 | 18,970 | 17,007 | 20,740 |
| OCR pages | 0 | 1 | 0 | 0 | 0 |
| Tables detected / fell back / proposed | 2 / 1 / 1 | 3 / 2 / 0 | 3 / 0 / 2 | 2 / 0 / 2 (1 kept prose) | 5 / 0 / 4 |
| Headings | 15 | 24 | 4 | 33 | 13 |
| Footnotes emitted / visible | 9 / 9 | 3 / 3 | 1 / 7 (six numbered endnotes and one dagger note) | 0 real (one bogus `[^0]: -`) / at least 2 | 7 (three numbered, four legend lines) / 8 numbered |
| Warnings raised | table fallback | table fallback | none | proposal kept as prose | none |

Seven pages converted to **zero words with no warning**: Wry pp. 18-21 and
York pp. 12, 22, 23 (mechanism A).

## 3. Defects by mechanism across the set, ranked by documents x damage

Format of the example: page, what the page shows, what was emitted, stage.

| # | Mechanism | Documents | Example | Covered by | Status |
| --- | --- | --- | --- | --- | --- |
| A | Sideways pages deleted whole by the tilt filter | wry (4 pp.), york (3 pp.) | York p. 12: Table 1, a 17 x 20 correlation matrix printed sideways; emitted nothing; extract_page | new (a regression from batch A's watermark fix) | **fixed** ab57a91 |
| B | Tables with multi-line or stacked cells shredded or merged | greenwood, york, jay, peng | Greenwood p. 7: Table 1, three columns of wrapped text; emitted one 13-column row; detect_tables fallback | PLAN item 2 (and 1, 4) | evidence added to PLAN |
| C | Minus and "<" from pi fonts read as "2" and "," | york | York p. 14: coefficient -0.10*; emitted `20.10*`; extract_page (font has no ToUnicode) | new | **fixed** 5115e54 |
| D | Section headings at body size missed | wry, york, (greenwood partly) | Wry: 4 headings in 49 pages, all of them the title; York "THEORY AND HYPOTHESES" is prose; classify | CLAUDE.md defect 2, PLAN item 10 neighbourhood | open, not isolated (heading evidence) |
| E | Aggregator notice page as content | greenwood, wry, jay | Wry p. 49: EBSCOhost notice; emitted as the last paragraph; no stage removes it | new signature (REPORT-jstor item 5 mechanism) | **fixed** 4d1d492 |
| F | Prose or notes turned into a table | peng, wry | Wry p. 37: six numbered endnotes; emitted a 2-column table `| 1. | Note that the data ...`, so none is a footnote; propose_tables_from_text | PLAN item 5; REPORT-jstor B | evidence added to PLAN |
| G | Drop capitals detached | peng | Peng p. 4: heading "Two Core Propositions", paragraph opening with a three-line "T"; emitted `# Two Core Propositions T` and "he first ..."; extract_page order | new | **fixed** 2fd0542 |
| H | Publisher OCR layer errors | jay | Jay p. 1: footnote mark "1"; layer reads "^"; emitted "organization^" and "^ The term ..." as prose; also "GHANGE", "Anal)rtic", headings `### y^\` and `# \` from figure text | outside markerlite (REPORT-jstor H is the Tesseract analogue) | open; a re-OCR option would be a gate change, so not proposed here |
| I | Significance legend emitted as footnotes | york | York p. 15: "†p < .10 *p < .05 ..." under Table 2; emitted `[^*]: p , .05` etc.; proc_footnotes | new (item 8's risk note anticipated it) | **fixed** 62f2b07 |
| J | Figure panel letters as headings | york | York p. 16: panels "A", "B", "C", "D"; emitted `### A`, `### B D`; classify | new | **fixed** ef27681 |
| K | Numbered footnotes not recovered | york (5 of 8), jay | York: notes 2-5 and 8 are referenced in the body and not emitted as definitions; stage not traced in this pass | REPORT-jstor F is the OCR analogue; this is digital | open; needs its own trace |
| L | Wrapped title and heading lines as separate headings | greenwood, york, wry, jay, peng | Greenwood p. 1: two-line title; emitted two `#` lines; Peng "The Roots of ... in / Strategy" | PLAN item 10 | open |
| M | Bold seams across soft breaks | greenwood (65), jay (67), peng (11) | Greenwood p. 1 abstract: `**... fields.** **As such ...**`; block_text | PLAN item 9 | open |
| N | Reference entries as headings | greenwood (3), jay (2) | Greenwood p. 20: "DiPiazza, S. 1999. Testimony before the ABA Commis-"; emitted `###`; classify | REPORT-kitchener A is the OCR analogue | open; digital pages have no in-references rule yet |
| O | Journal line, running head and copyright line on page 1 | peng, jay, york | Peng p. 1: "2009 63 Peng, Sun, Pinkham, and Chen" and "Copyright by the Academy of Management; ..."; emitted once each (removed on later pages); proc_marginalia needs a repeat that page 1's variant does not give | known design (repetition evidence) | open, low damage |
| P | Vertical axis labels of figures dropped silently | york pp. 16-20 | "Predicted number of new LEED-certified buildings"; emitted nothing; extract_page tilt filter, below the 0.8 share | consequence of A's design | accepted; they are figure furniture |

## 4. Fixes implemented (new and isolated), with before/after on the real file

| Commit | Fix | Fixture | Real document, before -> after |
| --- | --- | --- | --- |
| ab57a91 | turn sideways pages upright (`ROTATED_PAGE_MIN_FRAC` 0.8; `/Rotate` baked in) | rotated_pages | Wry pp. 18-21: 0, 0, 0, 0 -> 270, 276, 256, 285 words. York pp. 12, 22, 23: 0, 0, 0 -> 305, 331, 212 |
| 4d1d492 | EBSCOhost signature, native and OCR'd | provenance_pages p6, ebsco_notice_scan | Wry p. 49, Jay p. 24, Greenwood p. 23: 47-word notice as prose -> source comment, empty page |
| 62f2b07 | significance legend is not a footnote | table_legend | York definitions 1, 6, †, *, **, ***, 7 -> 1, 6, 7; legend kept under each table |
| 5115e54 | pi-font minus and "<" repaired; `content_words` strips only real tags | pi_minus | York: 223 spans; tokens like `20.10` 190 -> 2; minus signs 0 -> 207; `p , .` 16 -> 0 |
| 2fd0542 | drop capitals reattached; one-word headings with real weight | dropcap (manuscript, manuscript_numcol improve) | Peng: six headings with a stray capital and seven paragraphs missing a first letter -> none; "Discussion", "Contributions", "Conclusion" are headings |
| ef27681 | figure panel letters are not headings | panel_letters | York: 13 headings, ten of them panel letters -> 3 |

None changes table admission, the OCR gate thresholds, or a heading size
threshold. The pi-font repair reorders `convert()` (all pages are extracted
before any table is built, because the repair needs the document's font
inventory); table decisions on every fixture and on SBTi are unchanged by it.

Two side effects worth knowing. The one-word heading rule also makes
"Introduction" and "Method" headings in the manuscript fixtures (they were
bold text, defect 2) and settles their levels at h1. And `content_words` now
counts text after a bare "<": see section 6.

## 5. Evidence added to PLAN-tables.md (not fixed)

- **Item 2** (logical rows, wrapped cells): Greenwood pp. 7, 10, 11; York
  pp. 12, 14-15, 22-23; Jay p. 6.
- **Item 5** (prose vs one-column tables): Peng p. 2; Wry p. 37.
- **Item 6** (front-matter pseudo-tables): no new case in this set; all five
  first pages stay prose. Recorded as a negative result.

## 6. Content words, all ten reference documents, final code

| Document | Content words | Change since REPORT-kitchener / HEAD of this task | Why |
| --- | --- | --- | --- |
| Peng 2009 | 12,046 | 12,053 at HEAD | drop caps and headings; no text added or lost |
| Greenwood & Suddaby 2006 | 14,777 | 14,825 at HEAD | EBSCO notice (47 words) removed |
| Wry et al. 2013 | 18,441 | 17,400 at HEAD | four sideways pages recovered; notice removed |
| Jay 2013 | 16,377 | 16,425 at HEAD | notice removed |
| York et al. 2018 | 19,930 | 19,080 at HEAD | three sideways pages recovered; pi glyphs |
| Kitchener 2002 | 13,256 | 13,257 | item 8: one line-end hyphen closed inside a footnote |
| Suchman 1995 | 16,458 | 16,460 | item 8: two hyphens closed inside footnotes |
| Kostova & Zaheer 1999 | 11,297 | 11,299 | item 8: two hyphens closed inside a footnote (verified by word diff) |
| SBTi protocol | 18,345 | 16,266 | **metric, not converter**: see note |
| Ragins 2012 | 6,625 | 6,625 | unchanged |

The five earlier documents are unchanged in content. Kostova was diffed word
by word against its v0.1.10 output: the only differences are "per- mitting"
-> "permitting" and "re- sponsibilities" -> "responsibilities", both inside
footnote 1, because item 8 merges a note's lines before formatting and closes
line-end hyphens. Kitchener (-1) and Suchman (-2) move by the same mechanism;
they were not diffed individually. Ragins is identical.

**The metric changed once in this task.** `content_words` used to strip
everything between any "<" and the next ">" as an HTML tag. The pi-font
repair produced "p < .05" and one such pair swallowed 4,500 words from York's
count while the Markdown was intact. It now strips real tags only. Applied to
the unchanged v0.1.10 outputs, the corrected metric gives the same count for
nine documents and 18,345 instead of 16,266 for SBTi, which contains ">60%"
and "<" in prose. The 16,266 in REPORT-kitchener.md and the v0.1.10 report is
therefore an undercount by the old pattern, not a different conversion.
