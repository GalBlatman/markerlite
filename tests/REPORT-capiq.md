# Capital IQ Key Developments follow-up

The licensed source is read locally as ignored
`tests/real/capiq_keydev.pdf`. Neither the PDF, its supplied Markdown, nor any
document text is committed. Evidence below identifies pages and geometry but
does not reproduce company names, headlines, or the licensed footer.

## B0 — confirmed baseline findings

The PDF has 185 pages. Pages 1–3 are the contents; pages 4–185 contain 47
company sections and 2,325 logical data rows in one continuing four-column
layout.

### B1: section titles are suppressed running heads

On pages 4–185 the only company-level section label is a header-band line at
approximately y=42.7–59.2 pt. There are 47 distinct contiguous runs. Their
page bounds are:

```text
4–7, 8–11, 12–15, 16–19, 20–23, 24–27, 28–31, 32–35, 36–39,
40–43, 44–47, 48–51, 52–55, 56–59, 60–63, 64–67, 68–71,
72–75, 76–78, 79–82, 83–86, 87–88, 89–92, 93–96, 97–100,
101–104, 105–108, 109–112, 113–116, 117–120, 121–124,
125–128, 129–132, 133–135, 136–139, 140–142, 143–146,
147–149, 150–153, 154–157, 158–161, 162–165, 166–169,
170–173, 174–177, 178–181, 182–185
```

Every one is recorded as `proc_marginalia` suppression, including the first
page of each run, so none can become a section heading in the body. Pages 2
and 3 contain two additional header-shaped values from the contents layout;
they are outside the 47 data-section runs.

### B2: hard hyphens are removed at line joins

The rendered/source lines show the named uppercase compounds split after a
printed hyphen: the first appears repeatedly beginning on PDF p. 4, the
vehicle compound appears on p. 26, and the reliability compound appears on
p. 127. Current Markdown removes the printed hyphen from all three. The
lowercase `trans-` / `action` control belongs in the fixture; lowercase
dehyphenation remains the intended behavior.

### B3: fill-backed banners arrive late in stream order

Each section-opening page (pp. 4, 8, 12, …, 182) has a dark banner at
y=137.6–150.0 pt. On every one of the 47 pages its text block is emitted near
the end of the character stream, after all row blocks and immediately before
the running head/footer blocks. The banner therefore renders after the page's
rows. Across the 47 sections, 45 interior banner headings appear with the next
section's content instead of at their own geometric section start; the first
and last are the boundary cases.

### B4: contents entries and page numbers are separate blocks

On pp. 1–3, the 47 contents labels are separate blocks from their page-number
columns. `_demote_toc` only recognizes a run when each individual block ends
in a page number. It therefore sees no qualifying run: the labels remain
headings while the detached number columns render as repeated numeric text.
This is an isolated contents-layout mismatch, but no fix is made in B0.

### B5: current table detection evidence

The region trace records 47 candidates on 47 PDF pages. Forty-five reconstruct
as grids and two keep ordered prose: region 41 on p. 165 has no reconstruction
result, and region 44 on p. 177 reconstructs 212 of 249 member tokens, below
the 0.9 guard. The 45 grids contain 306 reconstructed body rows. This differs
from the brief's 39-page/300-row observation; B5 will reconcile the page and
row definitions rather than changing detection.

## Token baseline

Under the standard content-word metric, both the supplied v0.1.14 Markdown
and the current B0 conversion contain **56,419** words. The native PDF layer
contains 60,392 whitespace tokens. The net difference is 3,973 tokens:
3,872 tokens are in 731 recorded furniture suppressions (running heads,
licensed footers, copyright/footer lines, and page counters), while the
remaining net 101 is explained by lossless line-end joins and Markdown/table
normalization. The multiset comparison is 4,070 source-only occurrences and
97 output-only occurrences. No unrecorded content-loss class was found.

## B1 — sectioned running heads

Committed behavior promotes the first header in a contiguous repeated run
when the document has at least three distinct qualifying run values and each
run lasts at least two pages. The promoted block moves to the beginning of its
source page and renders as a section heading; later copies in the run remain
suppressed. A two-value alternating author/title pattern forms no two-page
run, so ordinary journal furniture is unchanged.

On the real export, `stats["section_heads_emitted"]` records **47** promoted
heads at PDF pages 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60,
64, 68, 72, 76, 79, 83, 87, 89, 93, 97, 101, 105, 109, 113, 117, 121, 125,
129, 133, 136, 140, 143, 147, 150, 154, 158, 162, 166, 170, 174, 178, and
182. Comparing the 47 raw contents lines with the 47 emitted headings gives an
exact ordered match. Table decisions remain 47 total and two fallbacks.

