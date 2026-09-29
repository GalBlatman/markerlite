# Batch C block 1 — experiments and fallback-to-prose implementation

Baseline: `9662c99`. Measured in WSL on 2026-09-28. No commit, push, or tag.

**Stopped under the amended region constraint.** The first general prose guard changes ten protected region decisions and the cell matrix of another protected region. Item 5 is not complete; item 6 was not started. The rejected implementation and draft fixture generator were removed from the working tree after the measurements. This report is the only repository change.

The extra changes are a failure of the draft guard, not evidence that those regions should be approved for reclassification. The rendered criteria tables contain narrative cells that must remain in their parent grids. The next implementation would need parent-grid context before it can reject a candidate.

## Measured states

| State | SBTi regions | Fallbacks | Standard content words |
| --- | ---: | ---: | ---: |
| Baseline | 55 | 30 | 18,345 |
| Diagnostic excluding only region 39 | 54 | 29 | 18,347 |
| Rejected general guard | 44 | 26 | 18,375 |

The isolated diagnostic filters the known region in memory solely to measure the requested result; it is not a document-specific production fix. Every remaining decision and cell hash is identical in that diagnostic.

Region 39 contains 69 source words but its current fallback retains 67. The missing tokens are `is` after `target year`, and the final `data.`. Both are visible on the rendered page. The user approved recovering both during this task. **Table-markup difference: zero content words. Recovered source words: +2.** The standard metric already removes table pipes, separator rows, HTML tags, and emphasis. The prose has all 69 words, in source/page reading order, with no table markup. It joins the bold lead-in and the following explanation into one paragraph. The rejected broad guard introduces a further net +28 elsewhere, outside the authorized change.

## Mechanism and stopping point

The draft tested member lines for flowing prose, with horizontal row separators, simultaneous cell lines, and repeated record starts under a distinct header as counter-evidence. White filled rectangles behind SBTi text must not count as visible row rules. However, rejecting candidates on their current member lines alone misclassifies narrative cells inside parent tables. Rejection also changes which members later overlapping candidates can consume: region 17 retains its reconstruction decision but changes its cells after region 16 is rejected.

The draft synthetic fixture was also unfinished: the detector combined adjacent cases into one candidate. Its output did not yet satisfy prose / prose / prose / table / table. No expected output was blessed. No full regression result is claimed for the rejected draft.

The blocked experiment did not touch `table_recon.py`. PLAN and CLAUDE statuses remain unchanged because neither item is done. AGENTS.md required no regeneration.

## Every original region

Original region IDs remain stable in this report; subsequent emitted numbering shifts when regions disappear. Identity is matched by PDF page and bounding box. Cell checks compare each parsed cell hash, including row and column positions.

| Original region | PDF page | Baseline decision | Draft decision | Cell hashes |
| ---: | ---: | --- | --- | --- |
| 1 | 2 | reconstruction | reconstruction | identical |
| 2 | 3 | fallback | fallback | identical |
| 3 | 10 | reconstruction | not emitted | **BLOCKER: removed** |
| 4 | 11 | fallback | fallback | identical |
| 5 | 11 | fallback | fallback | identical |
| 6 | 12 | fallback | fallback | identical |
| 7 | 13 | fallback | fallback | identical |
| 8 | 14 | reconstruction | not emitted | **BLOCKER: removed** |
| 9 | 15 | reconstruction | reconstruction | identical |
| 10 | 16 | reconstruction | reconstruction | identical |
| 11 | 16 | reconstruction | reconstruction | identical |
| 12 | 16 | fallback | fallback | identical |
| 13 | 17 | fallback | fallback | identical |
| 14 | 17 | fallback | fallback | identical |
| 15 | 19 | reconstruction | not emitted | **BLOCKER: removed** |
| 16 | 20 | fallback | not emitted | **BLOCKER: removed** |
| 17 | 20 | reconstruction | reconstruction | **BLOCKER: changed** |
| 18 | 22 | fallback | fallback | identical |
| 19 | 24 | reconstruction | reconstruction | identical |
| 20 | 25 | reconstruction | not emitted | **BLOCKER: removed** |
| 21 | 25 | fallback | not emitted | **BLOCKER: removed** |
| 22 | 26 | reconstruction | reconstruction | identical |
| 23 | 26 | fallback | not emitted | **BLOCKER: removed** |
| 24 | 27 | reconstruction | not emitted | **BLOCKER: removed** |
| 25 | 29 | fallback | fallback | identical |
| 26 | 29 | fallback | fallback | identical |
| 27 | 30 | reconstruction | reconstruction | identical |
| 28 | 31 | reconstruction | reconstruction | identical |
| 29 | 32 | reconstruction | not emitted | **BLOCKER: removed** |
| 30 | 34 | fallback | fallback | identical |
| 31 | 35 | reconstruction | not emitted | **BLOCKER: removed** |
| 32 | 36 | reconstruction | reconstruction | identical |
| 33 | 36 | fallback | fallback | identical |
| 34 | 40 | reconstruction | reconstruction | identical |
| 35 | 42 | reconstruction | reconstruction | identical |
| 36 | 43 | fallback | fallback | identical |
| 37 | 44 | fallback | fallback | identical |
| 38 | 45 | fallback | fallback | identical |
| 39 | 45 | fallback | not emitted | removed (allowed) |
| 40 | 46 | fallback | fallback | identical |
| 41 | 47 | fallback | fallback | identical |
| 42 | 48 | fallback | fallback | identical |
| 43 | 49 | fallback | fallback | identical |
| 44 | 53 | fallback | fallback | identical |
| 45 | 54 | reconstruction | reconstruction | identical |
| 46 | 55 | fallback | fallback | identical |
| 47 | 56 | reconstruction | reconstruction | identical |
| 48 | 57 | reconstruction | reconstruction | identical |
| 49 | 58 | reconstruction | reconstruction | identical |
| 50 | 60 | fallback | fallback | identical |
| 51 | 60 | reconstruction | reconstruction | identical |
| 52 | 61 | fallback | fallback | identical |
| 53 | 61 | reconstruction | reconstruction | identical |
| 54 | 62 | fallback | fallback | identical |
| 55 | 63 | fallback | fallback | identical |

There are no newly emitted regions. Region 38 remains a fallback with identical cells. Of the 54 protected regions, 43 retain both decision and cells, ten disappear, and region 17 retains its decision but changes its cells.

## Rendered-page evidence for every blocker

Each crop below is rendered directly from the original SBTi PDF. The crops were visually inspected. The before/after Markdown for their entire pages follows, so text moving into a later overlapping region is not mistaken for text loss. Region 17 overlaps region 16 on p. 20. Narrative-only criteria cells and their parent table boundaries are visible in these crops.

### Region 3, PDF p. 10

Bounding box: `(546.12, 349.59, 788.16, 526.1)`.

![Rendered source region 3](/tmp/batchC-draft/region-03.png)

### Region 8, PDF p. 14

Bounding box: `(298.56, 141.26, 536.16, 320.01)`.

![Rendered source region 8](/tmp/batchC-draft/region-08.png)

### Region 15, PDF p. 19

Bounding box: `(546.12, 176.63, 788.16, 328.65)`.

![Rendered source region 15](/tmp/batchC-draft/region-15.png)

### Region 16, PDF p. 20

Bounding box: `(546.12, 117.89, 788.16, 515.13)`.

![Rendered source region 16](/tmp/batchC-draft/region-16.png)

### Region 17, PDF p. 20

Bounding box: `(316.56, 117.89, 788.21, 528.97)`.

![Rendered source region 17](/tmp/batchC-draft/region-17.png)

### Region 20, PDF p. 25

Bounding box: `(546.12, 117.9, 788.16, 512.82)`.

![Rendered source region 20](/tmp/batchC-draft/region-20.png)

### Region 21, PDF p. 25

Bounding box: `(55.56, 117.9, 788.11, 528.1)`.

![Rendered source region 21](/tmp/batchC-draft/region-21.png)

### Region 23, PDF p. 26

Bounding box: `(316.56, 117.85, 788.09, 538.44)`.

![Rendered source region 23](/tmp/batchC-draft/region-23.png)

### Region 24, PDF p. 27

Bounding box: `(564.12, 117.71, 788.1, 523.13)`.

![Rendered source region 24](/tmp/batchC-draft/region-24.png)

### Region 29, PDF p. 32

Bounding box: `(546.12, 117.9, 788.16, 295.05)`.

![Rendered source region 29](/tmp/batchC-draft/region-29.png)

### Region 31, PDF p. 35

Bounding box: `(546.12, 117.85, 788.16, 213.6)`.

![Rendered source region 31](/tmp/batchC-draft/region-31.png)

## Content words

Counts use `markerlite.content_words()` without a replacement metric. Baseline runs completed for all ten reference documents and both pipeline inputs. Pipeline PDFs were read in place under `/home/galbl/unknown-knowns/pilot/pdf/` and were never copied into the repository. The blocked experiment was not extended to those documents; an em dash means not measured, not unchanged.

| Document | Baseline | Rejected draft | Explanation |
| --- | ---: | ---: | --- |
| Target-Validation-Protocol | 18345 | 18375 | +2 approved recovery; +28 from forbidden changes |
| Ragins craft of clear writing 2012 | 6625 | — | stopped before after-run |
| peng2009 | 12046 | — | stopped before after-run |
| greenwood2006 | 14777 | — | stopped before after-run |
| wry2013 | 18441 | — | stopped before after-run |
| jay2013 | 16377 | — | stopped before after-run |
| york2018 | 19930 | — | stopped before after-run |
| kitchener2002 | 13256 | — | stopped before after-run |
| suchman1995 | 16458 | — | stopped before after-run |
| kostova1999 | 11297 | — | stopped before after-run |
| R01285 | 23062 | — | stopped before after-run |
| R02611 | 15307 | — | stopped before after-run |
| paper | 304 | 304 | exact cell matrices unchanged |
| hard | 1021 | 1021 | exact cell matrices unchanged |

The hard.pdf and paper.pdf comparisons include every cell on every page, so their first-page tables are also unchanged. Kostova Figure 1, SBTi p. 48 visual parent-cell verification, the pipeline first pages, and Ragins p. 1 after-verification remain outstanding. This report makes no fix claim for them.

## SBTi page-level word changes

| PDF page | Baseline | Rejected draft | Delta |
| ---: | ---: | ---: | ---: |
| 20 | 432 | 423 | -9 |
| 25 | 380 | 402 | +22 |
| 27 | 167 | 182 | +15 |
| 45 | 109 | 111 | +2 |

The region-only diagnostic has exactly the +2 on p. 45. All other deltas above belong to the rejected broad guard.

## Before and after Markdown

These are actual complete page outputs from the baseline and rejected draft, with page-marker comments omitted. “After” here does not denote shipped or accepted behavior.

### PDF p. 10: before

