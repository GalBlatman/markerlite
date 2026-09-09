"""Generate AGENTS.md from the canonical CLAUDE.md instructions."""

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "CLAUDE.md").read_bytes()
    title, separator, body = source.partition(b"\n")
    title = title.replace(b"for Claude Code", b"for coding agents")
    header = b"<!-- GENERATED from CLAUDE.md by tools/sync_agents.py - do not edit -->\n"
    (root / "AGENTS.md").write_bytes(header + title + separator + body)


if __name__ == "__main__":
    main()