`sectioned_running_heads.pdf` covers three runs of two pages plus a four-page
alternating author/title control. It emits exactly three headings and no
alternating head text. The existing full suite is unchanged: **77/77**
reference and Packet golden entries match, with zero OCR skips, so journal
running heads and Packet B suppression lists retain their exact hashes.

Content words rise from 56,419 to **56,652**, exactly the 233 tokens restored
as one heading per section. Against the 60,392 native tokens, the net
difference is now 3,740: 3,639 recorded furniture tokens plus the same 101
lossless join/markup difference as B0. The multiset comparison is 3,837
source-only and 97 output-only occurrences. No table output or other document
content changed.

## B2 — blocked hard-hyphen trial (uncommitted)

The trial, rather than v0.1.14, introduced the audited
`sector- specific`→`sectorspecific` and `189- 221`→`189221` changes: v0.1.14
kept those particular source lines apart in fallback prose. Independently,
v0.1.14 already emits `Sectorspecific` at other ordinary-body line joins in
the SBTi document. The revised design therefore has to replace the existing
body behavior as well as add consistent handling to tables and fallback
prose.

The requested case rule works on the Capital IQ export but fails its full-
corpus acceptance check. The trial produces zero `FixedIncome` occurrences:
50 `FixedIncome` and seven `Fixed- Income` occurrences become `Fixed-Income`,
and the named vehicle and reliability compounds each gain their printed
hyphen. One additional organization-name compound changes the same way; its
licensed source token is omitted here. In total, 60 Capital IQ lines change.
Content words fall from 56,652 to **56,645**, solely because the seven
reconstructed-table cells turn two whitespace tokens into one. The remaining
53 joins stay one content word. Table and suppression decisions are unchanged.

The blocker is that uppercase continuation is not proof of a hard compound.
The reference and Packet A/B audit invents hyphens in unhyphenated proper
names, including `Mc-Carthy`, `Di-Maggio`, `Mc-Adam`, and `Mac-Millan`.
Applying the rule to fallback prose also removes real lowercase hard hyphens
and hyphens in numeric ranges. The implementation, fixture, and expected file
remain uncommitted, and B3 has not started.

The complete token audit follows. A zero word delta means one output token was
replaced by one token; a negative delta is a newly closed whitespace split.

