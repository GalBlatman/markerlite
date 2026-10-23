# Menus, preferences and block 2 stop 3

## Scope and starting point

Requested order: A1–A5, then B1–B5, one commit per item. Starting
main: 55a9a22. Baseline: tests/golden/v0.1.18.json, 89 entries.
Pipeline sources are read in place under /home/galbl/unknown-knowns.
No release or default-grid decision is part of this work.

## A1 — menu bar and shared commands

Adds native File, Edit, View, Tools and Help menus, Alt mnemonics,
keyboard shortcuts, a ten-file recent list with missing files disabled,
saved System/Light/Dark selection (MARKERLITE_THEME wins), preview font
size, and About/license links. Main-menu row commands use the existing
context-menu handlers and enablement; Convert, Cancel, folder commands
and Clear call the existing button handlers. Selection removal changes
only in-memory rows. Exit waits for cancellation before closing.

The initial Preferences window exposes the shared theme choice; A4
extends it with the remaining app-wide settings. Check OCR and Check
for updates are extended under A3 and A2 respectively.

Validation: actual Tk App construction and menu refresh passed;
check_gui.py passed; existing GUI logic/status/menu tests passed (47).
The full archived-commit golden log is recorded after each commit.

## A2 — user-initiated update check

Help → Check for updates makes one HTTPS GET to the GitHub latest-release
endpoint, with a ten-second timeout and no redirect, retry or polling.
The worker returns through the existing Tk event queue; closing the app
waits for it. Numeric version comparison distinguishes 0.1.10 from 0.1.9.
An update offers its tag page; failures offer Releases. Invalid replies,
HTTP errors and offline/timeout paths are tested using injected transports.
No network requests occur in tests. SECURITY.md and README describe this
single optional request and browser hand-off.

## A3 — Check OCR

Tools → Check OCR and the header's Tesseract label invoke the same window.
It displays discovery status, full executable path, version and recovery
instructions. Versions below 5.0 are labelled outdated; missing/outdated
installs offer the Windows download page through the OS browser. Opening
this window performs local discovery and --version only; it fetches nothing.
Six pure tests cover missing, unreadable, old and current engines.

## A4 — app-wide preferences

Output defaults and Explorer integration move into Preferences; the main
Options panel retains only per-run conversion flags. Preferences also
holds automatic output opening, automatic conversion of Explorer inputs,
a validated Tesseract override and the same theme setting as View.
Schema 2 settings live in %APPDATA%/markerlite/settings.json; schema 1
(theme/recents) migrates with defaults. Corrupt/unknown settings log one
reset message and use defaults. Writes replace a temporary JSON file.
OCR overrides run --version locally and apply between batches, preserving
the active batch's engine. Reset selects defaults; Save applies them.
Tests cover round trips, migration, corrupt/unknown data, invalid field
types, recent-file bounds, and executable validation/failures.

## A5 — tests and UI verification

Pure tests cover shared menu enablement, all terminal Clear finished
states, recents, settings round trips/migration/corruption, OCR executable
validation/version flags, and update replies and errors. Gap checks also
make Clear disable during conversion and make the output-folder/Markdown
buttons disable when the last output row is removed. No fake-widget tests
are used. Actual Tk construction of all five menus, Preferences and Check
OCR passed under WSL.

Windows screenshots are currently blocked: the desktop is locked. The
native App was launched with only hard.pdf and isolated temporary settings;
the attempted capture showed the lock screen, so that image was discarded.
No menu, Preferences, Check OCR or update-dialog screenshots are claimed
in either theme. No Linux or mocked-dialog screenshots substitute for them.
The owner has been asked to unlock the desktop; capture can then resume.

Final local Part A checks: 271 unit tests passed; three named-pipe tests
are Windows-only and skipped under WSL. The pinned sv-ttk sprite test ran.
All fixture regressions passed. Ruff check/format and check_gui.py passed.
A1's archived golden audit passed 89/89 with zero OCR skips. The other
per-commit audit logs are retained in tests/audits/ as each run finishes.
Windows CI now captures the real source App's five menus, Preferences,
Check OCR and the actual update-check result in both themes, using only
hard.pdf and temporary settings. Its gui-screenshots artifact still needs
visual review; unavailable desktop states are explicitly recorded.

The first Windows screenshot attempt exposed a harness issue: native
Windows menu.post() blocks, and Tk menu.unpost() does not dismiss it.
The corrected harness captures cached window bounds in a worker, touches
no Tk widgets there, then posts WM_CANCELMODE and native Escape messages only to its own
window and joins the worker. No global keyboard input is injected. References: [Tk menu manual](https://www.tcl-lang.org/man/tcl8.7/TkCmd/menu.html) (unpost) and [Microsoft WM_CANCELMODE](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-cancelmode).
This changes verification tooling only; app commands are unaffected.

The successful 3e230c1 Windows capture produced all 16 requested states
(ten menus plus Preferences, Check OCR and the live update result in both
themes). Visual review found that the short update message allowed its title to
truncate. This is corrected before final capture. Dialog and menu colours
are also explicitly tied to the selected palette, including muted disabled
menu text, so fallback themes remain consistent. The capture
helper now uses visible DWM frame bounds to exclude the runner console
behind the invisible resize border, and posts each menu below its own
native menu-bar item. Save diagnostics writes directly to the selected
file, so it also works when the executable's folder is read-only.
