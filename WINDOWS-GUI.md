# markerlite on Windows — the drag-and-drop app

This runs natively on Windows. WSL is not involved: markerlite is pure Python,
and the only external piece is the Tesseract binary, which has a Windows build.
A WSL or Linux install, if you have one, is unaffected — this is an
independent copy.

## 1. Python

Install Python 3.12 or 3.13 from [python.org](https://www.python.org/downloads/).
**Tick "Add python.exe to PATH"** on the first screen — the launcher script
depends on it.

Verify in PowerShell:

```powershell
python --version
```

## 2. Dependencies

```powershell
pip install pymupdf scikit-learn rapidfuzz regex numpy tkinterdnd2
```

`tkinterdnd2` is what makes the drop zone accept files. Without it the app still
runs — the drop zone becomes a click-to-browse button — so it's recommended, not
required.

## 3. Tesseract (only for scanned PDFs)

Grab the installer from the
[UB Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki) and tick the
option to add it to PATH. Skip this if your PDFs are all digital — everything
else works without it, and scanned files simply fail loudly rather than
producing garbage.

## 4. Put the files somewhere permanent

Copy the whole folder to something like `C:\Tools\markerlite\`. It needs to keep
these together:

```
markerlite_gui.py     the app
markerlite.py         the converter
table_recon.py        table grid reconstruction (vendored from Marker)
markerlite.bat        launcher
```

## 5. Run it

Double-click **`markerlite.bat`**. That uses `pythonw`, so no black console
window appears behind the app.

To pin it: right-click `markerlite.bat` → **Show more options** → **Send to** →
**Desktop (create shortcut)**. Then right-click the shortcut → Properties →
**Change Icon** if you want something better than the default.

## Using it

- **Drop PDFs** onto the zone at the top — files or whole folders. Dropping a
  folder adds every PDF in it. Or click the zone to browse.
- **Output**: either next to each original PDF, or one fixed folder you pick.
- **Extract images** pulls figures out to `<name>_images\` and links them.
- **Crop equations** writes `<name>_math\` plus a JSON manifest — the crops are
  what you hand to a vision model to get real LaTeX, since the `$$` blocks in
  the markdown are only a text-layer approximation.
- **Preview** shows the converted markdown for whichever file you select. Worth
  actually reading before you trust a document — see the known failure modes in
  README.md, particularly around tables and heading levels.
- Files convert one at a time on a background thread. One failure doesn't stop
  the batch; that file just shows `failed`, and selecting it shows the error.

## If drag-and-drop doesn't work

From source, drag-and-drop needs `tkinterdnd2` in the **same** Python that
runs the app. The status line at the bottom of the window says so when it is
missing; the fix is `pip install tkinterdnd2`. The exe has it built in.

For anything else, run the app with `--diag`:

```powershell
.\markerlite.exe --diag
```

It writes `markerlite-diag.txt` next to the exe (or next to `markerlite_gui.py`
from source) with the Python and Tcl versions, whether the drag-and-drop
library loaded, and the exact error if it did not.

## If it doesn't start

Double-clicking does nothing and no window appears: `pythonw` isn't on PATH.
Open `markerlite.bat` in Notepad and replace `pythonw` with the full path, e.g.
`C:\Users\<you>\AppData\Local\Programs\Python\Python312\pythonw.exe`.

To see the error instead of a silent failure, run it from PowerShell:

```powershell
python C:\Tools\markerlite\markerlite_gui.py
```

## A single .exe (no Python needed)

Double-click **`build_exe.bat`**. It installs PyInstaller, builds, and leaves
a folder at `dist\markerlite\` with `markerlite.exe` inside. Takes a couple
of minutes, once.

The result needs no Python on any machine you copy it to. Copy the **whole
folder** — the DLLs beside the exe are part of the program. It is large (~150MB,
mostly scikit-learn and PyMuPDF). A folder build is used rather than a single
self-extracting file because it starts in about a second and draws fewer
antivirus false positives.

### "Windows protected your PC"

The first time you run the exe, Windows SmartScreen shows a blue dialog saying
it *prevented an unrecognized app from starting*. This is not a detection of
anything wrong — it appears for every executable that has not been signed with
a paid code-signing certificate, from any publisher Windows has not seen
before.

To run it: click **More info**, then **Run anyway**. Windows asks once per
file and then remembers.

If you would rather not click through that, the alternative is the Python
route above: nothing is unsigned there, because you are running the source
with your own Python.

**The .exe does not include Tesseract.** Digital PDFs — nearly everything from a
publisher — work fine without it. Scanned PDFs need Tesseract installed
separately and on PATH, and will fail with a clear message otherwise.

If you would rather not build at all, download the current build from the
repository's **Releases** page: unzip, open the `markerlite` folder, run
`markerlite.exe`. Each release is produced by
`.github/workflows/build-windows.yml` on a GitHub Actions Windows runner when a
version tag is pushed.
