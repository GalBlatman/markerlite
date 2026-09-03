# Reading Order Under Adversarial Layout: A Synthetic Benchmark for Weight-Free PDF Conversion

### Ada Lovelace and Charles Babbage

*Analytical Engine Laboratory, London*

**Abstract** Reading order is the first thing a converter gets wrong and the last thing a reader forgives. The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read. Geometric sorting of blocks discards that signal and replaces it with a guess about columns. On two-column pages the guess fails at every figure, every table, and every footnote. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project. We report where the approach breaks so that a reader can decide whether it fits their documents.

## 1 Introduction

Reading order is the first thing a converter gets wrong and the last thing a reader forgives[^1]. The character stream of a well-formed PDF already encodes the order in which the author expected the text to be read. Geometric sorting of blocks discards that signal and replaces it with a guess about columns. On two-column pages the guess fails at every figure, every table, and every footnote.

We therefore treat stream order as authoritative and only intervene where a page has no text layer at all. Running heads are the second source of noise, because they repeat on every page and sit exactly where a heading would. Position alone cannot separate the two: a section title drawn at the top margin looks like a header to any rule that only inspects coordinates. Repetition can, since a header recurs across pages while a title appears once.

## 2 Related Work

The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright, so it can be redistributed[^2]with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line. A converter that joins lines with a space will emit a broken word at every such break.

Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback. Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference. The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use.

The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion. The text-layer path handles digital publications; a raster copy of the same file drives the recognition path. Both paths converge on the same block structure before any processor runs. Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project.

## 3 Benchmark Design

Line heights are clustered to recover heading levels when a document has no section numbers. When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them. Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time.

The remaining processors are direct ports and are documented against the source files they come from. Every threshold in the code was set by looking at a failure, not by tuning against a corpus. That makes the thresholds easy to defend and easy to revise when a new failure appears. We report where the approach breaks so that a reader can decide whether it fits their documents.

[^1]: Readers do forgive a wrong word; they rarely forgive a paragraph from the second column spliced into the first.

[^2]: The footer zone is the bottom thirteen percent of the page in the reference implementation.

| Feature | Precision | Recall | N |
| --- | --- | --- | --- |
| Two columns | 0.98 | 0.97 | 12 |
| Running head | 1.00 | 0.94 | 12 |
| Footnotes | 0.91 | 0.88 | 9 |
| Ruled table | 0.87 | 0.83 | 6 |
| Hyphenation | 0.99 | 0.99 | 12 |

*Table 1. Conversion accuracy on the synthetic set, by layout feature. Higher is better; the last column counts documents.*

Multi-line table cells remain the weakest point and are listed as partial support[^3]. Journals that style every heading identically defeat the height clustering and lose a level. Scanned pages inherit every error of the recogniser, including stray page numbers in the middle of a paragraph. None of these failures corrupts the surrounding text; they degrade the structure rather than the content.

## 4 Results

The synthetic set is regenerated from scripts, so a fixture can be changed and the change reviewed. Expected outputs are committed beside the fixtures and compared byte for byte. A behaviour change that is intended is recorded by rewriting the expected files in the same commit. An unintended change fails the build before it reaches a release.

The vendored table code is treated as third-party and is not edited locally. Where the original relied on a learned layout model, a font-size rule stands in for it. The rule is coarse, but it is inspectable, and a wrong answer can be traced to a number in the source. Reviewers asked whether the approach generalises beyond journal articles; we make no such claim.

## 5 Discussion

Books, slides and forms have layouts these heuristics were never shown and would misread. The scope is deliberately narrow: articles with a text layer, converted for reading by a language model. Within that scope the results are stable across the publishers we tried. Outside it, users should expect to check the output before trusting it.

A second reviewer asked for timings; conversion runs at a few pages per second on a laptop. Most of that time is spent in the table detector, which is invoked on every page. Skipping it on pages with no ruling lines would halve the runtime at no cost to accuracy. We leave that optimisation for a later release and note it here for completeness.

[^3]: The generators and the fixtures ship in the repository under an Apache-2.0 licence.