```markdown
**C4 – Scope 3** *If a company’s relevant scope 3 emissions are 40%* *or more of total scope 1, 2, and 3 emissions, they* *must be included in near-term science-based targets.* *All companies involved in the sale or distribution of* *natural gas and/or other fossil fuels shall set scope 3* *targets for the use of sold products, irrespective of the* *share of these emissions compared to the total scope* *1, 2, and 3 emissions of the company.*

- For companies ***not*** involved in the sale or distribution of natural gas and/or other fossil fuel, at least one S3 target must be set if the S3 emissions are responsible for more than 40% of the total S1+S2+S3 emissions.
- For companies involved in the sale, transmission, or distribution of fossil fuels, a scope 3 target on use of sold products must be set regardless of how these emissions contribute to the overall inventory. Please see criterion 22 for further details.

For companies not involved in the sale or distribution of natural gas and/or other fossil fuels: **Criterion met if:**

  - S3 emissions represent 40% or more of total S1+2+3 emissions. ***AND***
  - At least one S3 target has been set. **Criterion not met if:**
    - S3 emissions represent 40% or more of total S1+2+3 emissions. ***AND***
  - No target(s) on S3 have been set. For companies involved in the sale, transmission, or distribution of fossil fuels, companies must follow criterion 22.

#### I.IV Emissions coverage

**C5 – Scope 1, 2, and 3 allowable exclusions:** *Companies may exclude up to 5% of scope 1 and* *scope 2 emissions combined in the boundary of the* *inventory and target. Companies may exclude a* *maximum of 5% of emissions from their total scope 3* *inventory.*

Scope 1 and 2:

- The GHG inventory for scope 1 and 2 must account for at least 95% of corporate-wide emissions. All exclusions (e.g., activities, facilities) must be clearly justified with estimates of associated emissions value(s).
- Specific regions/business activities can be excluded if they represent less than 5% of total S1 and 2 emissions. If specific regions or business sections are excluded from S1 or S2, the company must assess if these emissions are relevant for S3 accounting and account for them per the requirements of the GHG Protocol Scope 3 Standard.

| Criterion met if: |
| --- |
| ● No GHG emissions are excluded from the S1 and S2 inventory or target boundary. OR |
| ● GHG exclusions of S1 and S2 combined in the inventory and target boundary represent less than 5% of total S1 and S2 emissions. AND |
| ● If exclusions include specific regions or business, the company confirms it will follow the C26 and C27 recalculation criteria and will not include these specifications in the official target language. |
```

### PDF p. 10: rejected draft after

```markdown
**C4 – Scope 3** *If a company’s relevant scope 3 emissions are 40%* *or more of total scope 1, 2, and 3 emissions, they* *must be included in near-term science-based targets.* *All companies involved in the sale or distribution of* *natural gas and/or other fossil fuels shall set scope 3* *targets for the use of sold products, irrespective of the* *share of these emissions compared to the total scope* *1, 2, and 3 emissions of the company.*

- For companies ***not*** involved in the sale or distribution of natural gas and/or other fossil fuel, at least one S3 target must be set if the S3 emissions are responsible for more than 40% of the total S1+S2+S3 emissions.
- For companies involved in the sale, transmission, or distribution of fossil fuels, a scope 3 target on use of sold products must be set regardless of how these emissions contribute to the overall inventory. Please see criterion 22 for further details.

For companies not involved in the sale or distribution of natural gas and/or other fossil fuels: **Criterion met if:**

  - S3 emissions represent 40% or more of total S1+2+3 emissions. ***AND***
  - At least one S3 target has been set. **Criterion not met if:**
    - S3 emissions represent 40% or more of total S1+2+3 emissions. ***AND***
  - No target(s) on S3 have been set. For companies involved in the sale, transmission, or distribution of fossil fuels, companies must follow criterion 22.

#### I.IV Emissions coverage

**C5 – Scope 1, 2, and 3 allowable exclusions:** *Companies may exclude up to 5% of scope 1 and* *scope 2 emissions combined in the boundary of the* *inventory and target. Companies may exclude a* *maximum of 5% of emissions from their total scope 3* *inventory.*

Scope 1 and 2:

- The GHG inventory for scope 1 and 2 must account for at least 95% of corporate-wide emissions. All exclusions (e.g., activities, facilities) must be clearly justified with estimates of associated emissions value(s).
- Specific regions/business activities can be excluded if they represent less than 5% of total S1 and 2 emissions. If specific regions or business sections are excluded from S1 or S2, the company must assess if these emissions are relevant for S3 accounting and account for them per the requirements of the GHG Protocol Scope 3 Standard.

**Criterion met if:**

  - No GHG emissions are excluded from the S1 and S2 inventory or target boundary. ***OR***
  - GHG exclusions of S1 and S2 combined in the inventory and target boundary represent less than 5% of total S1 and S2 emissions. ***AND***
  - If exclusions include specific regions or business, the company confirms it will follow the C26 and C27 recalculation criteria and will not include these specifications in the official target language.
```

### PDF p. 14: before

```markdown
#### II. Method validity

**C7 – Method validity** *Targets must be modeled using the latest version of* *methods and tools approved by the initiative. Targets* *modeled using previous versions of the tools or* *methods can only be submitted to the SBTi for* *validation within 6 months of the publication of the* *revised method or sector-specific tools.*

| ● Companies must use correct target setting methods for their sector. |
| --- |
| ● The latest version of the method/tool must be used to set targets. |
| ● Older versions of a method or a tool can only be used within 6 months of the publication of an updated version unless otherwise noted. |
| ● The SBTi recommends using the most ambitious decarbonization scenarios that lead to the earliest reductions and the least cumulative emissions. |

If an approved SBT method was employed to develop the target: **Criterion met if:**

- The latest version of the methods and tools are used to set the targets. ***AND***
- If the company is in a sector that requires a specific method to be used, the appropriate method/tool is used. ***OR***
- An older version of a tool/method was used but the target was submitted within 6 months of the publication of the latest corresponding tool/method. **Criterion not met if:**
  - If the company is in a sector that requires a specific method to be used, the appropriate method/tool is not used. ***OR***
  - An older version of a tool/method was used but the target was submitted after 6 months of the publication of the latest corresponding tool/method.

#### III. Emissions accounting requirements

**C8 – Scope 2 accounting approach** *Companies shall disclose whether they are using a* *location- or market-based accounting approach as* *per the GHG Protocol Scope 2 Guidance to calculate* *base year emissions and to track performance*

- Companies must select consistent approaches for S2 accounting for the base year GHG inventory and tracking progress against S2 targets.
- When modeling targets using the SDA, it companies should model purchased heat and

**Criterion met if:**

  - The method used to account for base year and most recent year S2 inventory is the same. ***AND***
  - The method used to track performance towards its S2 target is consistent with the
```

### PDF p. 14: rejected draft after

```markdown
#### II. Method validity

**C7 – Method validity** *Targets must be modeled using the latest version of* *methods and tools approved by the initiative. Targets* *modeled using previous versions of the tools or* *methods can only be submitted to the SBTi for* *validation within 6 months of the publication of the* *revised method or sector-specific tools.*

- Companies must use correct target setting methods for their sector.
- The latest version of the method/tool must be used to set targets.
- Older versions of a method or a tool can only be used within 6 months of the publication of an updated version unless otherwise noted.
- The SBTi recommends using the most ambitious decarbonization scenarios that lead to the earliest reductions and the least cumulative emissions.

If an approved SBT method was employed to develop the target: **Criterion met if:**

  - The latest version of the methods and tools are used to set the targets. ***AND***
  - If the company is in a sector that requires a specific method to be used, the appropriate method/tool is used. ***OR***
  - An older version of a tool/method was used but the target was submitted within 6 months of the publication of the latest corresponding tool/method. **Criterion not met if:**
    - If the company is in a sector that requires a specific method to be used, the appropriate method/tool is not used. ***OR***
    - An older version of a tool/method was used but the target was submitted after 6 months of the publication of the latest corresponding tool/method.

#### III. Emissions accounting requirements

**C8 – Scope 2 accounting approach** *Companies shall disclose whether they are using a* *location- or market-based accounting approach as* *per the GHG Protocol Scope 2 Guidance to calculate* *base year emissions and to track performance*

  - Companies must select consistent approaches for S2 accounting for the base year GHG inventory and tracking progress against S2 targets.
  - When modeling targets using the SDA, it companies should model purchased heat and

**Criterion met if:**

    - The method used to account for base year and most recent year S2 inventory is the same. ***AND***
    - The method used to track performance towards its S2 target is consistent with the
```

### PDF p. 19: before

```markdown
**Criterion not met if:**

● Any form of voluntary or compliance-related offsets is counted as reductions toward the progress of the company’s target.

**C12 - Avoided emissions** *Avoided emissions fall under a separate accounting* *system from corporate inventories and do not count* *toward near-term science-based emission reduction* *targets.*

- Avoided emissions accounting is not permitted in the GHG inventory or target boundary. The following are example claims that are not valid when setting SBTs:
  - Product use targets, which claim to “help avoid” product users’ emissions in comparison to an alternative product, on a purely hypothetical basis.
  - Claims that a product’s total lifecycle emissions are lower than alternative products that provide equivalent functions.
  - Use of “baselining” to calculate the emissions impact of a product, which is only acceptable for project accounting and different from corporate accounting.

| Criterion met if: |
| --- |
| ● No use of avoided emissions is disclosed by the company in the submission form. AND |
| ● No sign of the use of avoided emissions in the inventory or the target boundary. Criterion not met if: |
| ● Submission reveals any use of avoided emissions, either as part of the inventory or the target setting process. |

#### IV. Target Formulation

#### IV.I Timeframe

**C13 – Base and target years** *Absolute and intensity-based emission reduction* *near-term targets must cover a minimum of 5 years* *and a maximum of 10 years from the date the target* ● This criterion applies to percentage-based scope 1 and/or 2 and/or 3 emission reduction targets, either in absolute or intensity-based terms. Supplier engagement targets (see **Criterion met if:**

● A percentage-based emission reduction target (intensity or absolute) is being set for scope 1 and/or 2 and/or 3. ***AND***
```

### PDF p. 19: rejected draft after

```markdown
**Criterion not met if:**

● Any form of voluntary or compliance-related offsets is counted as reductions toward the progress of the company’s target.

**C12 - Avoided emissions** *Avoided emissions fall under a separate accounting* *system from corporate inventories and do not count* *toward near-term science-based emission reduction* *targets.*

- Avoided emissions accounting is not permitted in the GHG inventory or target boundary. The following are example claims that are not valid when setting SBTs:
  - Product use targets, which claim to “help avoid” product users’ emissions in comparison to an alternative product, on a purely hypothetical basis.
  - Claims that a product’s total lifecycle emissions are lower than alternative products that provide equivalent functions.
  - Use of “baselining” to calculate the emissions impact of a product, which is only acceptable for project accounting and different from corporate accounting.

**Criterion met if**:

    - No use of avoided emissions is disclosed by the company in the submission form. ***AND***
    - No sign of the use of avoided emissions in the inventory or the target boundary. **Criterion not met if:**
    - Submission reveals any use of avoided emissions, either as part of the inventory or the target setting process.

#### IV. Target Formulation

#### IV.I Timeframe

**C13 – Base and target years** *Absolute and intensity-based emission reduction* *near-term targets must cover a minimum of 5 years* *and a maximum of 10 years from the date the target* ● This criterion applies to percentage-based scope 1 and/or 2 and/or 3 emission reduction targets, either in absolute or intensity-based terms. Supplier engagement targets (see **Criterion met if:**

● A percentage-based emission reduction target (intensity or absolute) is being set for scope 1 and/or 2 and/or 3. ***AND***
```

### PDF p. 20: before

