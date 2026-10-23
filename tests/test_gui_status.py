"""The file list's Status and Time columns, progress, and theme choice
(markerlite/gui_logic.py): pure functions, no Tk."""

import pathlib

import pytest

from markerlite.cancel import Cancelled
from markerlite.gui_logic import (
    CANCELLING,
    STATUS_DOTS,
    ConversionOptions,
    ProgressToken,
    elapsed_text,
    overall_progress,
    progress_checks,
    run_batch,
    status_cell,
    theme_for,
)


@pytest.mark.parametrize(
    "state, kwargs, text, dot",
    [
        ("queued", {}, "Queued", "muted"),
        ("converting", {}, "Converting…", "busy"),
        ("converting", {"percent": 0}, "Converting 0%", "busy"),
        ("converting", {"percent": 42}, "Converting 42%", "busy"),
        ("converting", {"percent": 100}, "Converting 99%", "busy"),
        ("cancelling", {}, CANCELLING, "warn"),
        ("done", {}, "Done", "ok"),
        ("done", {"warnings": 0}, "Done", "ok"),
        ("done", {"warnings": 1}, "Done with 1 warning", "warn"),
        ("done", {"warnings": 3}, "Done with 3 warnings", "warn"),
        ("failed", {}, "Failed", "bad"),
        ("cancelled", {}, "Cancelled", "muted"),
        ("skipped", {}, "Skipped", "muted"),
    ],
)
def test_status_cell(state, kwargs, text, dot):
    assert status_cell(state, **kwargs) == (text, dot)
    assert dot in STATUS_DOTS


def test_status_cell_rejects_unknown_state():
    with pytest.raises(ValueError):
        status_cell("halfway")


def test_cancelling_matches_the_status_bar_text():
    assert status_cell("cancelling")[0] == "Cancelling…"


@pytest.mark.parametrize(
    "seconds, text",
    [
        (None, ""),
        (0, "0.0 s"),
        (4.26, "4.3 s"),
        (59.94, "59.9 s"),
        (75.4, "1:15"),
        (3600, "60:00"),
    ],
)
def test_elapsed_text(seconds, text):
    assert elapsed_text(seconds) == text


def test_overall_progress():
    assert overall_progress(0, 0, 0) == 0
    assert overall_progress(0, 50, 2) == 25
    assert overall_progress(1, 50, 2) == 75
    assert overall_progress(2, 0, 2) == 100


@pytest.mark.parametrize(
    "value, override, theme",
    [
        (1, None, "light"),
        (0, None, "dark"),
        (None, None, "light"),
        (1, "dark", "dark"),
        (0, "LIGHT", "light"),
        (0, "blue", "dark"),
    ],
)
def test_theme_for(value, override, theme):
    assert theme_for(value, override) == theme


def test_progress_token_counts_checks_and_stays_below_100():
    seen = []
    token = ProgressToken(lambda src, pct: seen.append((src, pct)))
    token.begin("a.pdf", 3)
    for _ in range(progress_checks(3) + 5):  # OCR calls overshoot
        token.check()
    pcts = [p for _s, p in seen]
    assert pcts == sorted(set(pcts)) and pcts[-1] == 99
    assert all(s == "a.pdf" for s, _p in seen)
    token.cancel()
    with pytest.raises(Cancelled):
        token.check()


def test_progress_token_without_pages_reports_nothing():
    seen = []
    token = ProgressToken(lambda src, pct: seen.append(pct))
    token.begin("a.pdf", 0)
    token.check()
    assert seen == []


def test_run_batch_emits_pages_and_progress(tmp_path):
    events = []
    token = ProgressToken(lambda src, pct: events.append(("progress", src, pct)))
    pdf = tmp_path / "a.pdf"

    def convert(path, outdir, *args, cancel=None, grids=False):
        for _ in range(progress_checks(2)):
            cancel.check()
        md = outdir / "a.md"
        md.write_text("x", encoding="utf-8")
        return md, {"stats": {"pages": 2}}

    opts = ConversionOptions(False, False, False, "fixed", str(tmp_path / "out"))
    run_batch(
        [pdf],
        opts,
        convert,
        token,
        events.append,
        lambda *a: None,
        page_count=lambda p: 2,
    )
    kinds = [e[0] for e in events]
    assert kinds[:2] == ["busy", "pages"] and events[1] == ("pages", str(pdf), 2)
    assert "progress" in kinds and kinds[-1] == "done"
    assert max(e[2] for e in events if e[0] == "progress") == 99


def test_run_batch_without_page_count_is_unchanged(tmp_path):
    events = []

    def convert(path, outdir, *args, cancel=None, grids=False):
        md = outdir / "a.md"
        md.write_text("x", encoding="utf-8")
        return md, {"stats": {}}

    opts = ConversionOptions(False, False, False, "fixed", str(tmp_path / "out"))
    run_batch(
        [pathlib.Path("a.pdf")], opts, convert, None, events.append, lambda *a: None
    )
    assert [e[0] for e in events] == ["busy", "done"]


def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_meets_wcag_aa_and_dots_meet_3_to_1(theme):
    from markerlite.gui_logic import ACCENT, DOT_COLOUR, PALETTES

    c = PALETTES[theme]
    text_pairs = [
        (c["ink"], c["bg"]),
        (c["ink"], c["card"]),
        (c["muted"], c["bg"]),
        (c["muted"], c["card"]),
        (c["warn"], c["bg"]),
        (c["sel_fg"], c["sel_bg"]),
        ("#ffffff", ACCENT),  # the primary button
    ]
    for fg, bg in text_pairs:
        assert _contrast(fg, bg) >= 4.5, (theme, fg, bg, _contrast(fg, bg))
    for key in DOT_COLOUR.values():
        if key == "dot_muted":
            continue  # queued/cancelled: deliberately quiet, labelled in text
        assert _contrast(c[key], c["card"]) >= 3.0, (theme, key)


def test_row_details_keeps_the_old_column_counts():
    from markerlite.gui_logic import row_details

    assert row_details({"pages": 4, "words": 1234}) == "1,234 content words"
    assert (
        row_details(
            {"pages": 4, "words": 10, "ocr_pages": 2, "tables": 3, "tables_fallback": 1}
        )
        == "10 content words · 2/4 pages OCR'd · 3 tables (1 kept as prose)"
    )
    assert row_details({"pages": 1, "words": 5, "tables": 1}) == (
        "5 content words · 1 table"
    )
