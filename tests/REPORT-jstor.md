# Diagnosis: two AMR PDFs that convert badly (Suchman 1995, Kostova & Zaheer 1999)

Diagnosis only. No converter change was made. Files copied to `tests/real/`
(gitignored) as `suchman1995.pdf` and `kostova1999.pdf`; Zotero originals untouched.

**Headline.** Neither file is a JSTOR download, and neither has a text layer.
Both are page-image scans with a short native copyright stamp on every page,
and that stamp is exactly what defeats the converter: `extract_page` only OCRs
a page with fewer than 20 native characters, the stamps supply 38 and 103, so
no page is OCR'd and the output is the stamps plus the aggregator cover page.
With OCR forced (diagnostic run, WSL, Tesseract 5.5.0) the pipeline recovers
16,898 and 11,533 words, and a second tier of defects appears, all specific to
the OCR path. There is no `issues.md` in the repo; cross-references below are
to `tests/PLAN-tables.md` only.

## 1. Characterisation

| | suchman1995.pdf | kostova1999.pdf |
| --- | --- | --- |
| Source | ProQuest ABI/INFORM Global | ResearchGate upload |
| Producer / creator | 3-Heights PDF Optimization Shell 4.8; created 2005-06-28 | Acrobat 3.0 Import Plug-in; created 1999-02-23; title "AMX;01JAN99" |
| Pages | 40 (p1 = journal p571 with ProQuest citation banner; p40 = refs tail + bio) | 19 (p1 = ResearchGate cover; p2-19 = journal pp. 64-81) |
| Text layer | None. Every page is one full-page bilevel raster, 1706x1961 px (200 dpi), plus native Helvetica stamp "Reproduced with permission of the copyright owner. Further reproduction prohibited without permission." (103 chars, bottom). p1 adds a 275-char native banner: title, author, "Academy of Management. The Academy of Management Review; Jul 1995; 20, 3; ABI/INFORM Global pg. 571". | p1 native only (557 chars, SourceSansPro/Martel: title, "DOI: 10.2307/259037", citation counts, uploader note). p2-19: one full-page bilevel raster 2460x3390 px (300 dpi) plus native Helvetica-Bold stamp "Copyright © 1999. All rights reserved." (38 chars); p19 adds "View publication stats" (4 pt). |
| OCR layer | None (no invisible text; fonts named are only the stamps) | None |
| JSTOR cover / terms page | No. JSTOR appears nowhere. | No. The DOI 10.2307 is JSTOR's prefix but the page is ResearchGate's. |
| Columns (from the raster) | 1 (1995 AMR single-column layout) | 2 (1999 AMR two-column layout); cover page 1 |
| Rotated text | None (all native lines dir (1,0); OCR lines horizontal) | None |
| Tables / figures | Figure 1 (p14, boxed typology grid), Table 1 (p30, rule-less 4-column strategy list), footnotes with superscript refs, references pp. 35-40, author bio p40 | Figure 1 (p7, boxed proposition diagram), 10 indented italic Propositions, footnotes, references pp. 16-18, bios p19 |

Same document class? Yes for the converter's purposes: both are "aggregator
scan + per-page native stamp + provenance page". They differ in aggregator
(ProQuest vs ResearchGate), column count (1 vs 2), and scan resolution (200
vs 300 dpi). They are NOT the class the task anticipated (JSTOR, which ships
a text layer and a terms page); item 5 below reinterprets that request.

## 2. Conversion on HEAD (f1f0d16), `--page-markers`

| | suchman1995 | kostova1999 |
| --- | --- | --- |
| summarize() | `40 pages -> 893 B Markdown` | `19 pages -> 968 B Markdown` |
| Words in Markdown | 185 | 155 |
| PyMuPDF raw text words (native layer only) | 4,155 (40 x the stamp + banner) | 191 (cover) + 18 x 6 (stamps) |
| Words on the page images (Tesseract, --psm 1, all confidences) | 17,550 | 12,010 |
| OCR pages | 0 of 40 | 0 of 19 |

Identical on Windows (no Tesseract) and WSL (Tesseract present): the OCR gate
never opens, so Tesseract's presence is irrelevant. The 185 Suchman words are
the p1 banner (rendered as bold + italic prose); the 39 per-page stamps are
removed by `proc_ignore_common` (correctly). The 155 Kostova words are the
ResearchGate cover, rendered as an h2 title plus "CITATIONS 2,718 / READS
3,585 / SEE PROFILE" paragraphs.

