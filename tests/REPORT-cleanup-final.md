# Cleanup final report

The approved cleanup through Phase 5b is complete. The final verified source
commit is `d33f10c`. No tag was created. Conversion behavior stayed fixed to
the v0.1.14 golden baseline.

## Production lines: v0.1.14 and final

Production here means the converter package, the two compatibility shims, and
the GUI. It excludes tests, generated fixtures, build tools, documentation,
and the vendored `table_recon.py`.

| Source | v0.1.14 lines | Final lines |
|---|---:|---:|
| root `markerlite.py` | 4,197 | 12 |
| root `table_wrap.py` | 148 | 10 |
| `markerlite_gui.py` | 816 | 924 |
| `markerlite/` owned modules | 0 | 5,276 |
| **Total** | **5,161** | **6,222** |

The final package total is:

| Module | Lines |
|---|---:|
| `markerlite/__init__.py` | 47 |
| `markerlite/api.py` | 156 |
| `markerlite/classification.py` | 389 |
| `markerlite/cli.py` | 104 |
| `markerlite/extraction.py` | 643 |
| `markerlite/figures.py` | 801 |
| `markerlite/gui_logic.py` | 60 |
| `markerlite/model.py` | 395 |
| `markerlite/processors.py` | 883 |
| `markerlite/render.py` | 419 |
| `markerlite/stats.py` | 249 |
| `markerlite/table_wrap.py` | 176 |
| `markerlite/tables.py` | 822 |
| `markerlite/thresholds.py` | 132 |
| **Package total** | **5,276** |

Movement and deletion are different parts of that change. At the Phase 3
boundary, before Ruff formatting changed physical line breaks, 4,180 lines
moved out of root `markerlite.py` into owned modules. The 148-line
`table_wrap.py` implementation also moved into the package, with a 10-line
root import shim retained. Normalized AST fingerprints matched for all 137
pre-existing functions and methods: zero changed, missing, or added function
bodies at that move.

Phase 2 deleted six production lines, each independently proven output-inert
against all 77 golden entries on the scratch audit branch:

| Phase 2 deletion | Production lines removed |
|---|---:|
| unused reconstruction `score` unpack in `detect_tables` | 1 |
| unused `FOOTNOTE_START` plus its stale comment | 4 |
| unused `page` local in `proc_continuation` | 1 |
| **Production deletion** | **6** |

Phase 2 also removed one unused fixture local and simplified one test helper
signature without removing a whole line. The suspected fallback grid/HTML
path was retained because its scratch deletion changed fixture Markdown and
stats. No other production candidate survived the scratch audit. Relative to
v0.1.14, the final tree therefore has 6 proven production deletions and 1,067
additional physical lines from compatibility shims, formatting, typed stats,
named/calibrated thresholds, package initialization, and the extracted pure
GUI helpers. The large root-file reduction is relocation rather than deletion.

## Golden output contract

The local WSL run used Python 3.14, PyMuPDF 1.28.2, and Tesseract 5.5.0, the
versions recorded by the manifest.

| Gate | Result |
|---|---:|
| generated fixtures and option modes | 41/41 matched |
| repository real PDFs | 11/11 matched |
| Packet A/B logical inputs, read in place | 25/25 matched |
| **Complete local corpus** | **77/77 matched** |
| OCR entries skipped | 0 |

Every WSL Markdown byte hash, canonical complete-stats hash, hand-off JSON
hash, and binary crop hash matched v0.1.14. The full corpus was resolved from
`/home/galbl/unknown-knowns-markerlite-v0112` and
`/home/galbl/unknown-knowns`; no source PDF was copied into the repository.

Windows writes text files with CRLF while the manifest was recorded on WSL
with LF. The golden verifier now canonicalizes newlines only when hashing
generated `.md`, `.json`, and `.txt` artifacts. This made the cross-platform
comparison meaningful without changing converter output. Binary artifacts
remain byte-hashed, and the canonical stats object remains exact. The
converter's file-writing code was not changed.

`python tests/regress.py` passed every fixture check. Ruff format and the
enabled `E4`, `E7`, `E9`, `F`, and `I` checks passed. Pytest passed all 21
direct tests, including the pure GUI option, output-directory, warning,
summary, and provenance helpers. No fake Tk widget tests were added.

## Coverage before and after

Both measurements used branch coverage and the full local corpus. The Phase 1
baseline included the monolith, GUI, and wrapped-table module. The final
measurement includes every owned package module, the root compatibility
module, and the same GUI limitation.

| Measure | Phase 1 | Final |
|---|---:|---:|
| statements | 3,216 | 3,467 |
| missed statements | 758 | 703 |
| branches | 1,518 | 1,520 |
| partial branches | 88 | 83 |
| **combined coverage, including unimported Tk GUI** | **78%** | **81%** |

The loaded converter/package aggregate is 94%; its module results range from
89% for wrapped-table recovery to 100% for API initialization, GUI logic, and
thresholds. The new `markerlite/gui_logic.py` has 100% coverage. The local WSL
interpreter has no Tk installation, so all 567 statements in
`markerlite_gui.py` remain unexecuted locally and are validated by static
method checking and the Windows executable tests rather than fake-widget
coverage. CLI is 19% because subprocess execution is recorded separately from
the coverage process. Even with the deliberately unimported Tk module included,
combined coverage rose from 78% to 81%.

## CI and local platform checks

Both GitHub workflows are green on `d33f10c`:

- Ubuntu: [run 36632595078](https://github.com/GalBlatman/markerlite/actions/runs/36632595078)
  passed locked installation, generated-agent sync, Ruff, tests with coverage,
  fixture regression, and golden fixture hashes.
- Windows: [run 36632595179](https://github.com/GalBlatman/markerlite/actions/runs/36632595179)
  passed the same source gates, the PyInstaller build, converter smoke test,
  diagnostic launch, embedded-icon check, archive construction, and artifact
  upload.

The first Phase 5b Windows run exposed a CI race: PowerShell checked for the
diagnostic file before the windowed child process finished writing it. Commit
`d33f10c` uses `Start-Process -Wait`, checks the diagnostic process exit code,
and then reads the file. The replacement run passed.

The local Windows build used PyInstaller 6.22.3 under Python 3.14.7 on Windows
11. A normal GUI launch remained alive for the smoke interval and was then
closed. `markerlite.exe --diag` completed and reported:

- `frozen=True`, Windows 11 AMD64;
- Tcl/Tk 9.0.4;
- `HAVE_DND=True` and `TkinterDnD.Tk() OK` with tkdnd 2.10.2.

`tools/check_exe_icon.py` found all seven expected `RT_ICON` payloads and
matched them byte-for-byte to `assets/icon.ico` at 16, 24, 32, 48, 64, 128,
and 256 pixels. `python check_gui.py` reported 33 `App` methods and all 18
`self` calls resolved.

## Locked clean install

A new virtual environment at `/tmp/markerlite-final-clean-3cded35` installed
the project from a built wheel with `requirements-lock.txt` as constraints.
It resolved the exact runtime versions in the lock, including NumPy 2.5.3,
PyMuPDF 1.28.2, RapidFuzz 3.14.6, regex 2026.9.29, and scikit-learn 1.9.1.

From `/tmp`, outside the checkout's import path:

```text
markerlite --version
markerlite 0.1.14
```

The installed package converted `table_only_footer.pdf`, reported metadata
version `0.1.14`, and produced Markdown SHA-256
`dc439f015fabc04aaafa24d43299e8abc4d4890d95d5702207e21c6797d87db7`,
exactly matching the v0.1.14 golden manifest. Its complete stats object also
matched through the 77-entry full-corpus gate.