| Document | Words before→trial | Every changed token (multiplicity where >1) |
|---|---:|---|
| SBTi Target Validation Protocol | 18,425→18,416 | `SBTi- endorsed`→`SBTiendorsed`; `forward- looking`→`forwardlooking`; `sector- specific`→`sectorspecific` (2); `well- to-wheel`→`wellto-wheel`; `“fuel- and`→`“fueland`; `cross- sector`→`crosssector` (2); `use- phase`→`usephase` |
| Greenwood 2006 | 14,773→14,773 | `BadenBaden,`→`Baden-Baden,` |
| Kitchener 2002 | 13,256→13,256 | `AddisonWesley.`→`Addison-Wesley.`; `PrenticeHall.`→`Prentice-Hall.` |
| Peng 2009 | 12,010→12,005 | `soci- ologists`→`sociologists`; `Institu- tions`→`Institutions`; `cog- nitive`→`cognitive`; `stabil- ity`→`stability`; `for- mal`→`formal`; `McCarthy,`→`Mc-Carthy,`; `DiMaggio`→`Di-Maggio`; `PleggenkuhleMiles,`→`Pleggenkuhle-Miles,`; `SouthWestern`→`South-Western` |
| Suchman 1995 | 16,459→16,459 | `227266.`→`227-266.` |
| Wry 2013 | 18,441→18,441 | `OwenSmith,`→`Owen-Smith,` |
| York 2018 | 19,383→19,383 | `GreenSpec`→`Green-Spec` |
| R00030 | 21,285→21,285 | `TrevorRoper`→`Trevor-Roper`; `HowardGrenville`→`Howard-Grenville` (4); `PreColumbian`→`Pre-Columbian`; `Tradition-asConstraint`→`Tradition-as-Constraint`; `Tradition-asResource`→`Tradition-as-Resource`; `CounterEnlightenment`→`Counter-Enlightenment` |
| R00032 | 29,754→29,732 | `Sub- field`→`Subfield` (2); `con- figuring`→`configuring`; `Indus- try`→`Industry` (4); `environ- mental`→`environmental`; `protect- tion`→`protecttion`; `Brid- ging`→`Bridging`; `Self- replicating`→`Selfreplicating`; `Nanotech- nology`→`Nanotechnology`; `Inter- stitial`→`Interstitial` (2); `professiona- lize`→`professionalize`; `Account- ing`→`Accounting`; `Profes- sional`→`Professional` (2); `organization- al`→`organizational`; `Comp- etitive`→`Competitive` (2); `189- 221.`→`189221.` |
| R00063 | 18,441→18,441 | `OwenSmith,`→`Owen-Smith,` |
| R00087 (autonomous and pilot copies) | 21,235→21,235 each | `jurisdictionsGermany`→`jurisdictions—Germany` |
| R00112 | 20,317→20,317 | `SocioEconomics,`→`Socio-Economics,`; `PaavilainenM€antym€aki`→`Paavilainen-M€antym€aki` |
| R00153 | 23,779→23,779 | `RabeHesketh`→`Rabe-Hesketh` |
| R00160 | 19,383→19,383 | `GreenSpec`→`Green-Spec` |
| R00293 | 16,605→16,597 | `algorith- mic`→`algorithmic`; `for- mula.`→`formula.` (2); `docu- ments`→`documents`; `sub- sidiary`→`subsidiary`; `algo- rithmic`→`algorithmic`; `al- most`→`almost`; `ac- tual`→`actual` |
| R00359 | 14,773→14,773 | `BadenBaden,`→`Baden-Baden,` |
| R00373 | 13,749→13,749 | `McAdam`→`Mc-Adam`; `DaimlerBenz,`→`Daimler-Benz,`; `MacMillan,`→`Mac-Millan,`; `Lopez-deSilanes,`→`Lopez-de-Silanes,` |
| R00443 | 16,304→16,304 | `197185.`→`1971-85.`; `coFollowing`→`co-Following`; `JosseyBass.`→`Jossey-Bass.`; `19191979.`→`1919-1979.` |
| R00446 | 13,068→13,068 | `DavisPolk's`→`Davis-Polk's`; `MarkbamBugbee`→`Markbam-Bugbee`; `JosseyBass.`→`Jossey-Bass.` |
| R00639 | 17,063→17,063 | `PrenticeHall.`→`Prentice-Hall.` |
| R00717 | 15,249→15,249 | `K€uberlingJost`→`K€uberling-Jost` (3); `KishGephart`→`Kish-Gephart` (2); URL `Survey2020`→`Survey-2020` |
| R00860 | 18,122→18,100 | `215254.`→`215-254.`; `prac- tice`→`practice`; `theoriza- tion`→`theorization`; `man- agement`→`management` (2); `evalua- tors`→`evaluators`; `Aus- tin`→`Austin`; `communica- tion`→`communication`; `recog- nize`→`recognize`; `en- dorsement`→`endorsement`; `num- ber`→`number`; `manage- ment`→`management`; `authori- zation`→`authorization`; `support- ed`→`supported`; `influ- ential`→`influential`; `per- sons`→`persons`; `de- velopment`→`development`; `inevi- table`→`inevitable`; `favoura- ble`→`favourable`; `enti- ty`→`entity`; `Green- wood`→`Greenwood`; `story- telling`→`storytelling` (2) |
| R00014 | 20,663→20,661 | `SahlinAndersson`→`Sahlin-Andersson`; `journals*American`→`journals—*American`; `Neo- institutionalism`→`Neoinstitutionalism`; `taken- for-granted`→`takenfor-granted` |
| R00023 | 17,010→17,006 | `FerronVilchez`→`Ferron-Vilchez`; `ZaragozaWatkins`→`Zaragoza-Watkins`; `3370- 3381.`→`33703381.`; `1227- 1253.`→`12271253.`; `298323`→`298-323`; `Multi- Governmental`→`Multi-Governmental`; `Multi- governmental`→`Multigovernmental` |
| R02659 | 19,475→19,470 | `govern- ment's`→`government's`; `investi- gating`→`investigating`; `govern- ment`→`government`; `offi- cials`→`officials`; `partic- ularly`→`particularly` |
| R05732 | 15,612→15,612 | `RoseAckermann,`→`Rose-Ackermann,` |

## B2 revised — blocked by no-evidence lowercase compounds (uncommitted)