**Forced-OCR diagnostic** (same pipeline, `_ocr_page` called on every page,
native stamps dropped; scratch script only):

| | suchman1995 | kostova1999 |
| --- | --- | --- |
| Words in Markdown | 16,898 (my regex count 16,492) | 11,533 (11,034) |
| Tesseract words | 17,550 | 12,010 |
| Body size detected | 7.9 pt | 7.9 pt |
| SectionHeader blocks | 62 (true headings: ~18) | 27 (true: ~12) |
| Tables emitted | 0 (two real ones missed) | 5 (one real figure, four are shredded prose) |
| Footnotes recovered | 2 of 3 | 2 of 5 |
| Words dropped by the conf<30 filter | 0 on prose pages; 16 on the Figure 1 page, 10 on the Table 1 page (all garbage or rule fragments) | 0-1 per page |

The steady ~6% per-page word deficit on Suchman prose pages is not loss: it is
end-of-line dehyphenation (about 20 joins per page) plus the removed running
head (6 words). Real loss is concentrated on Kostova p2 (580 -> 476) and p15
(743 -> 449); see mechanism B.

## 3. Defects, grouped by mechanism, ranked by damage

Format: page, what the reader sees, what markerlite emitted, stage.

### A. The OCR gate is defeated by the copyright stamp (extract_page) - 100% of body text

- Suchman p2-40, Kostova p2-19: a full page of journal text; emitted nothing
  but `<!-- page N -->`. `extract_page` computes `text_len` over the native
  layer (103 / 38 chars), which is >= 20, so `_ocr_page` is never called.
- Suchman p1: the journal page (title, abstract, first paragraphs, author
  note); emitted only ProQuest's native banner, as `**title** author *journal*
  ... pg. 571`, with the banner's title as bold text and no heading.
- Kostova p2-19 stamp: "Copyright © 1999. All rights reserved." on every
  page; emitted nothing (correct: `proc_ignore_common` removes it). Suchman's
  stamp likewise. This part works and must keep working after the fix.

New. Not in PLAN-tables.md (which is table-only). This one mechanism accounts
for 98% of the missing content in both files.

### B. Justified OCR prose becomes a pseudo-table and loses rows (propose_tables_from_text) - ~400 words, Kostova only

- Kostova p2 right column, "provides us with a theoretical foundation on which
  to examine these questions. Scholars have defined organizational legitimacy
  as ... (Dowling & Pfeffer, 1975; Hannan & Freeman, 1977; ...)": emitted a
  six-column pipe table whose rows are single text lines with words in
  arbitrary cells and with about half the lines missing between rows (104
  words gone on the page).
- Kostova p15, two passages of the Discussion ("...there are certain
  characteristics of MNEs that are different..." and "Clearly, this is just a
  beginning..."): a 5-column and a 7-column pipe table, 294 words gone.
- Kostova p11, Proposition 3: emitted as a 2-column table "| Proposition 3:
  The greater the institu- | |" with the proposition's lines split across two
  cells; words kept but unreadable.
- Kostova p7, Figure 1 (boxed diagram P1-P10 -> challenge to legitimacy):
  emitted as a 4-column table with the running head "1999 | Kostova and
  Zaheer FIGURE 1 | 69" as its header row. Arguably the best available
  rendering of a diagram, but the header row is furniture.

Stage: `propose_tables_from_text`. Tesseract's justified two-column text has
word starts that recur at the same x across enough rows to pass
`_columns_align`, and the reconstruction then keeps only the rows the grid
judge likes. `_table_sane`'s empty-cell test is what drops the rows. The
HEAD text-loss guard does not apply here because this path has no geometric
grid to compare against (noted in commit 62c3ff8).
Related: PLAN item 4 (token-conservation gaps) and item 5 (boxed prose vs
one-column tables) describe the same failure shape for vector PDFs; this is
its OCR-page form and is not listed there.

### C. Heading classification fires on noisy OCR line heights (classify/_is_heading) - ~60 false headings across both

- Suchman p1: "Despite its centrality, however, the literature on
  organizational" (first line of a body paragraph that continues on p2):
  emitted `## Despite its centrality...`. p3 "In this article, I adopt an
  inclusive...": `##`. p4 "legitimation dynamics (cf. Ginzel...)": `##`. p8
  "As was noted previously...": `##`. p33 "This article has attempted to bring
  some coherence...": `#` (h1). Same pattern on ~40 body lines in Suchman and
  ~12 in Kostova (p2 "a whole or at its subunits? ...": `###`; p3 "nature of
  legitimacy, and the process of legiti-": `##`, splitting a paragraph at a
  hyphen; p13 "Proposition 9: ...": `###` while Propositions 1-8 and 10 are
  block quotes).
