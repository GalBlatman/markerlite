# Security hardening: findings and status

An external static review of commit b3ed8a5 (v0.1.15) raised the findings
below. Conversion is local and offline; the GUI also has an explicit,
user-initiated HTTPS update check. These are treated as robustness fixes: a
pathological PDF must never stall or crash a batch, and a tripped limit
must degrade visibly, never silently. The reviewer's raw files are not
committed.

Every item was one commit. After each commit the 77-entry golden audit
(`tests/golden.py verify --scope full`, run from an archive of exactly
that commit in WSL with Tesseract 5.5.0) must match every entry: no
Markdown or stats hash may change in this part.

## Status

| # | Finding | Status | Commit |
| --- | --- | --- | --- |
| 1 | `--apply-figures` / `--apply-math` trust the manifest's `stem`, so a manifest can rewrite a file outside `--outdir` | fixed | ce01672 |
| 2 | CI holds `contents: write` in every step, leaves the token in `.git/config`, and uses movable action tags | resolved; release isolation verified at v0.2.0 | aaf1d74 |
| 3 | `build_exe.bat` expands paths unquoted and depends on the current directory | fixed | 7e6f171 |
| 4 | File names and exception text reach the run log, GUI and console raw | fixed | c61ed22 |
| 5a | Table projection: no check on coordinates handed to table_recon | fixed | 6ae3742 |
| 5b | Horizontal-rule pairing is cubic and uncapped | fixed | 394f062, 239916f (format) |
| 5c | Code indentation trusts the glyph width | fixed | c1f0034 |
| 5d | Provenance regex rebuilt per line, uncapped | fixed | 124da1e |
| 5e | Vector clustering quadratic, run twice per page, uncapped | fixed | 164e73d |
| 5f | Image export decodes the source without a size check | fixed, and two worse decoders found and fixed | 8e7e1fd |
| 5g | OCR render size and TSV capture unbounded | fixed | 845702f |
| 6 | No security policy | resolved; private reporting verified enabled | 3697f2a |
| — | Per-page time budget | proposed below, not implemented | — |

## How a tripped limit degrades

One mechanism serves every limit. `note_limit()` records the page, the
limit's name, the observed value, the cap and the action taken.
`build_stats()` reports the records as `stats["resource_limits"]`, a key
that is present only when a limit tripped, so ordinary output and every
golden stats hash are unchanged. `stat_warnings()` adds one line, "N
resource limits reached (name pN, ...); content kept, see stats", which
the CLI, the GUI's file list and tooltip, and the run log all show. In no
case is source text dropped: the region stays as prose, a figure keeps
its placeholder, a page keeps its text.

## Limits: measured maxima and chosen limits

Measured by converting 76 documents with instrumentation: everything in
`tests/real` (the ten reference documents, R02027, the SBTi protocol and
Capital IQ), the 24 packet documents of the golden corpus resolved by
SHA-256, and every fixture. Each limit is at least ten times the observed
maximum.

| Limit | Constant | Observed maximum (where) | Limit | Ratio |
| --- | --- | --- | --- | --- |
| 5a table projection | `TABLE_PROJECTION_MARGIN` | no non-finite coordinate; 172.5 pt outside the page, 0.22 of its larger side (SBTi) | 3.0 page sides outside the page | 13.6x |
| 5b rule segments per page | `TABLE_RULES_MAX` | 75 (R00023) | 1,000 | 13x |
| 5b rule rows per page | `TABLE_RULE_ROWS_MAX` | 31 (R00293) | 400 | 13x |
| 5c code glyph width | `CODE_MIN_CHAR_WIDTH` | narrowest 2.706 pt (R00443, the only code block) | under 0.25 pt is implausible | 10.8x |
| 5c code indent | `CODE_MAX_INDENT` | 12 spaces (R00443) | 120 spaces | 10x |
| 5d provenance pieces | `PROVENANCE_MAX_PIECES` | 8 (fixture); 6 on a real document (Suchman) | 80 | 10x |
| 5e drawings per page | `FIGURE_VECTOR_MAX_DRAWINGS` | 326 (R00032) | 4,000 | 12x |
| 5f image source pixels | `FIGURE_IMAGE_MAX_PIXELS` | 23.2 million (R00639) | 240 million | 10x |
| 5g OCR pixels at 300 dpi | `OCR_MAX_PIXELS` | 8.4 million on an OCR'd page (Suchman); 8.7 million on any page | 90 million | 10x |
| 5g Tesseract TSV | `OCR_MAX_TSV_BYTES` | 42.5 KB (Kostova) | 1 MB | 23x |

Evidence is thin for 5c: the corpus holds one code block.

## Findings in detail

### 1. Manifest path confinement (ce01672)

Both apply commands go through `markerlite/paths.py`. The stem must be a
plain file name: no separator of either kind, no drive or colon, not "."
or "..", no control characters, no leading or trailing spaces or dots.
The resolved target must sit directly in the resolved `--outdir`. A
refused manifest stops with "markerlite: refused: ..." and a non-zero
exit. Tests cover 19 rejected forms in the helper and 21 in each command
(absolute POSIX and drive paths, drive-relative, bare drive, "." and
"..", escapes with either slash, mixed separators, UNC with either slash,
an alternate data stream, NUL, newline, edge spaces and dots, empty,
non-strings), and check that a file beside the output folder is
untouched. Valid manifests still apply to `<outdir>/<stem>.md` only.

### 2. CI least privilege (aaf1d74)

