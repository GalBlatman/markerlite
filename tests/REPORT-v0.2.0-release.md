# v0.2.0 release verification

Published October 23, 2026. Annotated tag v0.2.0 points to
00514b4781e991f19502cc0d2e6616360f3bd220, the verified documentation-only
commit after 009948d. No tag was moved.

## Preconditions

Final-commit CI passed: Windows run 40018711697; Ubuntu run 40018711693.
Its historical archived audit compared all 89 entries, zero OCR skips,
with exactly the three accepted B3 differences (SBTi, R00077, R00112).
That historical comparison exits 1 for those intentional differences;
it does not mean the new candidate baseline failed. The new v0.2.0
baseline passed all 186 entries at 009948d; only report/log files changed
between that commit and the tag. Full outputs and the accepted changes are
in REPORT-v0.2.0-rc.md and tests/audits/.

## Published asset

[Release workflow 40020542297](https://github.com/GalBlatman/markerlite/actions/runs/40020542297)
passed, including the tag/version check and bundled VERSION check.
[Release v0.2.0](https://github.com/GalBlatman/markerlite/releases/tag/v0.2.0)
is published, not draft or prerelease; the live latest-release API returns
v0.2.0. The release body exactly matches tools/release_notes.py's output:
the v0.2.0 CHANGELOG section plus the standard Windows download instructions.

Downloaded markerlite-windows.zip: 94,921,158 bytes. SHA-256:

```
615ae7e2de75cc807f73689dc887db3b1bd8021b2d978f30ef3d8582b7a8f712
```

This equals the asset's GitHub digest and the release build log's digest.
Every archive entry was checked: no markerlite-diag.txt. Diagnostics created
by the following local check exist only in the temporary extracted folder.

## Published exe and installed tag

The actual published zip was extracted into an isolated Windows temporary
folder. Its exe --diag completed successfully; its first line is exactly
`markerlite 0.2.0`. The real exe window-title smoke test passed with exactly
`markerlite 0.2.0`, then terminated and waited for its process.

A clean WSL environment installed git+https://github.com/GalBlatman/markerlite.git@v0.2.0
using requirements-lock.txt constraints. Installed CLI --version reports
0.2.0. hard.pdf converts successfully in both modes: default output has the
`grids disabled; text kept as prose` marker and no HTML table; --grids output
has the ruling-line grid marker and a grid. No corpus document was used for
these smoke tests.

The installed tag's real, unmocked update function queried the live latest
release and returned `You're up to date`, with no release-navigation URL.
The final published exe's Help-menu click is not certified by that function
check: this session has no node_repl tool required by the computer-use skill.
The owner has been asked to verify Help → Check for updates in the downloaded
exe. No fake dialog, substituted response, or claimed menu screenshot.

## Follow-up documentation

CLAUDE.md identifies v0.2.0 as the current published release; AGENTS.md is
regenerated. The backlog records the 16 CI OCR skips from differing runner
Tesseract versions. Future options: pin Tesseract in CI, or per-version OCR
baselines. Neither is implemented; matching-engine WSL passed without skips.
The release tag remains on 00514b4; this documentation follows on main.
