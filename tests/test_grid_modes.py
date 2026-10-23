"""Default-off source prose and explicit grid mode across every interface."""

import dataclasses
import json
from pathlib import Path
from unittest.mock import patch

import markerlite
from markerlite import cli
from markerlite.gui_logic import snapshot_options
from markerlite.gui_settings import defaults, load_settings

ROOT = Path(__file__).resolve().parent


def test_api_default_is_source_prose_and_explicit_grids_keep_layout(tmp_path):
    source = ROOT / "fixtures" / "hard.pdf"
    (tmp_path / "off").mkdir()
    (tmp_path / "on").mkdir()
    off, info = markerlite.convert(source, tmp_path / "off")
    off_text = off.read_text()
    assert "grids disabled; text kept as prose" in off_text
    assert "grid from" not in off_text and "<table" not in off_text
    on, on_info = markerlite.convert(source, tmp_path / "on", grids=True)
    assert "grid from ruling lines" in on.read_text()
    assert info["stats"]["tables_grids_disabled"] == info["stats"]["tables"]
    assert "tables_grids_disabled" not in on_info["stats"]
    assert info["stats"]["words"] == on_info["stats"]["words"]


def test_cli_default_and_explicit_switches(tmp_path):
    for flags, expected in (([], False), (["--grids"], True), (["--no-grids"], False)):
        with (
            patch("sys.argv", ["markerlite", "input.pdf", "-o", str(tmp_path), *flags]),
            patch.object(
                cli, "convert", return_value=(tmp_path / "input.md", {"stats": {}})
            ) as convert,
        ):
            cli.main()
        assert convert.call_args.kwargs["grids"] is expected


def test_preferences_migrate_with_grids_off_and_snapshot_overrides(tmp_path):
    data = defaults()
    assert data["table_grids"] is False
    data.pop("table_grids")
    data["schema_version"] = 2
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    assert load_settings(path)["table_grids"] is False
    data.update(schema_version=3, table_grids=True)
    path.write_text(json.dumps(data))
    assert load_settings(path)["table_grids"] is True
    options = snapshot_options(False, False, False, "beside", "", True)
    assert dataclasses.asdict(options)["grids"] is True
