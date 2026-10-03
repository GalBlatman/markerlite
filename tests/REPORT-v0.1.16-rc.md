# v0.1.16 release candidate: rulings 1-3 and pre-tag checks

Date 2026-10-03. Owner rulings on block 2 stop 1, then the release
candidate. Sweeps cover 69 documents: the 37 fixture PDFs of the golden
manifest, all 12 files of tests/real, and the 20 packet documents that are
not byte-identical to a tests/real file. The golden manifest's 25 packet
entries are those 20, four files identical to tests/real (Greenwood 2006 =
R00359, Jay 2013 = R00258, Wry 2013 = R00063, York 2018 = R00160) and
R00087 listed under two paths. Packet documents are read in place in WSL.
No third-party text is quoted below beyond page numbers and one journal
name already in the suppression audit.

## 1. Running heads: position always, type size except on OCR pages (8d9defc)

Expected: R00014 masthead kept; Kitchener p22 and Kostova p4 heads still
suppressed; nothing else changes. Result: exactly that. One document
changes: R00014 89 -> 88 records (p1 keeps "Academy of Management
Annals"); every record of the other 68 documents is identical (page,
reason, text and bbox), including Kitchener (77) and Kostova (58).

Suppression records per document, before (840c16f) and after:

| Document | Before | After |
| --- | --- | --- |
| real: R02027.pdf | 78 | 78 |
| real: Ragins craft of clear writing 2012.pdf | 1324 | 1324 |
| real: Target-Validation-Protocol.pdf | 174 | 174 |
| real: capiq_keydev.pdf | 681 | 681 |
| real: greenwood2006.pdf | 65 | 65 |
| real: jay2013.pdf | 70 | 70 |
| real: kitchener2002.pdf | 77 | 77 |
| real: kostova1999.pdf | 58 | 58 |
| real: peng2009.pdf | 58 | 58 |
| real: suchman1995.pdf | 82 | 82 |
| real: wry2013.pdf | 52 | 52 |
| real: york2018.pdf | 94 | 94 |
| packet: R00030.pdf | 114 | 114 |
| packet: R00032.pdf | 95 | 95 |
| packet: R00077.pdf | 51 | 51 |
| packet: R00087.pdf | 55 | 55 |
| packet: R00112.pdf | 95 | 95 |
| packet: R00153.pdf | 110 | 110 |
| packet: R00263.pdf | 55 | 55 |
| packet: R00293.pdf | 73 | 73 |
| packet: R00373.pdf | 56 | 56 |
| packet: R00443.pdf | 67 | 67 |
| packet: R00446.pdf | 55 | 55 |
| packet: R00639.pdf | 17 | 17 |
| packet: R00717.pdf | 67 | 67 |
| packet: R00860.pdf | 3707 | 3707 |
| packet: R00014.pdf **(changed)** | 89 | 88 |
| packet: R00023.pdf | 54 | 54 |
| packet: R02659.pdf | 87 | 87 |
| packet: R05732.pdf | 29 | 29 |
| packet: S0004.pdf | 35 | 35 |
| packet: S0009.pdf | 120 | 120 |
| fixture: all_text_wrapped.pdf | 0 | 0 |
| fixture: bibliography_symbols.pdf | 0 | 0 |
| fixture: bold_bullets.pdf | 0 | 0 |
| fixture: caption_inside_table.pdf | 1 | 1 |
| fixture: continued_table_header.pdf | 6 | 6 |
| fixture: dropcap.pdf | 0 | 0 |
| fixture: ebsco_notice_scan.pdf | 4 | 4 |
| fixture: edge_content.pdf | 8 | 8 |
| fixture: figure_dedup.pdf | 0 | 0 |
| fixture: figure_source_labels.pdf | 0 | 0 |
| fixture: footnote_biglabel.pdf | 1 | 1 |
| fixture: footnote_bold_wrapped.pdf | 1 | 1 |
| fixture: footnote_repro.pdf | 1 | 1 |
| fixture: garbled_font.pdf | 0 | 0 |
| fixture: hard.pdf | 6 | 6 |
| fixture: hard_footer_first.pdf | 6 | 6 |
| fixture: images_inline.pdf | 0 | 0 |
| fixture: isolated_ocr_page.pdf | 0 | 0 |
| fixture: journal_front_matter.pdf | 2 | 2 |
| fixture: justified_scan.pdf | 0 | 0 |
| fixture: list_lookalikes.pdf | 0 | 0 |
| fixture: manuscript.pdf | 52 | 52 |
| fixture: manuscript_numcol.pdf | 248 | 248 |
| fixture: panel_letters.pdf | 0 | 0 |
| fixture: paper.pdf | 1 | 1 |
| fixture: pi_minus.pdf | 0 | 0 |
| fixture: provenance_pages.pdf | 50 | 50 |
| fixture: repro.pdf | 6 | 6 |
| fixture: repro_tight.pdf | 3 | 3 |
| fixture: rotated_pages.pdf | 0 | 0 |
| fixture: scanned.pdf | 4 | 4 |
| fixture: scanned_with_stamp.pdf | 7 | 7 |
| fixture: table_legend.pdf | 0 | 0 |
| fixture: table_only_footer.pdf | 2 | 2 |
| fixture: tall_cell.pdf | 0 | 0 |
| fixture: watermark.pdf | 6 | 6 |
| fixture: year_column.pdf | 40 | 40 |

