## 1 Scope

Running heads are the second source of noise, because they repeat on every page and sit exactly where a heading would. Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates. Repetition can, since a header recurs across pages while a title appears once. The benchmark documents in this study were built to exercise those two decisions and nothing else.

Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line. A converter that joins lines with a space will emit a broken word at every such break. Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback.

| Metric | 2025 | 2026 | 2027 |
| --- | --- | --- | --- |
| Share of renewable electricity | 80% | 84% | 88% |
| Minimum coverage | 67% | 67% | 67% |

Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use. The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion.

The text-layer path handles digital publications; a raster copy of the same file drives the recognition path. Both paths converge on the same block structure before any processor runs. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project. Line heights are clustered to recover heading levels when a document has no section numbers.

When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them. Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time. The remaining processors are direct ports and are documented against the source files they come from.

Every threshold in the code was set by looking at a failure, not by tuning against a corpus. That makes the thresholds easy to defend and easy to revise when a new failure appears. We report where the approach breaks so that a reader can decide whether it fits their documents. Multi-line table cells remain the weakest point and are listed as partial support.

Journals that style every heading identically defeat the height clustering and lose a level. Scanned pages inherit every error of the recogniser, including stray page numbers in the middle of a paragraph. None of these failures corrupts the surrounding text; they degrade the structure rather than the content. The synthetic set is regenerated from scripts, so a fixture can be changed and the change reviewed.

Expected outputs are committed beside the fixtures and compared byte for byte. A behaviour change that is intended is recorded by rewriting the expected files in the same commit. An unintended change fails the build before it reaches a release. The vendored table code is treated as third-party and is not edited locally.
