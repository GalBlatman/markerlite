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
                   "ebsco_notice_scan"}


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
