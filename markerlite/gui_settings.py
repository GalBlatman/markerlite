"""App-wide preferences, independent of Tk and conversion options."""

from __future__ import annotations

import json
import os
import pathlib

SCHEMA_VERSION = 3


def settings_path():
    return (
        pathlib.Path(os.environ.get("APPDATA", str(pathlib.Path.home() / ".config")))
        / "markerlite"
        / "settings.json"
    )


def defaults():
    return {
        "schema_version": SCHEMA_VERSION,
        "theme": "system",
        "table_grids": False,
        "recent_files": [],
        "output_mode": "beside",
        "output_dir": str(pathlib.Path.home() / "Documents" / "markdown"),
        "auto_open": False,
        "explorer_auto_start": True,
        "tesseract_path": "",
    }


def recent_files(paths, added=()):
    result = []
    for path in list(added) + list(paths):
        value = str(pathlib.Path(path).absolute())
        if value.casefold() not in {p.casefold() for p in result}:
            result.append(value)
    return result[:10]


def load_settings(path=None, log=lambda line: None):
    path = path or settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or type(data.get("schema_version")) is not int
            or data["schema_version"] not in (1, 2, SCHEMA_VERSION)
        ):
            raise ValueError("unknown settings schema")
        result = defaults()
        if data.get("theme") not in ("system", "light", "dark"):
            raise ValueError("invalid theme")
        paths = data.get("recent_files", [])
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            raise ValueError("invalid recent files")
        result.update(theme=data["theme"], recent_files=recent_files(paths))
        # v1 held theme and recents only. New app-wide preferences take defaults.
        if data["schema_version"] >= 2:
            if data.get("output_mode") not in ("beside", "fixed"):
                raise ValueError("invalid output location")
            for key in ("output_dir", "tesseract_path"):
                if not isinstance(data.get(key), str):
                    raise ValueError(f"invalid {key}")
                result[key] = data[key]
            for key in ("auto_open", "explorer_auto_start"):
                if type(data.get(key)) is not bool:
                    raise ValueError(f"invalid {key}")
                result[key] = data[key]
            result["output_mode"] = data["output_mode"]
            if result["output_mode"] == "fixed" and not result["output_dir"].strip():
                raise ValueError("fixed output folder is empty")
        if data["schema_version"] >= 3:
            if type(data.get("table_grids")) is not bool:
                raise ValueError("invalid table_grids")
            result["table_grids"] = data["table_grids"]
        return result
    except FileNotFoundError:
        return defaults()
    except (OSError, ValueError, TypeError) as exc:
        log(f"Settings reset to defaults: {exc}")
        return defaults()


def save_settings(data, path=None):
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.part")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
