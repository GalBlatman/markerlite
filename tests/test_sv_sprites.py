"""The recoloured sv-ttk spritesheets (assets/sv-ttk) match the installed
sv-ttk. They are copies of that version's sheets; a different version can
move or redraw sprites, and the app would paste wrong pieces over them."""

import pathlib
from importlib.metadata import PackageNotFoundError, version

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_recoloured_sprites_match_installed_sv_ttk():
    try:
        installed = version("sv-ttk")
    except PackageNotFoundError:
        pytest.skip("sv-ttk is not installed (the gui extra)")
    generated = (ROOT / "assets" / "sv-ttk" / "SV_TTK_VERSION").read_text().strip()
    assert installed == generated, (
        f"sv-ttk {installed} is installed but assets/sv-ttk was generated from "
        f"sv-ttk {generated}: rerun python tools/recolour_sprites.py and commit "
        "the new sheets, or pin sv-ttk back to the generated version"
    )
