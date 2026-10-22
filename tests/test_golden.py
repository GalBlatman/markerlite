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