Both workflows default to `contents: read`. Publication moved to a
`release` job that needs the build, runs only for a `v*` tag, alone holds
`contents: write`, checks nothing out and only downloads the built zip.
It checks that the VERSION bundled in the zip equals the tag. Every
checkout sets `persist-credentials: false`. Actions are pinned to commit
SHAs, at the latest release within the major already in use:

| Action | Pinned commit | Version |
| --- | --- | --- |
| actions/checkout | fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 | v5.1.0 |
| actions/setup-python | ece7cb06caefa5fff74198d8649806c4678c61a1 | v6.3.0 |
| actions/upload-artifact | cf430e030ddbb5b0abf93d22962f4752f3646cd9 | v7.0.2 (node24; was v5.0.0, node20) |
| actions/download-artifact | 9000827ccba6bdab643e8b6fd33ac0654aef8333 | v8.0.2 (node24; was v5.0.0, node20) |

Verified: the read-only build and test jobs passed on every push from
aaf1d74 on (one failure, 394f062, was a formatting slip fixed in
239916f).

**Release verification completed:** the v0.2.0 tag run
[40020542297](https://github.com/GalBlatman/markerlite/actions/runs/40020542297)
passed the checkout-free release job after the read-only build, checked its
bundled version, and published the archive. The published SHA-256 matched
GitHub's digest, and its notes came from the CHANGELOG section; see
REPORT-v0.2.0-release.md. Main pushes do not publish. A read-only API check
on 2026-10-24 also confirms private vulnerability reporting is enabled; no
repository settings were changed by this patch.

### 3. build_exe.bat (7e6f171)

The script enters its own folder with `pushd "%~dp0"` and leaves with
`popd` on both paths, quotes every path and every echo that expands one,
and keeps CRLF line endings. From a copy in a folder named
"a & b dir\markerlite src", started elsewhere: the old script failed at
PyInstaller ("Unable to find ...\assets"); the new one built, printed the
dist path with its "&" literally, exited 0, restored the starting folder,
and the built exe's `--diag` first line was "markerlite 0.1.15".

### 4. Safe display (c61ed22)

`markerlite/display.py`, `safe_display()`, renders every C0 and C1 control
(with DEL), U+2028 and U+2029, and the bidirectional overrides and isolates
as visible escapes such as `\n`, `\x1b` and `‮`. It is applied to
the run log's lines, the file list, the status bar, the preview's error
text, and the CLI's status and error messages. Paths for file-system work
stay raw. A name holding LF, CR, ESC, BEL, DEL, NEL, U+2028 and U+202E
becomes one inert line in every helper; on Linux the CLI converts a
fixture copied to a file named with LF, CR and ESC and prints one escaped
line.

### 5a. Table projection (6ae3742)

A glyph with a 1e30 vertical scale has a finite box reaching 5e19 pt
beyond the page. A ruled-table candidate never sees it, because its
tokens are filtered by position; a text proposal does. The crafted
fixture puts such a glyph in a five-row aligned block. With the limit the
block stays prose with all 18 words, plus the record and the warning.
With the limit off, conversion still finished in 0.1 s, but the glyph
dragged "1.2X" into the header row. On this input the risk was a
misplaced cell, not a stall.

### 5b. Rule pairing (394f062)

The zone search is now quadratic with a binary search, and caption ends
are found once per page. A property test compares it with the old cubic
search on 300 random rule sets: identical. Timing on full-width rows
(old / new): 100 rows 0.016 / 0.004 s; 400 rows 0.820 / 0.109 s, with
77,028 zones. A whole conversion of a 390-row page takes 1.3 s. Fixtures
with 450 rows, and with 1,100 segments, trip the caps and keep the text.

### 5c. Code indentation (c1f0034)

Courier at 0.3 pt (glyphs 0.18 pt wide) keeps its lines without a rebuilt
indent; a line indented 3,000 pt (500 spaces) is cut to 120.

### 5d. Provenance matching (124da1e)

`ProvenanceMatcher` is built once per document and passed to every page.
Above 80 pieces only the run-together pattern is skipped; exact stamp
lines are still dropped. A 100-page fixture with a different stamp on
every page converts in 0.9 s, keeps its 100 body lines and drops every
stamp.

### 5e. Vector clustering (164e73d)

This was a real stall. Each cluster now keeps its bounding box as it
grows, and the drawings and regions are computed once per page and
reused. A property test against the old loop on 300 random sets of boxes,
zero-sized ones included, gives identical clusters. It also caught a
first version that never grew the boxes, because PyMuPDF's `Rect |=`
builds a new object. One clustering call on the crafted strokes:

| Drawings | Old | New |
| ---: | ---: | ---: |
| 326 | 0.53 s | 0.00 s |
| 1,000 | 4.81 s | 0.02 s |
| 4,500 | 101.09 s | 0.06 s |

The old code ran it twice per page, so a 4,500-stroke page cost about
200 s. That fixture now trips the cap, keeps both paragraphs and still
emits its figure placeholder.

### 5f. Image decoding (8e7e1fd)

The review named `Pixmap(doc, xref)` in `--images`. Measuring a crafted
20,000 x 20,000 grey image (0.4 MB of Flate data, 400 MB decoded) found
two worse decoders that run on every conversion:

| Call | Peak memory |
| --- | ---: |
| `get_text("rawdict")` / `"dict"` (image blocks requested by default) | 818 MB |
| `get_image_info(xrefs=True)` | 436 MB |
| `Pixmap(doc, xref)` | 436 MB |
| plain `get_image_info()`, `get_image_bbox()` | 54 MB |
| rendering a crop / the page at 300 dpi | 58 / 86 MB |

On a page with an image over the budget, text extraction no longer
requests image blocks (no caller used them), figure rasters are located
with the non-decoding calls, and `--images` exports a page render of the
placement. Pages under the budget take the old path unchanged. The
fixture's conversion went from 933 MB and 8.3 s to 170 MB and 0.1 s (with
`--images`, 933 MB and 10.3 s to 175 MB and 0.1 s).

