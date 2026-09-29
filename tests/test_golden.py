import pathlib
import sys

TESTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

from golden import sha256_text_file  # noqa: E402


def test_text_hash_ignores_platform_newlines(tmp_path):
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"first\nsecond\n")
    crlf.write_bytes(b"first\r\nsecond\r\n")

    assert sha256_text_file(lf) == sha256_text_file(crlf)