- Kostova p3, footnote 1 "Currently, the most accepted definition of the
  MNE...": emitted `## 1 Currently, the most accepted...` and its wrapped
  continuation as a body paragraph.
- Suchman p14, Figure 1 cell text ("Continual Influence Character |"):
  emitted as `#`, `##`, `####` headings, one per grid row.
- Real headings mostly survive but with inconsistent levels: "PART I:
  THEORETICAL INTRODUCTION" (p3) is plain text, "PART Il: THREE TYPES" (p9)
  is `###`, "Defining Legitimacy" `###`, "Pragmatic Legitimacy" `##`.

Stage: `classify` -> `_is_heading`, `bigger = size > body*1.06`. On OCR pages
the span size is derived from Tesseract's line box, which swells on any line
with tall ascenders, a superscript, or a speck, so a page shows sizes 5-13 pt
around a 7.9 pt body and single lines clear the 6% threshold. `proc_reflow`
then cannot join the misclassified line to its paragraph, so each false
heading also breaks a paragraph. The `scanned.md` fixture already shows this
(`#### Tables were drawn ... bef-` / `### ore the text-alignment...`); it was
recorded there as an OCR artefact. New as a mechanism; not in PLAN.

### D. Running heads survive when OCR garbles the page number (proc_marginalia) - 6 lines, Suchman

- Suchman p9 "1995 Suchman 579": emitted `## 1995 Suchman $79`. p21 `## 1995
  Suchman §91`, p25 `## 1395 Suchman S95`, p27 `## 1995 Suchman $97`; p30
  "600 Academy of Management Review July" merged into the Table 1 paragraph;
  p38 `## 608 Academy of Review July`. The other ~34 running heads are removed.
- Kostova: all 18 running heads removed (its page numbers OCR cleanly).

Stage: `proc_marginalia`. `_clean_text` strips leading/trailing digit runs,
so "1995 Suchman 579" -> "Suchman" and repeats; "1995 Suchman $79" -> "Suchman
$79" and misses the 90% fuzzy match. Combined with C, the survivor is then
promoted to a heading. New; small.

### E. Rule-less tables and boxed figures on scans are not recovered (detect_tables / propose_tables_from_text) - 2 tables, Suchman

- Suchman p30, Table 1 "Legitimation Strategies" (3 x 4 grid of strategy
  lists with dash sub-items, three horizontal rules only): emitted as one
  run-on paragraph "600 Academy of Management Review July TABLE 1
  Legitimation Strategies Gain Maintain Repair General Conform to environment
  Perceive change Normalize Select environment ..." followed by fragments as
  a block quote and short paragraphs. All words present, structure gone.
- Suchman p14, Figure 1 "A Typology of Legitimacy" (boxed 3 x 2 grid with
  dashed sub-boxes): emitted as headings and fragments (see C); the dashed
  rules OCR as "______", "H 1", "| 2" tokens.

Stage: `detect_tables` finds nothing (a raster has no vector rules);
`propose_tables_from_text` rejects Table 1 (its cells are multi-line lists,
so token starts do not recur row after row) while accepting the prose in B.
This is the mirror image of B and the same fix should address both. PLAN
items 1-4 assume a `find_tables` grid and do not cover scans.

### F. Footnote references and some notes are lost on OCR pages (classify/_is_footnote, render) - 3 notes, refs everywhere

- Suchman p1 author note (unnumbered, small type): emitted as body text
  (acceptable, it is one). Footnotes 2 and 3 (p9, p16) recovered as `[^2]`,
  `[^3]`; note 1 (p4, "1 ... Ashforth & Gibbs") not: it is the same mechanism
  as Kostova's note 1 in C.
- Kostova: notes 3 and 5 recovered; 1 (heading, C), 2 and 4 missing.
- All superscript references in body text: emitted as nothing or as a stray
  digit glued to a word ("strategy.’" p3). Tesseract has no superscript flag,
  so `render` never produces `[^N]` references; the definitions are orphaned.

Stage: classify + render. Known limitation of the OCR path, not previously
written down. Partial fix possible (label matching without the flag); low
priority against A-C.

