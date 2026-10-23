"""Atomic output: a conversion that fails leaves no .part file and the
previous complete output intact (markerlite/output.py)."""

import pathlib
import shutil

import pytest

import markerlite
from markerlite import api, output

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "fixtures" / "repro.pdf"  # rasters, a chart, equations


def _snapshot(folder: pathlib.Path) -> dict:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def _convert(outdir):
    return markerlite.convert(PDF, outdir, images=True, do_flag_math=True, grids=True)


def _parts(folder):
    return [p.name for p in folder.rglob("*") if ".part" in p.name or ".old" in p.name]


@pytest.mark.parametrize("error", [RuntimeError, KeyboardInterrupt])
def test_failure_mid_conversion_keeps_previous_output(tmp_path, monkeypatch, error):
    _convert(tmp_path)
    before = _snapshot(tmp_path)
    assert any(name.startswith("repro_images/") for name in before)
    assert any(name.startswith("repro_math/") for name in before)

    def boom(*args, **kwargs):  # after every folder and manifest is staged
        raise error("stop")

    monkeypatch.setattr(api, "render", boom)
    with pytest.raises(error):
        _convert(tmp_path)
    assert _parts(tmp_path) == []
    assert _snapshot(tmp_path) == before


def test_success_replaces_output_and_leaves_nothing_behind(tmp_path):
    _convert(tmp_path)
    (tmp_path / "repro_images" / "stale.png").write_bytes(b"old")
    md, _info = _convert(tmp_path)
    assert md == tmp_path / "repro.md" and md.read_text(encoding="utf-8")
    assert not (tmp_path / "repro_images" / "stale.png").exists()  # swapped whole
    assert _parts(tmp_path) == []
    # links name the final folder, never the staging one
    assert "repro_images/" in md.read_text(encoding="utf-8")
    assert ".part" not in md.read_text(encoding="utf-8")


def test_part_left_by_a_killed_run_is_removed(tmp_path):
    (tmp_path / "repro.md.part").write_text("half", encoding="utf-8")
    (tmp_path / "repro_images.part").mkdir()
    _convert(tmp_path)
    assert _parts(tmp_path) == []


def test_flag_figures_manifest_links_final_folder(tmp_path):
    md, info = markerlite.convert(PDF, tmp_path, do_flag_figures=True, grids=True)
    files = [r["file"] for r in info["figures"] if r["file"]]
    assert files and all(f.startswith("repro_figures/") for f in files)
    assert all((tmp_path / f).is_file() for f in files)
    assert (tmp_path / "repro_figures.json").is_file()
    assert _parts(tmp_path) == []


def test_write_text_atomic_keeps_original_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "a.md"
    target.write_text("complete", encoding="utf-8")

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(output.os, "replace", fail)
    with pytest.raises(OSError):
        output.write_text_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "complete"
    assert not (tmp_path / "a.md.part").exists()


def test_folder_swap_restores_old_folder_if_rename_fails(tmp_path, monkeypatch):
    final = tmp_path / "x_images"
    final.mkdir()
    (final / "a.png").write_bytes(b"old")
    out = output.Output(tmp_path)
    part = out.folder("x_images")
    part.mkdir()
    (part / "a.png").write_bytes(b"new")
    real = output.os.replace

    def flaky(src, dst):
        if pathlib.Path(src) == part:
            raise OSError("locked")
        return real(src, dst)

    monkeypatch.setattr(output.os, "replace", flaky)
    with pytest.raises(OSError):
        out.commit()
    assert (final / "a.png").read_bytes() == b"old"
    shutil.rmtree(part)