```markdown
*is submitted to the SBTi for validation. The choice of* *base year must be no earlier than 2015.*

| C19) and renewable electricity targets (see C21) are exceptions. |
| --- |
| ● If the target is submitted for validation in the first half of the year (i.e., by the end of June), |
| the timeframe includes the year of submission. If submitted in the second half of the year, the timeframe begins from the start of the following year. |
| ● For example, for targets submitted for validation in the first half of 2023 the valid target years are between 2027 and 2032 inclusive. For those submitted in the second half of 2023 (from 1 July), the valid target years are between 2028 and 2033 inclusive. |
| ● Long-term targets can only be validated in |
| accordance with the Net-Zero Standard Criteria. |
| ● Base years must cover a complete past calendar or financial year. |
| ● Companies must select either a calendar year or a financial year and apply this consistently across the choice of base years for scopes 1, 2 and 3 (if relevant). |
| ● The choice of base year must be no earlier than 2015. |
| ● It is recommended companies use the same base year and most recent year when reporting greenhouse gas inventories to the SBTi, but, if necessary, companies can report a different year for scope 3 when compared to |

|  | ● The target year is between 5 and 10 years |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  | (inclusive) from the date of submission to the |  |  |  |  |  |  |  |  |
|  |  | SBTi. AND |  |  |  |  |  |  |  |  |
|  | ● Base year data is for a complete past calendar |  |  |  |  |  |  |  |  |  |
|  |  | or financial year. AND |  |  |  |  |  |  |  |  |
|  | ● The choice of calendar year or financial year is |  |  |  |  |  |  |  |  |  |
|  |  | applied consistently for base year and target |  |  |  |  |  |  |  |  |
|  |  | year for targets covering a specific scope of |  |  |  |  |  |  |  |  |
|  |  | emissions i.e., if a company chooses to use a |  |  |  |  |  |  |  |  |
|  |  | fiscal year for a scope 1+2 target, this needs to |  |  |  |  |  |  |  |  |
|  |  | be applied for both the base year and target |  |  |  |  |  |  |  |  |
|  |  | year for a scope 1+2 target. AND |  |  |  |  |  |  |  |  |
|  | ● The choice of a calendar year or a financial |  |  |  |  |  |  |  |  |  |
|  |  | year is applied consistently across base years |  |  |  |  |  |  |  |  |
|  |  | for scopes 1, 2 and 3 (if relevant). |  |  |  |  |  |  |  |  |
| Criterion not met if: |  |  |  |  |  |  |  |  |  |  |
|  | ● The target year is not between 5 and 10 years |  |  |  |  |  |  |  |  |  |
|  |  | (inclusive) from the date of submission to the |  |  |  |  |  |  |  |  |
|  |  | SBTi. OR |  |  |  |  |  |  |  |  |
|  | ● Base year data is not available for a complete |  |  |  |  |  |  |  |  |  |
|  |  | past calendar or financial year. OR |  |  |  |  |  |  |  |  |
|  | ● Only a long-term target (10 years from the date |  |  |  |  |  |  |  |  |  |
|  |  | of submission up to 2050) has been submitted. |  |  |  |  |  |  |  |  |
|  |  | OR |  |  |  |  |  |  |  |  |
|  | ● The choice of calendar year or financial year is |  |  |  |  |  |  |  |  |  |
|  |  | not applied consistently for base year and |  |  |  |  |  |  |  |  |
|  |  | target year for targets covering a specific scope |  |  |  |  |  |  |  |  |
|  |  | of emissions. OR |  |  |  |  |  |  |  |  |
```

### PDF p. 20: rejected draft after

```markdown
*is submitted to the SBTi for validation. The choice of* *base year must be no earlier than 2015.*

| C19) and renewable electricity targets (see | ● The target year is between 5 and 10 years |
| --- | --- |
| C21) are exceptions. | (inclusive) from the date of submission to the |
| ● If the target is submitted for validation in the | SBTi. AND |
| first half of the year (i.e., by the end of June), | ● Base year data is for a complete past calendar |
| the timeframe includes the year of | or financial year. AND |
| submission. If submitted in the second half of | ● The choice of calendar year or financial year is |
| the year, the timeframe begins from the start | applied consistently for base year and target |
| of the following year. | year for targets covering a specific scope of |
| ● For example, for targets submitted for | emissions i.e., if a company chooses to use a |
| validation in the first half of 2023 the valid | fiscal year for a scope 1+2 target, this needs to |
| target years are between 2027 and 2032 | be applied for both the base year and target |
| inclusive. For those submitted in the second | year for a scope 1+2 target. AND |
| half of 2023 (from 1 July), the valid target | ● The choice of a calendar year or a financial |
| years are between 2028 and 2033 inclusive. | year is applied consistently across base years |
| ● Long-term targets can only be validated in | for scopes 1, 2 and 3 (if relevant). |
| accordance with the Net-Zero Standard |  |
| Criteria. | Criterion not met if: |
| ● Base years must cover a complete past | ● The target year is not between 5 and 10 years |
| calendar or financial year. | (inclusive) from the date of submission to the |
| ● Companies must select either a calendar year | SBTi. OR |
| or a financial year and apply this consistently | ● Base year data is not available for a complete |
| across the choice of base years for scopes 1, | past calendar or financial year. OR |
| 2 and 3 (if relevant). | ● Only a long-term target (10 years from the date |
| ● The choice of base year must be no earlier | of submission up to 2050) has been submitted. |
| than 2015. | OR |
| ● It is recommended companies use the same | ● The choice of calendar year or financial year is |
| base year and most recent year when | not applied consistently for base year and |
| reporting greenhouse gas inventories to the | target year for targets covering a specific scope |
| SBTi, but, if necessary, companies can report | of emissions. OR |
```

### PDF p. 25: before

```markdown
| C18 - Level of ambition | for scope 3 | emissions (covering scope 3 consistent to keep 2°C For If |  | absolute | percentage-based |  | emission ambition from must be, at a well-below 2°C economic paired with aligned to reduction in be based per unit of of value set out in of value guide to earnings (EBITDA) + costs should and board the cost of external |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reductions targets At a minimum, near-term the entire value chain categories) must be with the level of global temperature compared to pre-industrial | scope 3 targets or individual aligned with methods decarbonization required increase well-below temperatures. |  | reduction | targets: |  |  |  |  |  |  |  |  |  |
|  |  |  | ● | The timeframe | ambition | (i.e., |  |  |  |  |  |  |  |
|  |  |  |  | the base year | to the target | year) |  |  |  |  |  |  |  |
|  |  |  |  | minimum, | aligned with | the |  |  |  |  |  |  |  |
|  |  |  |  | ambition threshold. |  |  |  |  |  |  |  |  |  |
|  |  |  | the | target is based | on | reduction of |  |  |  |  |  |  |  |
|  |  |  | intensity): |  |  |  |  |  |  |  |  |  |  |
|  |  |  | ● | The intensity | targets | must be |  |  |  |  |  |  |  |
|  |  |  |  | relevant activity | growth | projections. |  |  |  |  |  |  |  |
|  |  |  | ● | Economic | intensity | reductions are |  |  |  |  |  |  |  |
|  |  |  |  | at least a 7% | economic | intensity |  |  |  |  |  |  |  |
|  |  |  |  | annual compounded |  | terms. |  |  |  |  |  |  |  |
|  |  |  | ● | The economic | intensity | metric must |  |  |  |  |  |  |  |
|  |  |  |  | on greenhouse | gas | emissions |  |  |  |  |  |  |  |
|  |  |  |  | value added | (GEVA), the | calculations |  |  |  |  |  |  |  |
|  |  |  |  | added must | use the | formulae |  |  |  |  |  |  |  |
|  |  |  |  | “Greenhouse | gas emissions | per unit |  |  |  |  |  |  |  |
|  |  |  |  | added (“GEVA”) | — A | corporate |  |  |  |  |  |  |  |
|  |  |  |  | voluntary climate | action”: |  |  |  |  |  |  |  |  |
|  |  |  | ● | Value added = | gross | profit. |  |  |  |  |  |  |  |
|  |  |  | ● | Value added | = operating | profit = |  |  |  |  |  |  |  |
|  |  |  |  | before interest | and | depreciation |  |  |  |  |  |  |  |
|  |  |  |  | all personnel | costs. | Personnel |  |  |  |  |  |  |  |
|  |  |  |  | include payment | to | management |  |  |  |  |  |  |  |
|  |  |  |  | members. |  |  |  |  |  |  |  |  |  |
|  |  |  | ● | Value added | = sales | revenue - |  |  |  |  |  |  |  |
|  |  |  |  | goods and | services | purchased from |  |  |  |  |  |  |  |
|  |  |  |  | suppliers |  |  |  |  |  |  |  |  |  |

| For absolute based percentage emission reduction targets, criterion met if: |
| --- |
| ● For base years after 2020, the absolute |
| emissions reduction meets the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target |
| ● For base years between 2015 and 2020 (inclusive), the absolute emissions reduction meets the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target For economic intensity-based percentage emission reduction targets, criterion met if: |
| ● GEVA is used as the chosen economic intensity metric and an acceptable formula has been used to calculate GEVA. AND |
| ● For base years after 2020, the economic |
| intensity emissions reduction meets the minimum reduction value as set out below over the target period: Minimum value for economic intensity target = |
| ● For base years between 2015 and 2020 (inclusive), the economic intensity emissions reduction meets the minimum reduction value over the target period as set out below: |
```

### PDF p. 25: rejected draft after

```markdown
**C18 - Level of ambition for scope 3 emissions** **reductions targets** *At a minimum, near-term scope 3 targets (covering* *the entire value chain or individual scope 3* *categories) must be aligned with methods consistent* *with the level of decarbonization required to keep* *global* *temperature* *increase* *well-below* *2°C* *compared to pre-industrial temperatures.*

**For** **absolute** **percentage-based** **emission** **reduction targets:**

- The timeframe ambition (i.e., ambition from the base year to the target year) must be, at a minimum, aligned with the well-below 2°C ambition threshold. **If the target is based on reduction of economic** **intensity):**
  - The intensity targets must be paired with relevant activity growth projections.
  - Economic intensity reductions are aligned to at least a 7% economic intensity reduction in annual compounded terms.
  - The economic intensity metric must be based on greenhouse gas emissions per unit of value added (GEVA), the calculations of value added must use the formulae set out in “Greenhouse gas emissions per unit of value added (“GEVA”) — A corporate guide to voluntary climate action”:
  - Value added = gross profit.
  - Value added = operating profit = earnings before interest and depreciation (EBITDA) + all personnel costs. Personnel costs should include payment to management and board members.
  - Value added = sales revenue - the cost of goods and services purchased from external suppliers

**For absolute based percentage emission reduction** **targets, criterion met if:**

    - For base years after 2020, the absolute emissions reduction meets the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target = 2.5% x (Target year - 2020)
    - For base years between 2015 and 2020 (inclusive), the absolute emissions reduction meets the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target = 2.5% x (Target year - base year)

**For economic intensity-based percentage emission** **reduction targets, criterion met if:**

    - GEVA is used as the chosen economic intensity metric and an acceptable formula has been used to calculate GEVA. ***AND***
    - For base years after 2020, the economic intensity emissions reduction meets the minimum reduction value as set out below over the target period: Minimum value for economic intensity target = 100% - (93%) <sup>(Target year - 2020)</sup>
    - For base years between 2015 and 2020 (inclusive), the economic intensity emissions reduction meets the minimum reduction value over the target period as set out below:
```

### PDF p. 26: before

