# Diagnosis: Kitchener 2002 (Organization Studies, SAGE scan) against v0.1.9

File copied to `tests/real/kitchener2002.pdf` (gitignored); the Zotero
original was not touched. Diagnosis was done on v0.1.9 (a65b83c); the
isolated fixes that followed are listed in section 4 with their commits.

## 1. Characterisation

| | kitchener2002.pdf |
| --- | --- |
| Source | SAGE Journals Online (oss.sagepub.com), downloaded 2012 |
| Producer / creator | Apex PDFWriter, modified by iText 4.2.0; title metadata present; created 2004, modified 2026-01-05 |
| Pages | 30 (journal pp. 391-420); no cover page, no terms page |
| Text layer | None. Every page is one full-page bilevel raster, 4064 x 5632 px (600 dpi), plus a native Helvetica 5 pt stamp at the foot in three pieces: "Downloaded from ", "oss.sagepub.com", " at SAGE Publications on December 7, 2012" (72 chars). Page 1 adds "from the SAGE Social Science Collections. All Rights Reserved." (134 chars total). |
| OCR layer | None |
| Columns | Body single column with a wide left margin that carries the author box (p1), the journal box (p1), and side labels ("Note", "References"); references pp. 25-30 in two narrow columns |
| Rotated text | None |
| Tables / figures | Figure 1 (p10): a four-column boxed model set as text; no ruled tables; one asterisk footnote (p24 "Note"); references pp. 25-30 |

Same class as Suchman and Kostova: an aggregator scan with a per-page
native stamp. It differs in aggregator (SAGE), in stamp size (5 pt, three
native pieces per line), in scan resolution (600 dpi), and in having no
cover page at all.

**Does the OCR gate fire?** Yes, on all 30 pages, and it should. Every page
has one raster covering 100% of the page (0.8 required), 72-134 native
characters (500 allowed), all in the bottom 5% of the page (15% margin
allowed). Neither a miss nor a false fire. Suchman page 1 was the tight case
for the raster fraction (0.896); this document adds nothing new about the
thresholds. The 600 dpi scan renders at 300 dpi for Tesseract as the others
do, and recognition quality is the best of the four (see section 3, H).

## 2. Conversion with v0.1.9, `--page-markers`

| | |
| --- | --- |
| summarize() | `30 pages -> 92 KB Markdown · 30 OCR'd · 1 text-table proposal kept as prose` |
| Content words kept (metric below) | 13,276 |
| Tesseract words on the page images (all confidences, diagnostic) | 14,043 |
| OCR pages | 30 of 30 |
| Tables detected / fallen back | 1 proposal accepted (a reference entry, p26), 1 proposal kept as prose; 0 geometric tables (no vector rules on a scan) |
| Headings | 62 |

The 767-word gap to Tesseract is not loss: no page keeps less than 90% of
its Tesseract words. It is dehyphenation (about 15 line-end joins per page)
plus the removed running heads.

**Word metric.** From this report on, every count is `markdown_words()` in
`tests/audit_table_recovery.py`, called "content words": whitespace tokens
of the Markdown after removing HTML comments, table separator rows, HTML
tags, heading hashes, pipes, emphasis stars and `$$` fences, NFKC-normalised.
Earlier reports quoted gross counts (REPORT-jstor: comments stripped only;
batch A: a different regex); those figures are not comparable with the
table in section 5.

## 3. Defects, grouped by mechanism, ranked by damage

Format: page, what the page shows, what markerlite emitted, stage.

### A. Reference list rendered as ~50 headings (classify/_is_heading) - pp. 25-30

- p25-30: "Ackroyd, Stephen" / "1995 'The new public management...'" author
  lines each on their own line, entry hanging-indented below; emitted `##
  Ackroyd, Stephen`, `### Andreopoulos, Spyros`, `## 1995 'Hospital
  reorganization after merger'...`, `### Hinings` (a wrapped surname) - 50
  of the 62 headings in the document. Stage: `_is_heading` on OCR pages
  accepts any short title-case line (the v0.1.9 rule that replaced the size
  test) and any short numbered line; Tesseract gives each author line its
  own block. New (REPORT-jstor C was the opposite problem); not in PLAN.
  **Fixed**: d751f0f, 92ac229, b36d5a7.

### B. One-word headings missed (classify/_is_heading) - 4 headings

- p1 "Abstract", p1 "Introduction", p24 "Note", p25 "References": bold,
  body size; emitted as plain paragraphs, so the article's opening sections
  and its back matter have no structure. Stage: the title-case test needs
  two words, and after OCR there is neither a bold flag nor a taller line
  box. New. **Fixed**: f2e1adb (behind the size gate; did not reach the
  real document), 92ac229 (before the gate).

### C. SAGE stamp read back by Tesseract (detect_provenance) - p1

