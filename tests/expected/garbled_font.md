<!-- ocr page 1 -->

## 2 Theory

Reading order is the first thing a converter gets wrong and the last thing a reader forgives. The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read. Geometric sorting of blocks discards that signal and replaces it with a guess about columns. On two-column pages the guess fails at every figure, every table, and every footnote.

Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates. Repetition can, since a header recurs across pages while a title appears once. The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter.

Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback. Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use.
