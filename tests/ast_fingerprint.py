#!/usr/bin/env python3
"""Hash function ASTs while ignoring file and line locations."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib


def fingerprints(paths: list[pathlib.Path]) -> dict[str, str]:
    result = {}

    def walk(body, parents=()):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = ".".join((*parents, node.name))
                digest = hashlib.sha256(
                    ast.dump(node, include_attributes=False).encode("utf-8")
                ).hexdigest()
                if name in result and result[name] != digest:
                    raise ValueError(f"conflicting function name: {name}")
                result[name] = digest
                walk(node.body, (*parents, node.name))
            elif isinstance(node, ast.ClassDef):
                walk(node.body, (*parents, node.name))

    for path in paths:
        walk(ast.parse(path.read_text(encoding="utf-8")).body)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=pathlib.Path)
    parser.add_argument("--compare", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    current = fingerprints(args.paths)
    if args.output:
        args.output.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if not args.compare:
        print(json.dumps(current, indent=2, sort_keys=True))
        return 0
    before = json.loads(args.compare.read_text(encoding="utf-8"))
    names = sorted(set(before) | set(current))
    mismatches = [
        (name, before.get(name), current.get(name))
        for name in names
        if before.get(name) != current.get(name)
    ]
    if mismatches:
        for name, old, new in mismatches:
            print(f"MISMATCH {name} {old or 'missing'} {new or 'missing'}")
        return 1
    print(f"all {len(current)} function AST fingerprints match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
