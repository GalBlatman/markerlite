## 1 Introduction

Repetition can, since a header recurs across pages while a title appears once. The benchmark documents in this study were built to exercise those two decisions and nothing else. Each document is short, synthetic, and free of copyright, so it can be redistributed with the converter. Hyphenation across a column break is a small case that reveals whether continuation logic inspects the trailing character of a line.

A converter that joins lines with a space will emit a broken word at every such break. Tables were drawn with visible ruling lines so that the vector-based detector fires before the text-alignment fallback. Footnotes were set two points smaller than the body and anchored in the bottom fifth of the column. Their labels are superscript digits, and matching digits appear in the body at the point of reference.

The abstract runs across the full measure while the body is set in two columns, which is the arrangement most journals use. The manuscripts we care about in practice are less tidy than this, and we return to them in the discussion. The text-layer path handles digital publications; a raster copy of the same file drives the recognition path. Both paths converge on the same block structure before any processor runs.

*Figure 1. A raster image embedded as an XObject: gradient background with two filled shapes. The caption sits directly under the image.*

Nothing in the pipeline depends on a downloaded model, which is the constraint that motivated the project. Line heights are clustered to recover heading levels when a document has no section numbers. When numbers are present they win, because a numbered heading states its own depth. Captions are recognised by their leading label and attached to the nearest figure or table above them.

## 2 Materials and Methods

Equations are left as images for a later pass rather than transcribed into notation that would be wrong half the time. The remaining processors are direct ports and are documented against the source files they come from. Every threshold in the code was set by looking at a failure, not by tuning against a corpus. That makes the thresholds easy to defend and easy to revise when a new failure appears.

The model is a linear response with a Gaussian disturbance term:

$$
y = α + βx + ε, ε ~ N(0, σ²) (1)
$$

We report where the approach breaks so that a reader can decide whether it fits their documents. Multi-line table cells remain the weakest point and are listed as partial support. Journals that style every heading identically defeat the height clustering and lose a level. Scanned pages inherit every error of the recogniser, including stray page numbers in the middle of a paragraph.

C1 C2 C3 C4 C5 0

25

50

75

100

*Figure 2. A vector chart drawn with path operators: five conditions, response in percent. No image object is involved.*

None of these failures corrupts the surrounding text; they degrade the structure rather than the content. The synthetic set is regenerated from scripts, so a fixture can be changed and the change reviewed. Expected outputs are committed beside the fixtures and compared byte for byte. A behaviour change that is intended is recorded by rewriting the expected files in the same commit.

## 3 Results and Discussion

An unintended change fails the build before it reaches a release. The vendored table code is treated as third-party and is not edited locally. Where the original relied on a learned layout model, a font-size rule stands in for it. The rule is coarse, but it is inspectable, and a wrong answer can be traced to a number in the source.

Summing over conditions gives the pooled estimate

$$
µ = (1/n) Σ yi, i = 1, …, n (2)
$$

Reviewers asked whether the approach generalises beyond journal articles; we make no such claim. Books, slides and forms have layouts these heuristics were never shown and would misread. The scope is deliberately narrow: articles with a text layer, converted for reading by a language model. Within that scope the results are stable across the publishers we tried.

Outside it, users should expect to check the output before trusting it. A second reviewer asked for timings; conversion runs at a few pages per second on a laptop. Most of that time is spent in the table detector, which is invoked on every page. Skipping it on pages with no ruling lines would halve the runtime at no cost to accuracy.
