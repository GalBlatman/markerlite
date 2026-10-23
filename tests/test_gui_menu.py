"""Right-click menu logic (gui_logic): which entries apply, what the
warnings window says, and how a path reaches the file manager."""

import pathlib

from markerlite.gui_logic import MENU_ITEMS, menu_state, reveal_command, warning_details


def test_entries_before_conversion():
    s = menu_state(pdf_exists=True, md_exists=False, converted=False, running=False)
    assert set(s) == set(MENU_ITEMS)
    assert (
        s["Open PDF"]
        and s["Show in folder"]
        and s["Re-convert"]
        and s["Remove from list"]
    )
    assert not s["Open Markdown"] and not s["Copy Markdown"] and not s["Show warnings"]


def test_entries_after_conversion_and_while_running():
    s = menu_state(pdf_exists=True, md_exists=True, converted=True, running=False)
    assert all(s.values())
    busy = menu_state(pdf_exists=True, md_exists=True, converted=True, running=True)
    assert not busy["Re-convert"] and not busy["Remove from list"]
    assert busy["Open Markdown"] and busy["Show warnings"]


def test_missing_files_disable_their_entries():
    s = menu_state(pdf_exists=False, md_exists=False, converted=True, running=False)
    assert not s["Open PDF"] and not s["Show in folder"] and not s["Re-convert"]
    assert s["Show warnings"] and s["Remove from list"]


def test_warning_details():
    assert warning_details({}) == ["No warnings"]
    stats = {
        "lossy_pages": [{"page": 3, "source": 400, "emitted": 120}],
        "fragment_pages": [{"page": 16, "letter_tokens": 92, "short_share": 0.957}],
        "tables": 4,
        "tables_fallback": 2,
        "resource_limits": [
            {
                "page": 1,
                "limit": "image_pixels",
                "observed": 4e8,
                "cap": 2.4e8,
                "action": "kept",
            }
        ],
    }
    lines = warning_details(stats)
    assert lines[0] == "Lossy page 3: 120 of 400 source words emitted"
    assert lines[1].startswith("Fragment page 16: 96%")
    assert "Tables kept as prose: 2 of 4" in lines
    assert lines[3].startswith("Resource limit image_pixels on page 1")


def test_warning_text_is_displayed_safely():
    stats = {
        "resource_limits": [
            {"page": 1, "limit": "x\nforged", "observed": 1, "cap": 0, "action": "a"}
        ]
    }
    assert "\n" not in warning_details(stats)[0]


def test_reveal_passes_the_path_as_one_argument():
    p = pathlib.Path("C:/a b/c & d.md")
    cmd = reveal_command(p, "win32")
    assert cmd == ["explorer", f"/select,{p}"] and len(cmd) == 2
    assert reveal_command(p, "darwin") == ["open", "-R", str(p)]


def test_main_menu_reuses_row_enablement():
    from markerlite.gui_logic import main_menu_state

    empty = main_menu_state(False, [], False, False)
    assert not any(empty.values())
    row = menu_state(True, True, True, False)
    ready = main_menu_state(False, [row], True, True)
    assert ready["Convert"] and ready["Copy Markdown"] and ready["Clear finished"]
    busy = main_menu_state(True, [menu_state(True, True, True, True)], True, True)
    assert busy["Cancel"] and busy["Copy Markdown"]
    assert (
        not busy["Convert"] and not busy["Remove from list"] and not busy["Clear list"]
    )