```markdown
| intensity: If target is based on reduction of physical |
| --- |
| ● The physical intensity denominator must be representative of the company's emissions in the target boundary. |
| ● The physical intensity denominator corresponds to a measurable product, output or level or service, it cannot be a unit of monetary or economic value. Companies are required to provide a clear definition of the physical intensity unit applied in this type of target. |
| ● If an SDA pathway is available, the timeframe ambition must be aligned with the minimum ambition threshold of the relevant SDA pathway. |
| ● If no SDA pathway is relevant, targets must drive ambitious physical intensity reduction to lead to at least a 7% physical intensity reduction in annual compounded terms. |

|  |  |  |  | For For |  | Minimum value for | economic | intensity | target = |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  | 100% - (93%) (Target | year – base | year) |  |
|  |  |  |  |  |  | physical intensity-based |  | percentage | emission |
|  |  |  |  |  | reduction | targets, criterion | met if: |  |  |
|  |  |  |  |  | ● | If an SDA pathway | is available, | the | timeframe |
|  |  |  |  |  |  | ambition is aligned | with the | minimum | ambition |
|  |  |  |  |  |  | threshold of the | relevant SDA | pathway. | OR |
|  |  |  |  |  | ● | For base years | after 2020, | the | physical |
|  |  |  |  |  |  | intensity emissions | reduction |  | meets the |
|  |  |  |  |  |  | minimum reduction | value as | set out | below over |
|  |  |  |  |  |  | the target period: |  |  |  |
|  |  |  |  |  |  | Minimum value for | physical | intensity | target = |
|  |  |  |  |  |  | 100% - (93%) (Target | year - 2020) |  |  |
|  |  |  |  |  | ● | For base years | between | 2015 | and 2020 |
|  |  |  |  |  |  | (inclusive), the | physical | intensity | emissions |
|  |  |  |  |  |  | reduction meets the | minimum | reduction | value |
|  |  |  |  |  |  | over the target period | as set | out below: |  |
|  |  |  |  |  |  | Minimum value for | physical | intensity | target = |
|  |  |  |  |  |  | 100% - (93%) (Target | year – base | year) |  |
|  |  |  |  |  |  | absolute based | percentage | emission | reduction |
|  |  |  |  |  | targets, | criterion not met | if: |  |  |
|  |  |  |  |  | ● | For base years | after 2020, | the | absolute |
|  |  |  |  |  |  | emissions reduction | does | not | meet the |
|  |  |  |  |  |  | minimum reduction | value over | the | target period |
|  |  |  |  |  |  | as set out below: |  |  |  |
|  |  |  |  |  |  | Minimum value for | absolute | contraction | target |
|  |  |  |  |  |  | = 2.5% x (Target | year - 2020) |  |  |
|  |  |  |  |  | ● | For base years | between | 2015 | and 2020 |
|  |  |  |  |  |  | (inclusive), the | absolute | emissions | reduction |
```

### PDF p. 26: rejected draft after

```markdown
| intensity: If target is based on reduction of physical |
| --- |
| ● The physical intensity denominator must be representative of the company's emissions in the target boundary. |
| ● The physical intensity denominator corresponds to a measurable product, output or level or service, it cannot be a unit of monetary or economic value. Companies are required to provide a clear definition of the physical intensity unit applied in this type of target. |
| ● If an SDA pathway is available, the timeframe ambition must be aligned with the minimum ambition threshold of the relevant SDA pathway. |
| ● If no SDA pathway is relevant, targets must drive ambitious physical intensity reduction to lead to at least a 7% physical intensity reduction in annual compounded terms. |

Minimum value for economic intensity target = 100% - (93%) <sup>(Target year – base year)</sup> **For physical intensity-based percentage emission** **reduction targets, criterion met if:**

- If an SDA pathway is available, the timeframe ambition is aligned with the minimum ambition threshold of the relevant SDA pathway. ***OR***
- For base years after 2020, the physical intensity emissions reduction meets the minimum reduction value as set out below over the target period: Minimum value for physical intensity target = 100% - (93%) <sup>(Target year - 2020)</sup>
- For base years between 2015 and 2020 (inclusive), the physical intensity emissions reduction meets the minimum reduction value over the target period as set out below: Minimum value for physical intensity target = 100% - (93%) <sup>(Target year – base year)</sup> **For absolute based percentage emission reduction** **targets, criterion not met if:**
  - For base years after 2020, the absolute emissions reduction does not meet the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target = 2.5% x (Target year - 2020)
  - For base years between 2015 and 2020 (inclusive), the absolute emissions reduction
```

### PDF p. 27: before

```markdown
| does not meet the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target = 2.5% x (Target year - base year) For economic intensity-based percentage emission reduction targets, criterion not met if: |
| --- |
| ● GEVA is not used as the chosen economic intensity metric, or an acceptable formula has not been used to calculate GEVA. AND |
| ● For base years after 2020, the economic intensity emissions reduction does not meet the minimum reduction value as set out below over the target period: Minimum value for economic intensity target = |
| ● For base years between 2015 and 2020 (inclusive), the economic intensity emissions |
| reduction does not meet the minimum reduction value over the target period as set out below: Minimum value for economic intensity target = For physical intensity-based percentage emission reduction targets, criterion not met if: |
| ● If an SDA pathway is available, the timeframe ambition is not aligned with the minimum |
| ambition threshold of the relevant SDA pathway. OR |
```

### PDF p. 27: rejected draft after

```markdown
<!-- figure: p. 27; caption: none found -->

does not meet the minimum reduction value over the target period as set out below: Minimum value for absolute contraction target = 2.5% x (Target year - base year) **For economic intensity-based percentage emission** **reduction targets, criterion not met if:**

- GEVA is not used as the chosen economic intensity metric, or an acceptable formula has not been used to calculate GEVA. ***AND***
- For base years after 2020, the economic intensity emissions reduction does not meet the minimum reduction value as set out below over the target period: Minimum value for economic intensity target = 100% - (93%) <sup>(Target year - 2020)</sup>
- For base years between 2015 and 2020 (inclusive), the economic intensity emissions reduction does not meet the minimum reduction value over the target period as set out below: Minimum value for economic intensity target = 100% - (93%) <sup>(Target year – base year)</sup> **For physical intensity-based percentage emission** **reduction targets, criterion not met if:**
  - If an SDA pathway is available, the timeframe ambition is not aligned with the minimum ambition threshold of the relevant SDA pathway. ***OR***
```

### PDF p. 32: before

```markdown
**C22 - Sale, transmission, distribution of oil,** **natural gas, coal as well as other fossil fuels** *Companies that sell, transmit, or distribute natural* *gas – or other fossil fuel products – shall set emission* *reduction scope 3 targets for the “use of sold* *products” category, that are at a minimum consistent* *with the level of decarbonization required to keep* *global temperature increase to 1.5°C compared to* *pre-industrial temperatures, irrespective of the share* *of these emissions compared to the total scope 1, 2,* *and 3 emissions of the company, company's sector* *classification, or whether fossil fuel sale/distribution is* *the* *company's* *primary* *business.* *Customer* *engagement targets are not eligible for this criterion.*

This criterion is only relevant for companies that are involved in the sale, transmission, distribution of oil, natural gas, coal as well as other fossil fuels. Companies that derive 50% or more of revenue from fossil fuels cannot have their targets validated at this time and must follow the Oil and Gas sector methodology once published.

- Companies must disclose if this criterion is relevant and, if so, must submit a scope 3 target that covers 100% of downstream use of fossil fuels.
- Fossil fuels distributed or transmitted must be accounted for in GHG inventory and target boundary, even if they are not sold directly by the company.
- The timeframe ambition must be, at a minimum, aligned with the 1.5°C ambition threshold.

| Criterion met if: |
| --- |
| ● At least one target covering the direct use phase emissions of fossil fuels sold, transmitted, or distributed is set. AND |
| ● Timeframe ambition in absolute terms is aligned with a 1.5°C pathway. Criterion not met if: |
| ● No target has been set that covers the direct use phase emissions of fossil fuels sold, transmitted, or distributed. OR |
| ● Timeframe ambition in absolute terms is not aligned with a 1.5°C pathway. |

**C23 - Companies in the fossil fuel production** **business or with significant revenue from fossil** **fuel business lines** *The SBTi will not currently validate targets for:* *Companies with any level of direct involvement in* *exploration, extraction, mining and/or production of* *oil, natural gas, coal or other fossil fuels, irrespective* *of percentage revenue generated by these activities.* *Companies that derive 50% or more of their revenue* *from the sale, transmission and distribution of fossil* *fuels, or by providing equipment or services to fossil* *fuel companies.*

● Companies with any level of direct involvement in exploration, extraction, mining and/or production of oil, natural gas, coal or other fossil fuels, irrespective of percentage revenue generated by these activities, i.e., including, but not limited to, integrated oil and gas companies, integrated gas companies, exploration and production pure players, refining and marketing pure players, oil products distributors, gas distributors and retailers and traditional oil and gas service companies cannot get their targets validated at this stage.

**Criterion met if:**

  - Company is not involved in exploration, extraction, mining and/or production of oil, natural gas, coal, as well as other fossil fuels i.e., no revenue is generated from these activities. ***OR***
  - Company does not derive 50% or more of their revenue from the sale, transmission and distribution of fossil fuels, or providing equipment or services to fossil fuel companies. ***OR***
```

### PDF p. 32: rejected draft after

```markdown
**C22 - Sale, transmission, distribution of oil,** **natural gas, coal as well as other fossil fuels** *Companies that sell, transmit, or distribute natural* *gas – or other fossil fuel products – shall set emission* *reduction scope 3 targets for the “use of sold* *products” category, that are at a minimum consistent* *with the level of decarbonization required to keep* *global temperature increase to 1.5°C compared to* *pre-industrial temperatures, irrespective of the share* *of these emissions compared to the total scope 1, 2,* *and 3 emissions of the company, company's sector* *classification, or whether fossil fuel sale/distribution is* *the* *company's* *primary* *business.* *Customer* *engagement targets are not eligible for this criterion.*

This criterion is only relevant for companies that are involved in the sale, transmission, distribution of oil, natural gas, coal as well as other fossil fuels. Companies that derive 50% or more of revenue from fossil fuels cannot have their targets validated at this time and must follow the Oil and Gas sector methodology once published.

- Companies must disclose if this criterion is relevant and, if so, must submit a scope 3 target that covers 100% of downstream use of fossil fuels.
- Fossil fuels distributed or transmitted must be accounted for in GHG inventory and target boundary, even if they are not sold directly by the company.
- The timeframe ambition must be, at a minimum, aligned with the 1.5°C ambition threshold.

**Criterion met if:**

  - At least one target covering the direct use phase emissions of fossil fuels sold, transmitted, or distributed is set. ***AND***
  - Timeframe ambition in absolute terms is aligned with a 1.5°C pathway. **Criterion not met if:**
    - No target has been set that covers the direct use phase emissions of fossil fuels sold, transmitted, or distributed. ***OR***
    - Timeframe ambition in absolute terms is not aligned with a 1.5°C pathway.

**C23 - Companies in the fossil fuel production** **business or with significant revenue from fossil** **fuel business lines** *The SBTi will not currently validate targets for:* *Companies with any level of direct involvement in* *exploration, extraction, mining and/or production of* *oil, natural gas, coal or other fossil fuels, irrespective* *of percentage revenue generated by these activities.* *Companies that derive 50% or more of their revenue* *from the sale, transmission and distribution of fossil* *fuels, or by providing equipment or services to fossil* *fuel companies.*

● Companies with any level of direct involvement in exploration, extraction, mining and/or production of oil, natural gas, coal or other fossil fuels, irrespective of percentage revenue generated by these activities, i.e., including, but not limited to, integrated oil and gas companies, integrated gas companies, exploration and production pure players, refining and marketing pure players, oil products distributors, gas distributors and retailers and traditional oil and gas service companies cannot get their targets validated at this stage.

**Criterion met if:**

    - Company is not involved in exploration, extraction, mining and/or production of oil, natural gas, coal, as well as other fossil fuels i.e., no revenue is generated from these activities. ***OR***
    - Company does not derive 50% or more of their revenue from the sale, transmission and distribution of fossil fuels, or providing equipment or services to fossil fuel companies. ***OR***
```

### PDF p. 35: before

