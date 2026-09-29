#!/usr/bin/env python3
"""Record and verify output hashes without storing third-party document text.

Fixture hashes are always runnable. ``--scope full`` also verifies tests/real
and every logical Packet A/B source, resolving packet PDFs by their recorded
SHA-256 across one or more ``--corpus-root`` directories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import markerlite  # noqa: E402

DEFAULT_MANIFEST = ROOT / "tests" / "golden" / "v0.1.14.json"
PACKET_GLOB = "*PACKET-*.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


def tesseract_version() -> str | None:
    executable = shutil.which("tesseract")
    if not executable:
        return None
    result = subprocess.run([executable, "--version"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        return None
    return result.stdout.splitlines()[0].strip() if result.stdout else None


def environment() -> dict:
    return {
        "pymupdf": pymupdf.VersionBind,
        "tesseract": tesseract_version(),
    }


def packet_sources(packet_root: pathlib.Path) -> list[dict]:
    by_locator = {}
    for packet in sorted(packet_root.glob(PACKET_GLOB)):
        payload = json.loads(packet.read_text(encoding="utf-8"))
        for case in payload["cases"]:
            source = case.get("source_pdf")
            source_hash = case.get("source_pdf_sha256")
            if not source or not source_hash:
                continue
            parts = pathlib.PurePosixPath(source).parts
            if "pilot" in parts:
                start = parts.index("pilot")
            elif "autonomous" in parts:
                start = parts.index("autonomous")
            elif "stack" in parts:
                start = parts.index("stack")
            else:
                raise ValueError(f"cannot make packet locator from {source}")
            locator = pathlib.PurePosixPath(*parts[start:]).as_posix()
            by_locator[locator] = {
                "id": f"packet:{locator}",
                "group": "packet",
                "path": locator,
                "source_sha256": source_hash,
                "mode": "default",
            }
    return [by_locator[key] for key in sorted(by_locator)]


def source_specs(packet_root: pathlib.Path) -> list[dict]:
    specs = []
    for group, directory in (("fixture", ROOT / "tests" / "fixtures"),
                             ("real", ROOT / "tests" / "real")):
        for path in sorted(directory.glob("*.pdf")):
            rel = path.relative_to(ROOT).as_posix()
            specs.append({
                "id": f"{group}:{rel}",
                "group": group,
                "path": rel,
                "source_sha256": sha256_file(path),
                "mode": "default",
            })
    specs.extend(packet_sources(packet_root))
    repro = "tests/fixtures/repro.pdf"
    isolated = "tests/fixtures/isolated_ocr_page.pdf"
    extras = [
        (isolated, "page-markers"),
        (repro, "images"),
        (repro, "flag-figures"),
        (repro, "flag-math"),
    ]
    for rel, mode in extras:
        path = ROOT / rel
        specs.append({
            "id": f"fixture:{rel}:{mode}",
            "group": "fixture",
            "path": rel,
            "source_sha256": sha256_file(path),
            "mode": mode,
        })
    return specs


def index_corpus(roots: Iterable[pathlib.Path]) -> dict[str, pathlib.Path]:
    index = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            digest = sha256_file(path)
            index.setdefault(digest, path)
    return index


def resolve_source(spec: dict, corpus_roots: list[pathlib.Path],
                   corpus_index: dict[str, pathlib.Path]) -> pathlib.Path | None:
    if spec["group"] != "packet":
        path = ROOT / spec["path"]
        return path if path.is_file() else None
    for root in corpus_roots:
        direct = root / spec["path"]
        if direct.is_file() and sha256_file(direct) == spec["source_sha256"]:
            return direct
    return corpus_index.get(spec["source_sha256"])


def mode_options(mode: str) -> dict:
    return {
        "default": {},
        "page-markers": {"page_markers": True},
        "images": {"images": True},
        "flag-figures": {"do_flag_figures": True},
        "flag-math": {"do_flag_math": True},
    }[mode]


def artifact_hashes(directory: pathlib.Path, markdown: pathlib.Path) -> dict:
    artifacts = {}
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        if path == markdown:
            continue
        artifacts[path.relative_to(directory).as_posix()] = sha256_file(path)
    return artifacts


def run_one(spec: dict, source: pathlib.Path, work: pathlib.Path) -> dict:
    outdir = work / sha256_bytes(spec["id"].encode("utf-8"))[:16]
    outdir.mkdir(parents=True)
    markdown, info = markerlite.convert(source, outdir, **mode_options(spec["mode"]))
    with pymupdf.open(source) as document:
        pages = len(document)
    result = dict(spec)
    result.update({
        "pages": pages,
        "markdown_sha256": sha256_file(markdown),
        "stats_sha256": canonical_hash(info["stats"]),
        "ocr": bool(info["stats"].get("ocr_pages")),
        "artifacts": artifact_hashes(outdir, markdown),
    })
    return result


def selected(entries: list[dict], scope: str) -> list[dict]:
    groups = {"fixture"} if scope == "fixtures" else (
        {"fixture", "real"} if scope == "repo" else {"fixture", "real", "packet"})
    return [entry for entry in entries if entry["group"] in groups]


def record(args) -> int:
    specs = selected(source_specs(args.packet_root), args.scope)
    corpus_index = index_corpus(args.corpus_root) if args.scope == "full" else {}
    entries = []
    with tempfile.TemporaryDirectory(prefix="markerlite-golden-") as tmp:
        work = pathlib.Path(tmp)
        for number, spec in enumerate(specs, 1):
            source = resolve_source(spec, args.corpus_root, corpus_index)
            if source is None:
                raise FileNotFoundError(f"missing {spec['id']}")
            if sha256_file(source) != spec["source_sha256"]:
                raise RuntimeError(f"source hash differs for {spec['id']}: {source}")
            print(f"record {number:02d}/{len(specs):02d} {spec['id']}", flush=True)
            entries.append(run_one(spec, source, work))
    payload = {
        "schema": 1,
        "baseline": "v0.1.14",
        "created_with": environment(),
        "entries": entries,
    }
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"wrote {len(entries)} entries to {args.output}")
    return 0


def verify(args) -> int:
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = selected(payload["entries"], args.scope)
    current_env = environment()
    recorded_env = payload["created_with"]
    print(f"PyMuPDF recorded={recorded_env['pymupdf']} current={current_env['pymupdf']}")
    print(f"Tesseract recorded={recorded_env['tesseract']!r} current={current_env['tesseract']!r}")
    corpus_index = index_corpus(args.corpus_root) if args.scope == "full" else {}
    failures = 0
    skipped_ocr = 0
    with tempfile.TemporaryDirectory(prefix="markerlite-golden-") as tmp:
        work = pathlib.Path(tmp)
        for number, expected in enumerate(entries, 1):
            source = resolve_source(expected, args.corpus_root, corpus_index)
            if source is None:
                print(f"MISSING {expected['id']}")
                failures += 1
                continue
            if sha256_file(source) != expected["source_sha256"]:
                print(f"FAIL source hash {expected['id']}: {source}")
                failures += 1
                continue
            if expected["ocr"] and current_env["tesseract"] != recorded_env["tesseract"]:
                print(f"SKIP OCR version mismatch {expected['id']}")
                skipped_ocr += 1
                continue
            print(f"verify {number:02d}/{len(entries):02d} {expected['id']}", flush=True)
            actual = run_one({key: expected[key] for key in
                              ("id", "group", "path", "source_sha256", "mode")},
                             source, work)
            differences = [key for key in
                           ("pages", "markdown_sha256", "stats_sha256", "ocr", "artifacts")
                           if actual[key] != expected[key]]
            if differences:
                failures += 1
                print(f"FAIL {expected['id']}: {', '.join(differences)}")
    if failures:
        print(f"{failures} golden entries differ; {skipped_ocr} OCR entries skipped")
        return 1
    print(f"all {len(entries) - skipped_ocr} compared golden entries match; "
          f"{skipped_ocr} OCR entries skipped")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("record", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--scope", choices=("fixtures", "repo", "full"),
                             default="fixtures")
        command.add_argument("--corpus-root", action="append", type=pathlib.Path,
                             default=[])
        if name == "record":
            command.add_argument("--packet-root", type=pathlib.Path, required=True)
            command.add_argument("--output", type=pathlib.Path, required=True)
        else:
            command.add_argument("--manifest", type=pathlib.Path,
                                 default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return record(args) if args.command == "record" else verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