### 5g. OCR (845702f)

The page's pixels at 300 dpi are computed from its box before rendering;
above the budget the page is rendered at the lower dpi that fits.
Tesseract's TSV goes to a file and at most 1 MB is read, cut at a line
end; it is now decoded as UTF-8 explicitly, where it used the locale's
encoding before. The crafted 4,000 pt page (278 million pixels at 300 dpi)
gets a lower dpi; with the budgets lowered, the scanned fixture still
yields its text and records the limits.

### 6. Security policy (3697f2a)

SECURITY.md states the threat model in five lines, the scope, and how to
report. The original scan found private vulnerability reporting disabled.
A fresh read-only GET of the repository private-vulnerability-reporting
endpoint on 2026-10-24 returns `enabled: true`; that administrative item is
now resolved. The policy retains its fallback for unavailable reporting.

## Per-page time budget: proposal, not implemented

A budget that can stop work midway needs a thread or a process: MuPDF
calls and Tesseract cannot be interrupted from the same thread. The
limits above bound the known super-linear paths, and Tesseract keeps its
180 s timeout. Proposal: run each document's conversion in a child
process (`multiprocessing` with the spawn method, which the frozen exe
supports) with a wall-clock budget per page times the page count; on
expiry, kill the child, record the document as failed with "time budget
exceeded" in the run log and the GUI, and continue the batch. This keeps
one pathological PDF from stalling a batch without changing any
conversion. It needs a decision because it changes the GUI's worker model.

## Golden audit after every commit

| Commit | Item | Golden (77 entries) |
| --- | --- | --- |
| dd0b0f4 | baseline (before Part A) | 77/77 identical, 0 OCR skipped |
| ce01672 | A1 manifest path confinement | 77/77 identical, 0 OCR skipped |
| aaf1d74 | A2 CI least privilege | 77/77 identical, 0 OCR skipped |
| 7e6f171 | A3 build_exe.bat quoting | 77/77 identical, 0 OCR skipped |
| c61ed22 | A4 safe display | 77/77 identical, 0 OCR skipped |
| 3697f2a | A6 SECURITY.md | 77/77 identical, 0 OCR skipped |
| 6ae3742 | A5a table projection | 77/77 identical, 0 OCR skipped |
| 394f062 | A5b rule zones | 77/77 identical, 0 OCR skipped |
| 239916f | A5b format fix | 77/77 identical, 0 OCR skipped |
| c1f0034 | A5c code indentation | 77/77 identical, 0 OCR skipped |
| 124da1e | A5d provenance matcher | 77/77 identical, 0 OCR skipped |
| 164e73d | A5e vector clustering | 77/77 identical, 0 OCR skipped |
| 8e7e1fd | A5f image pixel budget | 77/77 identical, 0 OCR skipped |
| 845702f | A5g OCR pixels and TSV bytes | 77/77 identical, 0 OCR skipped |

This report's own commit changes no code; its audit is listed in the
commit that follows it.


## Second scan: v0.2.1 work (revision 00514b4)

The second scan is verified against tests/golden/v0.2.0.json, 186 entries
in both grid modes. No baseline is regenerated. Every numbered item is a
separate commit; archived verification uses exactly that commit, with PDFs
read in place. A differing hash is a blocker.

### Second-scan disposition

| Item | Finding / outcome | Commits |
| --- | --- | --- |
| 1 | Per-file CLI isolation; deterministic hashed shortening for long stems | 8863319 |
| 2 | Back up the whole target set before swaps; rollback every target on failure | 9ac8ce4, d8470dc |
| 3 | GUI display funnels; static AST sink test and multiline/control-character test | 80748f8 |
| 4 | Validated OCR geometry, crop device caps, cumulative decoded-source reservation on every render/decode route | b985d2c, a1ab2f8, e2736c0 |
| 5 | Absolute table coordinate, input-token and geometric/reconstructed-cell guards | bf131ba, 7ad36af |
| 6 | Pairwise candidate caps and inner-loop cancellation checks | fab4880, 69c7934 |
| 7 | Bounded producer stdout with kill/reap; crop count and encoded-byte budgets | 8d8ceac, a0dafb1; parser/producer tests c05968b, fe76cfa |
| 8 | Size/count/type-checked apply manifests; parse once; one Markdown scan | dde6e25 |
| 9 | Pinned Python/pip, generated hash lock, isolated pinned OCR installer | 37186a7 |
| Deferred | Document page / retained-memory / output / wall-clock budgets | Planned per-document worker process; no implementation in this patch |

Implementation commits kept findings separate. Additional same-item follow-up
commits were necessary for rollback intent after a successful rename, reader
startup cleanup, renderer source reservations and the reconstruction boundary;
published history was preserved. This deviates from exactly one commit per
item, rather than concealing those corrections in a rewritten history.
No table_recon.py edits, document-specific rules, threshold relaxation or
baseline regeneration. Ordinary Markdown/stats must remain byte-identical.

### Item 1: batch isolation and long output names

Each conversion and output-directory creation has its own exception boundary.
A malformed middle PDF is reported while both valid neighbours finish; the
batch ends nonzero and lists its failures. The API discards staging on any
exception, so failed extraction/rendering leaves no .part. A 250-character
basename converts successfully with a deterministic SHA-256 identity suffix;
all derived names share that stem. The 255-byte component allowance minus the
longest suffix is a filesystem constraint, not a corpus work limit. Ordinary
names are unchanged. Tests cover the malformed mid-batch and long-name cases.

