"""Fixture regression: convert every PDF in tests/fixtures/ and diff the
Markdown against tests/expected/.

    python tests/regress.py            # exit 1 on any difference
    python tests/regress.py --update   # rewrite tests/expected/ (intentional change)
    python tests/regress.py hard repro # only these fixtures ("cli" = console check)
    python tests/regress.py -v         # full diffs instead of the first 40 lines

The expected files are the converter's current behaviour, frozen. A diff means
a change in behaviour; if the change is intended, rerun with --update and
commit the new expected files together with the code change, so the review
shows exactly what moved.

Fixtures that need Tesseract (the OCR path) are skipped when ``tesseract`` is
not on PATH, and say so; they never fail for that reason alone. The expected
output for those was produced with Tesseract 5.5.0.

Comparison is newline-normalised: the converter writes with the platform's
line ending and the expected files are stored with LF.
"""
from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import markerlite  # noqa: E402  (after sys.path)

FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = ROOT / "tests" / "expected"

# Fixtures with no text layer: their output depends on the OCR engine.
NEEDS_TESSERACT = {"scanned", "isolated_ocr_page", "scanned_with_stamp", "justified_scan",
                   "ebsco_notice_scan", "garbled_font"}


def convert_to_string(pdf: pathlib.Path, workdir: pathlib.Path) -> str:
    out, _info = markerlite.convert(pdf, workdir)
    return out.read_text(encoding="utf-8")  # universal newlines -> "\n"


def check_ocr_markers(pdf: pathlib.Path, workdir: pathlib.Path, plain: str) -> int:
    """OCR provenance survives both page-marker settings, even on a blank page."""
    out, _ = markerlite.convert(pdf, workdir, page_markers=True)
    marked = out.read_text(encoding="utf-8")
    expected = ["2", "3", "4"]
    if (re.findall(r"<!-- ocr page (\d+) -->", plain) == expected
            and re.findall(r"<!-- ocr page (\d+) -->", marked) == expected
            and re.findall(r"<!-- page (\d+) -->", marked) == ["1", "2", "3", "4"]
            and all(f"<!-- page {n} -->\n\n<!-- ocr page {n} -->" in marked
                    for n in expected)
            and "<!-- page " not in plain):
        print("ok    ocr-provenance   isolated OCR markers with and without page markers")
        return 0
    print("FAIL  ocr-provenance   missing, duplicated, or misplaced page markers")
    return 1


def check_journal_front_matter(pdf: pathlib.Path, workdir: pathlib.Path) -> int:
    """Both journal layouts reject front matter, keeping original blocks and
    a real data table; every variant also runs alone as PDF page 1.
    """
    from unittest.mock import patch
    import pymupdf
    expected = [["Group", "Observed", "Expected"], ["Alpha", "12", "15"],
                ["Beta", "18", "21"], ["Gamma", "24", "27"]]
    root = workdir / "journal-controls"
    root.mkdir(exist_ok=True)
    detect = markerlite.detect_tables
    kept_blocks = []
    def spy_detect(pm, page):
        originals = list(page.blocks)
        detect(pm, page)
        kept_blocks.extend(b for b in originals if b.journal_front_matter)
        assert all(any(b is after for after in page.blocks)
                   for b in originals if b.journal_front_matter)
    with patch.object(markerlite, "detect_tables", spy_detect):
        stats, tables = table_cells(pdf, root / "combined")
    if stats["tables"] != 3 or stats["tables_fallback"] or len(kept_blocks) < 8:
        print("FAIL  journal-front: wrong candidates or original blocks consumed")
        return 1
    if len(tables) != 3 or any(t[2] != expected for t in tables):
        print("FAIL  journal-front: data cells changed", tables)
        return 1
    text = (root / "combined" / "journal_front_matter.md").read_text()
    titles = ("Organizations responding to competing demands",
              "Evaluations of organizations across changing contexts")
    if (any(not re.search(r"(?m)^#{1,6} " + re.escape(t) + r"$", text) for t in titles)
            or "a b s t r a c t\n\nThis study" not in text
            or "**Abstract** This study" not in text
            or "<!-- table p." in text):
        print("FAIL  journal-front: title or abstract classification")
        return 1
    with patch.object(markerlite, "_journal_front_matter", lambda *args: False):
        disabled, _ = table_cells(pdf, root / "disabled")
    if disabled["tables"] != 5 or disabled["tables_fallback"] != 2:
        print("FAIL  journal-front: negative cases no longer reproduce the defect")
        return 1
    with pymupdf.open(pdf) as document:
        for n in range(3):
            single = root / f"journal_page_{n + 1}.pdf"
            with pymupdf.open() as part:
                part.insert_pdf(document, from_page=n, to_page=n)
                part.save(single)
            stats, tables = table_cells(single, root / str(n))
            if stats["tables"] != 1 or stats["tables_fallback"] or tables[0][2] != expected:
                print("FAIL  journal-front: page-one data/booktabs control", n + 1)
                return 1
    print("ok    journal-front    two negatives, original blocks, headings, abstract, page-one cells")
    return 0