```markdown
such as CDP’s annual questionnaire, though annual reports, sustainability reports and the company’s website are acceptable. ● For more substantive reporting guidance on how the SBTi recommends companies should publicly report on their GHG emissions inventory and annual progress against their published science-based targets, please visit the Corporate Manual.

| Criterion not met if: |
| --- |
| ● The company does not commit to publicly |
| reporting its GHG inventory and target progress on an annual basis. OR |
| ● It is not stated where this information will be disclosed. |

**C26 - Mandatory target recalculation** *To ensure consistency with the most recent climate* *science and best practices, targets must be* *reviewed, and if necessary, recalculated and* *revalidated, at a minimum every 5 years. For* *companies with targets approved in 2020 or earlier,* *targets must be reviewed and revalidated by 2025, if* *necessary. Companies with an approved target that* *requires recalculation must follow the most recent* *applicable criteria at the time of resubmission. A* *company’s base year emissions recalculation policy* *must include a significance threshold of 5% or less* *that is applied to emission recalculations or in the* *absence of a base year emissions recalculation* *policy, a company must agree to apply a 5%* *significance threshold for emission recalculations.*

- Companies must state whether they will review, and if necessary, recalculate and revalidate their targets, at a minimum, every 5 years.
- SBTi’s significance threshold is defined as a cumulative change of five percent or larger in an organization’s total base year emissions (tCO2e).
- All companies must adhere to the SBTi’s 5% significance threshold.
- For more information on base year recalculation policies, please visit page 35 of the GHG Protocol Corporate Standard.
- A company’s base year emissions recalculation policy must include a significance threshold of 5% or less that is applied to emission recalculations.
- In the absence of a base year emissions recalculation policy, a company must agree to apply a 5% significance threshold for emission recalculations.

**Criterion met if:**

  - The company commits to review, and if necessary, recalculate and revalidate their targets at a minimum every 5 years. ***AND***
  - The company commits that they will follow the most recent criteria if re-submitting targets. ***AND***
  - The company agrees to adhere to the SBTi’s 5% significance threshold for base year emissions recalculation. ***OR***
  - The company’s base year emissions recalculation policy has a significance threshold of 5% or less. **Criterion not met if:**
    - The company does not commit to review, and if necessary, recalculate and revalidate their targets at a minimum every 5 years. ***OR***
    - The company does not commit that they will follow the most recent criteria if re-submitting targets. ***OR***
```

### PDF p. 35: rejected draft after

```markdown
such as CDP’s annual questionnaire, though annual reports, sustainability reports and the company’s website are acceptable. ● For more substantive reporting guidance on how the SBTi recommends companies should publicly report on their GHG emissions inventory and annual progress against their published science-based targets, please visit the Corporate Manual.

**Criterion not met if:**

- The company does not commit to publicly reporting its GHG inventory and target progress on an annual basis. ***OR***
- It is not stated where this information will be disclosed.

**C26 - Mandatory target recalculation** *To ensure consistency with the most recent climate* *science and best practices, targets must be* *reviewed, and if necessary, recalculated and* *revalidated, at a minimum every 5 years. For* *companies with targets approved in 2020 or earlier,* *targets must be reviewed and revalidated by 2025, if* *necessary. Companies with an approved target that* *requires recalculation must follow the most recent* *applicable criteria at the time of resubmission. A* *company’s base year emissions recalculation policy* *must include a significance threshold of 5% or less* *that is applied to emission recalculations or in the* *absence of a base year emissions recalculation* *policy, a company must agree to apply a 5%* *significance threshold for emission recalculations.*

- Companies must state whether they will review, and if necessary, recalculate and revalidate their targets, at a minimum, every 5 years.
- SBTi’s significance threshold is defined as a cumulative change of five percent or larger in an organization’s total base year emissions (tCO2e).
- All companies must adhere to the SBTi’s 5% significance threshold.
- For more information on base year recalculation policies, please visit page 35 of the GHG Protocol Corporate Standard.
- A company’s base year emissions recalculation policy must include a significance threshold of 5% or less that is applied to emission recalculations.
- In the absence of a base year emissions recalculation policy, a company must agree to apply a 5% significance threshold for emission recalculations.

**Criterion met if:**

  - The company commits to review, and if necessary, recalculate and revalidate their targets at a minimum every 5 years. ***AND***
  - The company commits that they will follow the most recent criteria if re-submitting targets. ***AND***
  - The company agrees to adhere to the SBTi’s 5% significance threshold for base year emissions recalculation. ***OR***
  - The company’s base year emissions recalculation policy has a significance threshold of 5% or less. **Criterion not met if:**
    - The company does not commit to review, and if necessary, recalculate and revalidate their targets at a minimum every 5 years. ***OR***
    - The company does not commit that they will follow the most recent criteria if re-submitting targets. ***OR***
```

### PDF p. 45: before

```markdown
| NZA | = | Percentage reduction (%) required for reaching the sector’s emissions intensity in 2050 from the chosen target base year (depends on sector and base year intensity). |
| --- | --- | --- |
| A0 | = | Minimum target ambition (%) based on the sector-specific intensity method before FLA adjustment. |

| Option 2. The emissions | intensity reduction between the | most | recent year and target year |
| --- | --- | --- | --- |
| consistent with intensity | convergence between the most | recent | year and 2050. |
| In other words, the target | needs to be consistent with the | ambition | required from the sector-specific |
| intensity method using most | recent year data. In some cases, | this will | require a larger reduction than |
| calculated by the sector-specific | intensity convergence using base | year |  |
```

### PDF p. 45: rejected draft after

```markdown
| NZA | = | Percentage reduction (%) required for reaching the sector’s emissions intensity in 2050 from the chosen target base year (depends on sector and base year intensity). |
| --- | --- | --- |
| A0 | = | Minimum target ambition (%) based on the sector-specific intensity method before FLA adjustment. |

**Option 2. The emissions intensity reduction between the most recent year and target year is** **consistent with intensity convergence between the most recent year and 2050.** In other words, the target needs to be consistent with the ambition required from the sector-specific intensity method using most recent year data. In some cases, this will require a larger reduction than calculated by the sector-specific intensity convergence using base year data.
```

## Local audit artifacts

- [Rejected implementation and fixture-generator patch](/tmp/batchC-draft/rejected-item5.patch)
- [Baseline and region-39-only diagnostic audit](/tmp/batchC-region39/audit.json)
- [Rejected guard audit](/tmp/batchC-region39/guard-audit.json)
- [Rendered PDF p. 45](/tmp/batchC-region39/page45.png)

These temporary artifacts contain diagnostics and rendered crops, not copies of pipeline PDFs. They are local review aids and are not committed. The working converter has been restored to the baseline.

## Retry: spanned-source-line distribution (2026-09-29)

**Stopped before implementation: no clear separation.** This retry measures the requested geometry-only signal on the unchanged `9662c99` converter. All 55 baseline decisions are retained. The run still produces 55 regions, 30 fallbacks, and 18,345 standard content words. No candidate was rejected and no threshold was fitted.

### Measurement definition

- Denominator: every nonblank original extracted `Line` in the candidate's actual member blocks at the emission decision, after caption isolation and earlier candidates' consumption. Blank lines are excluded; lines remain distinct, without combining neighboring cells' source lines.
- Geometry: the PyMuPDF candidate's `tbl.rows[].cells`, which also supplies the geometric fallback. This measures candidate column cuts, not columns inferred by parsing reconstruction HTML. Reconstruction HTML has no source-coordinate cuts.
- Numerator: source lines whose nonwhitespace glyph centers occupy both sides of a shared vertical edge between adjacent cells at the source line's vertical midpoint. Cell edges must coincide within 0.01 PDF points. Occupancy on each side must be strictly beyond the shared edge, so a character centered on the edge alone does not count.
- Continuity: both fragments belong to the same original printed source line; the line is read left to right. We do not concatenate separate lines from different cells to manufacture a spanning line. The examples below were also checked against the rendered PDF.
- Share: numerator / denominator. Each line counts once even if it crosses many cuts. No content, column-count, or border-only rejection is used.

The natural “most lines” reference is named `TABLE_SPANNED_LINE_SHARE_MIN = 0.5`, with a strict `share > TABLE_SPANNED_LINE_SHARE_MIN` comparison. This is a diagnostic reference only; **no production constant or rejection rule was added** because the distribution fails the prerequisite. Raising that constant into the narrow interval above 27/28 would tune it to this corpus, which the user prohibited.

### Full distribution

| Original region | PDF page | Existing decision | Spanned / source lines | Spanned-line share | Above majority |
| ---: | ---: | --- | ---: | ---: | --- |
| 1 | 2 | reconstruction | 1 / 51 | 1.9608% | no |
| 2 | 3 | fallback | 0 / 34 | 0.0000% | no |
| 3 | 10 | reconstruction | 3 / 12 | 25.0000% | no |
| 4 | 11 | fallback | 3 / 35 | 8.5714% | no |
| 5 | 11 | fallback | 28 / 38 | 73.6842% | yes |
| 6 | 12 | fallback | 34 / 59 | 57.6271% | yes |
| 7 | 13 | fallback | 2 / 12 | 16.6667% | no |
| 8 | 14 | reconstruction | 2 / 11 | 18.1818% | no |
| 9 | 15 | reconstruction | 2 / 26 | 7.6923% | no |
| 10 | 16 | reconstruction | 0 / 14 | 0.0000% | no |
| 11 | 16 | reconstruction | 1 / 11 | 9.0909% | no |
| 12 | 16 | fallback | 41 / 49 | 83.6735% | yes |
| 13 | 17 | fallback | 0 / 54 | 0.0000% | no |
| 14 | 17 | fallback | 33 / 42 | 78.5714% | yes |
| 15 | 19 | reconstruction | 1 / 9 | 11.1111% | no |
| 16 | 20 | fallback | 0 / 28 | 0.0000% | no |
| 17 | 20 | reconstruction | 29 / 35 | 82.8571% | yes |
| 18 | 22 | fallback | 1 / 46 | 2.1739% | no |
| 19 | 24 | reconstruction | 3 / 46 | 6.5217% | no |
| 20 | 25 | reconstruction | 1 / 29 | 3.4483% | no |
| 21 | 25 | fallback | 36 / 44 | 81.8182% | yes |
| 22 | 26 | reconstruction | 2 / 23 | 8.6957% | no |
| 23 | 26 | fallback | 27 / 29 | 93.1034% | yes |
| 24 | 27 | reconstruction | 27 / 28 | 96.4286% | yes |
| 25 | 29 | fallback | 0 / 14 | 0.0000% | no |
| 26 | 29 | fallback | 35 / 39 | 89.7436% | yes |
| 27 | 30 | reconstruction | 0 / 33 | 0.0000% | no |
| 28 | 31 | reconstruction | 0 / 67 | 0.0000% | no |
| 29 | 32 | reconstruction | 2 / 12 | 16.6667% | no |
| 30 | 34 | fallback | 45 / 53 | 84.9057% | yes |
| 31 | 35 | reconstruction | 0 / 6 | 0.0000% | no |
| 32 | 36 | reconstruction | 0 / 25 | 0.0000% | no |
| 33 | 36 | fallback | 38 / 63 | 60.3175% | yes |
| 34 | 40 | reconstruction | 0 / 27 | 0.0000% | no |
| 35 | 42 | reconstruction | 0 / 11 | 0.0000% | no |
| 36 | 43 | fallback | 26 / 41 | 63.4146% | yes |
| 37 | 44 | fallback | 1 / 3 | 33.3333% | no |
| 38 | 45 | fallback | 2 / 5 | 40.0000% | no |
| 39 | 45 | fallback | 5 / 5 | 100.0000% | yes |
| 40 | 46 | fallback | 0 / 23 | 0.0000% | no |
| 41 | 47 | fallback | 28 / 32 | 87.5000% | yes |
| 42 | 48 | fallback | 18 / 23 | 78.2609% | yes |
| 43 | 49 | fallback | 0 / 33 | 0.0000% | no |
| 44 | 53 | fallback | 0 / 63 | 0.0000% | no |
| 45 | 54 | reconstruction | 67 / 77 | 87.0130% | yes |
| 46 | 55 | fallback | 56 / 78 | 71.7949% | yes |
| 47 | 56 | reconstruction | 34 / 36 | 94.4444% | yes |
| 48 | 57 | reconstruction | 42 / 49 | 85.7143% | yes |
| 49 | 58 | reconstruction | 0 / 52 | 0.0000% | no |
| 50 | 60 | fallback | 0 / 23 | 0.0000% | no |
| 51 | 60 | reconstruction | 0 / 31 | 0.0000% | no |
| 52 | 61 | fallback | 0 / 24 | 0.0000% | no |
| 53 | 61 | reconstruction | 0 / 10 | 0.0000% | no |
| 54 | 62 | fallback | 44 / 51 | 86.2745% | yes |
| 55 | 63 | fallback | 0 / 24 | 0.0000% | no |