### Item 2: complete output rollback

Stage all files/folders, move every existing target into one private backup
directory, swap every staged path, then delete backups. Tests inject failure
both before and immediately after each of six backup/swap rename positions,
asserting the old set byte for byte, absent new targets, no staged remnants.
Rollback failure is explicit and retains the recovery directory instead of
deleting the only old copy. Apply-manifest rewrites share this transaction.

### Item 3: safe display

Every dynamic GUI text/label/title/dialog/Text insertion uses safe_display
or the multiline display_text funnel. The latter applies safe_display to each
line while preserving structural preview newlines. Tooltips, provenance,
warnings, status and the log therefore escape terminal/control and Unicode
reordering characters. An AST call-site test refuses unwrapped dynamic sinks;
pure helper tests exercise controls without fake widgets. check_gui.py passes
(85 methods, 56 self-calls). Filesystem paths are not rewritten for display.

### Item 4: raster budgets

Measured all 84 unique PDFs represented by the 186-entry baseline. Source
PDFs were opened in place; measurement saved counts only. The evidence is
security-v021-observed.json. Whole-page dimensions conservatively bound the
figure/equation crop dimensions because clips lie inside the page. Decoded
source bytes conservatively count four channels per image placement per page.
Repeated actual decode reservations consume the document budget again.
Text extraction no longer requests unused decoded image blocks at all.

| Quantity | Observed maximum | Chosen cap | Ratio |
| --- | ---: | ---: | ---: |
| Crop device long side at 200 dpi | 2,339 px | 24,000 px | 10.26x |
| Whole-page raster pixels at 300 dpi (bounds 200-dpi crops) | 8,703,348 | 90,000,000 | 10.34x |
| Complete decode/render source reservations, four channels, repeats counted | 11,979,380,000 (R00639) | 128,000,000,000 | 10.68x |

OCR estimates require finite positive dimensions, clamp each side to at
least one point and round device dimensions upward. A page that cannot fit
at 1 dpi keeps native text with a limit record. Crops lower resolution to
fit both side/pixel limits; impossible crops keep the placeholder/source
text with a limit record. Exhausted source decode reservations use the
non-decoding placement route; image export can render a bounded crop.
All records flow through the existing resource_limits stats/warning path.
Tests force each branch, including a fractional page side and nonfinite
geometry, without allocating the dangerous raster.


### Item 5: bounded table work

All 84 unique baseline PDFs were measured without copying them. Additional
native rawdict measurements rebuilt the owned reconstruction-token shape;
whole-page counts bound individual native table candidates. Maximum native
source fragments: 1,090 (R02659 p. 25); reconstruction tokens: 461
(R00443 p. 14). The existing OCR TSV cap also bounds OCR input; matching-engine
full golden verification covers all OCR candidates. Chosen token cap:
12,000 (11.0x the larger native bound); cell cap: 8,000 versus 630 measured
(SBTi p. 28; 12.7x); absolute coordinate/span cap: 10,000 points versus
842.04 measured (R00023 p. 1; 11.9x). The absolute bound is independent of
page size and supplements the existing relative projection guard.

Check member cardinality/geometry before isolation or reconstruction,
recheck the actual token array before table_recon, and independently check
before allocating/scanning geometric cells. A candidate exceeding a limit
keeps original source blocks as prose, with resource_limits and the shared
warning. No table_recon.py changes. Forced-low-cap tests keep source text
and prove the geometric scan is refused before cell allocation.


### Item 6: pairwise candidates and cancellation

Image placement: 32 source-image candidates per page observed (R00717 p. 9),
cap 400 (12.5x). Diagram gate: 24 stroked rectangle candidates observed
(hard.pdf p. 2), cap 256 (10.7x). Cross-page furniture: the measured
whole-document source-block upper bound is 5,402 (Capital IQ), cap 60,000
(11.1x); this conservatively bounds filtered candidates, rather than
claiming 5,402 actual running-head candidates. Check the actual evidence
list too, before pairwise matching. Counts are in security-v021-observed.json.

Oversized-image placement skips pairwise xref matching above its cap and
keeps non-decoded placements/placeholders/source text. Diagram evaluation
rejects to prose when capped and records its limit. Furniture analysis
keeps every original block when capped. The inner loops check the active
conversion cancellation token, including word-by-cell scanning. A Cancelled
exception remains outside Exception handlers. Focused tests prove each
cap avoids its pair loop and an active iterator notices cancellation.
The legacy projection fixture now expects the earlier absolute-span guard;
CI at bf131ba failed only that outdated named-guard assertion, not output
conservation. It is corrected here without changing any golden baseline.
Cancellation timing results against the v0.1.17 table follow in the final
verification section after the archived reference runs complete.


### Item 7: bounded Tesseract stdout and crop disk writes

All 17 OCR source documents in the baseline were converted with a byte-count
observer on the actual stdout capture; no recognized text was saved as
measurement data. Maximum TSV: 42,506 bytes (Kostova); maximum OSD stdout:
125 bytes (R02027). The 1,000,000-byte TSV cap is 23.5x; the 4,096-byte OSD
cap is 32.8x. Read at most cap+1 from a pipe, kill/reap the producer on
overflow, trim partial TSV rows, and join the reader on success, cancellation
or timeout. No full TSV/OSD output file is written first. Partial recognition
is explicitly warned; recognized prefix and any native source text remain.