def check_fallback_prose(pdf: pathlib.Path, workdir: pathlib.Path) -> int:
    """The tall-cell fixture keeps its successful grid; its original lossy
    reconstruction (wrapped recovery disabled) keeps every source token as prose.
    Also exercise the unavailable-reconstruction branch without changing the PDF.
    """
    from collections import Counter
    from unittest.mock import patch
    import unicodedata
    normalize = lambda text: Counter(unicodedata.normalize("NFKC", text).split())
    original_render = markerlite.render
    original_recon = markerlite.reconstruct_table_html
    directory = workdir / "fallback-prose"
    directory.mkdir(exist_ok=True)
    for unavailable in (False, True):
        captured = []
        def spy(pages, **kwargs):
            for page in pages:
                for block in page.blocks:
                    if block.fallback_paragraphs:
                        raw = "\n".join(ln.text for ln in block.lines)
                        prose = "\n\n".join(markerlite.fallback_prose(block))
                        captured.append((normalize(raw), normalize(prose), prose))
            return original_render(pages, **kwargs)
        with patch.object(markerlite, "recover_wrapped_lines", lambda lines, res, *args: res), \
                patch.object(markerlite, "reconstruct_table_html",
                             None if unavailable else original_recon), \
                patch.object(markerlite, "render", spy):
            output, info = markerlite.convert(pdf, directory)
        text = output.read_text(encoding="utf-8")
        marker = "<!-- table p. 1: reconstruction failed; text kept as prose -->"
        if (len(captured) != 1 or captured[0][0] != captured[0][1]
                or "|" in captured[0][2] or "<table" in captured[0][2]
                or captured[0][2] not in text
                or text != (EXPECTED / "tall_cell_fallback.md").read_text(encoding="utf-8")
                or text.count(marker) != 1 or "|" in text
                or info["stats"]["tables"] != 1 or info["stats"]["tables_fallback"] != 1
                or "1 of 1 table kept as prose" not in markerlite.summarize(info["stats"])):
            print("FAIL  fallback-prose: source tokens, marker, or statistics")
            return 1
        # Fixture has distinct row labels and wrapped phrases: their source
        # sequence must remain intact, rather than sorting all lines by y.
        prose = captured[0][2]
        ordered = ["Criterion", "Requirement", "Assessment", "C1 Boundary",
                   "consolidation approach", "Met if all included", "C2 Gases",
                   "Met if none excluded", "C3 Scopes", "Met if both covered"]
        positions = [prose.index(word) for word in ordered]
        if positions != sorted(positions):
            print("FAIL  fallback-prose: source reading order")
            return 1
    print("ok    fallback-prose   lossy/unavailable reconstruction: tokens, order, marker, stats")
    return 0