- p1 foot: the 5 pt "Downloaded from oss.sagepub.com at SAGE Publications
  on December 7, 2012" and "from the SAGE Social Science Collections. All
  Rights Reserved."; emitted as two paragraphs at the end of page 1 (on
  pages 2-30 `proc_ignore_common` removed the repeated line). No provenance
  comment, because SAGE was not a signature. Stage: extract_page discards
  the native pieces, Tesseract reads the printed stamp, and the provenance
  line drop ran only on native pages. New signature (REPORT-jstor item 5
  anticipated "or whatever it is"). **Fixed**: 1bbd3c2, bbc1da2 - the SAGE
  signature, a `<!-- source: SAGE Journals (oss.sagepub.com); downloaded at
  SAGE Publications on December 7, 2012 -->` comment, and the line drop on
  OCR pages (which also removes the ProQuest banner Tesseract re-read on
  Suchman p1).

### D. Page-1 margin boxes ahead of the title (extract_page / OCR order) - p1

- p1: the left-margin author box ("Martin Kitchener / Department of Social
  and Behavioral Sciences...") and journal box ("Organization Studies /
  2002, 23/3 / 391-420 / © 2002 EGOS / 0170-8406/02...") sit beside the
  abstract; emitted first, before the title, with "#### Organization
  Studies" as a heading and the title paragraph beginning "© 2002 EGOS
  0170-8406/02 0023-0016 $3.00 Mobilizing the Logic of Managerialism...".
  Stage: Tesseract's block order (psm 1 reads the narrow left column
  first), then `_is_heading` on the short title-case box line. Known
  limitation of the OCR path (reading order is Tesseract's); the title
  itself is not a heading because it ends in "*". Not fixed; no isolated
  fix (needs layout reasoning about margin columns).

### E. Figure 1 as prose (propose_tables_from_text) - p10

- p10: a four-column boxed model (Antecedent -> Mobilization ->
  Establishment of Myths -> Organizational Outcomes) with a paragraph in
  each box; emitted as four paragraphs in column order plus "Highly
  institutionalized population..." and "*Figure 1.*" as a caption line.
  Readable, structure lost. Stage: no vector rules, and the boxes are
  multi-line so `_columns_align` rejects the proposal. Same as REPORT-jstor
  E (rule-less scanned tables). Not fixed; belongs to the tables track.

### F. A reference entry turned into a table (propose_tables_from_text) - p26

- p26 "Kitchener, Martin, Ian Kirkpatrick, and Richard Whipp / 1999
  'Decoupling managerial audit: Evidence from the local authority
  children's homes sector'..."; emitted as a 4-column pipe table of
  fragments. Words kept, so the interim guard (70cf029) let it through.
  Stage: `propose_tables_from_text`; REPORT-jstor B / PLAN item 5. Not fixed.

### G. Running heads (proc_marginalia) - none survive

- "392 Martin Kitchener" / "Mobilizing the Logic of Managerialism in
  Professional Fields 393" alternate verso/recto; all 30 removed. The
  digit-token rule from 5506fe7 handles the alternating page numbers. No
  defect; recorded because it is the case Suchman failed.

### H. OCR text quality (outside markerlite)

- Very clean at 600 dpi: "Whittington", "Hasselbladh", "deinstitutionalize"
  all correct on the pages read; "_legitimate?" (p27, an italic word with
  an underline artefact) is the only misread noticed. Footnote marker "*"
  in the title is read as "*" and the note as `[^*]`, which happens to be
  valid.

## 4. Fixes implemented (isolated; one commit each) and what was not

| Commit | Fix | Fixture |
| --- | --- | --- |
| 1bbd3c2 | SAGE provenance signature; provenance line drop on OCR pages | provenance_pages p5 (native SAGE stamp under a body page) |
| f2e1adb | lone capitalised word is a heading on OCR pages | scanned_with_stamp p3 ("Abstract", "Introduction") |
| d751f0f | title case is not a heading after "References" on OCR pages | scanned_with_stamp p3 (four author lines) |
| 92ac229 | one-word / references keyword judged before the size gate; only all-caps inside a reference list | scanned p1 "Abstract"; scanned_with_stamp p3 |
| bbc1da2 | SAGE "at ... on ..." piece found in any native order | (real document; the fixture's merged line already passed) |
| b36d5a7 | "References" itself stays a heading (flag raised after it) | scanned_with_stamp p3 |

None of these touches table admission or the OCR gate thresholds. Not
implemented: D (margin-column reading order), E and F (scanned tables and
proposal shredding, tables track).

**What the fourth document says about the gate thresholds:** nothing that
argues for a change. Coverage 1.0, native 72-134 chars, stamp at 95-98% of
page height. The only constraint it adds is that a stamp may be several
native pieces on one visual line, which affects the provenance matcher,
not the gate.

## 5. Final content words (one metric, final code)

| Document | Content words | Notes |
| --- | --- | --- |
| Kitchener 2002 | 13,257 | 30 OCR'd; headings 62 -> 17 |
| Suchman 1995 | 16,460 | 40 OCR'd |
| Kostova & Zaheer 1999 | 11,299 | 18 OCR'd, ResearchGate cover dropped |
| SBTi protocol | 16,266 | digital; unchanged from v0.1.9 |
| Ragins 2012 | 6,625 | digital; unchanged from v0.1.9 |

`tests/audit_table_recovery.py` now audits the three scans as well when
Tesseract is on PATH (or any PDFs given on the command line), and its trace
assertion allows for accepted text-table proposals (`stats["proposals"]`).
