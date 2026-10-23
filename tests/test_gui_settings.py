"""Settings and executable validation tests; no Tk or real subprocesses."""

import json
import subprocess

import pytest

from markerlite.gui_ocr import validate_override
from markerlite.gui_settings import defaults, load_settings, recent_files, save_settings


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    data = defaults()
    data.update(
        theme="dark",
        output_mode="fixed",
        output_dir=str(tmp_path),
        auto_open=True,
        explorer_auto_start=False,
        tesseract_path="/ocr/tesseract",
    )
    save_settings(data, path)
    assert load_settings(path) == data
    assert not path.with_suffix(".json.part").exists()


def test_missing_settings_have_defaults(tmp_path):
    assert load_settings(tmp_path / "missing") == defaults()


def test_migrate_schema_one(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": 1, "theme": "dark", "recent_files": []})
    )
    data = load_settings(path)
    assert data["schema_version"] == 3 and data["theme"] == "dark"
    assert data["output_mode"] == "beside" and data["explorer_auto_start"]


@pytest.mark.parametrize(
    "payload",
    ["{broken", "null", "[]", '{"schema_version":999}', '{"schema_version":true}'],
)
def test_corrupt_or_unknown_settings_log_once(tmp_path, payload):
    path = tmp_path / "settings.json"
    path.write_text(payload)
    logged = []
    assert load_settings(path, logged.append) == defaults()
    assert len(logged) == 1 and "defaults" in logged[0]


@pytest.mark.parametrize(
    "key,value",
    [
        ("theme", "invalid"),
        ("table_grids", "yes"),
        ("auto_open", "yes"),
        ("explorer_auto_start", 1),
        ("output_mode", "relative"),
        ("tesseract_path", None),
        ("recent_files", [2]),
    ],
)
def test_invalid_field_resets_settings(tmp_path, key, value):
    path = tmp_path / "settings.json"
    data = defaults()
    data[key] = value
    path.write_text(json.dumps(data))
    logged = []
    assert load_settings(path, logged.append) == defaults() and logged


def test_recent_deduplicates_and_caps_without_removing_missing_paths(tmp_path):
    paths = [str(tmp_path / f"{i}.pdf") for i in range(15)]
    recents = recent_files(paths, [paths[3], paths[3].upper()])
    assert len(recents) == 10 and recents[0] == paths[3]
    assert len({p.casefold() for p in recents}) == 10
    assert not (tmp_path / "3.pdf").exists()


def test_override_runs_full_path_without_shell(tmp_path):
    executable = tmp_path / "tesseract.exe"
    executable.write_text("")
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args, 0, stdout="tesseract v5.5.0\nfeatures", stderr=""
        )

    assert validate_override(str(executable), run=run) == str(executable.resolve())
    assert calls[0][0] == [str(executable.resolve()), "--version"]
    assert calls[0][1]["timeout"] == 5 and "shell" not in calls[0][1]


@pytest.mark.parametrize(
    "result",
    [
        subprocess.CompletedProcess([], 1, stdout="tesseract 5.0", stderr=""),
        subprocess.CompletedProcess([], 0, stdout="another tool", stderr=""),
    ],
)
def test_override_rejects_wrong_executable(result):
    with pytest.raises(ValueError):
        validate_override(
            "/fake/tesseract",
            is_file=lambda path: True,
            run=lambda *args, **kwargs: result,
        )


@pytest.mark.parametrize(
    "error", [OSError("not executable"), subprocess.TimeoutExpired("tesseract", 5)]
)
def test_override_execution_errors(error):
    def run(*args, **kwargs):
        raise error

    with pytest.raises(ValueError):
        validate_override("/fake/tesseract", is_file=lambda path: True, run=run)


def test_override_missing_file_does_not_launch():
    def run(*args, **kwargs):
        raise AssertionError("must not run")

    with pytest.raises(ValueError):
        validate_override("/missing/tesseract", is_file=lambda path: False, run=run)
