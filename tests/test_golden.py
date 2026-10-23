import pathlib
import sys

TESTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

import golden  # noqa: E402
from golden import sha256_text_file  # noqa: E402


def test_text_hash_ignores_platform_newlines(tmp_path):
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"first\nsecond\n")
    crlf.write_bytes(b"first\r\nsecond\r\n")

    assert sha256_text_file(lf) == sha256_text_file(crlf)


def test_excluded_file_never_recorded(tmp_path, monkeypatch):
    real = tmp_path / "tests" / "real"
    real.mkdir(parents=True)
    (tmp_path / "tests" / "fixtures").mkdir()
    (tmp_path / "markerlite").mkdir()
    (tmp_path / "markerlite" / "VERSION").write_text("0.0.0\n", encoding="ascii")
    for name in ("open.pdf", "secret.pdf"):
        (real / name).write_bytes(b"%PDF-1.4 " + name.encode())
    exclude = real / ".golden-exclude"
    exclude.write_text("# confidential\nsecret.pdf\n", encoding="utf-8")
    monkeypatch.setattr(golden, "ROOT", tmp_path)
    monkeypatch.setattr(golden, "EXCLUDE_FILE", exclude)
    monkeypatch.setattr(golden, "packet_sources", lambda root: [])
    monkeypatch.setattr(golden, "sha256_file", lambda path: "0" * 64)
    real_specs = golden.source_specs

    def specs(root):
        return [s for s in real_specs(root) if s["group"] == "real"]

    monkeypatch.setattr(golden, "source_specs", specs)
    monkeypatch.setattr(
        golden, "run_one", lambda spec, source, work: {"id": spec["id"]}
    )
    output = tmp_path / "manifest.json"
    args = golden.parse_args(
        [
            "record",
            "--scope",
            "repo",
            "--packet-root",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )
    golden.record(args)
    text = output.read_text(encoding="utf-8")
    assert "open.pdf" in text
    assert "secret" not in text


def test_verify_forwards_explicit_grid_mode_and_preserves_legacy(tmp_path, monkeypatch):
    import json

    source = tmp_path / "tests" / "fixtures" / "mode.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic source identity")
    environment = {"pymupdf": "test", "tesseract": None}
    entries = []
    for i, mode in enumerate((None, False, True)):
        effective = True if mode is None else mode
        entry = {
            "id": f"mode-{i}",
            "group": "fixture",
            "path": "tests/fixtures/mode.pdf",
            "source_sha256": golden.sha256_file(source),
            "mode": "default",
            "pages": 1,
            "markdown_sha256": f"md-{effective}",
            "stats_sha256": f"stats-{effective}",
            "ocr": False,
            "artifacts": {},
        }
        if mode is not None:
            entry["grids"] = mode
        entries.append(entry)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"created_with": environment, "entries": entries}))
    monkeypatch.setattr(golden, "ROOT", tmp_path)
    monkeypatch.setattr(golden, "environment", lambda: environment)
    observed = []

    def run(spec, _source, _work):
        effective = spec.get("grids", True)
        observed.append(effective)
        return {
            "pages": 1,
            "markdown_sha256": f"md-{effective}",
            "stats_sha256": f"stats-{effective}",
            "ocr": False,
            "artifacts": {},
        }

    monkeypatch.setattr(golden, "run_one", run)
    assert (
        golden.verify(golden.parse_args(["verify", "--manifest", str(manifest)])) == 0
    )
    assert observed == [True, False, True]