def check_proposal_guard(pdf: pathlib.Path, workdir: pathlib.Path, guarded: str) -> int:
    """justified_scan: with the proposal-path text-loss guard the justified
    prose stays prose with every word, and the control page's real table is
    still detected; with the guard disabled the prose becomes a pseudo-table
    that drops rows. Both halves are asserted so CI notices if either changes."""
    import re as _re
    from unittest.mock import patch

    def per_page(md):
        parts = _re.split(r"<!-- page (\d+) -->", md)
        return {int(parts[i]): (markerlite.content_words(parts[i + 1]),
                                parts[i + 1].count("\n|"))
                for i in range(1, len(parts), 2)}

    for sub in ("guard", "noguard"):
        (workdir / sub).mkdir(parents=True, exist_ok=True)
    out, _ = markerlite.convert(pdf, workdir / "guard", page_markers=True)
    with_guard = per_page(out.read_text(encoding="utf-8"))
    with patch.object(markerlite, "TABLE_FALLBACK_MIN_KEEP", 0.0):
        out2, _ = markerlite.convert(pdf, workdir / "noguard", page_markers=True)
    without = per_page(out2.read_text(encoding="utf-8"))
    ok = (with_guard[1][1] == 0                      # prose page: no table lines
          and with_guard[2][1] >= 6                  # control page: header, rule, 4 rows
          and without[1][1] > 0                      # unguarded: pseudo-table appears
          and without[1][0] < with_guard[1][0]       # ... and drops words
          and with_guard[1][0] >= 300)               # every word kept (308 on record)
    if ok:
        print(f"ok    {'proposal-guard':16s} prose kept ({with_guard[1][0]} w), control table found, "
              f"unguarded loses {with_guard[1][0] - without[1][0]} w")
        return 0
    print(f"FAIL  {'proposal-guard':16s} guarded={with_guard} unguarded={without}")
    return 1


def check_conservation(workdir: pathlib.Path) -> int:
    """Per-page conservation: with the sideways-page fix switched off, the two
    table pages of rotated_pages hold words and emit none, and are reported
    as lossy with both numbers; with it on, no page of the fixture is."""
    from unittest.mock import patch
    pdf = FIXTURES / "rotated_pages.pdf"
    for sub in ("on", "off"):
        (workdir / sub).mkdir(parents=True, exist_ok=True)
    _o, info = markerlite.convert(pdf, workdir / "on")
    clean = info["stats"].get("lossy_pages")
    with patch.object(markerlite, "_normalise_rotation", lambda page: (page, False)):
        _o, info = markerlite.convert(pdf, workdir / "off")
    lossy = info["stats"].get("lossy_pages") or []
    line = markerlite.summarize(info["stats"])
    ok = (clean == [] and [d["page"] for d in lossy] == [2, 3]
          and all(d["emitted"] == 0 and d["source"] >= 20 for d in lossy)
          and "2 lossy pages" in line)
    if ok:
        print(f"ok    {'conservation':16s} sideways pages flagged when the fix is off "
              f"({lossy[0]['emitted']}/{lossy[0]['source']}), none when on")
        return 0
    print(f"FAIL  {'conservation':16s} on={clean!r} off={lossy!r} summary={line!r}")
    return 1


def check_garbled(workdir: pathlib.Path) -> int:
    """garbled_font: the scrambled text layer is detected whether or not OCR is
    available (this half runs without Tesseract), and no page of an ordinary
    fixture trips the detector."""
    from unittest.mock import patch
    (workdir / "garbled").mkdir(parents=True, exist_ok=True)
    with patch.object(markerlite, "_ocr_page", lambda page, idx, dpi=300: None):
        _o, info = markerlite.convert(FIXTURES / "garbled_font.pdf", workdir / "garbled")
        _o, clean = markerlite.convert(FIXTURES / "hard.pdf", workdir / "garbled")
        _o, refs = markerlite.convert(FIXTURES / "paper.pdf", workdir / "garbled")
    line = markerlite.summarize(info["stats"])
    ok = (info["stats"].get("garbled_pages") == [1] and "1 garbled page (1)" in line
          and "check Tesseract" in line
          and clean["stats"].get("garbled_pages") == [] and refs["stats"].get("garbled_pages") == [])
    if ok:
        print(f"ok    {'garbled':16s} scrambled text layer flagged; hard and paper clean")
        return 0
    print(f"FAIL  {'garbled':16s} stats={info['stats'].get('garbled_pages')!r} summary={line!r}")
    return 1