Crop counts and encoded bytes were measured by converting all 84 baseline
PDFs with images, figure crops and equation crops enabled together at
archived fab4880. All source PDFs stayed in place; temporary output was
removed after each measurement, and only counts/limit metadata are recorded.
R02659 is largest: 141 crops, 7,077,229 bytes. Caps: 2,048 crops (14.5x)
and 80,000,000 bytes (11.3x). The shared document counter covers figures,
equations and image export. Check count before rendering and byte length
before writing; retain placeholders/source text plus limit warning/stats.
PNG save versus byte encoding is byte-identical; 112 fixture golden hashes,
including crop artifacts and OCR, pass with zero skips before commit.
Source-image export reserves the individual source's bytes, not the bytes
of unrelated images on the same page.

Tests kill an overflowing producer, test exact-cap EOF, timeout and cancel,
assert no reader/process remains, and force crop count/byte exhaustion.
Item 2 follow-up d8470dc additionally registers rollback intent before each
rename, covering cancellation just after success; tests inject failure both
before and after every backup/swap. Published history is preserved rather
than rewriting the original item 2 commit.


### Item 4 follow-up: cover renderer source decoding too

The first raster commit covered explicit source decoding. OCR, orientation
renders and figure/equation crops can also decode embedded sources. They now
reserve before invoking MuPDF; an exhausted reservation skips the render
with a limit record and retains native text/placeholders. Re-OCR trial pages
report the original PDF page index. Forced-low-budget tests prove neither
OCR nor crop rendering is called after refusal.

All 84 PDFs were re-run with all crop modes enabled and complete reservation
accounting. The source-reservation maximum is 11,979,380,000 bytes (R00639),
so the final cap is 128,000,000,000 (10.68x), replacing the initial 40 GB
calibration that counted explicit decodes only. This is cumulative work
reservation, not a retained-memory/RSS limit. The latter remains deferred.
Per-document crop counts and encoded byte totals match the earlier real
crop measurement in all 84 documents. No new limit tripped during calibration.
OCR pixel reductions and invalid geometry are recorded before rendering,
so a later renderer/recognizer failure cannot hide a tripped limit.


### Item 5 follow-up: enforce the reconstruction boundary

All 84 documents were converted with observers on actual reconstruction
inputs and returned grids; every observed Markdown/stats pair matched the
baseline. Maximum actual input: 311 tokens (R00373 p. 12); returned grid:
552 cells (R00443 p. 14). The conservative pre-allocation grid bound is
29,055 cells (R00023 p. 51); cap 1,000,000 (34.4x). The independent whole-page
native bound is 51,207 (R00293 p. 3), also below one tenth of the cap.
The bound includes a header row and the larger of maximum row spans and
one-point projection width, covering both vendor candidate builders.

A review found that a failed post-token preflight could still reach the
old else branch. It now cannot. All vendor calls use the guarded wrapper;
returned and repaired HTML is checked against the 8,000-cell cap before
owned cell scans. Forced-limit tests spy on reconstruction/recovery to
prove refusal occurs first, including finite endpoints with an overflowing
span. Oversized candidates retain source prose and resource-limit stats.
No table_recon.py edit and no baseline regeneration.


### Item 7 test-boundary correction

The full CI suite exposed an orientation-parser test still mocking
subprocess.run after capture moved to bounded stdout. It unintentionally
invoked the installed engine and compared a real answer with mock data.
The test now intercepts capture_capped, asserts stdout mode and its cap,
and verifies the parser independently of engine version. The complete WSL
unit suite passes: 337 passed, three Windows-only skips. No runtime change.


### Item 8: apply manifests

The 84-document crop run's largest manifest is 95,892 bytes and 135
entries (R02659). Caps are 1,000,000 bytes (10.4x) and 2,048 entries
(15.2x), checked before parsing/entry processing. Reads request at most
cap+1; entry counts are checked before schema traversal. Validate container,
string/UTF-8, identifier, positive-page and finite-bbox types, including
boolean rejection for integer fields. Invalid input fails with a clear
error before Markdown is read or changed. A limit error carries the stable
resource_limits fields (page 0 denotes the manifest operation), and the CLI
prints the structured stats with its refusal warning.

CLI parses once and passes a validated snapshot through the API. Each apply
kind builds an entry lookup then scans Markdown once for all replacements;
figure replacement remains idempotent and math preserves intervening prose.
The resulting Markdown uses the rollback-capable output transaction.
Tests cover invalid schemas, byte/entry refusal, no second parse, single
scanner invocation and preservation/idempotence. No corpus baseline changes.


### Item 9: hash-checked build dependencies and installer isolation

Both workflows pin Python 3.12.10 (the common Windows/Linux patch in the
setup-python distribution manifest). pip 26.2.2 is bootstrapped with its
published SHA-256 hashes. A generated universal requirements lock supplies
hashes for every pinned dependency, including platform-conditional build
transitives. CI and build_exe.bat use --require-hashes --only-binary=:all:,
then install the trusted checkout with --no-deps --no-build-isolation.
Compatible project ranges remain in pyproject.toml. A fresh WSL virtual
environment successfully installed bootstrap, the complete hash lock and
the checkout without dependency/build-environment resolution.

Chocolatey Tesseract is pinned to 5.5.3.20260724 in a separate Windows
ocr-tests job. It runs the OCR suite and off-PATH discovery checks, uploads
no executable, and cannot share its installed files with the artifact
worker. The build job waits for OCR success but starts on a fresh worker
and never invokes the Tesseract installer. Release remains tag-only with
contents:write confined to its checkout-free publication job. The README
pipeline recipe uses the same two hash files from the selected tag.
Final candidate CI and clean-install evidence follow below.