## 2. Dehyphenation keeps a dash between digits (1e4daf7)

94 joins change, in 24 documents (the commit message says 23; the count
is 24). Every one is a digit, a hyphen or dash at the line end, and a digit
on the next line. No legitimate word join is removed: no fixture output
changes, word hyphenation ("con-" / "tinued", hard.pdf "bef-" / "ore") is
untouched, and no document changes anywhere except at these 94 joins. The
one URL (R00112, "2011-" / "019-2.pdf") was welded into a wrong file name
before. Capital IQ has none. Numbers only, as now emitted:

| Document | Joins | Now emitted (was: digits welded, or a space after an en dash) |
| --- | --- | --- |
| R00030.pdf | 2 | 1393-1418, 795-843 |
| R00032.pdf | 8 | 846–877, 817–834, 147–160, 673–696, 257–292, 237–281, 877–904, 234–254 |
| R00077.pdf | 2 | 215–216, 215–216 |
| R00087.pdf | 1 | 1990–2005 |
| R00112.pdf | 3 | 2011-019, 532–550, 311–326 |
| R00153.pdf | 3 | 237–254, 243–275, 59–95 |
| R00263.pdf | 2 | 773–802, 49–77 |
| R00293.pdf | 4 | 211–244, 221–235, 145–179, 202–228 |
| R00373.pdf | 8 | 165–183, 309–326, 10–23, 517–554, 559–575, 145–179, 1172–1182, 202–228 |
| R00443.pdf | 3 | 1971-85, 1919-1979, 621-643 |
| R00446.pdf | 1 | 567-595 |
| R00639.pdf | 2 | 297—309, 815—831 |
| R00860.pdf | 7 | 379-405, 329-360, 147-160, 1662-1697, 213-236, 47-66, 215-254 |
| R00014.pdf | 7 | 582–600, 27–48, 1990–2005, 183–203, 219–238, 129–153, 1–32 |
| R00023.pdf | 6 | 3370-3381, 1227-1253, 298-323, 143-173, 745-769, 1157-1178 |
| S0004.pdf | 4 | 1106-1142, 1562-1585, 1027-1050, 1325-1347 |
| greenwood2006.pdf | 6 | 325–355, 547–570, 583–613, 967–988, 1986–1990, 621–643 |
| jay2013.pdf | 3 | 1197-1207, 145-179, 951-973 |
| kitchener2002.pdf | 3 | 818-825, 417-453, 571-610 |
| kostova1999.pdf | 2 | 143-161, 929-984 |
| peng2009.pdf | 8 | 99–120, 115–130, 521–536, 621–650, 1027–1043, 496–520, 275–296, 427–442 |
| suchman1995.pdf | 3 | 31—40, 281-304, 227-266 |
| wry2013.pdf | 1 | 83–90 |
| york2018.pdf | 5 | 1047–1067, 1523–1545, 270–295, 1091–1106, 1093–1104 |

Total: 94 joins in 24 documents.

## 3. Fragment pages (1c98821)

