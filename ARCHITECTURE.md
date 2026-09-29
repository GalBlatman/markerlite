# Architecture

`markerlite` is an offline PDF-to-Markdown pipeline. The public API is
`markerlite.convert()`; `markerlite` is also the installed console command.
Root `markerlite.py` and `table_wrap.py` are compatibility shims for existing
source checkouts.

The package follows the conversion order:

1. `extraction.py` reads PyMuPDF's unsorted character stream, repairs known
   font problems, decides whether OCR is needed, and records provenance.
2. `tables.py` finds table regions and uses the vendored root
   `table_recon.py`; `table_wrap.py` conservatively reattaches wrapped cells.
3. `classification.py` labels blocks without changing their stream order.
4. `processors.py` applies reflow, furniture, footnote, heading, continuation,
   list, equation, and caption rules in the order called by `api.py`.
5. `figures.py` locates figures and raster equations and owns the crop/apply
   hand-offs.
6. `render.py` emits Markdown. `stats.py` builds the stable reporting schema.

`model.py` owns the page/block/line/span records and text patterns.
`thresholds.py` owns calibrated numeric behavior gates. A threshold change is
a behavior change: verify its fixture and motivating real document rather than
folding it into refactoring.

The safety boundary is `tests/golden/v0.1.14.json`. It hashes Markdown,
canonical stats, hand-off manifests, and crops for generated fixtures, local
reference PDFs, and the external Packet corpus. OCR hashes compare only when
the Tesseract version matches. `tests/regress.py` retains readable Markdown
diffs and specialized structural checks.

`requirements-lock.txt` pins CI and repeatable pipeline environments;
`pyproject.toml` contains compatible ranges for normal installation. The
Windows workflow builds the onedir GUI, launches it with `--diag`, and verifies
all icon resources. The Ubuntu workflow runs Tesseract-backed tests and
coverage. Releases remain tag-triggered and tags are created only by the
maintainer.
