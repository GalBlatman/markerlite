# markerlite — install and use (Windows / WSL)

Standalone. No model weights, no network access at runtime, no `marker-pdf`
install required.

## 1. Install

From a WSL terminal:

```bash
sudo apt update && sudo apt install -y tesseract-ocr
pip install pymupdf scikit-learn rapidfuzz regex numpy
```

`tesseract-ocr` is only needed for scanned PDFs (no text layer). Skip it if your
PDFs are digital publications — everything else works without it.

## 2. Convert

```bash
cd /path/to/markerlite
python3 markerlite.py ~/papers/smith2024.pdf -o ~/papers/md
```

Multiple files and globs work:

```bash
python3 markerlite.py ~/library/*/*.pdf -o ~/papers/md
```

Options:

| Flag | Effect |
| --- | --- |
| `-o DIR` | output directory (default `md_out`) |
| `--images` | extract figures (rasters and vector drawings) to `DIR/<stem>_images/` and link them |
| `--page-markers` | emit `<!-- page N -->` at each page boundary |
| `--flag-math` | crop each equation region to `DIR/<stem>_math/` and write a manifest |
| `--apply-math JSON` | splice transcribed LaTeX from a filled-in manifest back into the `.md` |

## 3. The equation pass

Equations are the one thing no weight-free heuristic can read. The text layer
gives you `ρ = λ µ, 0 < ρ < 1. (1)` — the glyphs, without the structure.

```bash
python3 markerlite.py paper.pdf -o md_out --flag-math
```

This writes `md_out/paper_math.json` with one entry per equation, each pointing
at a cropped PNG and carrying an empty `"latex"` field. Fill those in — by hand,
or by handing the crops to any vision model — then:

```bash
python3 markerlite.py --apply-math md_out/paper_math.json -o md_out
```

Each `$$` block in the markdown is replaced in place with your LaTeX.

## 4. If you want the real Marker as well

If you want the original with its full model pipeline:

```bash
pip install marker-pdf
marker_single paper.pdf --output_dir out --output_format markdown
```

First run downloads roughly 2GB of weights. On CPU expect somewhere around
10–30s per page — slow enough that markerlite is the better default for bulk
work, with Marker reserved for pages where equation quality actually matters.
If you have an NVIDIA GPU in WSL, Marker gets dramatically faster and becomes
the better choice outright.

## Files

- `markerlite.py` — the converter
- `table_recon.py` — vendored from Marker (Apache-2.0), table grid reconstruction
- `LICENSE-marker-Apache-2.0` — Marker's license, covering the vendored file