### Why this does not pass the gate

Region 39 is 5/5 (100%). The largest protected share is region 24 on PDF p. 27: 27/28 (96.4286%), just **3.5714 percentage points** lower. Region 47 on p. 56 is 34/36 (94.4444%); region 23 on p. 26 is 27/29 (93.1034%). The desired rejection rests on only five source lines: one line's classification changes its share by 20 percentage points, much larger than the observed margin.

A strict majority flags 20 candidates: region 39 and **19 protected regions** (5, 6, 12, 14, 17, 21, 23, 24, 26, 30, 33, 36, 41, 42, 45, 46, 47, 48, 54). These are measured flags, not actual changed decisions. Region 38 is 2/5 (40%) and would stay below that reference, but preserving region 38 does not solve the other collisions.

The geometry detects an invented grid cutting text, but that invented grid can also cut paragraphs inside a real parent table. Source-line spanning alone therefore does not establish that the candidate should become standalone prose. Region 24 currently reconstructs; region 47 currently falls back, so the collision includes a protected candidate using the same output path as region 39.

### Rendered checks

**Region 24, PDF p. 27, 27/28.** The rendered source shows a bounded criteria cell with lead-ins, bullets, and formulas. The first printed line, “does not meet the minimum reduction value”, crosses candidate cuts at x=633.1142, 687.3589, and 743.5026. Those cuts divide a continuous line within the criteria cell; they are not printed parent-cell boundaries.

![Region 24 rendered source](/tmp/batchC-span/region-24.png)

**Region 47, PDF p. 56, 34/36.** The rendered source shows a two-column parent table containing paragraphs. Its first source line, “The SBTi is developing a new”, spans the candidate cut at x=283.6703 inside the printed left cell. A high spanned-line share also occurs in a protected fallback region.

![Region 47 rendered source](/tmp/batchC-span/region-47.png)

**Region 42, PDF p. 48, 18/23.** The rendered page confirms the two-column parent table: labels on the left and narrative cells on the right. The “Green gas/biogas” label does not span a cut. The right-cell line beginning “The SBTi currently recommends that companies follow the guidance within the GHG” spans seven candidate cuts (x=456.3541, 521.4846, 543.3387, 579.4566, 636.1777, 690.8062, 726.4491). It is one continuous printed line inside its parent cell. A majority guard would reject this protected parent-table candidate. The unchanged converter still emits it as a fallback table; this retry does not implement or claim an improved rendering.

![Region 42 rendered source, PDF p. 48](/tmp/batchC-span/region-42.png)

**Region 39, PDF p. 45, 5/5.** All five printed lines span the three candidate cuts at x=196.5010, 365.8888, and 399.6357. The rendered page confirms the standalone explanation rather than a table. It shares the high-spanning geometry with the protected narrative cells above.

![Region 39 rendered source](/tmp/batchC-span/region-39.png)

### Retry status and reproducibility

The earlier report and experiment history are preserved above. Only this report was extended. The converter, vendored reconstruction, PLAN, CLAUDE, and AGENTS were not edited. No fixture was added, no commit/push/tag was made, and item 6 was not started. Kostova Figure 1 and new synthetic-fixture verification were not run because this prerequisite failed. No new claim about their behavior is made. paper.pdf and hard.pdf were not rerun in this diagnostic-only retry; their prior measurements remain recorded above.

- [Read-only measurement script](/tmp/batchC-span-audit.py)
- [All line-level measurements and unchanged-run statistics](/tmp/batchC-span/audit.json)
- [Unchanged-run SBTi Markdown](/tmp/batchC-span/Target-Validation-Protocol.md)

Rerun from the repository root with `/home/galbl/.markerlite-venv/bin/python /tmp/batchC-span-audit.py`. The script observes `detect_tables` at its emission counter via tracing and writes only under `/tmp/batchC-span/`. It does not patch detection or copy any input PDF.

## Replacement proposal: classify all 30 fallback regions (2026-09-29)

**Step 1 stops here: five usable grids exceed the permitted maximum of three.** No fallback-to-prose implementation was started. There are **5 usable grids and 25 shredded grids under the requested strict line-containment and row/column criteria**. Two of the latter are readable key/value layouts, identified explicitly below; counting those as usable would raise the usable total to seven and would not change the stop decision.

Usable regions: **2 (PDF p. 3), 43 (p. 49), 44 (p. 53), 52 (p. 61), and 55 (p. 63)**.

### Review method and limits

This is a visual and cell-by-cell review of the current fallback outputs, not classification by word count or by the earlier spanned-line share alone. All 30 regions were rendered afresh from the local original SBTi PDF and inspected against the parsed emitted cell matrices captured from the unchanged converter at `9662c99`. Earlier region IDs and bounding boxes were used to match the matrices. No pipeline PDF was copied or used in this SBTi-only step.

A usable grid must preserve printed cell membership and row/column relationships. A grid is marked shredded if it invents column fragments, turns continuation lines into records, misaligns headers with data, or consumes surrounding prose. Thus zero spanned-line share is insufficient: regions 13, 16, 25, 40, and 50 fail on row boundaries or column alignment. Conversely, the five usable cases retain narrative paragraphs in the correct cells and rows.

This classification does not certify perfect typography, bullet formatting, or token conservation. For example, the existing Markdown table renderer treats its first row as a header even on continuation pages; that presentation convention does not move text between cells. Region 44 ends with a printed continuation in the Buildings guidance cell, which correctly remains unfinished until the following page. No new word-count claims or conversion changes arise from this review.

### Complete classification

| Region | PDF page | Output rows × columns | Classification | Rendered-page and emitted-cell evidence |
| ---: | ---: | --- | --- | --- |
| 2 | 3 | 2 × 4 | **Usable grid** | Four printed columns remain four output columns: version 3.1, its change description, issue date, and effective date stay paired in one row. The opening continuation row is preserved. [Source crop](/tmp/batchC-fallback-review/region-02.png) |
| 4 | 11 | 28 × 5 | Shredded | One narrative criteria cell becomes 28 rows and five columns. Successive printed lines become separate records; the first bullet is split between output rows 1 and 2. [Source crop](/tmp/batchC-fallback-review/region-04.png) |
| 5 | 11 | 30 × 10 | Shredded | Two narrative columns become ten output columns and 30 rows. The first left-cell line is split into “Total exclusions for the” / “scope 1” / an accumulated last-column fragment. [Source crop](/tmp/batchC-fallback-review/region-05.png) |
| 6 | 12 | 30 × 9 | Shredded | The printed criteria columns become nine output columns and 30 rows. “additional 2% of scope 3 emissions on aggregate” is split among cells and mixed with later lines. [Source crop](/tmp/batchC-fallback-review/region-06.png) |
| 7 | 13 | 8 × 6 | Shredded | One criteria cell becomes six columns and eight rows; the lead-in, bullet, and wrapped continuation become separate records. [Source crop](/tmp/batchC-fallback-review/region-07.png) |
| 12 | 16 | 30 × 13 | Shredded | The three-column criteria table becomes 13 columns and 30 rows. “Estimates using tools such as the Scope 3” is fragmented across columns, with later line endings accumulated in a cell. [Source crop](/tmp/batchC-fallback-review/region-12.png) |
| 13 | 17 | 30 × 9 | Shredded | Zero column-spanning lines does not rescue the output: one narrative cell becomes nine columns and 30 rows. “and removals of CO2 associated with” and “bioenergy.” occupy separate records, while subsequent bullet lines drift to another output column. [Source crop](/tmp/batchC-fallback-review/region-13.png) |
| 14 | 17 | 30 × 11 | Shredded | The printed three-column parent becomes 11 columns and 30 rows. “Land-related emissions accounting shall include CO2” is split across four nonempty cells. [Source crop](/tmp/batchC-fallback-review/region-14.png) |
| 16 | 20 | 28 × 11 | Shredded | A single narrative cell becomes 11 columns and 28 rows. The first bullet starts in column 2; its next two lines move to column 3 and separate rows. [Source crop](/tmp/batchC-fallback-review/region-16.png) |
| 18 | 22 | 26 × 14 | Shredded | The three-column parent becomes 14 columns and 26 rows. The middle-cell paragraph is emitted a line per row while the entire right-cell narrative accumulates in one cell; rows no longer correspond to the printed table. [Source crop](/tmp/batchC-fallback-review/region-18.png) |
| 21 | 25 | 29 × 14 | Shredded | The printed three-column table becomes 14 columns and 29 rows. The criterion title is fragmented and later paragraphs are accumulated across arbitrary column cuts. [Source crop](/tmp/batchC-fallback-review/region-21.png) |
| 23 | 26 | 29 × 10 | Shredded | Two printed columns become ten output columns and 29 rows. Formula text is split across columns, and the “For” lead-ins accumulate separately from their phrases. [Source crop](/tmp/batchC-fallback-review/region-23.png) |
| 25 | 29 | 9 × 5 | Shredded | A single criteria cell becomes five columns and nine rows. The first bullet is split into successive rows, and its continuation changes column. [Source crop](/tmp/batchC-fallback-review/region-25.png) |
| 26 | 29 | 30 × 8 | Shredded | Three printed columns become eight output columns and 30 rows. Paragraph beginnings appear in one column while line endings from the entire paragraph accumulate in a neighboring cell. [Source crop](/tmp/batchC-fallback-review/region-26.png) |
| 30 | 34 | 26 × 11 | Shredded | The three-column criteria table and full-width section labels become 11 columns and 26 rows. Printed lines in narrative cells are split across invented columns. [Source crop](/tmp/batchC-fallback-review/region-30.png) |
| 33 | 36 | 23 × 15 | Shredded | Three printed columns become 15 output columns and 23 rows. A line such as “recalculation policy has a significance” is divided into four cells. [Source crop](/tmp/batchC-fallback-review/region-33.png) |
| 36 | 43 | 22 × 9 | Shredded | The candidate includes a real seven-column numerical table and the explanatory prose below it. Output has nine columns and 22 rows, splits the “Metric measured” header and row label, and consumes section headings and paragraphs into the grid. [Source crop](/tmp/batchC-fallback-review/region-36.png) |
| 37 | 44 | 2 × 3 | Shredded (strict; readable key/value) | Strict line-containment failure, although readable as key/value: the printed RTD = definition line occupies three output cells. The definition itself stays intact and in order. This is not sentence-fragment word salad; see the explicit borderline note below. [Source crop](/tmp/batchC-fallback-review/region-37.png) |
| 38 | 45 | 2 × 3 | Shredded (strict; readable key/value) | Strict line-containment failure, although readable as key/value: each NZA/A0 = definition line occupies three output cells. Both definitions stay intact and in order. See the explicit borderline note below. [Source crop](/tmp/batchC-fallback-review/region-38.png) |
| 39 | 45 | 5 × 4 | Shredded | Standalone Option 2 prose becomes a four-column, five-row table. Every source line spans cuts, and “is” plus the final “data.” are absent from the emitted grid. [Source crop](/tmp/batchC-fallback-review/region-39.png) |
| 40 | 46 | 4 × 6 | Shredded | The printed Topic/Guidance table becomes six output columns and four rows. Topic/Guidance headers occupy columns 2/5, but the first data row occupies columns 1/4; the final topic label is split into an extra row. [Source crop](/tmp/batchC-fallback-review/region-40.png) |
| 41 | 47 | 6 × 8 | Shredded | The two-column Topic/Guidance continuation becomes eight columns. Each guidance paragraph is broken into vertical fragments that do not read in sentence order across the row. [Source crop](/tmp/batchC-fallback-review/region-41.png) |
| 42 | 48 | 5 × 9 | Shredded | The two-column parent on p. 48 becomes nine columns. The green-gas guidance sentence is broken among eight right-side fragments; the RECs guidance also spills into an extra row. [Source crop](/tmp/batchC-fallback-review/region-42.png) |
| 43 | 49 | 3 × 2 | **Usable grid** | The two printed columns and three row bands remain intact. The continuation at the top has an empty left cell; the mandatory/optional and direct/indirect topics each keep their full guidance in the matching right cell. [Source crop](/tmp/batchC-fallback-review/region-43.png) |
| 44 | 53 | 5 × 3 | **Usable grid** | The printed Sector / Eligible methods / Guidance and further notes columns remain intact. Aluminium, Apparel and footwear, Aviation, and Buildings each retain their two matching narrative cells; the long aviation text stays in its own row. [Source crop](/tmp/batchC-fallback-review/region-44.png) |
| 46 | 55 | 7 × 8 | Shredded | The printed sector table has three columns but output has eight. Narrative cells are fragmented horizontally and the ICT/maritime records also acquire extra rows. [Source crop](/tmp/batchC-fallback-review/region-46.png) |
| 50 | 60 | 3 × 9 | Shredded | The three-column ambition table becomes nine columns. Header text occupies columns 2/5/8 and two rows, while the corresponding data occupy columns 1/4/7; the header-to-data alignment is wrong despite zero line-spanning share. [Source crop](/tmp/batchC-fallback-review/region-50.png) |
| 52 | 61 | 4 × 2 | **Usable grid** | All four printed topic/guidance rows remain paired in two columns: single-scope plus renewable electricity, multiple near-term targets, combined scopes, and scope 3 targets. Wrapped guidance stays within its matching cell. [Source crop](/tmp/batchC-fallback-review/region-52.png) |
| 54 | 62 | 16 × 8 | Shredded | Two printed columns become eight columns and 16 rows. Topic labels and target-language templates split across invented columns; the combined-scopes paragraph becomes many output records. [Source crop](/tmp/batchC-fallback-review/region-54.png) |
| 55 | 63 | 4 × 2 | **Usable grid** | The two-column continuation and three subsequent topic/guidance pairs retain their row boundaries: optional indirect use-phase emissions, General, and Use of bioenergy. Every wrapped paragraph stays in its matching right cell. [Source crop](/tmp/batchC-fallback-review/region-55.png) |