The revised implementation uses one whole-document evidence resolver in body
text, reconstructed table cells, fallback prose, and footnotes. Each rendered
line-break decision records its page, fragments, hyphenated and joined forms,
both non-break evidence counts, rule, and action in `stats["dehyphenation"]`.
The fixture covers document-hyphenated, document-joined, numeric-range,
default-join, and default-capitalized-compound decisions in prose and a ruled
table; a unit-level fallback-prose check exercises the same resolver.

The Capital IQ result passes the requested checks. Its 60 decisions comprise
58 `document-hyphenated` keeps and two
`default-capitalized-compound` keeps. It has zero `FixedIncome`; the named
vehicle and reliability compounds and the additional organization-name
compound are correct. The Markdown changes are the same 60 lines listed in
the first trial, and content words remain 56,645 because seven table-cell
spaces close.

The reference audit confirms that document evidence fixes the false surname
hyphens from the first trial: `McCarthy`, `DiMaggio`, `McAdam`, and
`MacMillan` all use `document-joined`. The numeric split on R00032 p. 94 uses
`numeric-range` and becomes `189-221`, never `189221`.

The revised rule nevertheless fails its correctness requirement on R02027.
This PDF has lowercase hard compounds which occur only at their line breaks,
so rule 3 requires an incorrect join:

| Page | Source break | Trial output | Evidence `(A-B, AB)` | Rule | Finding |
|---:|---|---|---:|---|---|
| 19 | `labor-` / `movement` | `labormovement` | `(0, 0)` | `default-join` | Incorrect; the rendered phrase is the compound modifier `labor-movement institutions`. |
| 39 | `business-to-` / `business` | `business-tobusiness` | `(0, 0)` | `default-join` | Incorrect; the rendered phrase is `business-to-business applications`. |

The same newly reached bold-line path also treats equation fragments on pp.
30, 31, and 36 as prose continuations (`t-00O`→`t00O`, `I-0`→`I0`,
`t-C`→`tC`, and `1-C`→`1C`). Those are not correct word repairs. These
findings make the revised B2 acceptance impossible under the specified rule
set without another exception or evidence source. The revised implementation
and fixture remain uncommitted. B3, B4, and B5 have not started.

### Amended symbol rule and second full audit

None of the six named failures is identical to v0.1.14. The exact v0.1.14
outputs are `labor-** **movement`, `business-to-** **business`, `t-** **00O`,
`I-** **0`, `t-** **C`, and `1-** **C`. The revised implementation reaches
these line breaks for the first time, so all six are changes relative to the
release baseline rather than pre-existing joins left unchanged.

The amended rule runs immediately after the numeric-range rule and keeps the
hyphen when either fragment contains a digit or is one character long. It
therefore repairs all four symbol cases to `t-00O`, `I-0`, `t-C`, and `1-C`.
Their audit records use `symbol-fragment` with action `keep`. The two lowercase
compounds still follow `default-join` and become `labormovement` and
`business-tobusiness`.

The second complete audit converted all 77 golden-manifest entries. Thirty-five
entries changed, comprising 1,107 normalized token-difference groups. Most are
correct soft-hyphen repairs, and document evidence correctly joins the tested
`McCarthy`, `DiMaggio`, `McAdam`, and `MacMillan` splits. The numeric split on
R00032 p. 94 remains `189-221`. The audit also found changes that are not
correct repairs:

| Document | v0.1.14 output | Revised output | Rule | Finding |
|---|---|---|---|---|
| R02027 p. 19 | `labor-** **movement` | `labormovement` | `default-join` | Drops the hyphen in `labor-movement institutions`. |
| R02027 p. 39 | `business-to-** **business` | `business-tobusiness` | `default-join` | Drops the hyphen in `business-to-business applications`. |
| R00153 | `UK- based` | `UKbased` | `default-join` | Drops the hyphen in a compound modifier. |
| R00443 | `organization-year- program` | `organization-yearprogram` | `default-join` | Drops the final compound hyphen. |
| R00023 | `LEED- certified` | `LEEDcertified` | `default-join` | Drops the hyphen in a compound modifier. |
| R00446 | `DavisPolk's` | `Davis-Polk's` | `default-capitalized-compound` | Inserts a hyphen into the name Davis Polk. |
| R00446 | `MarkbamBugbee` | `Markbam-Bugbee` | `default-capitalized-compound` | Inserts a hyphen into an OCR-damaged name. |

Other no-evidence joins include `Neo- institutionalism` to
`Neoinstitutionalism` in R00014 and `ID- Establishment` to `IDEstablishment`
in S0009. These are also changes relative to v0.1.14, so the amended blocker
condition is not met. No golden output was re-baselined. The implementation,
fixture, tests, and this audit remain uncommitted; B3, B4, and B5 remain
unstarted.

