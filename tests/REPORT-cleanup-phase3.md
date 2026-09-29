# Cleanup phases 1-3 report

The approved cleanup stopped after phase 3.  The output contract held: every
recorded Markdown byte stream, canonical stats object, hand-off manifest, and
crop hash is unchanged from the v0.1.14 baseline.

## Commits and gates

| Step | Commit | Result |
|---|---|---|
| plan amendments | `a799516` | approved amendments incorporated before code work |
| phase 1 | `a59ff9e` | golden safety net, coverage, and unobservable-code audit |
| phase 2 | `daddf49` | only scratch-proven output-inert code deleted |
| phase 3 | this commit | mechanical package split; no function-body change |

The final phase-3 verification used PyMuPDF 1.28.2 and Tesseract 5.5.0,
matching the versions recorded in `tests/golden/v0.1.14.json`.

| Golden scope | Result |
|---|---:|
| generated fixtures and option modes | 41/41 matched |
| complete local suite (fixtures, 11 real documents, 25 Packet inputs) | 77/77 matched |
| OCR entries skipped for version mismatch | 0 |

`python tests/regress.py` also passed every fixture check after the move.  The
full-corpus command read Packet sources from
`/home/galbl/unknown-knowns-markerlite-v0112` and
`/home/galbl/unknown-knowns`; no source PDF was copied into the repository.

## Mechanical package split

Before phase 3, root `markerlite.py` was 4,193 lines.  It is now a 13-line
compatibility/CLI shim.  Root `table_wrap.py` is a 10-line import shim; the
implementation moved without edits to `markerlite/table_wrap.py`.

| Module | Lines | Functions/methods |
|---|---:|---:|
| `markerlite/__init__.py` | 34 | 0 |
| `markerlite/api.py` | 161 | 1 |
| `markerlite/classification.py` | 368 | 12 |
| `markerlite/cli.py` | 83 | 1 |
| `markerlite/extraction.py` | 549 | 16 |
| `markerlite/figures.py` | 662 | 19 |
| `markerlite/model.py` | 412 | 21 |
| `markerlite/processors.py` | 734 | 24 |
| `markerlite/render.py` | 382 | 15 |
| `markerlite/stats.py` | 124 | 4 |
| `markerlite/table_wrap.py` | 148 | 5 |
| `markerlite/tables.py` | 703 | 21 |
| root `markerlite.py` shim | 13 | 0 |
| root `table_wrap.py` shim | 10 | 0 |
| **total** | **4,383** | **139 source definitions / 137 unique fingerprints** |

The definition count is two above the fingerprint count because identical
nested helper names share the same normalized body.  Phase 4 has not started:
shared constants deliberately remain in `model.py`, and stats remain the same
public dictionaries.

The vendored `table_recon.py` SHA-256 was
`04d398465ac6b55976086ea4a1fdabb0d883b6790a449c35c15c7ceb57232af1`
before and after the split.

## AST fingerprints

`tests/ast_fingerprint.py` hashes `ast.dump(..., include_attributes=False)`
for every function and method.  The before-move fingerprint file had SHA-256
`cb5a04d654ebbb494429afe24e61934b29f7d28f66f8fbd5ece1d00b730a3672`.

| Measure | Before | After |
|---|---:|---:|
| unique function/method fingerprints | 137 | 137 |
| exact matches | 137 | 137 |
| changed | 0 | 0 |
| missing | 0 | 0 |
| added | 0 | 0 |

Mismatch table:

| Function | Before | After |
|---|---|---|
| _none_ | — | — |

The new compatibility shims and package imports contain no moved function
bodies, so they need no exception from the comparison.

## Unobservable-code findings and phase-2 deletions

Every candidate below was first deleted alone on the scratch audit branch and
run through all 77 golden entries.  Phase 2 then made only the proven-safe
deletions.

| Candidate | Scratch result | Phase-2 result | Lines saved |
|---|---|---|---:|
| unused `detect_tables` reconstruction score | 77/77 matched | stop unpacking the unused score | 1 |
| unused `FOOTNOTE_START` and stale comment | 77/77 matched | deleted | 4 |
| unused `proc_continuation` page local | 77/77 matched | deleted | 1 |
| unused fixture `foot_notes` local | 77/77 matched | deleted | 1 |
| unused `guarded` test argument | 77/77 matched | removed from signature and call | 0 whole lines |

The proposed removal of fallback `_grid_from_members` / `_grid_to_html`
construction failed the fixture gate: `continued_table_header.pdf` changed
both Markdown and stats.  That path remains because it supplies the cell-word
baseline, sanity/admission result, and fallback decision.  Static-reference
and Ruff checks found no other compute-then-discard production result whose
removal preserved the golden hashes.

## GUI and executable verification

- `check_gui.py`: `OK: App defines 33 methods; all 18 self-calls resolve.`
- A fresh Windows onedir build completed with PyInstaller 6.22.3 under Python
  3.14.7.
- `dist/markerlite/markerlite.exe --diag` exited successfully on Windows 11
  AMD64.  It reported `frozen=True`, Tcl/Tk 9.0.4, `HAVE_DND=True`, and
  `TkinterDnD.Tk() OK (tkdnd 2.10.2)`.
- The executable contains seven `RT_ICON` resources.  Their payloads match
  `assets/icon.ico` exactly at 16, 24, 32, 48, 64, 128, and 256 pixels.

`py_compile` passed for both root shims, every package module, and the new
golden/fingerprint utilities.  `git diff --check` reported no whitespace
errors.  No tag was created.