**Borderline key/value layouts, regions 37 and 38:** the prior line-level audit records 1/3 and 2/5 original lines crossing cuts respectively. Under the requested strict “each printed line inside one cell” criterion, they are listed as shredded. Visually, their label / equals / complete-definition columns still read sensibly; they are materially better than the fragmented paragraphs elsewhere. The five unambiguous usable grids already exceed the gate without relying on either borderline case.

### Five usable grids: rendered source and complete emitted cell matrices

Each numbered row below is the current emitted matrix, including its first row; empty strings represent genuinely empty cells. These are existing output cells, not a proposed reconstruction. The complete matrices are included so the usable judgment can be checked against every row.

#### Region 2, PDF p. 3

Four printed columns remain four output columns: version 3.1, its change description, issue date, and effective date stay paired in one row. The opening continuation row is preserved.

![Rendered source region 2](/tmp/batchC-fallback-review/region-02.png)

```json
[
  [
    "",
    "Section 4 Conflict of interest policy Section 7 Target recalculation protocol",
    "",
    ""
  ],
  [
    "3.1",
    "Minor updates to provide further clarification and context to existing criteria, recommendations and use of terminology (criterion 4, 10 and 19 and recommendation 5 and 8). Clarifications on exclusions, significance thresholds and emissions coverage for scope 1, 2 and 3 targets (criterion 5 and 6). Clarification that companies setting renewable electricity sourcing targets that will be achieved through market-based mechanisms must report and track using market-based scope 2 emissions (criterion 8). Clarification that the target year criterion is only relevant for absolute and intensity-based emission reduction near-term targets (criterion 13). Revision of allowable years for assessing progress to date for submissions in 2023 (criterion 14). Clarification in language that scope 3 physical intensity targets (criterion 18) only needs to meet the 7% compounded emissions intensity reduction (and can lead to absolute emissions increase). Alignment of criterion 22 and 23 to the revised version of SBTi’s policy on fossil fuel companies. Further guidance for mandatory target recalculations (criterion 26). Revision of previous recommendation to criterion for triggered recalculations (criterion 27). Inclusion of most up to date information on sector developments and sector-specific criteria.",
    "March 29, 2023",
    "From March 29, 2023"
  ]
]
```

#### Region 43, PDF p. 49

The two printed columns and three row bands remain intact. The continuation at the top has an empty left cell; the mandatory/optional and direct/indirect topics each keep their full guidance in the matching right cell.

![Rendered source region 43](/tmp/batchC-fallback-review/region-43.png)

```json
[
  [
    "",
    "market-based accounting in scope 3, including the purchase of market-based renewable electricity instruments on behalf of the reporting company's suppliers, customers, lessors, lessees, franchisees, or investments."
  ],
  [
    "Mandatory versus optional scope 3 targets",
    "Companies may request to include targets to reduce optional scope 3 emissions in the target language. For companies that wish to include a supplemental/optional target on optional scope 3 emissions, the below needs to be followed: ● The optional scope 3 target will be assessed separately by the SBTi review team compared to the mandatory scope 3 target(s). ● The reduction plans for the target(s) covering optional scope 3 emissions is credible, ambitious and practical. ● Should the target be approved, the target language covering the optional scope 3 target should be separated in a standalone sentence from the rest of the target language. ● In the GHG inventory submitted to the SBTi, the mandatory scope 3 emissions representative of the minimum boundary shall be included in the inventory table. For a definition of optional emissions for each scope 3 category, please see Table 5.4 on page 34 and section 5.5 “Descriptions of scope 3 categories” of the Corporate Value Chain (Scope 3) Accounting and Reporting Standard."
  ],
  [
    "Direct use-phase emissions versus indirect use-phase emissions",
    "In scope 3 category 11 “use of sold products”, direct use-phase emissions are required to be reported, whereas the reporting of indirect use-phase emissions are optional. Please refer to the GHG Scope 3 Standard for a definition of direct and indirect use-phase emissions. The direct use-phase emissions of final products shall be calculated based upon the lifetime consumption of the product(s). The allocation methodology shall be disclosed for the direct use-phase of components, except for car engines wherein 100% of the direct use-phase emissions of the car/vehicle shall be reported. Furthermore, the calculation methodology shall be disclosed for indirect use-phase emissions."
  ]
]
```

#### Region 44, PDF p. 53

The printed Sector / Eligible methods / Guidance and further notes columns remain intact. Aluminium, Apparel and footwear, Aviation, and Buildings each retain their two matching narrative cells; the long aviation text stays in its own row.

![Rendered source region 44](/tmp/batchC-fallback-review/region-44.png)

```json
[
  [
    "Sector",
    "Eligible methods",
    "Guidance and further notes"
  ],
  [
    "Aluminium",
    "When setting SBTs, companies can set targets using the cross-sector pathway (absolute targets only).",
    "Guidance is being developed for the aluminium sector and is currently in the scoping phase."
  ],
  [
    "Apparel and footwear",
    "When setting SBTs, companies can set targets using the cross-sector pathway (absolute targets only).",
    "Optional guidance is available for companies in the apparel and footwear sector."
  ],
  [
    "Aviation",
    "When setting SBTs, companies providing air transport services can set targets using the physical intensity convergence method using the pathways available in the SBTi Aviation tool. The target boundary must cover well-to-wake emissions (WTW), as specified in the SBTi Aviation Guidance. Alternatively, when setting SBTs, companies can set targets using the cross-sector pathway (absolute targets).",
    "For all transport-related emissions across all sectors, companies shall report these emissions on a well-to-wheel (WTW) basis in their GHG inventory (well-to-wake for aviation). For aviation this is the sum of both scope 1 emissions from jet fuel combustion and scope 3 category 3 “fuel- and energy-related activities” emissions from upstream production and distribution of jet fuel. Aviation target formulation and communication must explicitly state that targets are exclusive of non-CO₂ factors. Targets must include a footnote stating that non-CO₂ factors which may also contribute to aviation-induced warming are not included in this target and whether the company has publicly reported or commits to publicly report its non-CO2 impacts."
  ],
  [
    "Buildings",
    "When setting SBTs, companies in these sectors are recommended to set absolute targets or intensity targets using the residential buildings pathway, service buildings pathway, or cross-sector pathway (absolute targets only).",
    "Real Estate Investment Trusts (REITs) wishing to set targets must specify if they are a mortgage-based or equity-based REIT. Equity REITs must pursue the regular target validation route for companies. Mortgage REITs must instead"
  ]
]
```

#### Region 52, PDF p. 61

All four printed topic/guidance rows remain paired in two columns: single-scope plus renewable electricity, multiple near-term targets, combined scopes, and scope 3 targets. Wrapped guidance stays within its matching cell.

![Rendered source region 52](/tmp/batchC-fallback-review/region-52.png)

```json
[
  [
    "Single scope + renewable electricity targets",
    "If a single scope 1 target and a renewable electricity target are set, the resulting classification will be based on an emissions weighted average reduction across the scopes. Renewable electricity procurement targets will be converted to absolute reductions based on the assumption that the procured renewable electricity has zero GHG emissions associated with its use. Heating, steam and cooling-related emissions not covered by renewable electricity targets will be considered separately when the aggregate scope 2 target ambition is calculated."
  ],
  [
    "Multiple near-term targets",
    "If multiple near-term scope 1 and 2 targets are submitted, the classification is based on the target with the furthest target year. E.g., if a company has two scope 1 and 2 targets with target years of 2025 and 2030, then temperature alignment is based on the 2030 target."
  ],
  [
    "Combined scope targets (scopes 1+2+3)",
    "Companies must provide the breakdown ambition for combined scope targets (scopes 1+2+3), i.e., the ambition of the scope 1+2 portion and the ambition of the scope 3 portion of the target. The classification of the company is then based only on the scope 1+2 ambition."
  ],
  [
    "Scope 3 targets",
    "Companies are welcome to set scope 3 targets that exceed minimum ambition or to update the level of ambition of scope 3 targets. However, the SBTi is currently not temperature classifying scope 3 targets."
  ]
]
```

#### Region 55, PDF p. 63

The two-column continuation and three subsequent topic/guidance pairs retain their row boundaries: optional indirect use-phase emissions, General, and Use of bioenergy. Every wrapped paragraph stays in its matching right cell.

![Rendered source region 55](/tmp/batchC-fallback-review/region-55.png)