def table_cells(pdf: pathlib.Path, workdir: pathlib.Path):
    """(stats, [(page, caption texts, cell matrix)]) for every table emitted."""
    from unittest.mock import patch
    seen = []
    render = markerlite.render

    def spy(pages, **kwargs):
        for page in pages:
            for blk in page.blocks:
                if blk.btype == "Table" and not blk.ignore_for_output:
                    parser = markerlite._TableParser()
                    parser.feed(blk.html or "")
                    seen.append((page.page_idx + 1,
                                 [" ".join(c.text.split()) for c in blk.children],
                                 [[" ".join(c.split()) for c in row]
                                  for row in [parser.header, *parser.rows]]))
        return render(pages, **kwargs)

    workdir.mkdir(parents=True, exist_ok=True)
    with patch.object(markerlite, "render", spy):
        _o, info = markerlite.convert(pdf, workdir)
    return info["stats"], seen


CAPTION_MATRIX = [
    ["Variable", "Hybrid A", "Business", "Hybrid B", "Charity"],
    ["Intent", "5.16", "4.91", "5.19", "5.40"],
    ["Cognitive", "4.64", "4.66", "4.43", "4.41"],
    ["Moral", "5.64", "5.35", "5.62", "5.89"],
]
CAPTION_TEXT = ("Table 1 Study 1 Descriptive Statistics of Model Variables by "
                "Experimental Condition")


def check_cell_matrix(workdir: pathlib.Path) -> int:
    """caption_inside_table: which token stands in which cell, not how many
    words survived. The caption is one block with its own word count, the
    note and the diagram labels are in no cell, and the body sentence that
    opens "Table 1 reports" stays prose."""
    stats, tables = table_cells(FIXTURES / "caption_inside_table.pdf", workdir / "matrix")
    text = (workdir / "matrix" / "caption_inside_table.md").read_text(encoding="utf-8")
    problems = []
    if len(tables) != 1:
        problems.append(f"{len(tables)} tables")
    else:
        _page, captions, matrix = tables[0]
        if matrix != CAPTION_MATRIX:
            problems.append(f"cell matrix {matrix!r}")
        if captions != [CAPTION_TEXT]:
            problems.append(f"caption {captions!r}")
    if stats.get("table_caption_words") != len(CAPTION_TEXT.split()):
        problems.append(f"caption words {stats.get('table_caption_words')!r}")
    if stats.get("table_captions_isolated") != 1:
        problems.append(f"captions isolated {stats.get('table_captions_isolated')!r}")
    for phrase in ("Note. Means on a seven-point scale.", "Table 1 reports the means by condition.",
                   "Legitimacy", ".087"):
        if text.count(phrase) != 1:
            problems.append(f"{phrase!r} appears {text.count(phrase)} times")
    if text.count(CAPTION_TEXT) != 1:
        problems.append("caption not emitted exactly once")
    if problems:
        print(f"FAIL  {'cell-matrix':16s} " + "; ".join(problems))
        return 1
    print(f"ok    {'cell-matrix':16s} 4x5 cells in place, caption apart "
          f"({stats['table_caption_words']} words), note and diagram outside")
    return 0


FIGURES_FILLED = FIXTURES / "repro_figures_filled.json"
FIGURES_EXPECTED = EXPECTED / "repro_described.md"


