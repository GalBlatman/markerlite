"""Read-only real-document audit; no PDF text is retained in the JSON snapshot.

Run with the reference PDFs present in tests/real/:
    python tests/audit_table_recovery.py --without-wrapped --output /tmp/before.json
    python tests/audit_table_recovery.py --output /tmp/after.json

The first command disables only wrapped recovery in this process; it does not
edit or copy the converter. Match regions by page, bbox, and source_digest.
"""

import argparse
from collections import Counter
from hashlib import sha256
from html import unescape
import inspect
import json
import pathlib
import re
import shutil
import sys
import tempfile
import unicodedata
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import markerlite  # noqa: E402


def words(text):
    """NFKC, entity decoding, whitespace split; retain case and punctuation."""
    return unicodedata.normalize("NFKC", unescape(text)).split()


def html_words(text):
    return words(re.sub(r"<[^>]*>", " ", text or ""))


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False).encode("utf-8")).hexdigest()


def errors(source, rendered):
    counter = Counter(html_words(rendered))
    return {"tokens": sum(counter.values()),
            "missing": sum((source - counter).values()),
            "duplicated_or_extra": sum((counter - source).values())}


def markdown_words(text):
    """CONTENT WORDS - the project's one word metric for real-document reports.

    Whitespace-split tokens of the Markdown after removing HTML comments
    (page/OCR/source markers), table separator rows, HTML tags, heading
    hashes, pipes, emphasis stars and $$ fences; NFKC-normalised. Every
    figure quoted in tests/REPORT-*.md from REPORT-kitchener.md onward uses
    this and nothing else (earlier reports mixed gross counts).
    Counts are not the historical gross-word metric. Keep normalization fixed
    across snapshots; this deliberately does not guess words from math glyphs.
    """
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"(?m)^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", " ", text)
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    text = text.replace("|", " ").replace("*", "").replace("$$", "")
    return len(words(text))


def capture(pdf, directory):
    records, cells = [], []
    source, start = inspect.getsourcelines(markerlite.detect_tables)
    decision_line = start + next(i for i, text in enumerate(source)
                                 if "page.tables_emitted += 1" in text)

    def trace(frame, event, arg):
        if frame.f_code is not markerlite.detect_tables.__code__:
            return None
        if event == "line" and frame.f_lineno == decision_line:
            state = frame.f_locals
            source_tokens = [token for block in state["members"] for line in block.lines
                             for token in words(line.text)]
            counts = Counter(source_tokens)
            reconstruction = state.get("res")
            records.append({
                "region": len(records) + 1,
                "page": state["page"].page_idx + 1,
                "bbox": list(state["bbox"]),
                "source_digest": digest(source_tokens),
                "source_tokens": len(source_tokens),
                "fallback": state["fell_back"],
                "reconstruction": errors(counts, reconstruction[0] if reconstruction else ""),
                "output": errors(counts, state["html"]),
            })
        return trace

    original_render = markerlite.render

    def render(pages, **kwargs):
        for page in pages:
            for block in page.blocks:
                if block.btype == "Table" and not block.ignore_for_output:
                    parser = markerlite._TableParser()
                    parser.feed(block.html)
                    cells.append({"page": page.page_idx + 1, "bbox": list(block.bbox),
                                  "cell_hashes": [[digest(cell) for cell in row]
                                                  for row in [parser.header, *parser.rows]]})
        return original_render(pages, **kwargs)

    previous_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        with patch.object(markerlite, "render", render):
            md, info = markerlite.convert(pdf, directory, page_markers=True)
    finally:
        sys.settrace(previous_trace)
    # The trace covers detect_tables; stats["tables"] also counts text-table
    # proposals accepted by propose_tables_from_text (stats["proposals"]).
    expected_records = info["stats"]["tables"] - info["stats"].get("proposals", 0)
    assert len(records) == expected_records, "incomplete decision trace"
    assert sum(r["fallback"] for r in records) == info["stats"]["tables_fallback"]
    return {"stats": info["stats"], "words": markdown_words(md.read_text(encoding="utf-8")),
            "regions": records, "tables": cells}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--without-wrapped", action="store_true")
    parser.add_argument("pdfs", nargs="*", help="audit only these PDFs")
    args = parser.parse_args()
    paths = [ROOT / "tests/real/Target-Validation-Protocol.pdf",
             ROOT / "tests/real/Ragins craft of clear writing 2012.pdf",
             ROOT / "tests/fixtures/paper.pdf", ROOT / "tests/fixtures/hard.pdf"]
    # Scanned reference documents need Tesseract; they are audited when present
    # and on PATH (WSL), and skipped otherwise.
    scans = [ROOT / "tests/real/suchman1995.pdf", ROOT / "tests/real/kostova1999.pdf",
             ROOT / "tests/real/kitchener2002.pdf"]
    if args.pdfs:
        paths = [pathlib.Path(x) for x in args.pdfs]
    elif shutil.which("tesseract"):
        paths += [x for x in scans if x.exists()]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        parser.error("missing local reference PDFs: " + ", ".join(missing))
    results = {}
    recovery = (lambda lines, original, *unused: original) if args.without_wrapped else (
        markerlite.recover_wrapped_lines)
    with tempfile.TemporaryDirectory(prefix="markerlite-table-audit-") as directory:
        with patch.object(markerlite, "recover_wrapped_lines", recovery):
            for pdf in paths:
                results[pdf.stem] = capture(pdf, pathlib.Path(directory))
                print(pdf.stem, results[pdf.stem]["stats"],
                      "content words:", results[pdf.stem]["words"], flush=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
