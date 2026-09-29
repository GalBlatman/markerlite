# Tesseract discovery follow-up

## Defect

v0.1.14 used `shutil.which("tesseract")` independently in OCR and the GUI.
The UB-Mannheim installer defaults to `C:\Program Files\Tesseract-OCR`; when
that directory was not added to `PATH`, the GUI reported “Tesseract not found”
and scanned pages emitted no OCR text even though Tesseract was installed.

## Implementation

`markerlite.extraction.discover_tesseract()` is the single discovery path used
by OCR and the GUI. Its order is:

1. `TESSERACT_CMD`;
2. `PATH`;
3. `HKLM\SOFTWARE\Tesseract-OCR` and
   `HKCU\SOFTWARE\Tesseract-OCR`, value `InstallDir`;
4. `%ProgramFiles%\Tesseract-OCR`;
5. `%ProgramFiles(x86)%\Tesseract-OCR`;
6. `%LOCALAPPDATA%\Programs\Tesseract-OCR`.

OCR invokes the returned full path. The GUI status shows the version and path,
and its missing state directs the user to install Tesseract or set
`TESSERACT_CMD`. `--diag` records the same version and path. Conversion info
records them under top-level `tesseract` metadata beside `stats`; they are kept
outside document stats because an absolute executable path is machine state
and would violate the required unchanged stats hashes.

## Verification

The injected unit suite covers the environment override, PATH, registry,
Program Files, 32-bit Program Files, LocalAppData, missing executable, version
output, and version failure. The Windows workflow installs Tesseract, removes
both the installer and Chocolatey directories from `PATH` for the discovery
check, asserts `--diag` reports the default install path, and converts
`scanned.pdf` with two OCR pages and more than 100 words.

Locally in WSL, Tesseract 5.5.0 was discovered through PATH. Pytest,
`check_gui.py`, and the fixture regression passed. All 41 fixture/mode golden
entries matched v0.1.14, including the OCR entries; zero OCR entries were
skipped. Markdown, document stats, and artifacts are unchanged.
