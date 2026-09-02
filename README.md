# markerlite — Marker's document understanding, without the weights

[Marker](https://github.com/datalab-to/marker) needs downloaded model weights
for five of its stages. markerlite is a reimplementation of the parts that
don't, plus weight-free substitutes for the parts that do.

It runs offline, on CPU, with no model downloads.

## What it is genuinely good at

- **Reading order on multi-column pages.** This is the main reason it exists.
  Marker orders text-layer pages by PDF character-stream position rather than by
  its learned reading-order head; the same signal is available from PyMuPDF, and
  it is what keeps a two-column journal article from interleaving its columns.
- **Running headers, footers and page numbers**, suppressed on evidence of
  repetition across pages rather than on position alone.
- **Paragraph flow** — text rejoined across line, column and page breaks, with
  hyphenation undone.
- **Headings**, with levels taken from section numbering when the document
  numbers its sections, and from font-size clustering otherwise.
- **Lists**, including nesting depth from indentation.
- **Footnotes**, as labeled definitions (`[^1]: ...`) with the in-text
  superscript emitted as the matching reference (`[^1]`). Notes wrapped across
  lines or blocks are merged; a superscript with no matching note (an exponent)
  is left as `<sup>`.

That set is reliable. What follows is not, and is described honestly because
the failure modes are quiet ones.

## What is partial

**Tables.** Sometimes excellent, sometimes wrong. Borderless and scanned tables
often reconstruct correctly; tables with tall multi-line cells can assign
content to the wrong row, which shifts values silently. Sanity checks reject the
worst reconstructions, but not all of them. **Verify any table you intend to
read as data.** This is not yet a feature to advertise.

**Figures.** Embedded raster images are extracted reliably. Vector drawings —
plotted charts, diagrams, flowcharts — are detected heuristically by clustering
path operators and rendering the region, which works on typical charts but will
miss some and occasionally capture something that isn't a figure. Figures are
placed at their position in the page, with adjacent captions attached.

**Equations.** markerlite does **not** convert formulas. The `$$` blocks hold a
text-layer approximation — the glyphs in reading order, not LaTeX. What it does
is find equation regions and crop them (`--flag-math`), so a vision model can
transcribe them; `--apply-math` splices the results back in. Detection uses
glyph content, equation numbering and display placement, so it catches
Symbol+Times equations that font-name matching misses, but it is not exhaustive.

**Scanned PDFs** are detected automatically and OCR'd through Tesseract, using
its own page segmentation so two-column scans keep their columns. The output
inherits Tesseract's errors — large display type is sometimes misread, and a
page number can land mid-text — so it is readable, not clean.

**Heading recovery on real journal articles** is decent but not complete. A
document that styles every heading identically, with no numbering, gives the
classifier little to work with, and some headings will come through as ordinary
paragraphs.

## What it will not do

Inline math inside a paragraph is not detected at all. Marker needs an LLM for
that too — its `line_merge.py` is a no-op unless `use_llm` is set.

## Get it

Two ways in. Pick whichever fits.

### A. The Windows app — no Python, no terminal

Download `markerlite-windows.zip` from the
[Releases page](https://github.com/GalBlatman/markerlite/releases/latest),
unzip it, open the `markerlite` folder and run **`markerlite.exe`**. Keep the
folder together — the files beside the exe are part of the program.

The first time, Windows SmartScreen will show a blue *"Windows protected your
PC"* dialog. That is what every unsigned program from a new publisher gets; it
is not a detection. Click **More info**, then **Run anyway**. It asks once.

The app does not include Tesseract, so scanned PDFs (no text layer) will fail
with a clear message. Digital PDFs — nearly everything from a publisher — work
without it. To add scanned support, install the
[UB-Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)
and tick "add to PATH".

### B. From source — any OS, and no SmartScreen prompt

Nothing is unsigned here because you run the code with your own Python.

```bash
pip install pymupdf scikit-learn rapidfuzz regex numpy
pip install tkinterdnd2          # optional: drag-and-drop in the GUI
# optional, for scanned PDFs:
#   apt install tesseract-ocr      (Linux / WSL)
#   brew install tesseract         (macOS)
#   UB-Mannheim installer          (Windows)
```

Then either launch the same GUI the app provides:

```bash
python markerlite_gui.py
```

or use the command line, below.

## Use

### The app

Drop PDFs onto the window — files, or a folder to take every PDF in it — and
click **Convert**. Output goes next to each PDF by default, or to one folder you
pick. The checkboxes are the command-line flags: extract images, crop equations,
insert page markers. The preview pane shows the Markdown of whichever file is
selected; read it before trusting a document, because the table and heading
defects described above are quiet. **Open Markdown** and **Open output folder**
do what they say. When a batch finishes, the status line reports it as
`17 pages → 76 KB Markdown · 3 figures · 2 equation crops`.

### The command line

```bash
python3 markerlite.py paper.pdf -o md_out
python3 markerlite.py *.pdf -o md_out --images --page-markers
python3 markerlite.py paper.pdf -o md_out --flag-math
python3 markerlite.py --apply-math md_out/paper_math.json -o md_out
```

| Flag | Effect |
| --- | --- |
| `-o DIR` | output directory (default `md_out`) |
| `--images` | extract figures (rasters and vector drawings) and link them |
| `--flag-math` | crop equation regions and write a JSON manifest |
| `--apply-math J` | splice transcribed LaTeX from a filled manifest into the `.md` |
| `--page-markers` | emit `<!-- page N -->` at each page boundary |

Page markers cost almost nothing in context and let you ask an LLM where in the
source PDF something appeared.

`INSTALL.md` walks through the WSL setup; `WINDOWS-GUI.md` covers the native
Windows install, the launcher, and building the exe yourself.

## Python API

```python
import sys, pathlib
sys.path.insert(0, "/path/to/markerlite")   # it does `from table_recon import ...`
from markerlite import convert, summarize

out_path, info = convert(pathlib.Path("in.pdf"), pathlib.Path("outdir"),
                         images=False, do_flag_math=False, page_markers=False)
print(summarize(info["stats"]))
# 17 pages → 76 KB Markdown · 3 figures · 2 equation crops
```

## Two bugs found in Marker's own code

1. `sectionheader.py` sorts its `(height, cluster)` array with
   `np.sort(..., axis=0)`, which sorts the two columns independently and
   scrambles the value→cluster pairing, permuting heading levels.
2. KMeans is asked for four clusters regardless of how many distinct heading
   sizes exist, so it splits one size and invents a level.

Both are fixed in markerlite.

## Licensing

`table_recon.py` is vendored from Marker (Apache-2.0); see
`LICENSE-marker-Apache-2.0`. Everything else is original.

## Performance

~1–2s per page for digital PDFs, ~15s per page for scanned ones.