Share of letter tokens of at most two letters, per page with >= 40 letter
tokens, on 1,326 pages (packet and tests/real):

| Share | Pages |
| --- | --- |
| 0.00-0.35 | 1,321 |
| 0.35-0.50 | 0 |
| 0.50 | 1 (R02027 p46, legal citations: "U.S.", "S.Ct.", "F.2d") |
| 0.50-0.92 | 0 |
| 0.92-0.97 | 4 (R00443 p14, p16; R02027 p31, p36) |

The 795 packet pages peak at 0.34 apart from R00443 p14 and p16; the 531 tests/real pages at 0.34 apart from R02027 p31, p36 and p46.
Threshold 0.7, mid-gap. Minimum 30 letter tokens, because R02027 p30 is a
fragment page with 36; the 16 pages with 10-39 letter tokens otherwise
peak at 0.17. Pages flagged by the implementation across all 69
documents: **R00443 p14, p16; R02027 p30, p31, p36**. No Markdown and no
other stats value changes in any document. Flag only.

Fixture `fragment_text`: prose 0.17 and legal citations 0.58 not flagged,
pieces 1.00 flagged. A page made only of reporter citations, denser than
anything in the reference set, can pass 0.7 (a first synthetic version of
the control page measured 0.72); the cost is a false warning, never text.

## 4. Release candidate (e51d6e7)

Contents: version display, security hardening A1-A7, B2 fallback marker
(with the released-candidate guard), and items 1-3 above. VERSION 0.1.16;
CHANGELOG.md new; README updated for the fallback marker, the digit rule,
running heads, and the fragment and resource-limit warnings. The release
notes are the CHANGELOG section (tools/release_notes.py, run by the build
job; the release job still checks out nothing).

Pre-tag checklist, on e51d6e7:

| Check | Result |
| --- | --- |
| ruff format and check, pytest (127 passed, 2 skipped), regress.py, golden fixtures, check_gui.py | pass (Windows) |
| regress.py with Tesseract 5.5.0 (WSL), OCR fixtures included | all fixtures match |
| `markerlite --version` from source, Windows and WSL | `0.1.16` |
| Local PyInstaller build of the committed tree (build_exe.bat) | exit 0 |
| Window title of the built exe | `markerlite 0.1.16` |
| Status-bar label | `v0.1.16` (screenshot checked) |
| First line of `--diag` | `markerlite 0.1.16`; `frozen=True`, `TkinterDnD.Tk()  OK` |
| CI on every commit of this round (test-ubuntu, build-windows-exe) | success |
| Gold tables re-score | below, unchanged from stop 1 |

Gold tables set at e51d6e7, as measured (29 tables, 8 controls, 1
ambiguous): tables EXACT 1, GRID-NEAR 4, GRID-WRONG 18, PROSE 6; exact
0.034, mean cell association 0.512, mean adjacency F1 0.369; controls
CLEAN 3, FALSE-GRID 5, FALSE-MARKER 0; ambiguous FALSE-GRID. No table
improvement is claimed.

### Golden audit after every commit (archived commit, 77 entries)

Against the v0.1.14 manifest; differences accumulate from stop 1. Every
differing entry is explained by a step of this round or of stop 1, and
every expected difference is present.

| Commit | Item | Entries differing | Added by this commit |
| --- | --- | --- | --- |
| 840c16f | stop-1 report (state before this round) | 8 | B2's 8 documents (stop 1) |
| 8d9defc | 1. running heads | 9 | R00014 (masthead kept) |
| 1e4daf7 | 2. digit dashes | 30 | the 21 further entries of the 24 documents with changed joins (identical files count once per manifest entry) |
| 1c98821 | 3. fragment pages | 31 | R02027, stats only (fragment_pages); R00443's stats change inside an entry already differing |
| e51d6e7 | 4. release candidate | 31 | none (no converter change) |


**To check after the owner's tag** (tests/REPORT-security.md, A7): two
jobs, `build` then `release`; token permissions `Contents: read` in build
and `Contents: write` in release; the bundled-version check passes; the
release shows `markerlite-windows.zip` and notes that are the download
instructions plus this CHANGELOG section; a push to main runs no release
job.

