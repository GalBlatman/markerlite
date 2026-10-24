"""Typed manifests fail before mutation; apply text is scanned once."""

import json
from types import SimpleNamespace

import pytest

from markerlite import apply_manifest as manifests


@pytest.mark.parametrize(
    "raw",
    [
        None,
        1,
        {},
        {"regions": {}},
        {"stem": "\ud800", "regions": []},
        {"regions": [1]},
        {"regions": [{"page": True}]},
        {"regions": [{"description": 2}]},
        {"regions": [{"latex": []}]},
        {"regions": [{"id": "bad id"}]},
        {"regions": [{"bbox": [0, 0, float("nan"), 1]}]},
    ],
)
def test_invalid_schema_is_a_clear_error(raw):
    with pytest.raises(manifests.ManifestError):
        manifests.load_manifest(raw, "figures")


def test_manifest_size_checked_with_bounded_read(tmp_path, monkeypatch):
    monkeypatch.setattr(manifests, "APPLY_MAX_MANIFEST_BYTES", 64)
    source = tmp_path / "large.json"
    source.write_bytes(b" " * 10000)
    with pytest.raises(manifests.ManifestLimitError) as error:
        manifests.load_manifest(source, "math")
    assert error.value.stats["resource_limits"][0]["observed"] == 65


def test_manifest_entry_cap_is_structured(monkeypatch):
    monkeypatch.setattr(manifests, "APPLY_MAX_MANIFEST_ENTRIES", 2)
    with pytest.raises(manifests.ManifestLimitError) as error:
        manifests.load_manifest({"regions": [{}, {}, {}]}, "math")
    assert error.value.stats["resource_limits"][0]["limit"] == "manifest_entries"


def test_validated_snapshot_is_not_parsed_again(tmp_path, monkeypatch):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"stem": "paper", "regions": []}))
    loaded = manifests.load_manifest(path, "math")
    monkeypatch.setattr(manifests.json, "loads", lambda *a: pytest.fail("parsed twice"))
    assert manifests.load_manifest(loaded, "math") is loaded


def test_figure_descriptions_use_one_scan_and_are_idempotent(monkeypatch):
    md = "\n".join(f"<!-- figure: p. {n}; caption: example -->" for n in range(1, 51))
    manifest = manifests.load_manifest(
        {
            "regions": [
                {"id": f"fig_p{n}_1", "description": f"Description {n}"}
                for n in range(1, 51)
            ]
        },
        "figures",
    )
    scanner = manifests._FIGURES
    calls = []

    def sub(*args):
        calls.append(1)
        return scanner.sub(*args)

    monkeypatch.setattr(manifests, "_FIGURES", SimpleNamespace(sub=sub))
    first, count = manifests.apply_figures_text(md, manifest)
    assert count == 50 and calls == [1]
    second, count = manifests.apply_figures_text(first, manifest)
    assert second == first and count == 50 and calls == [1, 1]


def test_math_uses_one_scan_and_preserves_surrounding_prose(monkeypatch):
    md = "before\n$$\nx\n$$\n\n<!-- markerlite:eq page1_eq0 -->\n\nbetween\n<!-- equation: p. 2; set as an image -->\n\n![](crop.png)\n\n<!-- markerlite:eq page2_eq0 -->\nafter"
    manifest = manifests.load_manifest(
        {
            "regions": [
                {"id": "page1_eq0", "latex": "a"},
                {"id": "page2_eq0", "latex": "b"},
            ]
        },
        "math",
    )
    scanner = manifests._MATH
    calls = []

    def sub(*args):
        calls.append(1)
        return scanner.sub(*args)

    monkeypatch.setattr(manifests, "_MATH", SimpleNamespace(sub=sub))
    result, count = manifests.apply_math_text(md, manifest)
    assert count == 2 and calls == [1]
    assert result == "before\n$$\na\n$$\n\nbetween\n$$\nb\n$$\nafter"


def test_cli_parses_manifest_once_and_uses_atomic_output(tmp_path, monkeypatch):
    from markerlite import cli

    source = tmp_path / "m.json"
    source.write_text(
        json.dumps({"stem": "paper", "regions": [{"id": "page1_eq0", "latex": "y"}]})
    )
    target = tmp_path / "paper.md"
    target.write_text("$$\nx\n$$\n\n<!-- markerlite:eq page1_eq0 -->\n")
    real = manifests.json.loads
    calls = []

    def loads(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(manifests.json, "loads", loads)
    monkeypatch.setattr(
        "sys.argv", ["markerlite", "--apply-math", str(source), "-o", str(tmp_path)]
    )
    cli.main()
    assert calls == [1]
    assert target.read_text() == "$$\ny\n$$\n"
    assert not list(tmp_path.glob("*.part"))


def test_invalid_manifest_does_not_touch_markdown(tmp_path):
    from markerlite.figures import apply_math

    md = tmp_path / "paper.md"
    md.write_bytes(b"previous complete output")
    manifest = tmp_path / "invalid.json"
    manifest.write_text(json.dumps({"regions": [{"latex": 12}]}))
    with pytest.raises(manifests.ManifestError):
        apply_math(md, manifest)
    assert md.read_bytes() == b"previous complete output"