### Complete raster-export calibration

A second full 84-document run covers raw image export with equation crops
(the alternative to figure-crop links). It yields 141 crops and 7,262,025
encoded bytes at maximum (R02659), versus 141 / 7,077,229 with figure crops.
Use the larger byte observation: 80,000,000 is 11.0x; the crop cap 2,048 is
14.5x. Maximum raw-mode decode/render reservations are 11,886,580,000
(R00639), below the combined-mode 11,979,380,000 maximum. Manifest maxima
stay 95,892 bytes and 135 entries. No limit tripped in either complete run.
Both per-document measurements are committed as counts only in
security-v021-observed.json. No PDF or source text was copied.


### Verification checkpoint for the disposition report

Archived exact-commit runs completed for 80748f8, 8863319, 8d8ceac, 9ac8ce4, a0dafb1, a1ab2f8, b985d2c, bf131ba, d8470dc, fab4880:
186/186 entries match, zero OCR skips, against v0.2.0.json. Logs are under
`tests/audits/v0.2.1/`; later commits are being audited by the same command,
without changing the manifest. Each archive links local reference inputs and
reads external corpus PDFs in place. Full native/OCR observation metadata
covers 84 unique PDFs; no calibration run tripped a limit.

The final pre-tag section will include the remaining exact-commit results,
the full 24-row cancellation comparison (120 requested cancellation points),
Windows OCR/artifact-worker checks and candidate installation/build checks.
No tag is authorized here. The page/retained-memory/output/wall-clock work
remains deferred to a timed per-document worker; killing it must leave only
private staging, with publication owned by the parent after success.


## v0.2.1 candidate: pre-tag verification

VERSION is 0.2.1; current published release remains v0.2.0. CHANGELOG now
records the patch and leaves document-wide worker budgets deferred. The
186-entry v0.2.0 manifest is unchanged. Candidate checks below are completed
against committed archives/build artifacts before requesting the owner tag;
no release/tag is created by this task.

The runtime/dependency implementation is complete. Candidate CI, clean
installation, exact-commit hashes and timing results are recorded below.


### Installer-free artifact-worker test correction

Separating the OCR installer exposed another test that implicitly required
Tesseract discovery despite being a simulated process-failure test. Its fake
page also lacked valid geometry, so on OCR-equipped machines it stopped
before reaching the producer. Give the stub finite dimensions and an empty
image inventory, force discovery, and raise at capture_capped. This tests
the intended failure boundary both with and without a system OCR install;
it changes no conversion code or expected output.


Candidate notes use the existing release-note section layout (Robustness,
Build, Deferred). The initial v0.2.1 notes lacked subsection headings and
failed the standing release-note test; headings now satisfy that contract.
This is documentation only, with no golden change.


### Item 4 final inventory correction: inline/repeated placements

get_images() resource dictionaries omit inline images and list reused
resources differently from placements. The 84-document non-decoding inventory
found ten pages in nine documents whose placement byte estimate is higher.
R00860 pp. 60–61 have zero resource-dictionary image bytes, but 1,508 / 1,524
placement bytes; these are now reserved before a decoder/render is called.
Use the larger of resource and placement byte estimates. An in-memory actual
inline-image test proves it is charged and refused before rendering at a
forced low cap; another test covers a reused resource's repeated placements.

Reconverted all nine affected documents in both raw-image and combined-crop
modes. Crop counts and encoded bytes are identical to the previous full run,
no limits tripped, and the overall maximum remains R00639's 11,979,380,000
bytes (the document is unaffected by this inventory correction). The 128 GB
cap remains 10.68x. Metadata for every page comparison and both nine-document
reruns is in security-v021-observed.json. Source PDFs stayed in place.


### Item 6 final inventory correction: bound both candidate lists

The complete 84-document non-decoding inventory measures up to 36 image
placements (R00717 p. 9), versus 32 resource entries. Check the larger count
before either xref hashing or source/placement matching, covering many
placements of one reused resource as well as many resources. Cap 400 is
11.1x the observed larger list. A test with one resource and two placements
under a forced cap proves neither decoding nor the pair loop is entered.
Normal placements and source text are retained on the capped route with
resource-limit stats. The measured corpus never reaches this cap.


### Completed candidate checks (runtime commit 69c7934)

- WSL: 358 unit passes, three platform skips, one existing homogeneous-font
  clustering warning; measured-module branch coverage 83% (5,183 statements,
  2,296 branches). All readable fixture regressions match.
