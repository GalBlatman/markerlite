"""A bad input cannot prevent later inputs or leave staged outputs."""

import pathlib
import shutil
from unittest.mock import patch

import pytest

import markerlite
from markerlite import cli
from markerlite.paths import OUTPUT_STEM_BYTES, output_stem

PDF = pathlib.Path(__file__).parent / "fixtures" / "hard.pdf"


def test_malformed_middle_input_continues_batch(tmp_path, capsys):
    first, bad, last = [
        tmp_path / name for name in ("first.pdf", "bad.pdf", "last.pdf")
    ]
    shutil.copyfile(PDF, first)
    bad.write_bytes(b"not a PDF")
    shutil.copyfile(PDF, last)
    out = tmp_path / "out"
    with patch(
        "sys.argv", ["markerlite", str(first), str(bad), str(last), "-o", str(out)]
    ):
        with pytest.raises(SystemExit) as error:
            cli.main()
    assert error.value.code == 1
    assert (out / "first.md").is_file() and (out / "last.md").is_file()
    assert not list(out.glob("*.part"))
    assert "1 file(s) failed: bad.pdf" in capsys.readouterr().err


@pytest.mark.parametrize("failure", [ValueError("extraction"), OSError("render")])
def test_conversion_exception_is_per_input(tmp_path, failure, capsys):
    with patch("sys.argv", ["markerlite", "bad.pdf", "good.pdf", "-o", str(tmp_path)]):
        with patch.object(
            cli, "convert", side_effect=[failure, (tmp_path / "good.md", {})]
        ) as convert:
            with pytest.raises(SystemExit) as error:
                cli.main()
    assert error.value.code == 1 and convert.call_count == 2
    assert "good.pdf ->" in capsys.readouterr().out


def test_250_character_basename_all_outputs_have_consistent_short_stem(tmp_path):
    source = tmp_path / ("a" * 246 + ".pdf")
    shutil.copyfile(PDF.with_name("repro.pdf"), source)
    out = tmp_path / "out"
    out.mkdir()
    md, info = markerlite.convert(
        source, out, images=True, do_flag_math=True, do_flag_figures=True
    )
    stem = output_stem(source.stem)
    assert md.name == stem + ".md" and md.is_file()
    assert stem == output_stem(source.stem)
    assert output_stem("ordinary") == "ordinary"
    assert len(stem.encode()) <= OUTPUT_STEM_BYTES
    assert output_stem(source.stem + "b") != stem
    assert not list(out.glob("*.part"))
    assert all(len(p.name.encode()) <= 255 for p in out.rglob("*"))
    assert (out / (stem + "_math.json")).is_file()


def test_unicode_shortening_preserves_complete_characters():
    name = output_stem("é" * 150)
    assert len(name.encode()) <= OUTPUT_STEM_BYTES
    assert "�" not in name
