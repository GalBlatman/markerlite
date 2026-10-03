# Block 2 table evidence: inventory and region labels

Two evidence sets for the block 2 plan (tests/PLAN-tables.md). Neither
reproduces document text.

1. A deduplicated inventory of table defects by mechanism, compiled from the
   Unknown Knowns v0.1.14 audit (pipeline PR GalBlatman/unknown-knowns#8,
   read in place in the audit worktree), Packet A and the Run-2 (A2)
   re-inventory, and this repository's reports. It reflects the audited
   versions (v0.1.12 and v0.1.14); the v0.1.15 status of each mechanism is
   measured separately by the region labels and the gold set.
2. `tests/block2-region-labels.json`: every table region v0.1.15 emits on 55
   unique files (the ten reference documents, R02027, the 25-PDF gate, the
   Run-2 documents, Capital IQ sampled), labelled against the rendered page,
   with the evidence features the confidence gate uses.

## Part 1. Inventory by mechanism

Research inventory compiled 2026-10-02 from the v0.1.14 audit worktree (`/home/galbl/unknown-knowns-markerlite-v0114`, pipeline PR #8, read in place) and the markerlite repository reports. Nothing was converted or rerun; every statement is taken from the named source. Content is identified by document id, page and a short structural description only. Capital IQ text is not quoted.

Source abbreviations (worktree paths are relative to the worktree root):

| Abbreviation | File |
| --- | --- |
| PacketA.json (section) | upstream/markerlite-v0.1.12-PACKET-A-table-structure.json (and .md twin); key = section, row_id, page |
| packet-a-status.json | pilot/markerlite-bump-v0114/packet-a-status.json; key = cases[].status |
| material-adjudication.json (MA) | pilot/markerlite-bump-v0114/material-adjudication.json; key = pages[].adjudication |
| cell-fallback-policy.json | pilot/markerlite-bump-v0114/cell-fallback-policy.json; key = pages[].marker_status |
| visual-review-gate25.json / -run2.json | pilot/markerlite-bump-v0114/visual-review-*.json; key = records[].table_checks, material_issue |
| run2-diagnostic.json | pilot/markerlite-bump-v0114/run2-diagnostic.json; key = new_regressions, a2_regressions_vs_e419550 |
| wrapper-diff-audit.md | pilot/markerlite-bump-v0114/wrapper-diff-audit.md (token-check and guard firings) |
| v0.1.14 *.stats.json table_fallbacks | pilot/markerlite-bump-v0114/{candidate,run2}-v0.1.14-noguard/<doc>.stats.json; key = table_fallbacks[] (hook, page, tokens_missing) |
| A2 defect_pages / other_table_events / suppression_finding | pilot/markerlite-bump-v0112/RUN2-TABLE-REINVENTORY-v0112.json (frozen A2 inventory, commit 3d9a06f) |
| PLAN-tables.md, REPORT-*.md, CLAUDE.md | C:\Users\galbl\markerlite\tests\ and repo root |
| SBTi | tests/real/Target-Validation-Protocol.pdf (PDF pages) |
| CapIQ | tests/real/capiq_keydev.pdf (licensed; text never quoted) |

Document aliases used by the repo reports: R00063 = Wry et al. 2013; R00160 = York et al. 2018; R00258 = Jay 2013; R00359 = Greenwood & Suddaby 2006; R00754 = Peng et al. 2009. Their repo-report pages are merged into the R-id rows.

e419550 = the historical converter (Run 1/Run 2 path). 'B-NEW' = new structural regression vs e419550 (blocks adoption); 'B-KNOWN' = also in e419550, v0.1.14 not worse; 'A' = policy-level improvement (ordered prose, no false grid). These labels come from packet-a-status.json.

### 1. Mechanisms

Twenty mechanisms, deduplicated by root cause. Each has exactly one outcome class. Page lists are in section 2; the counts are in section 3.

| ID | Mechanism | Stage | Root cause | Outcome | Pages | In e419550? | Status at v0.1.14 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | Figure or diagram admitted as a table | find_tables candidate admission (detect_tables) and propose_tables_from_text | Box-and-arrow diagrams, path diagrams and 2x2 design figures have labels that align into columns (or sit in ruled boxes), so they pass candidate admission; nothing tests for a figure before a grid is built. The grid pairs labels from unrelated boxes by vertical position. | FALSE GRID | R05732 p11; R00263 p8; R00263 p23; R00860 p60; R00860 p61; R00717 p9; R00153 p19; R00263 p9; R00831 p8; R02055 p7; R02611 p11; R02611 p12; R04077 p45; Kostova 1999 p7 | Yes on R00263 p8/p23, R00860 p60/p61, R00717 p9, R02611 p11 (grids identical to e419550). No on R02055 p7 and R02611 p12 (new grids). | Open. Packet A pages B-KNOWN (packet-a-status.json). R02055 p7 MATERIAL-NEW, blocks adoption (material-adjudication.json). Kostova Fig. 1 still a successful proposal (REPORT-batchC-block1.md step 3). Lossy variants (R00153 p19, R00263 p9, R00831 p8, R04077 p45) are hidden in v0.1.14 reading copies by the downstream token-check hook. |
| M02 | List-like text proposed as a 2-column grid | propose_tables_from_text (_columns_align) | Reference lists, numbered endnotes, propositions and hanging-indent entries have recurring x-starts (numbers, years, indents), so the column-alignment test accepts them; the first entry becomes the header row and each entry's year or number becomes column 1. | FALSE GRID | R00063 p37; R02190 p16; R07771 p16; R07771 p17; R07771 p18; R07771 p19; S0009 p17; Kostova 1999 10 or 11; Kitchener 2002 26 or 28 | Yes on R02190 p16, R07771 p18 (identical). No on R00063 p37 (e419550 emitted one paragraph). | Open. R00063 p37 STRUCTURAL-NEW, blocks (run2-diagnostic.json). PLAN item 4 proposes rejecting the numbered-reference pattern; not implemented. |
| M03 | Body prose or page layout captured into a table region | find_tables text/lines strategy; OCR text proposals on justified prose; candidate extent | Justified or two-column body text gives word gaps or column gutters that look like column cuts, or a real table's candidate extends over neighbouring body columns, headings and the caption. The page layout becomes the grid. | FALSE GRID | R00293 p8; R00754 p2; SBTi p43; SBTi p45; Kostova 1999 p2; Kostova 1999 p15 | Yes on R00293 p8 (identical to e419550). Not assessed for SBTi and Kostova (not pipeline documents). | Partly mitigated. Most such candidates now fail reconstruction and become fallback prose (then M05). R00293 p8 still a false grid (B-KNOWN). Kostova p2/p15 kept as prose by the interim justified_scan guard (CLAUDE.md). PLAN item 5 marked not needed after fallback-to-prose. |
| M04 | Single-row line-band grids from a text-table proposal | propose_tables_from_text on derotated R00087 Table 1 pages | In an unruled 4-column text table, a row whose author cell has a year-only second line beside three single-line bullets passes the column test on its own. A 2-column grid is emitted for that row alone: the year is paired with a bullet, the author name stays in prose above, and the next row's author is appended to the previous row's findings. | FALSE GRID | R00087 p12; R00087 p13; R00087 p15; R00087 p10 | No. e419550 emitted every row in order as prose with no grid. | Open and new. R00087 p10 MATERIAL-NEW; p12, p13, p15 STRUCTURAL-NEW; all block adoption (material-adjudication.json, run2-diagnostic.json). |
| M05 | Fallback marker on non-table content | detect_tables admission + text-loss guard + fallback-to-prose (commit 2103350) | A candidate admitted over references, double-spaced body text, or figure boxes fails reconstruction; the guard keeps its source lines as prose under `<!-- table p. N: reconstruction failed -->`. The marker asserts a table that does not exist. The block also keeps raw hard-wrapped lines (one-line paragraphs, unjoined line-end hyphens, '&amp;'). | FALSE MARKER | R05732 p11; R00023 p3; R00023 p7; R00023 p9; R00023 p11; R00023 p12; R00023 p22; R00023 p24; R00023 p27; R00023 p28; R00023 p34; R00023 p38; R00023 p39; R00023 p40; R00023 p41; R00023 p42; R00023 p45; S0004 p1; R00030 p70; R00032 p85; R00032 p86; R00032 p87; R00032 p88; R00153 p17; R00153 p21; R00293 p10; R00293 p15; R00293 p17; R00754 p2; R02659 p1; SBTi p45 | No marker in e419550 (class created by 2103350); the same candidates were cell-text fallback grids that the project guard reverted. | NON-MATERIAL per material-adjudication.json; 27 non-table pages in the v0.1.14 reading copies (cell-fallback-policy.json). Two more front-matter fallbacks (S0004 p1, R02659 p1) exist in raw upstream output; the downstream title-zone hook removes their markers. |
| M06 | Wrapped lines emitted as separate grid rows | table_recon reconstruction (row bands from printed baselines) + table_wrap wrapped-line recovery | Rows are cut at every printed baseline. Wrapped-line recovery only fires on complete geometric rows or short-key row starts (and not on numeric-transition tables), so multi-line cells and multi-line headers become one grid row per printed line; a logical row is split across 2-16 grid rows. | WRONG ASSOCIATION | R00077 p8; R00077 p32; R00112 p7; R00112 p14; R00112 p15; R00112 p24; R00263 p15; R00263 p20; R00639 p28; R00639 p29; R00315 p12; R00894 p8; R02611 p18; R05732 p4; R05732 p7 | Yes on R00112 p7, R00639 p28/p29, R00315 p12, R00894 p8, R05732 p4/p7. No on R00077 p8/p32, R00112 p14/p15, R00263 p15/p20 (e419550 had prose there). | Open. CLAUDE.md known defect 1. R00077 p8/p32, R00263 p15/p20 STRUCTURAL-NEW; R00112 p14/p15 MATERIAL-NEW (combined with M09). Wrapped header rows remain open since v0.1.12 (REPORT-v0.1.12.md, R02611 p18). |
| M07 | Rows collapsed into one row or columns fused into one cell | table_recon reconstruction (row/column cut search), often on derotated sparse regression or correlation tables; v0.1.12 cell-text fallback grids | When row cuts are not found the whole body is packed into one row (often the Markdown header): all variable labels in one cell, each model's coefficients stacked in one cell, empty cells dropped so values shift. When column cuts are missing, several columns are fused. In v0.1.12 the PyMuPDF cell-text fallback produced the same one-data-row shape. | WRONG ASSOCIATION | R00014 p6; R00014 p18; S0004 p6; S0004 p20; R00160 p12; R00373 p13; R00112 p7; R00112 p24; R00160 p14; R00160 p15; R00373 p14; R00359 p7; R00359 p10; R00315 p15; R05732 p4 | No on R00373 p13, R00160 p14 (e419550 kept label-to-value rows). Partly on R00160 p15 (e419550 merged one row, v0.1.14 four). Yes on R00112 p7, R00315 p15. R00373 p14: e419550 had a different (transposed) wrong grid. | Open. R00373 p13, R00160 p12/p14/p15 MATERIAL-NEW, block adoption. The v0.1.12 cell-text fallback shape (R00014 p6/p18, S0004 p6/p20) is gone: those are now fallback prose (M14). |
| M08 | Header misplaced | header-band detection in table_recon (_find_header_band) and candidate extent | The printed header lies outside the candidate or is not recognised as one band, so it is emitted as bold prose or '####' headings above the grid and the first data row takes the Markdown header slot; spanning headers are flattened into one column; a source header printed one column off is copied verbatim. | WRONG ASSOCIATION | R00160 p12; R00263 p5; R00063 p46; R00063 p47; R00077 p32; R00112 p14; R00112 p24; R00160 p15; R00263 p20; R00373 p14; R00263 p22; R00531 p6; R00315 p15; R00894 p8; R01114 p8; R02027 p22; R02027 p25; R02027 p34; R02659 p13; R05732 p4; S0009 p6; S0009 p13; S0009 p15; S0009 p23; SBTi p14; SBTi p58 | Yes on most pages (R00063 p47, R01114 p8, R02027 p22/p25/p34, S0009 p6/p13/p15/p23, R00263 p22, R00531 p6). No on R00160 p12, R00263 p20 (e419550 had no grid). | Open. R00063 p46 counted RESOLVED (correct grid) despite the flattened spanner. R00160 p12 MATERIAL-NEW; R00263 p20 STRUCTURAL-NEW. |
| M09 | Stacked panels merged, or row-label column fused into the first data column | table_recon column cuts and row grouping | Centred panel spanners (TEMPO/RECRUIT, FORWORK/NOWASTE, Banking/Healthcare field) and group labels are treated as text of the previous cell, so two sub-tables become one grid. When no cut separates the row-label column from the first period column, labels and values share one cell. | WRONG ASSOCIATION | R00112 p17; R00112 p14; R00112 p15; R02611 p25; S0009 p13; S0009 p15; S0009 p23 | No on R00112 p14/p15/p17 (e419550 emitted prose). Yes on S0009 p13/p15/p23. R02611 p25 better than e419550. | Open. R00112 p14, p15, p17 MATERIAL-NEW, block adoption. |
| M10 | One table split into several partial grids plus prose | page-local candidates and text proposals covering only parts of a table | Detection covers only some row bands (rule segments, proposal blocks); each part is emitted as its own headerless grid and the rows between are unmarked prose, sometimes with labels spliced into sentences. | WRONG ASSOCIATION | R00263 p5; R00112 p24; R00160 p15; R00263 p15; R00639 p28; R00639 p29; R00531 p6; R00315 p15; R01114 p8; R02027 p22; R02027 p34; S0009 p6; S0009 p13; S0009 p15; SBTi p40 | Yes on R00639 p28/p29, R00531 p6, R01114 p8, R02027 p22/p34, S0009 p6/p13/p15, R00315 p15, R00160 p15 (identical fragmentation). R00263 p5: e419550 had a different wrong grid. | Open. Mostly B-KNOWN or PRE-EXISTING. R00263 p15 (header-only grid, body prose) STRUCTURAL-NEW. |
| M11 | Table cells or rows detached from the table | candidate row extent; proc_footnotes / classify on lines outside the table region; fallback prose order | A final row or wrapped cell outside the candidate is emitted after the grid; dagger-bulleted cells and numbered row labels of undetected tables are reclassified as footnote definitions (`[^†]:`, `[^17]:`, `[^n1]:`); a fallback block emits one column after all rows. | WRONG ASSOCIATION | R00263 p5; R00860 p58; R00087 p12; R00087 p13; R00153 p33; R00446 p10; R00446 p13; R00112 p8; R00087 p9; R02659 p10; S0009 p23 | No on R00087 p9/p12/p13, R02659 p10, R00446 p13, R00112 p8 (e419550 kept the cells inline). Yes or similar on R00446 p10, R00153 p33, R00860 p58 (trailing line), S0009 p23. | Open. R00860 p58 STRUCTURAL-NEW; the footnote relocations are NON-MATERIAL 'representation obstacles' (run2-diagnostic.json). |
| M12 | Cross-page table not joined | detection is page-local; no continuation joining or repeated-header merging | A table that continues over pages is emitted as independent page-local pieces (grid on one page, prose or another grid on the next), with the header repeated or missing on continuation pages. | WRONG ASSOCIATION | R00063 p47; R00077 p32; R00160 p15; R00263 p20; R00032 p93; R00032 p94; SBTi p7; SBTi p8; SBTi p9; SBTi p10; SBTi p38; SBTi p39; SBTi p40; CapIQ 4-185 (47 sections) | Yes (e419550 is also page-local). | Open. PLAN item 2 records cross-page joining and repeated-header merging as future work (Capital IQ, REPORT-capiq.md B5). |
| M13 | Caption displaced or fused | caption isolation (_isolate_table, v0.1.12) handles only a leading caption inside the candidate; proc_captions attaches later | Captions end up inside a grid cell, after the table, at the page end ('Table N (continued)'), fused with header cells, or run into the table's prose. | WRONG ASSOCIATION | R00063 p46; R00293 p8; R00639 p23; R00023 p49; R02611 p18; R02611 p25; R05732 p6; S0004 p7; S0004 p8; S0004 p9; S0004 p10; S0004 p17; S0004 p19; S0004 p11; S0004 p12; S0004 p18 | Yes on most pages; R02611 p18 caption-in-grid fixed in v0.1.12 (REPORT-v0.1.12.md). | Open for the listed pages; minor except R00293 p8 (caption inside a false grid). |
| M14 | Failed reconstruction kept as prose: real table layout lost | text-loss guard (TABLE_FALLBACK_MIN_KEEP 0.9) / no reconstruction -> fallback_paragraphs (2103350) | When reconstruction fails or keeps < 0.9 of the geometric cells' words, the region's source lines are emitted in stream order. Words survive, but rows and columns are not marked; stream order can be column-major within row bands, so row association must be inferred. The rule is blanket: usable grids are sacrificed too. | MISSED TABLE | R00014 p6; R00014 p18; S0004 p6; S0004 p20; R00023 p47; R00112 p24; R00032 p94; R00153 p12; R00219 p65; R00293 p12; R00359 p7; R00359 p10; R00754 p2; R00112 p8; R00023 p49; R02659 p12; R02659 p13; SBTi p3; SBTi p11; SBTi p12; SBTi p13; SBTi p16; SBTi p17; SBTi p20; SBTi p22; SBTi p25; SBTi p26; SBTi p29; SBTi p34; SBTi p36; SBTi p43; SBTi p44; SBTi p45; SBTi p46; SBTi p47; SBTi p48; SBTi p49; SBTi p53; SBTi p55; SBTi p60; SBTi p61; SBTi p62; SBTi p63; CapIQ 165; CapIQ 177 | e419550's project token-check also reverted such tables to unmarked prose; v0.1.12 emitted cell-text fallback grids (Packet A A1). | By design and accepted under section 6 (cell-fallback-policy.json: 48/48 acceptable, markers on all 19 real failed tables). SBTi: 30 of 55 regions, including 5 usable grids lost (REPORT-batchC-block1.md). |
| M15 | Real table not detected | find_tables needs ruling lines; propose_tables_from_text rejects multi-line cells; proposals kept as prose (TABLE_FALLBACK_MIN_KEEP / justified_scan) | Rule-less, lightly ruled, scanned, rotated or continuation tables produce no candidate (or a proposal that is kept as prose), so the table is unmarked prose: rows glued to the previous row, column-major dumps, header rows as headings. | MISSED TABLE | R00639 p23; R00153 p33; R00153 p34; R00219 p55; R00373 p15; R00446 p10; R00446 p12; R00446 p13; R00446 p14; R00860 p57; R00263 p10; R00263 p11; R00263 p12; R00263 p16; R00263 p17; R00263 p18; R00087 p9; R00087 p14; R02659 p8; R02659 p10; S0004 p7; S0004 p8; S0004 p9; S0004 p10; S0004 p17; S0004 p19; SBTi p7; SBTi p8; SBTi p9; Suchman 1995 p30; CapIQ data pages without a detected region (inferred 135) | Yes on nearly all listed pages (identical or similar prose). S0004 p7-p10: v0.1.14 glues more row starts than e419550. | Open. NON-MATERIAL or PRE-EXISTING in material-adjudication.json. |
| M16 | Large candidate rejected by the page-area rule | detect_tables rejects candidates with area > 0.6 x page area | Full-table candidates on SBTi criteria pages cover about 0.61-0.63 of the page and are rejected; fragment candidates survive, and PyMuPDF also proposes spurious 13-19-column grids on these 3-column pages. | MISSED TABLE | SBTi p13; SBTi p26; SBTi p34; SBTi p10; SBTi p14; SBTi p38; SBTi p39 | Not assessed (SBTi is not a pipeline document). | Open. PLAN item 2 (structural-evidence exception to the 60% rule). |
| M17 | Lossy reconstruction accepted | reconstruction passing the 0.9 guard; propose_tables_from_text has no geometric reference | A grid that keeps >= 0.9 of member words passes the guard and silently drops the rest; on the proposal path there is no guard. In v0.1.14 the downstream token-check hook catches 14 such grids in the gate and 12 in Run-2 (wrapper-diff-audit.md); markerlite's own output still drops the words. | LOST TEXT | S0004 p20; R00030 p75; R00032 p89; R00153 p35; R00160 p22; R00160 p23; R00258 p6; R00359 p11; R00373 p12; R00087 p10; R00153 p19; R00263 p9; R00831 p8; R01285 p16; R02659 p14; R04077 p45; R05732 p6; R05732 p7; R05732 p10; R07771 p16; R07771 p17; R07771 p19; S0004 p11; S0004 p12; S0004 p18; S0008 p3; S0009 p17; SBTi p26; Kostova 1999 p2; Kostova 1999 p15 | e419550's project token-check reverted these to prose, except R05732 p7 (wrapped line lost in e419550 too). R00087 p10 'U.S.' kept by e419550. | Open. R00087 p10 MATERIAL-NEW. PLAN item 4 (token identity across both detection paths) not implemented. |
| M18 | Sideways region on an upright page dropped | extract_page tilt filter (page vertical share < ROTATED_PAGE_MIN_FRAC 0.8) | A quarter-turned table on a mostly upright page is neither turned nor kept: every sideways line is dropped. | LOST TEXT | R00443 p16 | Disputed: Packet A says v0.1.12 is worse (e419550 kept partial fragments); packet-a-status.json says identical to e419550. | Open, owner-ruled limitation (B-KNOWN). PLAN item 12 (rotate the region). lossy_pages disagreement, see below. |
| M19 | Table rows, headers or labels lost as furniture or label lines | proc_marginalia / proc_ignore_common (v0.1.12); separate label lines | Edge-band and repeated-line passes removed table header rows on continuation pages and last data rows at the page edge; separate 'TABLE N' label lines and a continuation caption were dropped. | LOST TEXT | R00014 p6; R00014 p18; R00263 p15; R00263 p20; R00263 p17; R02659 p8; S0004 p7; S0004 p8; S0004 p9; S0004 p10; S0004 p19; S0004 p11; S0004 p12; S0004 p18 | Header/row suppressions: no (e419550 emitted them). Label loss on R00014: yes (e419550 also lost them). | Fixed at v0.1.14 (Packet B 44/44, commit 702607d; R00014 labels present in v0.1.14 per packet-a-status.json). |
| M20 | Glyph loss inside table cells | extract_page text layer (pi fonts, publisher OCR layers, Tesseract) | Minus signs, '<', '=', '+', chi and rho are dropped or substituted ('5', '1', ','); scanned layers garble counts and words. The table's numbers change meaning without any word-count signal. | LOST TEXT | R00263 p5; R00373 p13; R00112 p7; R00373 p14; R00639 p28; R00153 p35; R00258 p6; R00373 p12; R00639 p23; R00373 p15; R00531 p6; R00112 p8; R00263 p10; R00263 p11; R00263 p12; R00263 p17; R00315 p12; R00315 p15; R02027 p34 | Yes (identical in e419550 on every listed page). | Open, B-KNOWN / source-layer. Pi-font repair (5115e54) fixed York (R00160) but not R00373. |

Cross-cutting observation (not a separate mechanism): 11 of the 17 B-NEW pages carry `derotated: true` in PacketA.json upstream_state (R00077 p32; R00087 p10, p12, p13, p15; R00112 p14, p15; R00160 p12; R00263 p15, p20; R00373 p13). e419550 emitted prose on these sideways pages; turning pages upright (ab57a91, REPORT-batch2.md mechanism A) exposed them to table detection, and M04, M06, M07 and M09 then fired. The remaining six (R00063 p37, R00077 p8, R00112 p17, R00160 p14, p15, R00860 p58) are upright.

### 2. Per-page cross-reference

One row per document page. Mechanisms listed first are the main cause; historical ones (fixed at v0.1.14) are named in the note. 'Outcome' lists every class the page's mechanisms produce. Rows with no mechanism are table pages that the sources rate correct or resolved; they are listed so that every A2 inventory page is covered.

| Document | Page | Mechanisms | Outcome | Sources | e419550 | v0.1.14 status | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R00014 | 6 | M14, M07, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | PacketA.json A1, A4-token-loss; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; visual-review-run2.json; A2 defect_pages | prose, same cell order, label lost | A: marked fallback prose | Table 1 (6x4). v0.1.12 cell-fallback grid 2x9 (M07). v0.1.14 prose is column-major within row pairs. 'TABLE 1' label lost in e419550/v0.1.12, present in v0.1.14. |
| R00014 | 18 | M14, M07, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | PacketA.json A1, A4-token-loss; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; visual-review-run2.json; A2 defect_pages | prose, same column order | A: marked fallback prose | Table 3 (2 columns). Prose gives column 1 then column 2; barrier-to-definition pairing lost. 'TABLE 3' label lost before v0.1.14. |
| R00023 | 3 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 7 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 9 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 11 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 12 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 22 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 24 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 27 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 28 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 34 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A (NON-MATERIAL) | Body prose, no table. Marked region emitted one source line per paragraph. |
| R00023 | 38 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; material-adjudication.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 39 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 40 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 41 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 42 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 45 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | no marker; prose | A | Hanging-indent reference list, no table. |
| R00023 | 47 | M14 | MISSED TABLE | PacketA.json A1-counterexample; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | unmarked paragraph | A: marked fallback prose | Counterexample: v0.1.12 fallback grid was a correct 4x3 table; now marked prose. |
| R00023 | 49 | M14, M13 | MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; cell-fallback-policy.json | caption and two header cells dropped | marked fallback prose | Table 3: caption after the prose with two header cells fused into it. |
| R00030 | 70 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; material-adjudication.json; A2 defect_pages; REPORT-batch3.md | entry kept cleanly | A (NON-MATERIAL) | Reference list. DISAGREEMENT: REPORT-batch3.md treats p70 as a 29-token ruled table region whose fallback lacks 2 tokens. |
| R00030 | 75 | M17 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; wrapper-diff-audit.md; v0.1.14 *.stats.json table_fallbacks; REPORT-batch3.md; PLAN-tables.md | unmarked prose | A (wrapper prose) | Landscape Table 3. Upstream grid drops words; downstream token-check reverts. DISAGREEMENT: B3 (1e7af01) 16 of 261 tokens missing, no fallback; v0.1.14 token-check 4 missing. |
| R00032 | 85 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages | no marker | A | Reference list. v0.1.12 also merged reference boundaries (A2 regressions list). |
| R00032 | 86 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages | no marker | A | Reference list. v0.1.12 also merged reference boundaries (A2 regressions list). |
| R00032 | 87 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages | no marker | A | Reference list. v0.1.12 also merged reference boundaries (A2 regressions list). |
| R00032 | 88 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages; material-adjudication.json | no marker | A | Reference list. v0.1.12 also merged reference boundaries (A2 regressions list). |
| R00032 | 89 | M17 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks | unmarked prose | A (wrapper prose) | 7x7 ruled Table 1; grid dropped 1 word. |
| R00032 | 90 | - | no current defect | A2 other_table_events; visual-review-run2.json | caption inside grid | correct grid | No current defect. |
| R00032 | 92 | - | no current defect | A2 defect_pages; visual-review-run2.json | flattened to prose | RESOLVED (correct grid) | No current defect. |
| R00032 | 93 | M12 | WRONG ASSOCIATION | A2 other_table_events; visual-review-run2.json | packed columns | correct grid | First page of Table 5; the continuation (p94) is prose. |
| R00032 | 94 | M14, M12 | MISSED TABLE, WRONG ASSOCIATION | A2 defect_pages; cell-fallback-policy.json; visual-review-run2.json | unmarked prose | A (marked prose) | Continuation of Table 5 falls back; table split between a grid (p93) and prose (p94); line-end hyphens unjoined. |
| R00063 | 37 | M02 | FALSE GRID | PacketA.json A3; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json; REPORT-batch2.md; REPORT-batchC-block1.md | one paragraph, no grid | B-NEW STRUCTURAL-NEW (blocks) | Numbered endnotes as 2-column grid (Wry 2013 p37 in B2/BC1); line-end hyphen not rejoined. |
| R00063 | 46 | M08, M13 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | RESOLVED (correct grid) | Spanning 'Citations' header flattened; caption below table. Counted RESOLVED by packet-a-status.json. |
| R00063 | 47 | M08, M12 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Continuation of the p46 table: header as loose paragraphs, first data row as Markdown header. |
| R00077 | 8 | M06 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json; REPORT-batch3.md | prose, no grid | B-NEW STRUCTURAL-NEW (blocks) | Table 1, 2 logical rows split into 4 grid rows at the first printed line. B3: all 153 tokens conserved. |
| R00077 | 32 | M06, M08, M12 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; REPORT-batch3.md | prose (columns interleaved) | B-NEW STRUCTURAL-NEW (blocks) | Landscape Table 2 continuation; header and each study row split into first-line and continuation rows (9 rows for 1+4). |
| R00077 | 38 | - | no current defect | A2 defect_pages; visual-review-run2.json | identical | NOT REPRODUCED | False proposal on endnote prose kept as prose; no output defect. |
| R00077 | 39 | - | no current defect | A2 defect_pages; visual-review-run2.json | identical | NOT REPRODUCED | False proposal kept as prose; text-layer run-together words only. |
| R00087 | 9 | M15, M11 | MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; visual-review-run2.json; material-adjudication.json | cell kept inline | NON-MATERIAL (reviewer: new) | Table 1 not detected; final row's level cell moved to three duplicate `[^†]:` definitions. |
| R00087 | 10 | M04, M17 | FALSE GRID, LOST TEXT | PacketA.json A4-token-loss, A5; packet-a-status.json; material-adjudication.json; visual-review-gate25.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; PLAN-tables.md | in-order prose, no loss | B-NEW MATERIAL-NEW (blocks) | Three 2-column grids from single-row line bands; wrapped 'U.S.' lost inside a text-table proposal (UNACCOUNTED in line accounting). Same PDF in gate25 and run2. |
| R00087 | 12 | M04, M11 | FALSE GRID, WRONG ASSOCIATION | PacketA.json A2, A5; packet-a-status.json; material-adjudication.json; visual-review-gate25.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | prose, no grid | B-NEW STRUCTURAL-NEW (blocks) | One row as stray 2-column grid; final row's level cell moved to three `[^†]:` definitions. |
| R00087 | 13 | M04, M11 | FALSE GRID, WRONG ASSOCIATION | PacketA.json A2, A5; packet-a-status.json; material-adjudication.json; visual-review-gate25.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | prose, no grid | B-NEW STRUCTURAL-NEW (blocks) | Same two patterns as p12. |
| R00087 | 14 | M15 | MISSED TABLE | visual-review-gate25.json | similar prose | unmarked prose | Table 1 continued; two proposals kept as prose. |
| R00087 | 15 | M04 | FALSE GRID | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-gate25.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | prose, no grid | B-NEW STRUCTURAL-NEW (blocks) | One row as stray 2-column grid. |
| R00112 | 7 | M07, M06, M20 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | 9-column Table 1 as 2-column grid; seven columns fused in one cell; header over 3 rows; '+' as '1'. |
| R00112 | 8 | M14, M11, M20 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | A2 other_table_events; cell-fallback-policy.json; material-adjudication.json; visual-review-run2.json | values in rows | NON-MATERIAL | Marked fallback: last column's header and 3 of 5 values emitted after the block; '=' as '5', '+' as '1'. |
| R00112 | 14 | M09, M06, M08 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | prose | B-NEW MATERIAL-NEW (blocks) | Rotated Table 3: row-label column merged into first period column; one grid row per printed line; year header demoted to a data row. |
| R00112 | 15 | M09, M06 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | prose | B-NEW MATERIAL-NEW (blocks) | Table 3 continuation: two stacked sub-tables in one grid; second panel label inside a first-panel cell. |
| R00112 | 17 | M09 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json | prose | B-NEW MATERIAL-NEW (blocks) | Table 4, two stacked panels in one 2-column grid; panel label inside the last cell of the first panel. |
| R00112 | 24 | M10, M14, M07, M08, M06 | MISSED TABLE, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 other_table_events | worse grid (cells mixed) | B-KNOWN structure | Rotated Table 5 split: unshaded rows as marked fallback prose, shaded rows as a 4-column grid with a data line as header and three columns fused. |
| R00153 | 12 | M14 | MISSED TABLE | A2 defect_pages; cell-fallback-policy.json; visual-review-run2.json | identical prose | marked fallback prose | Table 1, rows contiguous, cell boundaries lost. |
| R00153 | 17 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; material-adjudication.json; A2 defect_pages | labels as prose | B-KNOWN content loss | Figure 1 mediation diagram. The 'content loss' is 'R²' rendered as a footnote reference, not a table mechanism. |
| R00153 | 19 | M01, M17 | FALSE GRID, LOST TEXT | A2 defect_pages; material-adjudication.json; visual-review-run2.json; v0.1.14 *.stats.json table_fallbacks | same prose | PRE-EXISTING | Figure 2 mediation diagram: lossy proposal (9 tokens missing) reverted by downstream token-check. |
| R00153 | 21 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; material-adjudication.json; A2 defect_pages | labels as prose | B-KNOWN content loss | Figure 3 mediation diagram; same R² issue. |
| R00153 | 33 | M15, M11 | MISSED TABLE, WRONG ASSOCIATION | A2 defect_pages; visual-review-run2.json | same, wrong minus signs | unmarked prose | Tajfel matrices not proposed; one matrix emitted as footnote definition `[^n1]:`. |
| R00153 | 34 | M15 | MISSED TABLE | visual-review-run2.json | same placement | unmarked prose | Four matrices as unmarked number lines after the body text. |
| R00153 | 35 | M17, M20 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks | prose, wrong minus signs | A (wrapper prose) | Three stacked correlation tables; '=' and '≤' print as '5' and '#'. |
| R00160 | 12 | M08, M07 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json; REPORT-batch2.md | prose (MA) / see note | B-NEW MATERIAL-NEW (blocks) | Rotated correlation matrix (York 2018). Grid copies the source's one-column header offset; two correlations share one cell. DISAGREEMENT: PacketA vs_e419550 'better'; MA says e419550 emitted prose and v0.1.14 is new. B2 (older build) described all 17 row labels merged into one cell. |
| R00160 | 14 | M07 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; REPORT-batch2.md | separate label-to-value rows | B-NEW MATERIAL-NEW (blocks) | Regression Table 2: 28 of 33 body rows folded into the header row. |
| R00160 | 15 | M10, M07, M08, M12 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; REPORT-batch2.md | same fragmentation, one merged row | B-NEW MATERIAL-NEW (blocks) | Table 2 continued: 4 grids plus prose; header cells merge four coefficient/SE rows. DISAGREEMENT: PacketA says fragmentation identical to e419550; MA says worse (four merged rows vs one). |
| R00160 | 22 | M17 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks; REPORT-batch2.md | prose, garbled row | A (wrapper prose) | Rotated Table 3; grid missing 12 tokens. |
| R00160 | 23 | M17 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks; REPORT-batch2.md | prose | A (wrapper prose) | Table 3 continued; grid missing 11 tokens. |
| R00219 | 55 | M15 | MISSED TABLE | A2 defect_pages; visual-review-run2.json | column-major prose | unmarked prose (better) | Rotated Table 1 not detected; header row and a data row emitted as headings. |
| R00219 | 65 | M14 | MISSED TABLE | A2 other_table_events; cell-fallback-policy.json; visual-review-run2.json | prose | marked fallback prose | Row labels appended to previous row; last row's two cells merged. |
| R00258 | 6 | M17, M20 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks; REPORT-batch2.md | identical prose | B-KNOWN content loss | Jay 2013 Table 1 (scan with OCR layer): two lossy proposals; two numeric cells unreadable in the text layer. |
| R00263 | 5 | M10, M08, M11, M20 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages | different wrong grid | B-KNOWN structure | Table 1: only 6 middle row groups gridded (text proposal); wrapped data cell as header; wrapped 'Israel' outside grid; '<' lost (same as e419550). |
| R00263 | 8 | M01 | FALSE GRID | PacketA.json A3; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Figure 1 data-structure diagram. |
| R00263 | 9 | M01, M17 | FALSE GRID, LOST TEXT | A2 defect_pages; material-adjudication.json; visual-review-run2.json; v0.1.14 *.stats.json table_fallbacks | same | PRE-EXISTING | Figure 1 (continued) proposed as table; 46-token-lossy grid reverted by downstream token-check; labels spliced into body paragraph. |
| R00263 | 10 | M15, M20 | LOST TEXT, MISSED TABLE | material-adjudication.json; visual-review-run2.json | same | PRE-EXISTING | Rotated Table 2 not detected; '=' lost. |
| R00263 | 11 | M15, M20 | LOST TEXT, MISSED TABLE | material-adjudication.json; visual-review-run2.json | same | PRE-EXISTING | Table 2 continued not detected; '=' lost. |
| R00263 | 12 | M15, M20 | LOST TEXT, MISSED TABLE | material-adjudication.json; visual-review-run2.json | same | PRE-EXISTING | Table 2 continued; Evidence row appended to a cell paragraph. |
| R00263 | 15 | M06, M10, M19 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; A2 suppression_finding | no grid | B-NEW STRUCTURAL-NEW (blocks) | Derotated Table 3: grid built from the 3-line header block only, body stays prose. v0.1.12 also dropped the last data row via proc_marginalia (fixed by Packet B). DISAGREEMENT on class: PacketA 'TOKENS LOST' vs v0.1.14 structural. |
| R00263 | 16 | M15 | MISSED TABLE | visual-review-run2.json | interleaved header | unmarked prose (better) | Table 3 continued, not detected. |
| R00263 | 17 | M15, M19, M20 | LOST TEXT, MISSED TABLE | material-adjudication.json; visual-review-run2.json; run2-diagnostic.json; A2 suppression_finding | same | PRE-EXISTING | Table 3 continued; last data row suppressed by proc_marginalia in v0.1.12 (fixed); '+' lost. |
| R00263 | 18 | M15 | MISSED TABLE | visual-review-run2.json | - | unmarked prose | Table 3 continued, not detected. |
| R00263 | 20 | M08, M06, M19, M12 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json | no grid | B-NEW STRUCTURAL-NEW (blocks) | Table 3 continuation: first line of the data row is the Markdown header; true headers as '####'; 'TABLE 3 (Continued)' caption lost in v0.1.12 (v0.1.14 review: no content loss). |
| R00263 | 22 | M08 | WRONG ASSOCIATION | A2 other_table_events; visual-review-run2.json | identical | correct grid (VRR) / OTHER (A2) | Header row as bold paragraph above grid; first data row in header slot. |
| R00263 | 23 | M01 | FALSE GRID | PacketA.json A3; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Figure 2 flow diagram. |
| R00263 | 24 | - | no current defect | A2 other_table_events; visual-review-run2.json | identical | correct grid | Figure 3 is a real typology matrix; grid is right. No defect. |
| R00293 | 4 | - | no current defect | A2 other_table_events; visual-review-run2.json | same | correct grid | No defect. |
| R00293 | 8 | M03, M13 | FALSE GRID, WRONG ASSOCIATION | PacketA.json A3; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Two-column body text, caption and Table 3 (9 columns) swallowed by one 2-column grid. |
| R00293 | 10 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; material-adjudication.json; A2 defect_pages | prose | A (NON-MATERIAL) | Body text and block quote, no table; marked block leaves 7 line-end hyphens unjoined. |
| R00293 | 12 | M14 | MISSED TABLE | A2 defect_pages; cell-fallback-policy.json; visual-review-run2.json | unmarked run-on paragraph | marked fallback prose | Table 5; hanging-indent entries broken after the first line. |
| R00293 | 15 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages | same text | A | Flowchart side boxes (Figure 1). |
| R00293 | 17 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-run2.json; A2 defect_pages | same text | A | Figure 2 moderator boxes; one box split between fallback prose and figure text. |
| R00315 | 12 | M06, M20 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical | PRE-EXISTING | Table 2: each predictor split into two grid rows; minus and rho lost. |
| R00315 | 15 | M10, M08, M07, M20 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical | PRE-EXISTING | Table 4: three grids plus prose; header as five headings; values collapsed into one cell; minus signs lost. |
| R00359 | 7 | M14, M07 | MISSED TABLE, WRONG ASSOCIATION | A2 defect_pages; cell-fallback-policy.json; visual-review-run2.json; REPORT-batch2.md | same prose | marked fallback prose | Greenwood & Suddaby Table 1; B2 (v0.1.10): one 13-column fallback row. |
| R00359 | 10 | M14, M07 | MISSED TABLE, WRONG ASSOCIATION | A2 defect_pages; cell-fallback-policy.json; visual-review-run2.json; REPORT-batch2.md | same prose | marked fallback prose | Table 2; B2: 10 columns, one row. |
| R00359 | 11 | M17 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; visual-review-run2.json; A2 defect_pages; v0.1.14 *.stats.json table_fallbacks; REPORT-batch2.md | prose | A (wrapper prose) | Greenwood & Suddaby 2006 Table 3 (14 columns). |
| R00373 | 12 | M17, M20 | LOST TEXT | PacketA.json A4-rlw; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; v0.1.14 *.stats.json table_fallbacks | transposed scrambled grid | B-KNOWN content loss | Derotated Table 1; grid dropped 2 words; every negative correlation prints positive. |
| R00373 | 13 | M07, M20 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2, A5; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json | row-major prose, rows kept | B-NEW MATERIAL-NEW (blocks) | Derotated logit Table 2: all 22 predictor labels in one header cell, each model's coefficients stacked in one cell, empty cells dropped. Minus signs lost (same as e419550). |
| R00373 | 14 | M07, M08, M20 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events | transposed scrambled grid | B-KNOWN structure | Derotated 24-column correlation Table 3 as 5 columns; means and s.d.s in wrong cells; minus signs lost. |
| R00373 | 15 | M15, M20 | LOST TEXT, MISSED TABLE | A2 defect_pages; material-adjudication.json; visual-review-run2.json | same losses | unmarked prose | Table 4 not detected; header as '####'; Model-2-only values not placeable; minus signs and '<' lost. |
| R00443 | 16 | M18 | LOST TEXT | PacketA.json A4-token-loss; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events; run2-diagnostic.json; PLAN-tables.md item 12; REPORT-batch3.md; REPORT-v0.1.12.md | partial fragments (PacketA) / same (PAS) | B-KNOWN content loss | Landscape regression table on an upright scanned page; 163 of 336 words emitted. DISAGREEMENTS on e419550 and on lossy_pages (see section 4). |
| R00446 | 10 | M15, M11 | MISSED TABLE, WRONG ASSOCIATION | material-adjudication.json; visual-review-run2.json; run2-diagnostic.json | separate definitions | NON-MATERIAL | Two table columns emitted as trailing footnote definitions, adjacent column pairs joined. |
| R00446 | 12 | M15 | MISSED TABLE | A2 defect_pages; material-adjudication.json; visual-review-run2.json | identical | NON-MATERIAL | Table 4 proposal kept as prose; column-major dump, coefficients separated from SEs. |
| R00446 | 13 | M15, M11 | MISSED TABLE, WRONG ASSOCIATION | material-adjudication.json; visual-review-run2.json; run2-diagnostic.json | row labels kept in place | NON-MATERIAL | 14 row labels moved to unreferenced footnote definitions; rows no longer identifiable. |
| R00446 | 14 | M15 | MISSED TABLE | A2 defect_pages; visual-review-run2.json | identical | unmarked prose | Table 6 column-major; coefficients separated from SEs. |
| R00531 | 6 | M10, M08, M20 | LOST TEXT, WRONG ASSOCIATION | A2 defect_pages; material-adjudication.json; visual-review-run2.json | identical | PRE-EXISTING | Scan: Table 1 as four 2-column partial grids plus prose; OCR-garbled counts. |
| R00639 | 23 | M15, M20, M13 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | PacketA.json A4-token-loss; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages | same table text | B-KNOWN content loss | OCR Table 3: proposal kept as prose; panel b interleaved line by line; one word lost (OCR); caption fused. |
| R00639 | 28 | M10, M06, M20 | LOST TEXT, WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 other_table_events | identical grid | B-KNOWN structure | OCR page. Table 4: one event group gridded one row per wrapped line; rest prose with labels spliced into sentences; 3 words lost to OCR. |
| R00639 | 29 | M10, M06 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical grids | B-KNOWN structure | OCR page. Table 5: two line-fragment grids; one evidence entry cut across the grid boundary. |
| R00717 | 9 | M01 | FALSE GRID | PacketA.json A3; packet-a-status.json; material-adjudication.json; visual-review-gate25.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Two-panel figure as 2-column, 30-row grid. |
| R00754 | 2 | M14, M03, M05 | FALSE GRID, FALSE MARKER, MISSED TABLE | A2 defect_pages; cell-fallback-policy.json; material-adjudication.json; visual-review-run2.json; wrapper-diff-audit.md; REPORT-batch2.md | dehyphenated paragraph | marked fallback prose (NON-MATERIAL) | Peng 2009. Table 1 falls back (row-recoverable); the marked block also covers a right-column body paragraph kept as raw lines. B2 (v0.1.10): body prose beside Figure 1 emitted as a 6-column table. |
| R00754 | 14 | - | no current defect | A2 defect_pages; visual-review-run2.json | flattened | RESOLVED (correct grid) | No defect. |
| R00831 | 8 | M01, M17 | FALSE GRID, LOST TEXT | A2 defect_pages; material-adjudication.json; visual-review-run2.json; v0.1.14 *.stats.json table_fallbacks | same | PRE-EXISTING | Line charts detected as table; downstream token-check reverted (1 token missing). |
| R00831 | 11 | - | no current defect | A2 defect_pages; visual-review-run2.json | - | RESOLVED (correct grid) | Captioned FIGURE 2 but a real matrix; correct grid. |
| R00860 | 2 | - | no current defect | A2 other_table_events; visual-review-run2.json | - | correct grid | No defect. |
| R00860 | 57 | M15 | MISSED TABLE | material-adjudication.json; visual-review-run2.json | one glued label | NON-MATERIAL | Rotated Table 1 not detected; false list nesting; three row labels glued to previous row. |
| R00860 | 58 | M11 | WRONG ASSOCIATION | PacketA.json A2; packet-a-status.json; material-adjudication.json; visual-review-run2.json; A2 defect_pages; run2-diagnostic.json | run-on paragraph | B-NEW STRUCTURAL-NEW (blocks) | Table 2, final row's right cell emitted after the grid; grid asserts an empty cell. |
| R00860 | 59 | - | no current defect | A2 defect_pages; visual-review-run2.json | - | RESOLVED (correct grid) | No defect. |
| R00860 | 60 | M01 | FALSE GRID | PacketA.json A3; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Figure 1 box-and-arrow. |
| R00860 | 61 | M01 | FALSE GRID | PacketA.json A3; packet-a-status.json; visual-review-run2.json; A2 other_table_events | identical | B-KNOWN structure | Figure 2 box-and-arrow. |
| R00894 | 8 | M06, M08 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 1: two-line header split; one row split into two. |
| R01114 | 8 | M10, M08 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 2: header and first group as bold prose; four header-less grids. |
| R01285 | 16 | M17 | LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | identical prose | unmarked prose (wrapper) | Table 4; upstream grid reported missing 2 tokens; reviewer found them present in the reverted prose. |
| R02027 | 22 | M10, M08 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 1 as two partial grids plus bold prose; orphan continuation as header. |
| R02027 | 25 | M08 | WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical grids | NON-MATERIAL | Panel grids headerless; column labels once as prose. (Reviewer's 'new' flag is the running head, not the table.) |
| R02027 | 34 | M08, M10, M20 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical | NON-MATERIAL | Table 5: header outside as scrambled prose; one model's list becomes a separate table; chi-square cell empty. |
| R02055 | 7 | M01 | FALSE GRID | visual-review-gate25.json; material-adjudication.json | labels as prose, no grid | MATERIAL-NEW (blocks) | Fig. 1: false 3x3 grid mixes phrases from two figure boxes. |
| R02190 | 16 | M02 | FALSE GRID | visual-review-gate25.json | identical | unchanged | Two reference entries as a 2-column grid; next author merged into a cell. |
| R02611 | 11 | M01 | FALSE GRID | visual-review-gate25.json | identical | unchanged | Figure 1 path diagram as 2-column grid. |
| R02611 | 12 | M01 | FALSE GRID | visual-review-gate25.json | no grid | reviewer text: new; flag false | Figure 2 (2x2 design) as 2x2 grid. DISAGREEMENT: reviewer says the grid is new vs e419550 but new_structural_regression=false; absent from material-adjudication.json. |
| R02611 | 18 | M06, M13 | WRONG ASSOCIATION | visual-review-gate25.json; REPORT-v0.1.12.md; PLAN-tables.md item 7 | flattened to prose | correct grid (header not merged) | Table 1: 3-line header as 3 rows. Caption-in-grid fixed in v0.1.12. |
| R02611 | 25 | M09, M13 | WRONG ASSOCIATION | visual-review-gate25.json | transposed headerless grids | better | Rotated Table 2: panel label merged into a data cell; caption after table. |
| R02659 | 1 | M05 | FALSE MARKER | cell-fallback-policy.json; v0.1.14 *.stats.json table_fallbacks | - | no marker in reading copy | Front matter fallback in raw upstream; marker removed by downstream title-zone hook. Not among the 27. |
| R02659 | 8 | M15, M19 | LOST TEXT, MISSED TABLE | visual-review-gate25.json; A2 suppression_finding | identical | unmarked prose | Table 2 not detected; header row suppressed by proc_marginalia in v0.1.12 (fixed). |
| R02659 | 10 | M15, M11 | MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | row kept in place | NON-MATERIAL (reviewer: new) | Rotated Table 3 not detected; row (17) moved to a footnote definition, label lost. |
| R02659 | 12 | M14 | MISSED TABLE | visual-review-gate25.json; cell-fallback-policy.json | - | marked fallback prose | Table 5; sparse-row column placement lost. |
| R02659 | 13 | M14, M08 | MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; cell-fallback-policy.json | same defect | marked fallback prose | Table 6; 'Model 4' header emitted after the note. |
| R02659 | 14 | M17 | LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | identical | unmarked prose (wrapper) | Table 7; upstream grid missing 19 tokens. |
| R04077 | 45 | M01, M17 | FALSE GRID, LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | caption dropped | wrapper prose | Figure 1 diagram as lossy upstream table (2 tokens) reverted by token-check. |
| R05732 | 4 | M07, M06, M08 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 1: 8 columns as 7; header over 3 rows; continuations as rows. |
| R05732 | 6 | M17, M13 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json; v0.1.14 *.stats.json table_fallbacks | identical | NON-MATERIAL | Tables 2 and 3: lossy grid (9 tokens) reverted; both tables in one paragraph; caption stranded. |
| R05732 | 7 | M06, M17 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical (also lost) | PRE-EXISTING | Table 4: wrapped cell line '3 CSR/CPA)' lost; header and wraps as rows. |
| R05732 | 10 | M17 | LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | cells split into paragraphs | wrapper prose | Rotated Table 5 continued; lossy grid (12 tokens) reverted. |
| R05732 | 11 | M01, M05 | FALSE GRID, FALSE MARKER | PacketA.json A1; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; wrapper-diff-audit.md | box labels as prose | A: marked fallback prose | Figure 1 box-and-arrow model. v0.1.12 pseudo-grid; v0.1.14 false marker over figure labels. |
| R07771 | 16 | M02, M17 | FALSE GRID, LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | same | wrapper prose | Reference list: two lossy false tables (18 and 42 tokens) reverted. |
| R07771 | 17 | M02, M17 | FALSE GRID, LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | same | wrapper prose | Reference list: lossy false table (44 tokens) reverted. |
| R07771 | 18 | M02 | FALSE GRID | visual-review-gate25.json | identical | unchanged | Reference entries as 2-column grid. |
| R07771 | 19 | M02, M17 | FALSE GRID, LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | same | wrapper prose | Reference list: lossy false table (30 tokens) reverted. |
| S0004 | 1 | M05 | FALSE MARKER | PacketA.json A1-nontable; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | same prose | A (no marker in reading copy) | Front matter (title/metadata) admitted as a table; raw upstream falls back (upstream_fallback_prose=true); downstream title-zone hook removes it. Not among the 27. |
| S0004 | 6 | M14, M07 | MISSED TABLE, WRONG ASSOCIATION | PacketA.json A1; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | prose, rows together | A: marked fallback prose | Sideways Table 1 (12 rows). v0.1.12: one data row over 15 columns. |
| S0004 | 7 | M15, M13, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; A2 suppression_finding | rows on new paragraphs | unmarked prose (reviewer: new) | Table 1 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. Repeated header row suppressed in v0.1.12 (fixed). |
| S0004 | 8 | M15, M13, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; A2 suppression_finding | rows on new paragraphs | unmarked prose | Table 1 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. Repeated header row suppressed in v0.1.12 (fixed). |
| S0004 | 9 | M15, M13, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; A2 suppression_finding | rows on new paragraphs | unmarked prose | Table 1 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. Repeated header row suppressed in v0.1.12 (fixed). |
| S0004 | 10 | M15, M13, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; A2 suppression_finding | rows on new paragraphs | unmarked prose | Table 1 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. Repeated header row suppressed in v0.1.12 (fixed). |
| S0004 | 11 | M17, M13, M19 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks; A2 suppression_finding | rows on new paragraphs | wrapper prose | Lossy upstream grid (34 tokens) reverted to one unsegmented paragraph; continuation caption misplaced; repeated header suppressed in v0.1.12 (fixed). |
| S0004 | 12 | M17, M13, M19 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks; A2 suppression_finding | rows on new paragraphs | wrapper prose | Lossy upstream grid (9 tokens) reverted to one unsegmented paragraph; continuation caption misplaced; repeated header suppressed in v0.1.12 (fixed). |
| S0004 | 17 | M15, M13 | MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json | rows on new paragraphs | unmarked prose | Table 2 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. |
| S0004 | 18 | M17, M13, M19 | LOST TEXT, WRONG ASSOCIATION | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks; A2 suppression_finding | rows on new paragraphs | wrapper prose | Lossy upstream grid (22 tokens) reverted to one unsegmented paragraph; continuation caption misplaced; repeated header suppressed in v0.1.12 (fixed). |
| S0004 | 19 | M15, M13, M19 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | visual-review-gate25.json; A2 suppression_finding | caption at page end | unmarked prose | Table 2 continuation/page not detected; row starts glued to previous row; '(continued)' caption at page end. Repeated header row suppressed in v0.1.12 (fixed). |
| S0004 | 20 | M14, M07, M17 | LOST TEXT, MISSED TABLE, WRONG ASSOCIATION | PacketA.json A1; packet-a-status.json; cell-fallback-policy.json; visual-review-gate25.json | prose, rows together | A: marked fallback prose | 7 study rows. v0.1.12 grid lost one repeated token (10 -> 9 occurrences). |
| S0008 | 3 | M17 | LOST TEXT | visual-review-gate25.json; v0.1.14 *.stats.json table_fallbacks | identical | wrapper prose | Table 1: lossy grid (3 tokens) reverted; list items line-interleaved. |
| S0009 | 6 | M08, M10 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 1: no header row; two data rows outside grid. |
| S0009 | 13 | M10, M08, M09 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Table 4: five header-less grids; section labels fused into label cells. |
| S0009 | 15 | M10, M08, M09 | WRONG ASSOCIATION | visual-review-gate25.json; material-adjudication.json | identical | PRE-EXISTING | Table 5: three grids plus prose; group labels merged. |
| S0009 | 17 | M02, M17 | FALSE GRID, LOST TEXT | PLAN-tables.md item 4; visual-review-gate25.json | - | correct grid (VRG) | DISAGREEMENT: PLAN (v0.1.8) says pp17-22 pass reference numbers as 2-column tables and p17 loses 259 words; v0.1.14 reviewers rate pp17-22 CORRECT GRID on table pages. |
| S0009 | 23 | M08, M09, M11 | WRONG ASSOCIATION | visual-review-gate25.json | identical | unchanged | Tables 7 and 8: header outside; final row after grid. |
| SBTi | 2 | - | no current defect | REPORT-tables-step4.md | n/a | fixed (wrapped attachment) | Region 1 now reconstructs with 0 missing tokens. No current defect recorded. |
| SBTi | 3 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 2. Usable grid sacrificed to prose. |
| SBTi | 7 | M15, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 1 pages with no detected table. |
| SBTi | 8 | M15, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 1 pages with no detected table. |
| SBTi | 9 | M15, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 1 pages with no detected table. |
| SBTi | 10 | M16, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2; REPORT-tables-step4.md | n/a | open | Table 1: full candidate rejected (area > 0.6); region 3 reconstructs a fragment; lead-in ownership (PLAN item 3). |
| SBTi | 11 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 4, 5. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 12 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 6. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 13 | M14, M16 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 7. |
| SBTi | 14 | M08, M16 | MISSED TABLE, WRONG ASSOCIATION | REPORT-tables-step4.md | n/a | open | Region 8 fragment of criteria table; first bullet promoted to header. |
| SBTi | 16 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 12. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 17 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 13, 14. |
| SBTi | 20 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 16. |
| SBTi | 22 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 18. |
| SBTi | 25 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 21. |
| SBTi | 26 | M14, M16, M17 | LOST TEXT, MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md; CLAUDE.md; PLAN-tables.md item 4 | n/a | marked fallback prose | Fallback region(s) 23. CLAUDE.md defect 1 page. Historical M17: accepted reconstruction R22 kept 112/120 words and omitted a phrase (v0.1.8); fixed by wrapped attachment (TS4: R22 recovers 8 tokens). |
| SBTi | 29 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 25, 26. |
| SBTi | 34 | M14, M16 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md; CLAUDE.md | n/a | marked fallback prose | Fallback region(s) 30. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. CLAUDE.md defect 1 page. |
| SBTi | 36 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 33. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 38 | M16, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 2: no emitted table despite detected candidates. |
| SBTi | 39 | M16, M12 | MISSED TABLE, WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 2 continued: no emitted table. |
| SBTi | 40 | M10, M12 | WRONG ASSOCIATION | PLAN-tables.md item 2 | n/a | open | Table 2 resumes as a 4-column fragment of a 6-column table. |
| SBTi | 43 | M14, M03 | FALSE GRID, MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 36. Region 36 consumed section headings and paragraphs below a real table. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 44 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 37. Region 37 is a definition line ('Where:'); borderline. |
| SBTi | 45 | M14, M03, M05 | FALSE GRID, FALSE MARKER, MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 38, 39. Region 39 is standalone prose (false table, marker false); region 38 is a definition list. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 46 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 40. |
| SBTi | 47 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 41. |
| SBTi | 48 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 42. |
| SBTi | 49 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 43. Usable grid sacrificed to prose. |
| SBTi | 53 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 44. Usable grid sacrificed to prose. |
| SBTi | 55 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 46. |
| SBTi | 58 | M08 | WRONG ASSOCIATION | REPORT-tables-step4.md | n/a | open | Region 49: first continuation row acts as header. |
| SBTi | 60 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 50. |
| SBTi | 61 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 52. Usable grid sacrificed to prose. |
| SBTi | 62 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 54. Pre-prose fallback grid missed member words (TS4 final M > 0); recovered by 2103350. |
| SBTi | 63 | M14 | MISSED TABLE | REPORT-batchC-block1.md; REPORT-tables-step4.md | n/a | marked fallback prose | Fallback region(s) 55. Usable grid sacrificed to prose. |
| CapIQ | 165 | M14 | MISSED TABLE | REPORT-capiq.md B5 | n/a | ordered prose | Detected region with no reconstruction result (24 tokens). |
| CapIQ | 177 | M14 | MISSED TABLE | REPORT-capiq.md B5 | n/a | ordered prose | Reconstruction kept 212 of 249 tokens (0.851 < 0.9). |
| CapIQ | 4-185 (47 sections) | M12 | WRONG ASSOCIATION | REPORT-capiq.md B5; PLAN-tables.md item 2 | n/a | open | Each company section is one logical 4-column table over a contiguous page run; emitted as page-local pieces with the header repeated on continuation pages. |
| CapIQ | data pages without a detected region (inferred 135) | M15 | MISSED TABLE | REPORT-capiq.md B0/B5 | n/a | UNVERIFIED representation | 47 regions on 47 of the 182 data pages (pp. 4-185); how the other pages render is not recorded in REPORT-capiq.md. |
| Kitchener 2002 | 26 or 28 | M02 | FALSE GRID | REPORT-kitchener.md F; REPORT-batchC-block1.md step 3 | n/a | open | Reference entry as a 4-column table. DISAGREEMENT: REPORT-kitchener says p26, REPORT-batchC-block1 says p28. |
| Kostova 1999 | 2 | M03, M17 | FALSE GRID, LOST TEXT | REPORT-jstor.md B; CLAUDE.md | n/a | probably resolved (justified_scan guard) | OCR justified prose as a 6-column table, 104 words lost (older build). |
| Kostova 1999 | 7 | M01 | FALSE GRID | REPORT-jstor.md B; REPORT-batchC-block1.md step 3; REPORT-batch3.md | n/a | open | Figure 1 diagram as a successful text proposal; running head as header row; no figure placeholder. |
| Kostova 1999 | 15 | M03, M17 | FALSE GRID, LOST TEXT | REPORT-jstor.md B; CLAUDE.md | n/a | probably resolved (justified_scan guard) | Two OCR prose passages as 5- and 7-column tables, 294 words lost (older build). |
| Kostova 1999 | 10 or 11 | M02 | FALSE GRID | REPORT-jstor.md B; REPORT-batchC-block1.md step 3 | n/a | open | Proposition 3 as a 2-column grid. DISAGREEMENT: REPORT-jstor says p11, REPORT-batchC-block1 says p10. |
| Suchman 1995 | 30 | M15 | MISSED TABLE | REPORT-jstor.md E; CLAUDE.md | n/a | open | Scanned rule-less Table 1 as run-on paragraph (CLAUDE.md defect 4). |

#### UNCLASSIFIED

| Document | Page | Reason |
| --- | --- | --- |
| R00153 | 1 | Real bordered metadata table on a repository cover reverted to prose by the downstream title-zone hook; no markerlite defect recorded (A2 defect_pages, VRR). |
| R00894 | 15 | Downstream token-check reported 1 missing token that the reviewer found present (bold markup); the upstream grid itself was not reviewed (VRG, stats). |
| R00063 | 2 | Text-layer run-together words; not a table defect (A2 defect_pages). |
| R00160 | document | Run-together words per 1k tokens; not a table defect (A2, run2-textlayer-measures.json). |
| R00258 | 1 | OCR substitutions in the PDF's own text layer; not a table defect (A2). |
| R00443 | 1 | OCR substitutions in the PDF's own text layer; not a table defect (A2). |
| Ragins / ScholarOne | p1 (unspecified) | CLAUDE.md defect 3: ScholarOne cover sheets give junk tables on some manuscripts; no document/page evidence in the files read. Ragins p1 metadata table is genuine (BC1). |

### 3. Counts

Unit: a document page (one row in section 2). Countable rows: 200, of which 189 carry at least one mechanism and 11 are rated correct/resolved. Capital IQ aggregates (4 rows) and the two page-ambiguous rows (Kostova 'p10 or 11', Kitchener 'p26 or 28') are counted separately below. A page with several mechanisms counts once under each.

#### Pages per mechanism

| ID | Mechanism | Outcome | Pages | Packet A rows (any) | Packet A rows (primary) |
| --- | --- | --- | ---: | ---: | ---: |
| M01 | Figure or diagram admitted as a table | FALSE GRID | 14 | 6 | 6 |
| M02 | List-like text proposed as a 2-column grid | FALSE GRID | 7 | 1 | 1 |
| M03 | Body prose or page layout captured into a table region | FALSE GRID | 6 | 1 | 1 |
| M04 | Single-row line-band grids from a text-table proposal | FALSE GRID | 4 | 8 | 8 |
| M05 | Fallback marker on non-table content | FALSE MARKER | 31 | 28 | 27 |
| M06 | Wrapped lines emitted as separate grid rows | WRONG ASSOCIATION | 15 | 10 | 3 |
| M07 | Rows collapsed into one row or columns fused into one cell | WRONG ASSOCIATION | 15 | 12 | 9 |
| M08 | Header misplaced | WRONG ASSOCIATION | 26 | 10 | 4 |
| M09 | Stacked panels merged, or row-label column fused into the first data column | WRONG ASSOCIATION | 7 | 3 | 3 |
| M10 | One table split into several partial grids plus prose | WRONG ASSOCIATION | 15 | 6 | 5 |
| M11 | Table cells or rows detached from the table | WRONG ASSOCIATION | 11 | 6 | 1 |
| M12 | Cross-page table not joined | WRONG ASSOCIATION | 13 | 4 | 0 |
| M13 | Caption displaced or fused | WRONG ASSOCIATION | 16 | 3 | 0 |
| M14 | Failed reconstruction kept as prose: real table layout lost | MISSED TABLE | 43 | 6 | 1 |
| M15 | Real table not detected | MISSED TABLE | 30 | 1 | 1 |
| M16 | Large candidate rejected by the page-area rule | MISSED TABLE | 7 | 0 | 0 |
| M17 | Lossy reconstruction accepted | LOST TEXT | 30 | 12 | 8 |
| M18 | Sideways region on an upright page dropped | LOST TEXT | 1 | 1 | 1 |
| M19 | Table rows, headers or labels lost as furniture or label lines | LOST TEXT | 14 | 3 | 1 |
| M20 | Glyph loss inside table cells | LOST TEXT | 19 | 9 | 0 |

Capital IQ, not in the page counts: M12 = 47 sections (pp. 4-185); M14 = 2 pages (p165, p177); M15 = about 135 data pages with no detected region (inferred from 182 data pages minus 47 detected; representation not recorded). Page-ambiguous rows, not in the page counts: M01/M03/M17 are complete; M02 has Kostova Proposition 3 and Kitchener's reference entry.

#### Pages per outcome class

| Outcome | Pages |
| --- | ---: |
| FALSE GRID | 31 |
| WRONG ASSOCIATION | 76 |
| MISSED TABLE | 77 |
| LOST TEXT | 57 |
| FALSE MARKER | 31 |

#### Packet A cases per mechanism

Packet A has 79 cases in 80 rows (R00087 p10 appears in both corpora, packet-a-status.json counts). A case maps to every mechanism its described defect needs, so the 'any' column sums to more than 80; 'primary' sums to exactly 80. Mapping:

| Section | Document | Page | Mechanisms |
| --- | --- | --- | --- |
| A1 | R00014 | 6 | M07, M14 |
| A1 | R00014 | 18 | M07, M14 |
| A1 | S0004 | 6 | M07, M14 |
| A1 | S0004 | 20 | M07, M14, M17 |
| A1 | R05732 | 11 | M01, M05 |
| A1-counterexample | R00023 | 47 | M14 |
| A1-nontable | R00023 | 3 | M05 |
| A1-nontable | R00023 | 7 | M05 |
| A1-nontable | R00023 | 9 | M05 |
| A1-nontable | R00023 | 11 | M05 |
| A1-nontable | R00023 | 12 | M05 |
| A1-nontable | R00023 | 22 | M05 |
| A1-nontable | R00023 | 24 | M05 |
| A1-nontable | R00023 | 27 | M05 |
| A1-nontable | R00023 | 28 | M05 |
| A1-nontable | R00023 | 34 | M05 |
| A1-nontable | R00023 | 38 | M05 |
| A1-nontable | R00023 | 39 | M05 |
| A1-nontable | R00023 | 40 | M05 |
| A1-nontable | R00023 | 41 | M05 |
| A1-nontable | R00023 | 42 | M05 |
| A1-nontable | R00023 | 45 | M05 |
| A1-nontable | S0004 | 1 | M05 |
| A1-nontable | R00030 | 70 | M05 |
| A1-nontable | R00032 | 85 | M05 |
| A1-nontable | R00032 | 86 | M05 |
| A1-nontable | R00032 | 87 | M05 |
| A1-nontable | R00032 | 88 | M05 |
| A1-nontable | R00153 | 17 | M05 |
| A1-nontable | R00153 | 21 | M05 |
| A1-nontable | R00293 | 10 | M05 |
| A1-nontable | R00293 | 15 | M05 |
| A1-nontable | R00293 | 17 | M05 |
| A2 | R00077 | 8 | M06 |
| A2 | R00112 | 17 | M09 |
| A2 | R00160 | 12 | M08, M07 |
| A2 | R00263 | 5 | M10, M08, M11, M20 |
| A2 | R00373 | 13 | M07, M20 |
| A2 | R00860 | 58 | M11 |
| A2 | R00063 | 46 | M08, M13 |
| A2 | R00063 | 47 | M08, M12 |
| A2 | R00077 | 32 | M06, M08, M12 |
| A2 | R00087 | 12 | M04, M11 |
| A2 | R00087 | 13 | M04, M11 |
| A2 | R00087 | 15 | M04 |
| A2 | R00112 | 7 | M07, M06, M20 |
| A2 | R00112 | 14 | M09, M06, M08 |
| A2 | R00112 | 15 | M09, M06 |
| A2 | R00112 | 24 | M10, M14, M07, M08, M06 |
| A2 | R00160 | 14 | M07 |
| A2 | R00160 | 15 | M10, M07, M08, M12 |
| A2 | R00263 | 15 | M06, M10, M19 |
| A2 | R00263 | 20 | M08, M06, M19, M12 |
| A2 | R00373 | 14 | M07, M08, M20 |
| A2 | R00639 | 28 | M10, M06, M20 |
| A2 | R00639 | 29 | M10, M06 |
| A3 | R00063 | 37 | M02 |
| A3 | R00263 | 8 | M01 |
| A3 | R00263 | 23 | M01 |
| A3 | R00293 | 8 | M03, M13 |
| A3 | R00860 | 60 | M01 |
| A3 | R00860 | 61 | M01 |
| A3 | R00717 | 9 | M01 |
| A4-reconstruction-loses-words | R00030 | 75 | M17 |
| A4-reconstruction-loses-words | R00032 | 89 | M17 |
| A4-reconstruction-loses-words | R00153 | 35 | M17, M20 |
| A4-reconstruction-loses-words | R00160 | 22 | M17 |
| A4-reconstruction-loses-words | R00160 | 23 | M17 |
| A4-reconstruction-loses-words | R00258 | 6 | M17, M20 |
| A4-reconstruction-loses-words | R00359 | 11 | M17 |
| A4-reconstruction-loses-words | R00373 | 12 | M17, M20 |
| A4-token-loss | R00639 | 23 | M15, M20, M13 |
| A4-token-loss | R00443 | 16 | M18 |
| A4-token-loss (gate25) | R00087 | 10 | M04, M17 |
| A4-token-loss (run2) | R00087 | 10 | M04, M17 |
| A4-token-loss | R00014 | 6 and 18 (label lines) | M19 |
| A5 | R00373 | 13 | M07 |
| A5 | R00087 | 10 | M04, M17 |
| A5 | R00087 | 12 | M04, M11 |
| A5 | R00087 | 13 | M04, M11 |

Packet A by section: A1 5, A1-counterexample 1, A1-nontable 27, A2 23, A3 7, A4-reconstruction-loses-words 8, A4-token-loss 4 cases (5 rows), A5 4 (PacketA.json counts).

v0.1.14 status of the 80 rows (packet-a-status.json): A policy-level improvement 38; RESOLVED 1 (R00063 p46); B-KNOWN structure 13; B-KNOWN content loss 6; B-NEW 22 rows = 17 unique pages. run2-diagnostic.json counts 21 B-NEW rows because it excludes the gate25 row of R00087 p10.

### 4. Disagreements between sources

- **SBTi fallback count.** 30 of 55 regions in REPORT-tables-step4.md, REPORT-v0.1.12.md, REPORT-batchC-block1.md (baseline and after fallback-to-prose) and REPORT-suppression.md. 29 appears only as the in-memory diagnostic that excluded region 39 (REPORT-batchC-block1.md 'Measured states'); it never shipped. The v0.1.8 baseline was 36 (PLAN-tables.md). 30 is the current figure.
- **Non-table fallback markers: 27 vs 29.** cell-fallback-policy.json and FINAL-REPORT.md count 27 false markers in the v0.1.14 reading copies. Two more upstream fallbacks over front matter (S0004 p1, R02659 p1; `upstream_fallback_prose: true` in S0004.stats.json) have their markers removed by the downstream title-zone hook, so raw markerlite output has at least 29. R00754 p2 (marker also covering a body paragraph on a real-table page) is a third partial case.
- **R00443 p16 lossy_pages.** markerlite REPORT-batch3.md and REPORT-v0.1.12.md flag the page as lossy (163 of 336 words); the v0.1.12 A2 inventory files it under 'page-level conservation loss (lossy_pages)'; run2-diagnostic.json says 0 lossy pages in all 27 documents and that the page is 'no longer flagged'. PLAN item 12 already records this as unreconciled (wrapper denominator or page association).
- **R00443 p16 vs e419550.** PacketA.json: v0.1.12 'worse' (loses the partial coefficient fragments e419550 kept). packet-a-status.json: 'content loss identical in e419550 / source text layer'; visual-review-run2.json vs_e419550 = 'same'.
- **R00030 p70.** REPORT-batch3.md and PLAN item 2 describe a ruled 29-token region whose reconstruction returns 0 tokens and whose fallback lacks 2 tokens. PacketA.json, the A2 inventory (NOT REPRODUCED) and visual-review-run2.json say the page is a plain reference list with a spurious 3-line candidate, no table, nothing lost.
- **R00030 p75 loss size.** REPORT-batch3.md (converter 1e7af01): 245 of 261 tokens kept, 16 dropped, no fallback. v0.1.14 R00030.stats.json token-check: 4 tokens missing; PacketA.json names the same 4 words. Different builds and token units.
- **S0009 pp. 17-22.** PLAN item 4 (v0.1.8): aligned reference numbers pass as 2-column tables; p17 loses 259 of 761 words. visual-review-gate25.json (v0.1.14) rates pp17-22 CORRECT GRID with on_page = table. Either the pages hold real tables or the earlier diagnosis is stale; not resolved in the files read.
- **R00160 p12.** PacketA.json vs_e419550 'better'; material-adjudication.json 'MATERIAL-NEW, e419550 emitted prose (verified in output)'. REPORT-batch2.md (older build) described all 17 row labels in one cell; the A2 inventory describes a copied header offset plus one merged cell.
- **R00160 p15.** PacketA.json: fragmentation 'identical to e419550'. material-adjudication.json: header cells merge four coefficient/SE rows where e419550 merged one, 'a pre-existing class made worse' (MATERIAL-NEW).
- **R00263 p15 class.** PacketA.json / A2 inventory: TOKENS LOST (evidence row dropped; the A2 suppression finding attributes a last-row loss to proc_marginalia). v0.1.14: loss fixed by Packet B, page now STRUCTURAL-NEW for a header-only false grid.
- **R02611 p12.** The gate reviewer writes that the pseudo-table is new vs e419550, but the record's new_structural_regression_vs_e419550 is false and the page is absent from material-adjudication.json and the B-NEW list.
- **Representation labels for the same output.** R00087 p12/p13 and R00373 p13: A2 'GRID WITH WRONG CELL ASSOCIATIONS' vs v0.1.14 'PSEUDO-TABLE'. R00112 p24: cell-fallback-policy.json 'PSEUDO-TABLE' vs A2 'GRID WITH WRONG CELL ASSOCIATIONS'. R00263 p22: A2 'OTHER' vs visual-review-run2.json 'CORRECT GRID' (both describe the header outside the grid). The underlying output is the same; only the label differs.
- **Page numbers.** Kostova Proposition 3: p11 (REPORT-jstor.md) vs p10 (REPORT-batchC-block1.md). Kitchener reference-entry table: p26 (REPORT-kitchener.md) vs p28 (REPORT-batchC-block1.md). Possibly printed vs PDF numbering after a dropped cover; not checked.
- **Capital IQ counts.** The brief's 39 pages / 300 rows vs the decision trace's 47 regions on 47 pages, 45 grids, 306 body rows (REPORT-capiq.md B0/B5).


## Part 2. Region labels at v0.1.15

Every table region v0.1.15 emits on the 55 unique files was rendered and
labelled once against the printed page (`tests/block2-region-labels.json`).
Five pipeline files are byte-identical to reference files and were counted
once: R00063 is Wry 2013, R00160 York 2018, R00258 Jay 2013, R00359
Greenwood 2006 and R00754 Peng 2009. Capital IQ contributes 8 sampled grids
and its 2 fallbacks. The labels are one pass per region, not double-checked;
the gold set (tests/PLAN-tables.md, block 2) is the double-checked measure.

Grids, 167 in all:

| What the region is | Grids | Correct | Minor | Wrong |
| --- | ---: | ---: | ---: | ---: |
| A real table | 135 | 45 | 29 | 61 |
| A figure or diagram | 13 | 0 | 0 | 13 |
| A reference list | 12 | 6 | 0 | 6 |
| Notes or prose | 3 | 0 | 0 | 3 |
| A cover-sheet metadata box | 3 | 3 | 0 | 0 |
| Prose and a table merged | 1 | 0 | 0 | 1 |

Of the 135 table grids, 74 are cut from part of a table (a table split into
several grids, or partly missed); 39 grids drop words that are printed in
their region. The six "correct" reference-list grids are S0009 pp. 17-22,
a numbered bibliography that the publisher captions as Table 6.

By detection path:

| Path | Grids | Good (correct or minor table) | Wrong table | Not a table |
| --- | ---: | ---: | ---: | ---: |
| `find_tables` candidates | 103 | 38 | 46 | 19 |
| text proposals (`propose_tables_from_text`) | 64 | 36 | 15 | 13 |

Fallbacks ("reconstruction failed; text kept as prose"), 78 in all:

| What the region is | Fallbacks |
| --- | ---: |
| A real table | 46 |
| Body prose (R00023 x10, R00293 p10, R02659 p1, S0004 p1, SBTi p45) | 14 |
| A reference list (R00023 x6, R00030 p70, R00032 x4) | 11 |
| A figure (R00153 pp. 17, 21; R00293 pp. 15, 17; R05732 p11) | 5 |
| An equation's "Where:" key (SBTi pp. 44, 45) | 2 |

So 32 of the 78 markers (41%) assert a table that does not exist. The
v0.1.14 audit counted 27 such pages in the reading copies; its count
excludes S0004 p1 and R02659 p1, whose markers a downstream hook removes,
and it labels region by page, not by region.
