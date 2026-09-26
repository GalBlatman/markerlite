<!-- ocr page 1 -->

#### Journal of Synthetic Studies 12(3), 2026

#### Lovelace and Babbage

# Reading Order Under Adversarial Layout: A Synthetic Benchmark for Weight-Free PDF Conversion

### Ada Lovelace and Charles Babbage Analytical Engine Laboratory, London

Abstract

Reading order is the first thing a converter gets wrong and the last thing a reader forgives. The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read. Geometric sorting of blocks discards that signal

and replaces it with a guess about columns. On two-column pages the guess fails at every figure, every table, and every footnote. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project. We report where the approach breaks so that a reader can decide whether it fits their documents.

## 1 Introduction

Reading order is the first thing a converter gets wrong and the last thing a reader forgives . The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read. Geometric sorting of blocks discards that signal and replaces it with a guess about columns. On two-column pages the guess fails at every figure, every table, and every footnote.

We therefore treat stream order as authoritative and only intervene where a page has no text layer at all. Running heads are the second source of noise, because they repeat on every page and sit exactly where a heading would. Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates. Repetition can, since a header recurs across pages while a title appears once.

## 2 Related Work

The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line. A converter that joins lines with a space will emit a broken word at every such break.

#### Tables were drawn with visible ruling lines so that the vector-based detector fires bef-

! Readers do forgive a wrong word; they rarely forgive a paragraph from the second column spliced into the first.

### ore the text-alignment fallback. Footnotes were set two points

smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use.

The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion. The text-layer path handles digital publications; a raster copy of the same file drives the recognition path. Both paths converge on the same block structure before any processor runs. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project.

## 3 Benchmark Design

Line heights are clustered to recover heading levels when a document has no section numbers. When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them. Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time.

The remaining processors are direct ports and are documented against the source files they come from. Every threshold in the code was set by looking at a failure, not by tuning against a corpus. That makes the thresholds easy to defend and easy to revise when a new failure appears. We report where the approach breaks so that a reader can decide whether it fits their documents.

Reproduced with permission of the copyright owner. Further reproduction prohibited without permission.

[^2]: The footer zone is the bottom thirteen percent of the page in the reference implementation.
