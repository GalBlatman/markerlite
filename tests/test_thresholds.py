import inspect
import math

from markerlite import classification, extraction, figures, processors, tables
from markerlite import thresholds as t


def test_every_numeric_threshold_has_values_on_both_sides():
    thresholds = {
        name: value
        for name, value in vars(t).items()
        if name.isupper() and isinstance(value, (int, float))
    }
    assert thresholds
    for value in thresholds.values():
        below = math.nextafter(float(value), -math.inf)
        above = math.nextafter(float(value), math.inf)
        assert below < value < above


def test_public_gate_defaults_use_the_named_thresholds():
    defaults = {
        extraction._ocr_page: {"dpi": t.OCR_DPI},
        extraction.extract_page: {"max_line_tilt": t.MAX_LINE_TILT},
        tables._table_sane: {
            "max_header_ratio": t.TABLE_MAX_HEADER_RATIO,
            "max_empty_frac": t.TABLE_MAX_EMPTY_FRAC,
        },
        tables._columns_align: {
            "tol": t.PROPOSAL_ALIGN_TOL,
            "min_share": t.PROPOSAL_ALIGN_MIN_SHARE,
        },
        tables.propose_tables_from_text: {"min_score": t.PROPOSAL_MIN_SCORE},
        classification._demote_toc: {"min_run": t.TOC_MIN_RUN},
        processors.proc_line_numbers: {
            "margin_frac": t.LINE_NUMBER_MARGIN_FRAC,
            "min_count": t.LINE_NUMBER_MIN_COUNT,
        },
        processors.proc_marginalia: {
            "header_zone": t.MARGINALIA_HEADER_ZONE,
            "footer_zone": t.MARGINALIA_FOOTER_ZONE,
            "max_height_frac": t.MARGINALIA_MAX_HEIGHT_FRAC,
            "max_chars": t.MARGINALIA_MAX_CHARS,
        },
        figures._vector_regions: {
            "min_items": t.FIGURE_VECTOR_MIN_SEGMENTS,
            "min_side": t.FIGURE_VECTOR_MIN_SIDE,
        },
    }
    for function, expected in defaults.items():
        parameters = inspect.signature(function).parameters
        for name, value in expected.items():
            assert parameters[name].default == value
