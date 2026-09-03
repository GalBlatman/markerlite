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
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import markerlite  # noqa: E402  (after sys.path)

FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = ROOT / "tests" / "expected"

# Fixtures with no text layer: their output depends on the OCR engine.
NEEDS_TESSERACT = {"scanned"}


def convert_to_string(pdf: pathlib.Path, workdir: pathlib.Path) -> str:
    out, _info = markerlite.convert(pdf, workdir)
    return out.read_text(encoding="utf-8")  # universal newlines -> "\n"


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

    if args.update:
        return 0
    if failures:
        print(f"\n{failures} fixture(s) differ. If the change is intended: "
              f"python tests/regress.py --update")
        return 1
    print("\nall fixtures match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