### G. Provenance / aggregator furniture (extract_page, classify) - 2 pages, cosmetic but misleading

- Kostova p1 (ResearchGate cover): emitted as `## Organizational Legitimacy
  Under Conditions...` followed by "CITATIONS 2,718", "READS 3,585", "SEE
  PROFILE", "The user has requested enhancement of the downloaded file." A
  reader gets a fake h2 title and social-media counts before the article.
  The DOI line is the one thing worth keeping.
- Suchman p1 ProQuest banner: emitted as `**Managing legitimacy...** Suchman,
  Mark C *Academy of Management...* pg. 571`, then (with OCR) the same title
  again as `# MANAGING LEGITIMACY...`. Duplicate title; the "pg. 571" and
  volume/issue are the provenance worth keeping.
- Kostova p19 "View publication stats" (4 pt, ResearchGate footer): emitted
  as a paragraph after the bios in HEAD's output (`Copyright © 1999. All
  rights reserved.` also survives on this page because it is the last line
  and merges with the extra footer text).

Stage: nothing removes them; `classify` promotes the cover title. See item 5.

### H. OCR text quality (Tesseract, outside markerlite) - noted, not a markerlite defect

- Suchman: "jegitimacy" (p19 note), "Piefier" for Pfeffer (p2), "diverge" for
  diverse (p1), "198]" for 1981 (refs), "Carroil". Kostova: "PQ." for P9 in
  Figure 1, "‘Traditionally" (stray quote), "Proposition 7;" (semicolon).
- Suchman p30 Table 1 cells "Conform to dem nds", "—Demons': »ccess": the
  scan itself is broken there (visible in the page image), not the OCR.
- Kostova p3 "strategy.’ As such" - the superscript 1 read as an apostrophe.

At 200 dpi bilevel the recognition is good; roughly one word per page is
wrong. Nothing to fix in markerlite; worth a sentence in the README's OCR
caveat.

## 4. Fixes for the top three mechanisms

### A. OCR gate (extract_page) - recommend immediate implementation

Fix: OCR when the page is dominated by a raster and the native layer is
sparse, instead of when the native layer is nearly empty. Concretely, in
`extract_page`: if any image covers >= 90% of the page area (the same test
`_content_images` already uses to identify a background) and the native
layer has fewer than ~300 characters, call `_ocr_page`. When OCR is used,
drop the native layer: on these files it is a stamp, and on p1 it is the
banner that item 5 will capture separately. Three or four lines, one helper
reused, no interaction with table admission. Suggested constant
`OCR_MAX_NATIVE_CHARS = 300` with the comment that ProQuest and
ResearchGate stamp 38-103 native characters on every scanned page.

Fixture: `scanned_stamped.pdf` = the existing `scanned` generator plus a
per-page native "Reproduced with permission..." line at the foot and a p1
citation banner. Expected output should equal `scanned.md` apart from the
banner. Also add a ResearchGate-shaped cover page variant if item 5 is
approved (see below).

Risk: `images_inline` (full-page background + 1,500 chars of real text) is
above the threshold and unchanged. `isolated_ocr_page` (raster notice page,
no native text) already OCRs and is unchanged. A digital page that is 90%
one figure with a two-line caption (< 300 chars) would now be OCR'd and lose
its native caption for Tesseract's reading of it; I would guard that by
requiring the raster to be bilevel or 1-bit-per-component OR by keeping the
native lines that Tesseract did not also read. Simplest safe version: OCR
only when the covering raster is grayscale/bilevel and the native chars are
below 300. Both scans here qualify (bpc=1).

### C. Heading test on OCR pages (_is_heading) - recommend immediate implementation

Fix: on pages with `ocr_used`, do not accept `bigger` on its own. Require the
bold-only shape rules (numbered, title case, all caps, <= 12 words) for any
OCR block, i.e. treat `bigger` like `bold` there. Real headings in both
papers are all-caps or title case ("Defining Legitimacy", "PART II: ...",
"Cognitive Legitimacy", "CARGILL IN INDIA"), so they survive; body lines and
footnote openers do not. Alternatively derive OCR span size from the median
char height of the line's word boxes rather than the line box, which removes
the noise at its source but touches `_ocr_page`. The first is ~5 lines in
`_is_heading` with a `page.ocr_used` check threaded in from `classify`
(it already has `page`); isolated from tables.

Fixture: `scanned.pdf` already fails this (the `####`/`###` lines around
"bef-"/"ore"); its expected output would change to plain paragraphs, which is
the intended improvement. Add `scanned_twocol.pdf`: a raster of a two-column
page with an all-caps section heading, a title-case subheading, and a
numbered footnote, to lock in that true headings survive.

