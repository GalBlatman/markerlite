## Footnotes, References and Exponents

*A one-page reproduction*

On two-column pages the guess fails at every figure, every table, and every footnote. We therefore treat stream order as authoritative[^1]and only intervene where a page has no text layer at all. Running heads are the second source of noise, because they repeat on every page and sit exactly where a heading would. Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates. Repetition can, since a header recurs across pages while a title appears once.

The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line. A converter that joins lines with a space will emit a broken word at every such break. Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback.

The fit was close, with r[^2]= 0.81 across the twelve documents, and remained above 0.7 when the scanned copies were included[^2]in the pooled sample. Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use. The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion. The text-layer path handles digital publications; a raster copy of the same file drives the recognition path.

Both paths converge on the same block structure before any processor runs. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project. Line heights are clustered to recover heading levels when a document has no section numbers. When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them.

Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time. The remaining processors are direct ports and are documented against the source files they come from. Every threshold in the code was set by looking at a failure, not by tuning against a corpus. That makes the thresholds easy to defend and easy to revise when a new failure appears. We report where the approach breaks so that a reader can decide whether it fits their documents.

[^1]: Two columns, in every document in the set; the abstract runs full measure.

[^2]: Scanned copies were produced by rasterising the digital file at 150 dots per inch and recognising it with Tesseract at default settings; the recogniser was not tuned for the fonts used, which understates its accuracy on real scans.
