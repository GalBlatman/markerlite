from markerlite.model import Page
from markerlite.stats import (
    SUPPRESSION_REASONS,
    build_stats,
    stat_warnings,
    summarize,
)


EXPECTED_STATS_KEYS = {
    "suppressed",
    "pages",
    "bytes",
    "words",
    "low_yield_pages",
    "lossy_pages",
    "garbled_pages",
    "garbled_ocr",
    "rotated_pages",
    "pi_glyphs_repaired",
    "figures",
    "figure_crops",
    "figures_saved",
    "equations",
    "ocr_pages",
    "image_only_pages",
    "provenance",
    "tables",
    "tables_fallback",
    "table_captions_isolated",
    "table_caption_words",
    "table_lines_excluded",
    "proposals",
    "proposals_kept_prose",
}


def test_build_stats_keeps_the_public_dictionary_contract():
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    page.suppressed.append(
        {
            "page": 1,
            "bbox": [1, 2, 3, 4],
            "text": "Journal",
            "reason": "proc_marginalia",
        }
    )
    stats = build_stats([page], "Text\n", {}, [], 0, 0)

    assert set(stats) == EXPECTED_STATS_KEYS
    assert stats["pages"] == 1
    assert stats["bytes"] == 5
    assert stats["words"] == 1
    assert stats["suppressed"][0]["reason"] in SUPPRESSION_REASONS


def test_warning_policy_and_summary_wording_stay_centralized():
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    page.tables_emitted = 1
    page.tables_fell_back = 1
    stats = build_stats([page], "Text\n", {}, [], 0, 0)

    assert stat_warnings(stats) == ["1 of 1 table kept as prose"]
    assert summarize(stats).endswith(
        "0 source lines suppressed · 1 of 1 table kept as prose"
    )
