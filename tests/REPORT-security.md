# Security hardening: findings and status

An external static review of commit b3ed8a5 (v0.1.15) raised the findings
below. markerlite is a local, single-user tool with no network access at
runtime (SECURITY.md), so these are treated as robustness fixes first: a
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
| 2 | CI holds `contents: write` in every step, leaves the token in `.git/config`, and uses movable action tags | fixed; release job to be verified at the next tag | aaf1d74 |
| 3 | `build_exe.bat` expands paths unquoted and depends on the current directory | fixed | 7e6f171 |
| 4 | File names and exception text reach the run log, GUI and console raw | fixed | c61ed22 |
| 5a | Table projection: no check on coordinates handed to table_recon | fixed | 6ae3742 |
| 5b | Horizontal-rule pairing is cubic and uncapped | fixed | 394f062, 239916f (format) |
| 5c | Code indentation trusts the glyph width | fixed | c1f0034 |
| 5d | Provenance regex rebuilt per line, uncapped | fixed | 124da1e |
| 5e | Vector clustering quadratic, run twice per page, uncapped | fixed | 164e73d |
| 5f | Image export decodes the source without a size check | fixed, and two worse decoders found and fixed | 8e7e1fd |
| 5g | OCR render size and TSV capture unbounded | fixed | 845702f |
| 6 | No security policy | added; private vulnerability reporting must be switched on by the owner | 3697f2a |
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
| actions/upload-artifact | 330a01c490aca151604b8cf639adc76d48f6c5d4 | v5.0.0 |
| actions/download-artifact | 634f93cb2916e3fdff6788551b99b062d0335ce0 | v5.0.0 |

Verified: the read-only build and test jobs passed on every push from
aaf1d74 on (one failure, 394f062, was a formatting slip fixed in
239916f).

**To check at the next tag** (the release job cannot run before one):

1. The `build-windows-exe` run for the tag shows two jobs, `build` and
   `release`, and `release` starts only after `build` succeeds.
2. In the `build` job's log, the "Set up job" section lists
   `Contents: read` under GITHUB_TOKEN permissions; in the `release`
   job's log it lists `Contents: write`.
3. The `release` job's step "Check the bundled version against the tag"
   succeeds, and the release page shows `markerlite-windows.zip`.
4. A push to main still produces no release and no `release` job run.
4a. The release page's notes are the download instructions followed by the
   tag's CHANGELOG.md section (added before v0.1.16: the build job writes
   `release-notes.md` beside the zip in the artifact, and the release job,
   still without a checkout, publishes it with `--notes-file`).
5. If the release step fails with a permissions error, the repository's
   Settings, Actions, Workflow permissions must allow the per-job grant
   (the workflow asks for `contents: write` only in that job).

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
report. **Private vulnerability reporting is switched off** for the
repository (the API reports `enabled: false`); the owner must enable it
under Settings, Code security. Until then the policy's fallback applies:
an issue that asks for a private channel without details.

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