```json
[
  [
    "",
    "For example, Company A commits to reduce absolute scope 1 and 2 GHG emissions from non-revenue activities [insert target reduction percentage] % by [insert target year] from a [insert base year]. Company A also commits to reduce scope 1 and 2 GHG emissions from revenue activities [insert target reduction percentage] % per revenue passenger kilometer traveled by [insert target year] from a [insert base year] base year."
  ],
  [
    "Optional indirect use-phase emissions",
    "In the target language, the target on either the direct or indirect-use phase emissions needs to be separated from the rest of the target language. For example, Company A commits to reduce absolute scope 3 GHG emissions from purchased goods and service [insert target reduction percentage] % by [insert target year] from a [insert base year]. Company A also commits to reduce indirect use phase emissions [insert target reduction percentage] % by [insert target year] from a [insert base year]."
  ],
  [
    "General",
    "For clarity and transparency, percentage emissions reductions shall be expressed up to two decimal points."
  ],
  [
    "Use of bioenergy",
    "If a company is using bioenergy, the following footnote is required to be included in target language: “*The target boundary includes land-related emissions and removals from bioenergy feedstocks.\""
  ]
]
```

### Evidence for the other 25 regions

The complete table above links a freshly rendered crop for every region and states the observed failure. The full baseline matrices (including every empty cell) and source-line/cut measurements are preserved together in the diagnostic JSON below, rather than presenting only word counts.

- [All 30 fallback regions: complete emitted cells and source lines](/tmp/batchC-fallback-review/regions.json)
- [Earlier baseline Markdown](/tmp/batchC-baseline/Target-Validation-Protocol.md)

### Stop status

Fallback statistics remain **30 of 55 regions**; 25 reconstructed regions are untouched. Current baseline SBTi content words remain **18,345**. No new after-state exists. Steps 2–4 were not started: there is no prose-fallback code or marker, stats wording change, new fixture, reconstructed-region boxed-prose check, or front-matter change. README, PLAN, CLAUDE and generated AGENTS are unchanged. Only this existing uncommitted report was extended. Nothing was committed, pushed, or tagged. The user decides how to handle the five usable grids before implementation resumes.

## Accepted branch and step 2: fallback source prose

The user authorized continuation after reviewing the five usable grids. This section supersedes the earlier stop statuses; their evidence remains intact above.

### Branch A/B decision from the existing measurements

Usable fallback range: **0.00–0.00**. Shredded fallback range: **0.00–1.00**. Gap = minimum shredded minus maximum usable = **0.00**, below the required 0.20. The condition that every usable share be below every shredded share also fails. The measure was not adjusted. **Non-clean-margin branch: all fallbacks become ordered prose; no threshold constant is introduced.**

Region 37 (p. 44): 1/3 = 0.3333, becomes prose. Region 38 (p. 45): 2/5 = 0.40, becomes prose. Their rendered source remains:

![Region 37 source](/tmp/batchC-fallback-review/region-37.png)

![Region 38 source](/tmp/batchC-fallback-review/region-38.png)

**Known cost:** usable grids 2/p3, 43/p49, 44/p53, 52/p61, and 55/p63 lose their row/column layout. Their complete source-token multisets are retained, with zero gains or losses relative to their old grids. The five source images and original cell matrices are in the preceding section.

### Implementation and acceptance

Existing candidate membership, reconstruction, the 0.9 guard, and fallback decisions are unchanged. A fallback Table block now stores the original member paragraphs and renders those paragraphs instead of geometric cells. Keeping its internal Table identity prevents downstream classifiers and text-table proposals from consuming it again. Source blocks and lines retain PDF character-stream order; no geometry sort or dehyphenation is added. Nonblank source lines are emitted as Markdown soft line breaks, with original block boundaries between paragraphs. No pipes or HTML table are emitted for fallback regions.

Each fallback begins with `<!-- table p. N: reconstruction failed; text kept as prose -->`. HTML-sensitive characters are escaped, and list-like paragraph openers are escaped without changing their words. Stats retain `tables` and `tables_fallback`; the shared CLI/GUI/log warning now says “N of M tables kept as prose”. Page conservation uses the source text for these blocks.

**SBTi:** all 55 identities/decisions remain: 25 reconstructed grids and 30 prose fallbacks. Every cell of each of the 25 reconstructed grids is identical to baseline. All 30 fallback source-token multisets are identical to their emitted prose multisets under exactly `content_words()` normalization (retaining its normalized tokens for Counter comparison). Source-line order is retained verbatim; existing rendered-page evidence for all 30 is above. There are zero missing or extra source tokens in every region.

**Content words:** 18,345 → **18,425**, +80 recovered tokens. Table markup and the new marker contribute zero words. No old-grid token disappears. The table below names every gained token and multiplicity. Normalization counts bullet glyphs as tokens, so those gains are included rather than silently excluded.

| Original fallback region | PDF page | Source/prose words | Missing / extra vs source | Gains vs old grid |
| ---: | ---: | ---: | --- | --- |
| 2 | 3 | 201 | 0 / 0 | none |
| 4 | 11 | 170 | 0 / 0 | none |
| 5 | 11 | 187 | 0 / 0 | `Scope` |
| 6 | 12 | 251 | 0 / 0 | `of` ×2, `scope`, `●`, `and` ×3, `reported` ×2, `excluded`, `near-term`, `reduction`, `customer`, `at` ×2, `least` ×2, `two-thirds`, `(67%)`, `total` ×2, `cover`, `target`, `33%`, `Criterion` |
| 7 | 13 | 47 | 0 / 0 | none |
| 12 | 16 | 235 | 0 / 0 | `the` ×3, `and` ×2, `with`, `should`, `boundary`, `a`, `CO2` ×2, `emissions`, `from`, `processing`, `land`, `associated`, `alongside`, `these`, `scopes`, `1,`, `2`, `progress`, `report` ×2, `biogenic`, `i.e.,`, `also` |
| 13 | 17 | 165 | 0 / 0 | none |
| 14 | 17 | 218 | 0 / 0 | none |
| 16 | 20 | 207 | 0 / 0 | none |
| 18 | 22 | 252 | 0 / 0 | none |
| 21 | 25 | 220 | 0 / 0 | none |
| 23 | 26 | 190 | 0 / 0 | none |
| 25 | 29 | 51 | 0 / 0 | none |
| 26 | 29 | 246 | 0 / 0 | none |
| 30 | 34 | 297 | 0 / 0 | `●`, `Subsidiaries`, `of`, `fossil`, `fuel`, `companies`, `may`, `join`, `is`, `not`, `SBTi’s` |
| 33 | 36 | 240 | 0 / 0 | `●`, `The`, `company’s`, `base`, `year`, `emissions` |
| 36 | 43 | 306 | 0 / 0 | `2030`, `100%`, `temperature` |
| 37 | 44 | 19 | 0 / 0 | none |
| 38 | 45 | 42 | 0 / 0 | none |
| 39 | 45 | 69 | 0 / 0 | `is`, `data.` |
| 40 | 46 | 235 | 0 / 0 | none |
| 41 | 47 | 365 | 0 / 0 | none |
| 42 | 48 | 243 | 0 / 0 | none |
| 43 | 49 | 307 | 0 / 0 | none |
| 44 | 53 | 296 | 0 / 0 | none |
| 46 | 55 | 350 | 0 / 0 | none |
| 50 | 60 | 76 | 0 / 0 | none |
| 52 | 61 | 224 | 0 / 0 | none |
| 54 | 62 | 410 | 0 / 0 | `and`, `year].`, `to`, `1,2`, `be` |
| 55 | 63 | 198 | 0 / 0 | none |

### All reference documents and pipeline controls

All PDFs were run through the updated converter. Pipeline files were read in place. Counts use the unchanged `markerlite.content_words()` metric. “Retained cells” compares complete parsed matrices for every region that still reconstructs, including text-table proposals; equality implies identical per-cell hashes.

| Document | Before | After | Delta | Prose fallbacks | Retained cells |
| --- | ---: | ---: | ---: | ---: | --- |
| Target-Validation-Protocol | 18345 | 18425 | +80 | 30 | identical |
| Ragins craft of clear writing 2012 | 6625 | 6625 | +0 | 0 | identical |
| peng2009 | 12046 | 12046 | +0 | 1 | identical |
| greenwood2006 | 14777 | 14777 | +0 | 2 | identical |
| wry2013 | 18441 | 18441 | +0 | 0 | identical |
| jay2013 | 16377 | 16377 | +0 | 0 | identical |
| york2018 | 19930 | 19930 | +0 | 0 | identical |
| kitchener2002 | 13256 | 13256 | +0 | 0 | identical |
| suchman1995 | 16458 | 16458 | +0 | 0 | identical |
| kostova1999 | 11297 | 11297 | +0 | 0 | identical |
| R01285 | 23062 | 23063 | +1 | 1 | identical |
| R02611 | 15307 | 15307 | +0 | 1 | identical |
| paper | 304 | 304 | +0 | 0 | identical |
| hard | 1021 | 1021 | +0 | 0 | identical |

**peng2009:** p. 2: 183 source words conserved; gains {}; removals {}.

**greenwood2006:** p. 7: 389 source words conserved; gains {}; removals {}; p. 10: 233 source words conserved; gains {}; removals {}.

**R01285:** p. 1: 365 source words conserved; gains {"Society": 1}; removals {}.

**R02611:** p. 1: 198 source words conserved; gains {}; removals {}.

All other reference totals are unchanged. SBTi’s +80 and the listed R01285 recovery account for all count changes. paper.pdf and hard.pdf have byte-identical Markdown to their marked baseline outputs, and all their cell matrices remain identical. This step does not yet claim to fix journal front-matter classification or Kostova Figure 1.

### Tests

`python tests/regress.py` passed every existing fixture and auxiliary check after the converter change. The extended `tall_cell` check additionally passed in a focused run: normal reconstruction keeps the existing usable grid; disabling wrapped recovery exposes its original lossy reconstruction and emits prose; an unavailable reconstructor takes the same prose path. Both failure paths assert the complete source token multiset, ordered distinctive phrases, absence of pipes/table HTML, exact marker count, source text present in the actual output, fallback statistics and warning wording. Their full expected output is `tests/expected/tall_cell_fallback.md`. Existing expected outputs did not change.

This is the non-clean branch: the kept-grid fixture control is a successful reconstruction, not a fallback exception. No usable geometric fallback is silently exempted.

### Actual prose for regions 37, 38 and 39

#### Region 37, p. 44

```markdown
<!-- table p. 44: reconstruction failed; text kept as prose -->

Where:

RTD = Percentage reduction (%) to date expressed as the reduction between base year and most

recent year.
```

#### Region 38, p. 45

```markdown
<!-- table p. 45: reconstruction failed; text kept as prose -->

NZA = Percentage reduction (%) required for reaching the sector’s emissions intensity in 2050 from

the chosen target base year (depends on sector and base year intensity).

A0
= Minimum target ambition (%) based on the sector-specific intensity method before FLA

adjustment.
```

#### Region 39, p. 45

```markdown
<!-- table p. 45: reconstruction failed; text kept as prose -->

Option 2. The emissions intensity reduction between the most recent year and target year is
consistent with intensity convergence between the most recent year and 2050.
In other words, the target needs to be consistent with the ambition required from the sector-specific
intensity method using most recent year data. In some cases, this will require a larger reduction than
calculated by the sector-specific intensity convergence using base year data.
```

### Local reproducibility artifacts

- [Reference audit script, unchanged production normalization](/tmp/batchC-prose/audit.py)
- [SBTi source/prose multisets, all gains, and retained matrices](/tmp/batchC-prose/Target-Validation-Protocol.json)
- [SBTi resulting Markdown](/tmp/batchC-prose/Target-Validation-Protocol.md)

Boxed-prose evidence check (step 3) and journal front matter (step 4) follow this implementation commit. No release tag is authorized.