- Ruff check/format and check_gui.py pass: 85 methods, 56 self-calls.
- [Ubuntu CI 40083391955](https://github.com/GalBlatman/markerlite/actions/runs/40083391955)
  is green: 358 passes / three skips, fixture regression and golden checks.
- [Windows CI 40083391959](https://github.com/GalBlatman/markerlite/actions/runs/40083391959)
  is green. Separate pinned-Tesseract OCR worker: 359 passes / two skips,
  off-PATH discovery, OCR regression. Fresh artifact worker: 357 passes /
  four skips, no Tesseract installation, successful PyInstaller build.
- Each CI golden-fixture check compares 96 entries and explicitly skips 16
  because its engine differs from recorded Tesseract 5.5.0. This does not
  replace the required matching-engine, zero-skip, full 186-entry WSL audit.
- Frozen window title is exactly `markerlite 0.2.1`; all seven embedded icon
  payloads match; diagnostics and TkinterDnD/theme checks pass. Eighteen
  synthetic GUI screenshots were captured. Representative light/dark
  Preferences, Options, Help, OCR and update-dialog views were inspected;
  no fake-widget layout tests were added. Update screenshot is a test view,
  not evidence of a published v0.2.1 release.
- The downloaded Windows archive has no markerlite-diag.txt and contains
  VERSION 0.2.1. Its SHA-256 matches the build log:
  `8368ec46808296aba0e22609b565623a128507918ec604c4483b977817b4bf13`.
  This is the runtime-commit CI artifact; later documentation/tag builds
  have their own digest. No Release was published.
- Local Windows launch of that frozen exe with --diag exits zero. First
  line: `markerlite 0.2.1`; frozen Python 3.12.10; TkinterDnD available;
  installed Tesseract 5.5.3.20260724 found in Program Files.
- A fresh WSL virtual environment installs the bootstrap and complete lock
  with --require-hashes --only-binary=:all:, then installs archived 69c7934
  with --no-deps --no-build-isolation. pip check passes and the installed
  console command reports `markerlite 0.2.1`. All 30 installed owned source/data
  files and vendored table_recon.py match archived 69c7934 byte for byte.
  hard.pdf converts successfully
  with default prose and explicit grids; both modes retain 1,021 content
  words. Local test Python is 3.14.4; CI/build Python is pinned 3.12.10.
- Golden manifest SHA-256 is unchanged:
  `43f0df73ea5d8d41069c9613a355fc54fc706a838ebf2ba5ff4d8047b610cfac`.
  table_recon.py is unchanged, SHA-256
  `04d398465ac6b55976086ea4a1fdabb0d883b6790a449c35c15c7ceb57232af1`.
- The tag-only version/zip publication checks await the owner's tag. VERSION
  and generated candidate release notes both select 0.2.1; no tag is created.

Final exact-commit audit and cancellation evidence follow below. The final
documentation-only evidence commit is also audited and checked on main
before the task stops.


A final native-geometry cross-check normalizes rotations and measures the
whole-page span-coordinate union on all 84 PDFs: maximum 840.964 points
(R00717 p. 1), inside the original conservative 842.04-point page/word bound.
Running both actual find_tables strategies with the area/overlap filters
finds at most 539 geometric candidate cells (SBTi p. 17), below the original
unfiltered 630-cell calibration. The chosen 10,000-point and 8,000-cell caps
therefore remain above 10x. No constants or conversion code changed for this
cross-check; only counts are recorded in security-v021-observed.json.


### Final limit ledger

The detailed sections above name the source/page evidence. Conservative
whole-page bounds are labelled here rather than described as actual crop or
candidate counts. Every chosen cap is at least ten times its measured bound.

| Work | Observed maximum / conservative bound | Cap | Minimum margin |
| --- | ---: | ---: | ---: |
| OCR raster pixels | 8,703,348 whole-page bound | 90,000,000 | 10.34x |
| Crop device side | 2,339 px whole-page bound at 200 dpi | 24,000 | 10.26x |
| Crop raster pixels | 8,703,348 whole-page bound at 300 dpi | 90,000,000 | 10.34x |
| Cumulative source decode reservations | 11,979,380,000 bytes | 128,000,000,000 | 10.68x |
| Absolute table coordinates/span | 842.04 pt conservative page/word bound; native spans 840.964 | 10,000 | 11.88x |
| Table input tokens | 311 actual candidate; 1,090 whole-page fragment bound | 12,000 | 11.0x |
| Geometric/returned table cells | 630 unfiltered geometric bound; 552 returned | 8,000 | 12.7x |
| Internal reconstruction matrix bound | 29,055 actual; 51,207 whole-native-page bound | 1,000,000 | 19.5x |
| Image resources/placements | 32 / 36 | 400 each | 11.1x |
| Diagram boxes | 24 | 256 | 10.7x |
| Furniture evidence | 766 actual; 5,402 source-block bound | 60,000 | 11.1x |
| OCR TSV stdout | 42,506 bytes | 1,000,000 | 23.5x |
| Orientation stdout | 125 bytes | 4,096 | 32.8x |
| Crops/document | 141 | 2,048 | 14.5x |
| Encoded crop bytes/document | 7,262,025 | 80,000,000 | 11.0x |
| Apply-manifest bytes | 95,892 | 1,000,000 | 10.4x |
| Apply-manifest entries | 135 | 2,048 | 15.2x |

The portable filename component allowance is a filesystem constraint, not a
corpus work limit. The pre-existing OCR timeout is unchanged. Document-wide
page count, retained memory, total output and wall-clock budgets remain
explicitly deferred; the cumulative source reservation is not an RSS limit.


### Cancellation: v0.1.17 protocol, measured without an acceptance target

Twelve reference PDFs, grids enabled, OCR available and hidden; cancel at
10/30/50/70/90% of each newly measured conversion duration. Confidential
inputs remain excluded. The complete 24-row sweep uses archived 37186a7.
After the final inventory guards, archived 69c7934 rechecks the historically
slow references plus the affected Greenwood/York references (ten rows).
These sweeps ran while independent archived audits were active; they are
as-is wall-clock observations, not an isolated CPU benchmark. No samples
were dropped or a threshold adjusted to improve these numbers.

Full-sweep maximum: 4.59 s. Final-guard recheck maximum: 8.61 s
(SBTi, OCR available, 90% point), versus the historical 6.63 s maximum.
After every competing audit/timing process exited, the final 69c7934 SBTi
recheck reached 2.13 s. Both the parallel spike and isolated result
are retained. Cooperative cancellation still waits for uninterruptible
library calls; the planned worker process remains deferred.

| Document | OCR | v0.1.17 conversion / worst | 37186a7 conversion / worst | Final 69c7934 recheck worst |
| --- | --- | --- | --- | --- |
| capiq_keydev.pdf | yes | 57.5 / 0.39 s | 57.9 / 0.41 s | not re-run |
| greenwood2006.pdf | yes | 10.4 / 0.27 s | 9.9 / 0.24 s | 0.13 s |
| jay2013.pdf | yes | 20.7 / 0.23 s | 11.6 / 0.73 s | not re-run |
| kitchener2002.pdf | yes | 116.1 / 3.48 s | 121.7 / 0.03 s | 0.03 s |
| kostova1999.pdf | yes | 63.7 / 0.04 s | 81.7 / 0.03 s | not re-run |
| peng2009.pdf | yes | 6.5 / 0.28 s | 10.7 / 0.42 s | not re-run |
| R02027.pdf | yes | 35.2 / 0.22 s | 24.4 / 3.30 s | 2.21 s |
| Ragins craft of clear writing 2012.pdf | yes | 2.6 / 0.19 s | 4.1 / 0.10 s | not re-run |
| suchman1995.pdf | yes | 110.9 / 0.34 s | 624.7 / 0.05 s | not re-run |
| Target-Validation-Protocol.pdf | yes | 57.3 / 6.63 s | 27.4 / 4.59 s | 8.61 s |
| wry2013.pdf | yes | 8.9 / 0.16 s | 9.8 / 0.14 s | not re-run |
| york2018.pdf | yes | 10.0 / 0.28 s | 11.4 / 0.36 s | 0.37 s |
| capiq_keydev.pdf | hidden | 44.1 / 0.28 s | 53.4 / 0.34 s | not re-run |
| greenwood2006.pdf | hidden | 7.8 / 0.23 s | 7.4 / 0.28 s | 0.28 s |
| jay2013.pdf | hidden | 15.2 / 0.53 s | 9.6 / 0.46 s | not re-run |
| kitchener2002.pdf | hidden | 22.5 / 2.21 s | 7.3 / 2.08 s | 2.41 s |
| kostova1999.pdf | hidden | 6.2 / 0.51 s | 1.7 / 0.36 s | not re-run |
| peng2009.pdf | hidden | 4.9 / 0.22 s | 5.6 / 0.10 s | not re-run |
| R02027.pdf | hidden | 29.1 / 3.72 s | 20.2 / 1.82 s | 1.94 s |
| Ragins craft of clear writing 2012.pdf | hidden | 2.4 / 0.06 s | 4.8 / 0.10 s | not re-run |
| suchman1995.pdf | hidden | 6.2 / 0.09 s | 3.0 / 1.53 s | not re-run |
| Target-Validation-Protocol.pdf | hidden | 45.1 / 1.73 s | 30.0 / 2.98 s | 3.96 s |
| wry2013.pdf | hidden | 6.4 / 0.12 s | 7.9 / 0.13 s | not re-run |
| york2018.pdf | hidden | 7.5 / 0.41 s | 9.6 / 0.65 s | 0.23 s |

Isolated SBTi, same archived final code and five fractions per OCR mode:

| OCR | Conversion | Worst cancel |
| --- | ---: | ---: |
| yes | 20.98 s | 1.49 s |
| hidden | 20.11 s | 2.13 s |

Full sweep: 120 scheduled points, 117
raised Cancelled, 3 finished before the timer fired.
Final-guard recheck: 50 scheduled points, 44
raised Cancelled, 6 finished before the timer fired.
Isolated check: 10 scheduled points, 10
raised Cancelled, 0 finished before the timer fired.
Every completed case asserts no .part remains and no tracked Tesseract
child remains. Raw durations, all fractions and completion flags are in
security-v021-cancel.json; no document text is stored. The changing baseline
durations mean a percentage can land in a different stage from v0.1.17, so
this comparison does not attribute every latency difference to this patch.

### Final archived implementation audit

All twenty preceding commits pass 186/186, zero OCR skips, against the
unchanged v0.2.0 manifest. PDFs were read in place from the recorded source
roots. Markdown and complete canonical stats hashes match in both grid modes;
ordinary words, tables and suppression decisions are unchanged. The logs are
in tests/audits/v0.2.1 and their hashes are in security-v021-verification.json.

| Commit | Compared | OCR skips |
| --- | ---: | ---: |
| 8863319 | 186/186 | 0 |
| 9ac8ce4 | 186/186 | 0 |
| 80748f8 | 186/186 | 0 |
| b985d2c | 186/186 | 0 |
| bf131ba | 186/186 | 0 |
| fab4880 | 186/186 | 0 |
| d8470dc | 186/186 | 0 |
| 8d8ceac | 186/186 | 0 |
| a0dafb1 | 186/186 | 0 |
| a1ab2f8 | 186/186 | 0 |
| 7ad36af | 186/186 | 0 |
| c05968b | 186/186 | 0 |
| dde6e25 | 186/186 | 0 |
| 37186a7 | 186/186 | 0 |
| a7f7901 | 186/186 | 0 |
| 2799f08 | 186/186 | 0 |
| fe76cfa | 186/186 | 0 |
| bf68d94 | 186/186 | 0 |
| e2736c0 | 186/186 | 0 |
| 69c7934 | 186/186 | 0 |

The final evidence-only commit contains documentation, these measurements
and audit logs; it changes no production code. Its own archived audit and
main CI are run after commit and confirmed in the task completion message.
No tag or Release is created. All owned verification processes must exit
before the task stops. Tagging/publication is reserved for the owner.
