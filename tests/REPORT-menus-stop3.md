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
