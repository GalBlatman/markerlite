"""Named behavioral thresholds with their v0.1.14 calibration evidence."""

# Native/OCR gates: scanned, scanned_with_stamp, Suchman, Kostova, Kitchener.
OCR_MIN_NATIVE_CHARS = 20
OCR_MAX_NATIVE_CHARS = 500
OCR_RASTER_MIN_FRAC = 0.8
OCR_STAMP_MARGIN = 0.15

# A wide dark filled band is a page-local banner. Some reporting tools draw
# its text last, after the rows it visually introduces; only this narrow shape
# exception is repositioned geometrically, without sorting the page.
BANNER_FILL_MAX_LUMA = 0.5
BANNER_MIN_PAGE_WIDTH = 0.5
BANNER_TEXT_OVERLAP = 0.8
OCR_DPI = 300
OCR_PSM = 1
OCR_TIMEOUT_SECONDS = 180
OCR_MIN_CONFIDENCE = 30
GARBLE_MIN = 0.10
GARBLE_MIN_TOKENS = 50

# Rotation/tilt gates: rotated_pages, watermark, Wry, and York.
ROTATION_MIN_CHARS = 100
ROTATED_PAGE_MIN_FRAC = 0.8
ROTATION_AXIS_TOL = 0.1
ROTATION_VERTICAL_MIN = 0.9
MAX_LINE_TILT = 0.1

# Page diagnostics: SBTi cover, rotated_pages, and Ragins p. 2.
LOW_YIELD_WORDS = 15
CONSERVATION_MIN = 0.5
CONSERVATION_MIN_SOURCE = 20

# Pi-font/drop-cap evidence: pi_minus and dropcap fixtures.
PI_FONT_MIN_GLYPHS = 5
PI_FONT_MIN_SUSPICIOUS = 3
PI_FONT_MIN_GLUED_SHARE = 0.8
DROP_CAP_MIN_SCALE = 2.0

# Reconstruction and table guards: SBTi, tall_cell, paper, and hard.
TABLE_TOKEN_GAP_HEIGHT = 0.8
TABLE_ROW_TOLERANCE_HEIGHT = 0.5
TABLE_FALLBACK_MIN_KEEP = 0.9
TABLE_MAX_HEADER_RATIO = 1.4
TABLE_MAX_EMPTY_FRAC = 0.45
TABLE_CANDIDATE_MIN_AREA = 200
TABLE_CANDIDATE_MAX_PAGE_FRAC = 0.60
TABLE_CANDIDATE_MAX_OVERLAP = 0.60
TABLE_MEMBER_OVERLAP = 0.5
TABLE_CAPTION_MAX_SIZE_DELTA = 0.6
TABLE_CAPTION_MAX_GAP_HEIGHT = 0.8
TABLE_PHYSICAL_EDGE_Y = 0.95
TABLE_TOP_EDGE_Y = 0.08
TABLE_RULE_MIN_HEIGHT = 12
TABLE_RULE_MAX_HEIGHT_FRAC = 0.9
TABLE_RULE_MIN_WIDTH_FRAC = 0.15
TABLE_RULE_EDGE_TOL = 4
RULE_MIN_COVER = 0.6

# Text proposals/front matter: journal_front_matter and justified_scan.
FRONT_MATTER_MIN_PROSE_WORDS = 60
FRONT_MATTER_TITLE_MIN_WORDS = 4
FRONT_MATTER_TITLE_MAX_WORDS = 40
FRONT_MATTER_TITLE_SCALE = 1.25
FRONT_MATTER_JOURNAL_TITLE_SCALE = 0.95
PROPOSAL_ALIGN_TOL = 3.0
PROPOSAL_ALIGN_MIN_SHARE = 0.6
PROPOSAL_MIN_ROWS = 3
PROPOSAL_MIN_SCORE = 0.62
PROPOSAL_MIN_COLUMNS = 2
PROPOSAL_MAX_COLUMNS = 12

# Classification: repro, paper, footnotes, bibliography, dropcap, panels.
MONO_MIN_SHARE = 0.8
TOC_MIN_RUN = 5
TOC_NUMBER_COLUMN_MIN_X = 0.75
TOC_COLUMN_MATCH_MIN_SHARE = 0.8
TOC_COLUMN_Y_TOL = 2.0
EQUATION_CENTER_TOL = 0.12
EQUATION_MAX_WIDTH = 0.75
EQUATION_MATH_FONT_STRONG = 0.45
EQUATION_MATH_FONT_WEAK = 0.25
EQUATION_MATH_CHAR_WEAK = 0.05
EQUATION_MATH_CHAR_STRONG = 0.25
FOOTNOTE_MIN_Y = 0.70
FOOTNOTE_MAX_SIZE = 0.95
HEADING_BOLD_MIN_SHARE = 0.60
HEADING_TITLE_MIN_SHARE = 0.60

