# Capital IQ Key Developments follow-up

The licensed source is read locally as ignored
`tests/real/capiq_keydev.pdf`. Neither the PDF, its supplied Markdown, nor any
document text is committed. Evidence below identifies pages and geometry but
does not reproduce company names, headlines, or the licensed footer.

## B0 — confirmed baseline findings

The PDF has 185 pages. Pages 1–3 are the contents; pages 4–185 contain 47
company sections and 2,325 logical data rows in one continuing four-column
layout.

### B1: section titles are suppressed running heads

On pages 4–185 the only company-level section label is a header-band line at
approximately y=42.7–59.2 pt. There are 47 distinct contiguous runs. Their
page bounds are:

```text
4–7, 8–11, 12–15, 16–19, 20–23, 24–27, 28–31, 32–35, 36–39,
40–43, 44–47, 48–51, 52–55, 56–59, 60–63, 64–67, 68–71,
72–75, 76–78, 79–82, 83–86, 87–88, 89–92, 93–96, 97–100,
101–104, 105–108, 109–112, 113–116, 117–120, 121–124,
125–128, 129–132, 133–135, 136–139, 140–142, 143–146,
147–149, 150–153, 154–157, 158–161, 162–165, 166–169,
170–173, 174–177, 178–181, 182–185
```

Every one is recorded as `proc_marginalia` suppression, including the first
page of each run, so none can become a section heading in the body. Pages 2
and 3 contain two additional header-shaped values from the contents layout;
they are outside the 47 data-section runs.

### B2: hard hyphens are removed at line joins

The rendered/source lines show the named uppercase compounds split after a
printed hyphen: the first appears repeatedly beginning on PDF p. 4, the
vehicle compound appears on p. 26, and the reliability compound appears on
p. 127. Current Markdown removes the printed hyphen from all three. The
lowercase `trans-` / `action` control belongs in the fixture; lowercase
dehyphenation remains the intended behavior.

### B3: fill-backed banners arrive late in stream order

Each section-opening page (pp. 4, 8, 12, …, 182) has a dark banner at
y=137.6–150.0 pt. On every one of the 47 pages its text block is emitted near
the end of the character stream, after all row blocks and immediately before
the running head/footer blocks. The banner therefore renders after the page's
rows. Across the 47 sections, 45 interior banner headings appear with the next
section's content instead of at their own geometric section start; the first
and last are the boundary cases.

### B4: contents entries and page numbers are separate blocks

On pp. 1–3, the 47 contents labels are separate blocks from their page-number
columns. `_demote_toc` only recognizes a run when each individual block ends
in a page number. It therefore sees no qualifying run: the labels remain
headings while the detached number columns render as repeated numeric text.
This is an isolated contents-layout mismatch, but no fix is made in B0.

### B5: current table detection evidence

The region trace records 47 candidates on 47 PDF pages. Forty-five reconstruct
as grids and two keep ordered prose: region 41 on p. 165 has no reconstruction
result, and region 44 on p. 177 reconstructs 212 of 249 member tokens, below
the 0.9 guard. The 45 grids contain 306 reconstructed body rows. This differs
from the brief's 39-page/300-row observation; B5 will reconcile the page and
row definitions rather than changing detection.

## Token baseline

Under the standard content-word metric, both the supplied v0.1.14 Markdown
and the current B0 conversion contain **56,419** words. The native PDF layer
contains 60,392 whitespace tokens. The net difference is 3,973 tokens:
3,872 tokens are in 731 recorded furniture suppressions (running heads,
licensed footers, copyright/footer lines, and page counters), while the
remaining net 101 is explained by lossless line-end joins and Markdown/table
normalization. The multiset comparison is 4,070 source-only occurrences and
97 output-only occurrences. No unrecorded content-loss class was found.