### B2 final attempt — rejected by the full audit

The final design treated v0.1.14's join decision as an immutable base. It
never reached a line break that v0.1.14 left split, including every
bold/italic seam. At an existing join it could only restore the hyphen for a
numeric range, a fragment containing a digit or consisting of one character,
or a form found hyphenated elsewhere in the document and never found joined.
The uppercase default was removed.

The network-enabled focused run passed **4/4** tests. The full audit converted
all **77** golden-manifest entries. Every Markdown difference was a v0.1.14
join changed back to a hyphenated form; no new join or formatting-seam change
occurred. It found 294 token-difference groups in 33 manifest entries. Most
were correct repairs supported by document evidence or numeric ranges, but
the symbol-fragment rule still made an incorrect change: Jay 2013 and its
R00258 Packet copy changed the correctly joined OCR token `Bail)m` to
`Bai-l)m`. The same broad rule also changed components inside URLs. This is
the specified stop condition, so B2 is rejected rather than tuned again.

The seven named regressions from the preceding trial are byte-identical to
v0.1.14 in the final attempt: `UKbased`, `LEEDcertified`,
`organization-yearprogram`, `Davis-Polk's`, `Markbam-Bugbee`,
`labormovement`, and `business-tobusiness` are not introduced. The four
bold-seam cases likewise retain their exact v0.1.14 Markdown.

On Capital IQ the attempt has 56,652 content words, unchanged from B1. It
repairs all 50 `FixedIncome` joins using document evidence and repairs the
second `OrlenSynthos` occurrence because `Orlen-Synthos` appears elsewhere.
The no-evidence joins remain known limitations: `VehicleTo-Everything` and
`MissionCritical`. No Capital IQ table decision or furniture suppression
changes.

No golden baseline is updated. The B2 implementation, fixture, and tests are
discarded. A bundled word list is required before another general
dehyphenation attempt.

## B3 — fill-backed banner placement

The exception is based on drawing evidence rather than vocabulary. Extraction
marks text whose box is at least 80% covered by a filled band spanning at
least half the page width with mean RGB luminance at most 0.5. The marked
block is excluded from table membership. After tables, continuations,
captions, and figures are complete, it moves immediately before the first
surviving block geometrically below it. No other block moves relative to
another, so PDF stream order remains the default.

`late_banner.pdf` draws two records first and its dark section banner last.
The expected Markdown places `Current Records` between the filter and the
table heading while retaining both records in order.

On Capital IQ, all 47 section-opening pages contain the same dark band at
y=134.0–153.5 pt and its text at y=137.6–150.0 pt. Before B3, 45 banner
headings survived but appeared after their own rows; two were consumed by a
table candidate. After B3, all 47 render on their source page above the rows
they introduce. The 45 existing headings are pure moves. The two restored
headings replace the same words formerly embedded in table output, so content
words remain **56,652** and the Markdown line multiset changes only where
those two tables represent their rows.

The full 77-entry audit has zero Markdown differences and zero stats-hash
differences from the B1 baseline. The complete fixture regression, including
the new negative, passes.

## B4 — detached contents columns

The failure is isolated. A contents page is recognized only when at least five
right-column numeric lines begin beyond 75% of page width and at least 80% of
them pair one-to-one with left-column lines at the same vertical position
(within 2 pt). Each pair becomes one `TocEntry`; the original relative order
is retained. The contents heading, when it was drawn late, moves immediately
before those entries. `TocEntry` blocks count as page body for marginalia
bounds but are never themselves furniture candidates, so a first entry in the
header band survives while repeated footers do not.

`split_toc_columns.pdf` covers six bold labels emitted first, six detached
numbers emitted afterward, a late body paragraph, and the contents heading.
It renders one heading, six ordered list entries with their page numbers, then
the paragraph.

Capital IQ pp. 1–3 now render **94 ordered contents entries**: the company and
its corresponding report entry each retain their printed page number. The
standalone number columns and the 47 heading-shaped compound blocks are gone,
and the repeated licensed footer remains suppressed. Content words rise from
56,652 to **56,754**. Of the 102-token metric change, 94 are Markdown list
markers counted by the standard metric; the other eight are fragments and
page numbers from two entries that the old cross-page continuation had lost.
No source token is removed.

The full 77-entry audit has zero Markdown and stats differences from B3; no
existing golden document contains this detached-column pattern.
