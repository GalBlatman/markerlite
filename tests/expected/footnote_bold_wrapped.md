## Bold Footnotes Across Lines and Blocks

The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright[^3], so it can be redistributed with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line. A converter that joins lines with a space will emit a broken word at every such break. Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback.

Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column[^4]. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use. The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion. The text-layer path handles digital publications; a raster copy of the same file drives the recognition path.

Both paths converge on the same block structure before any processor runs. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project[^*]. Line heights are clustered to recover heading levels when a document has no section numbers. When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them.

[^3]: **During the 1960s and early 1970s a number of laws were passed and executive orders issued to address the civil rights of various groups, including the Readjustment Assistance Act of 1974 and 12 related statutes.**

[^4]: **The sample covers every firm that reported in the period; firms that reported in only one year are excluded from the panel and listed in the appendix.** *2 of them were later restored after the audit, as the appendix explains in detail; the restoration does not change any estimate reported here.*

[^*]: Corresponding author. The order of authors is alphabetical.