# Furniture: hard, manuscript, SBTi, and Packet B.
FURNITURE_HEIGHT_TOL = 0.015
FURNITURE_HEADER_BAND = 0.10
FURNITURE_FOOTER_BAND = 0.87
FURNITURE_TOUCH_TOL = 2
FURNITURE_X_TOL = 3
LINE_NUMBER_MARGIN_FRAC = 0.14
LINE_NUMBER_MIN_COUNT = 8
LINE_NUMBER_MIN_INCREASING = 0.8
LINE_NUMBER_MIN_BODY_WIDTH = 0.3
LINE_NUMBER_MIN_PAGE_EXTENT = 0.4
LINE_NUMBER_MIN_BODY_EXTENT = 0.7
MARGINALIA_HEADER_ZONE = 0.08
MARGINALIA_FOOTER_ZONE = 0.13
MARGINALIA_MAX_HEIGHT_FRAC = 0.035
MARGINALIA_MAX_CHARS = 150
# Capital IQ section runs; two-value alternating journal heads stay furniture.
SECTIONED_HEAD_MIN_DISTINCT = 3
SECTIONED_HEAD_MIN_RUN_PAGES = 2

# Reflow/continuation: hard, manuscript, repro_tight, lists, and footnotes.
REFLOW_MAX_GAP_LINES = 2.4
REFLOW_SIZE_DELTA = 0.15
REFLOW_X_TOL = 0.015
REFLOW_COLUMN_MARGIN = 0.14
REFLOW_BODY_SCALE = 0.9
CONTINUATION_COLUMN_GAP = 0.02
BLOCKQUOTE_MIN_INDENT = 0.1
BLOCKQUOTE_X_TOL = 0.01
LIST_MIN_INDENT = 0.01
EQUATION_MERGE_GAP = 1.8
CAPTION_GAP = 0.05

# Figure/equation geometry: repro, Peng, R00153, R00443, and SBTi formulas.
FIGURE_VECTOR_MIN_SEGMENTS = 8
FIGURE_VECTOR_MIN_SIDE = 60.0
FIGURE_PAGE_LINE_FRAC = 0.98
FIGURE_MIN_AREA_FRAC = 0.01
FIGURE_MAX_AREA_FRAC = 0.70
FIGURE_IMAGE_MIN_SIDE = 40.0
FIGURE_IMAGE_MAX_PAGE_FRAC = 0.90
FIGURE_IMAGE_SPAN_FRAC = 0.95
FIGURE_TABLE_OVERLAP = 0.5
FIGURE_RULED_TABLE_OVERLAP = 0.4
FIGURE_MAX_TEXT_DENSITY = 0.35
FIGURE_CAPTION_MAX_WORDS = 60
FIGURE_CAPTION_REACH = 0.25
RASTER_EQ_MAX_HEIGHT = 0.20
RASTER_EQ_REACH = 0.06
FIGURE_GROW_GAP = 0.04
FIGURE_CROP_DPI = 200

# Wrapped-cell recovery: all_text_wrapped ruled/unruled controls.
WRAP_RULE_COORD_TOL = 0.5
WRAP_HEADER_MAX_SPAN_WIDTH = 200
WRAP_MAX_RECORD_KEY_WORDS = 6

# Resource limits (tests/REPORT-security.md). A pathological PDF must never
# stall or crash a batch. Each limit is at least ten times the largest value
# measured on tests/real and the golden corpus (76 documents), and a tripped
# limit degrades visibly: a warning, a stats["resource_limits"] record, and
# the text kept.
#
# Table projection: coordinates handed to table_recon may lie outside the page
# by this many times the page's larger side. Measured: no non-finite
# coordinate; at most 172.5 pt outside a 612 x 792 pt page (0.22 of its larger
# side, SBTi). Limit 3.0 page sides.
TABLE_PROJECTION_MARGIN = 3.0

# Rule pairing for table zones. Measured: at most 75 horizontal rule
# segments on a page (R00023) and 31 distinct rule rows (R00293). Limits 1000
# segments (13x) and 400 rows (13x); above them the zone search is skipped.
TABLE_RULES_MAX = 1000
TABLE_RULE_ROWS_MAX = 400

# Code indentation. Measured: one code block in the corpus (R00443), average
# glyph width 2.706 pt, widest indent 12 spaces. Limits: a glyph narrower
# than 0.25 pt is implausible (a tenth of the narrowest seen); an indent is
# cut at 120 spaces (10x).
CODE_MIN_CHAR_WIDTH = 0.25
CODE_MAX_INDENT = 120
