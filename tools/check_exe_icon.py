#!/usr/bin/env python3
"""Assert that a Windows executable embeds every payload from icon.ico."""

from __future__ import annotations

import argparse
import pathlib
import struct

import pefile


def ico_payloads(path: pathlib.Path) -> list[bytes]:
    data = path.read_bytes()
    _reserved, kind, count = struct.unpack_from("<HHH", data)
    if kind != 1:
        raise ValueError(f"{path} is not an icon file")
    payloads = []
    for index in range(count):
        size, offset = struct.unpack_from("<II", data, 6 + index * 16 + 8)
        payloads.append(data[offset : offset + size])
    return payloads


def exe_payloads(path: pathlib.Path) -> list[bytes]:
    pe = pefile.PE(str(path))
    resources = pe.DIRECTORY_ENTRY_RESOURCE.entries
    icons = next(
        entry for entry in resources if entry.id == pefile.RESOURCE_TYPE["RT_ICON"]
    )
    payloads = []
    for icon in icons.directory.entries:
        for language in icon.directory.entries:
            item = language.data.struct
            payloads.append(pe.get_data(item.OffsetToData, item.Size))
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=pathlib.Path)
    parser.add_argument("ico", type=pathlib.Path)
    args = parser.parse_args()
    expected = ico_payloads(args.ico)
    actual = exe_payloads(args.exe)
    missing = [payload for payload in expected if payload not in actual]
    if missing or len(actual) != len(expected):
        print(
            f"FAIL: exe has {len(actual)} icon payloads; "
            f"ico has {len(expected)}; missing={len(missing)}"
        )
        return 1
    print(f"OK: all {len(expected)} icon payloads match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