def check_flag_figures(workdir: pathlib.Path, update: bool = False) -> int:
    """repro with --flag-figures: the manifest holds exactly the entries of
    the placeholders (the raster and the vector chart, not the equation set
    as a picture), every crop exists, and the Markdown is what it is
    without the flag. Applying tests/fixtures/repro_figures_filled.json
    gives tests/expected/repro_described.md, twice over."""
    import json
    plain_dir, flag_dir = workdir / "fig-plain", workdir / "fig-flag"
    for d in (plain_dir, flag_dir):
        d.mkdir(parents=True, exist_ok=True)
    plain_md, _i = markerlite.convert(FIXTURES / "repro.pdf", plain_dir)
    md, info = markerlite.convert(FIXTURES / "repro.pdf", flag_dir, do_flag_figures=True)
    text = md.read_text(encoding="utf-8")
    manifest = json.loads((flag_dir / "repro_figures.json").read_text(encoding="utf-8"))
    entries = manifest["regions"]
    holders = re.findall(r"<!-- figure: p\. (\d+); caption: (.*?) -->", text, re.S)
    problems = []
    if text != plain_md.read_text(encoding="utf-8"):
        problems.append("Markdown differs with the flag")
    if [(str(e["page"]), e["caption"]) for e in entries] != holders:
        problems.append(f"manifest {[(e['page'], e['caption'][:20]) for e in entries]!r} "
                        f"vs placeholders {[(h[0], h[1][:20]) for h in holders]!r}")
    if [e["id"] for e in entries] != ["fig_p1_1", "fig_p2_1"]:
        problems.append(f"ids {[e['id'] for e in entries]!r}")
    for e in entries:
        if set(e) != {"id", "page", "bbox", "caption", "file", "description"}:
            problems.append(f"keys {sorted(e)!r}")
        if e["description"] != "" or not (flag_dir / e["file"]).is_file():
            problems.append(f"entry {e['id']}: description or file")
    crops = sorted(f.name for f in (flag_dir / "repro_figures").glob("*.png"))
    if crops != ["fig_p1_1.png", "fig_p2_1.png"]:
        problems.append(f"crops {crops!r}")

    filled = json.loads(FIGURES_FILLED.read_text(encoding="utf-8"))
    (flag_dir / "filled.json").write_text(json.dumps(filled), encoding="utf-8")
    first = markerlite.apply_figures(md, flag_dir / "filled.json")
    once = md.read_text(encoding="utf-8")
    second = markerlite.apply_figures(md, flag_dir / "filled.json")
    twice = md.read_text(encoding="utf-8")
    if (first, second) != (1, 1):
        problems.append(f"applied {first} then {second}, expected 1 and 1")
    if once != twice:
        problems.append("a second apply changed the file")
    if markerlite.content_words(once) != markerlite.content_words(text):
        problems.append("content words changed by the description")
    if update:
        with open(FIGURES_EXPECTED, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(once)
        print(f"{'written':9s} {'repro_described':16s} -> {FIGURES_EXPECTED.relative_to(ROOT)}")
    elif not FIGURES_EXPECTED.exists() or FIGURES_EXPECTED.read_text(encoding="utf-8") != once:
        problems.append("output differs from expected/repro_described.md")
    if problems:
        print(f"FAIL  {'flag-figures':16s} " + "; ".join(problems))
        return 1
    print(f"ok    {'flag-figures':16s} 2 crops for 2 placeholders; description applied "
          f"once, unchanged on re-apply")
    return 0


def check_low_yield(workdir: pathlib.Path) -> int:
    """With OCR unavailable, every raster page of scanned_with_stamp is reported
    as low-yield and the summary says so. Runs without Tesseract by design."""
    from unittest.mock import patch
    pdf = FIXTURES / "scanned_with_stamp.pdf"
    with patch.object(markerlite, "_ocr_page", lambda page, idx, dpi=300: None):
        (workdir / "lowyield").mkdir(parents=True, exist_ok=True)
        _out, info = markerlite.convert(pdf, workdir / "lowyield")
    stats = info["stats"]
    line = markerlite.summarize(stats)
    if stats.get("low_yield_pages") == [1, 2, 3] and "3 low-yield pages (1, 2, 3)" in line \
            and "check Tesseract" in line:
        print(f"ok    {'low-yield':16s} 3 raster pages reported when OCR is unavailable")
        return 0
    print(f"FAIL  {'low-yield':16s} stats={stats.get('low_yield_pages')!r} summary={line!r}")
    return 1


def check_cli_console(pdf: pathlib.Path) -> int:
    """Run the CLI with a cp1252 console; return 1 on a non-zero exit."""
    import os
    import subprocess
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
    with tempfile.TemporaryDirectory(prefix="markerlite-cli-") as td:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "markerlite.py"), str(pdf), "-o", td],
            env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    if proc.returncode == 0:
        print(f"ok    {'cli-cp1252':16s} exit 0 on a cp1252 console")
        return 0
    print(f"FAIL  {'cli-cp1252':16s} exit {proc.returncode} on a cp1252 console")
    for line in proc.stderr.strip().splitlines()[-3:]:
        print("      " + line)
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="fixture stems to run (default: all)")
    ap.add_argument("--update", action="store_true",
                    help="rewrite tests/expected/ from the current output")
    ap.add_argument("-v", "--verbose", action="store_true", help="print full diffs")
    args = ap.parse_args(argv)

    pdfs = sorted(FIXTURES.glob("*.pdf"))
    run_cli = not args.names or "cli" in args.names
    if args.names:
        wanted = set(args.names) - {"cli"}
        pdfs = [p for p in pdfs if p.stem in wanted]
        missing = wanted - {p.stem for p in pdfs}
        if missing:
            print(f"no such fixture(s): {', '.join(sorted(missing))}")
            return 2
    if not pdfs and not run_cli:
        print(f"no fixtures found under {FIXTURES}")
        return 2

    have_tesseract = shutil.which("tesseract") is not None
    EXPECTED.mkdir(parents=True, exist_ok=True)
    failures = 0
    with tempfile.TemporaryDirectory(prefix="markerlite-regress-") as td:
        workdir = pathlib.Path(td)
        for pdf in pdfs:
            stem = pdf.stem
            exp_path = EXPECTED / f"{stem}.md"
            if stem in NEEDS_TESSERACT and not have_tesseract:
                print(f"SKIP  {stem:16s} needs tesseract on PATH")
                continue
            got = convert_to_string(pdf, workdir)
            if stem == "journal_front_matter":
                failures += check_journal_front_matter(pdf, workdir)
            if stem == "tall_cell":
                failures += check_fallback_prose(pdf, workdir)
            if stem == "justified_scan":
                failures += check_proposal_guard(pdf, workdir, got)
            if stem == "isolated_ocr_page":
                failures += check_ocr_markers(pdf, workdir, got)
            if args.update:
                old = exp_path.read_text(encoding="utf-8") if exp_path.exists() else None
                with open(exp_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(got)
                state = "unchanged" if old == got else ("written" if old is None else "UPDATED")
                print(f"{state:9s} {stem:16s} -> {exp_path.relative_to(ROOT)}")
                continue
            if not exp_path.exists():
                failures += 1
                print(f"FAIL  {stem:16s} no expected output; run with --update to create it")
                continue
            expected = exp_path.read_text(encoding="utf-8")
            if got == expected:
                print(f"ok    {stem:16s} {len(got.splitlines()):5d} lines")
                continue
            failures += 1
            diff = list(difflib.unified_diff(
                expected.splitlines(), got.splitlines(),
                fromfile=f"expected/{stem}.md", tofile=f"current/{stem}.md", lineterm="", n=2))
            print(f"FAIL  {stem:16s} output differs ({len(diff)} diff lines)")
            shown = diff if args.verbose else diff[:40]
            for line in shown:
                print("      " + line)
            if len(shown) < len(diff):
                print(f"      ... {len(diff) - len(shown)} more lines (use -v)")

    # The CLI must survive a console that cannot encode every character
    # (Windows cp1252): it once crashed after the first file of a batch.
    if run_cli:
        failures += check_cli_console(sorted(FIXTURES.glob("*.pdf"))[0])
        with tempfile.TemporaryDirectory(prefix="markerlite-lowyield-") as td:
            failures += check_low_yield(pathlib.Path(td))
            failures += check_conservation(pathlib.Path(td))
            failures += check_garbled(pathlib.Path(td))
            failures += check_cell_matrix(pathlib.Path(td))
            failures += check_flag_figures(pathlib.Path(td), update=args.update)

    if not args.names or "all_text_wrapped" in args.names:
        import unittest
        from test_table_wrap import WrappedCellsTests
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(WrappedCellsTests)
        result = unittest.TextTestRunner().run(suite)
        failures += not result.wasSuccessful()

    if args.update:
        return int(bool(failures))
    if failures:
        print(f"\n{failures} fixture(s) differ. If the change is intended: "
              f"python tests/regress.py --update")
        return 1
    print("\nall fixtures match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