Risk: `scanned.md` changes (improves). No digital fixture is affected
because the rule is gated on `ocr_used`. Bold-but-not-shaped headings on
scans (rare in journals) would demote to paragraphs.

### B. Pseudo-tables from OCR prose (propose_tables_from_text) - needs a design pass, not a one-liner

Fix, two guards: (1) token conservation: reject a proposed table whose HTML
keeps fewer than `TABLE_FALLBACK_MIN_KEEP` of the words in its source lines
(the guard HEAD applies in `detect_tables` has no counterpart here, and B is
exactly what it would catch: p2 and p15 keep about half). (2) prose rejection:
skip candidates whose lines have a near-constant width equal to a column
measure and whose token count per line varies like justified text
(coefficient of variation of tokens/line > 0.3). Guard (1) is mechanical and
safe; (2) needs tuning against E, where Table 1's list cells must still be
allowed through if the second-chance path is ever to recover them.
Interacts with table admission and with PLAN items 4 and 5, so it belongs in
the tables track after review.

Fixture: `scanned_justified.pdf`: raster of a two-column page set with
`multi_cell(align="J")` so Tesseract sees justified word starts, plus one
rule-less multi-line-cell table (the Suchman Table 1 shape) to keep E
honest. Expect: no pipe table from the prose; the table may stay prose until
E is addressed.

Risk: guard (1) alone cannot regress anything digital (it only rejects
proposals); guard (2) could reject genuine scanned tables with ragged cells,
which is why E's table should be in the same fixture.

Ranked after these: D (strip any digit-bearing token in `_clean_text` for
OCR pages; two lines, isolated; fixture = a scanned running head with a
garbled number), then F, then E.

## 5. The provenance page, reinterpreted

There is no JSTOR page in either file, so the JSTOR detector as specified
would match nothing here. The same need exists in a different shape:

- Kostova p1 is a ResearchGate cover: native text, fixed boilerplate ("See
  discussions, stats, and author profiles for this publication at:
  https://www.researchgate.net/...", "All content following this page was
  uploaded by ... on ...", "The user has requested enhancement of the
  downloaded file."), a citation line ("Article in Academy of Management
  Review · January 1999"), and a DOI line ("DOI: 10.2307/259037").
- Suchman p1 carries a ProQuest banner in the native layer, above the page
  image: title / author / "Academy of Management. The Academy of Management
  Review; Jul 1995; 20, 3; ABI/INFORM Global" / "pg. 571", and every page
  carries "Reproduced with permission of the copyright owner...".

Proposal: one detector, `provenance_page()`, run before OCR in `convert()`,
with three signatures: JSTOR ("JSTOR is a not-for-profit service", "Your use
of the JSTOR archive", "Stable URL:"), ResearchGate (the two boilerplate
sentences above), ProQuest ("Reproduced with permission of the copyright
owner" together with "ABI/INFORM" or "pg. N" on page 1). For a whole-page
match (JSTOR, ResearchGate) drop the page and emit at the top of the
Markdown a comment such as
`<!-- source: ResearchGate cover; Academy of Management Review · January 1999; DOI: 10.2307/259037 -->`
built from the citation line(s) and the Stable URL / DOI. For the ProQuest
banner (a header on a page that also carries content) drop the banner lines
and emit
`<!-- source: ProQuest ABI/INFORM Global; The Academy of Management Review; Jul 1995; 20, 3; pg. 571 -->`.
The per-page stamps keep being removed by `proc_ignore_common`; the detector
should not touch them. Add "View publication stats" to the ResearchGate
signature so p19's footer goes too.

Fixture: `provenance_pages.pdf` with three synthetic covers (JSTOR terms
page, ResearchGate cover, ProQuest banner over a body page) followed by two
body pages; expected output starts with three source comments and no cover
text. Risk: nil to existing fixtures (no fixture contains any of the
signature strings). Isolated from tables; ~40 lines, but it is a new
function rather than a one-line change.

## Order I would implement, if approved

1. A (OCR gate) - the whole document depends on it.
2. C (OCR heading test) - cheap, gated, fixes ~60 false headings.
3. D (garbled running-head numbers) - two lines.
4. 5 (provenance detector) - self-contained.
5. B and E together in the tables track, after PLAN items 4/5 are reviewed.
