"""Atomic output: nothing a conversion writes is visible until all of it is.

Every output file is written as ``<name>.part`` in the output folder and
renamed into place only when the conversion succeeds; every output folder
(``<stem>_images``, ``<stem>_math``, ``<stem>_figures``) is built as
``<name>.part`` and swapped in the same way. A conversion that fails or is
cancelled leaves no ``.part`` behind and the previous complete output
intact, so a half-written Markdown file never replaces a good one.

Markdown links and manifests always name the final folders: the writers
ask :meth:`Output.folder` for where to put a file and use the name they
asked for in links.
"""

from __future__ import annotations

import os
import pathlib
import shutil
from typing import List, Tuple

PART = ".part"


class Output:
    """The staged outputs of one conversion into ``outdir``."""

    def __init__(self, outdir: pathlib.Path):
        self.outdir = pathlib.Path(outdir)
        self._staged: List[Tuple[pathlib.Path, pathlib.Path, bool]] = []

    def _stage(self, name: str, is_dir: bool) -> pathlib.Path:
        final = self.outdir / name
        part = self.outdir / (name + PART)
        for staged, _final, _is_dir in self._staged:
            if staged == part:
                return part
        # A .part left by a killed process is never anyone's output.
        _remove(part)
        self._staged.append((part, final, is_dir))
        return part

    def file(self, name: str) -> pathlib.Path:
        """Where to write the output file ``name`` until commit."""
        return self._stage(name, is_dir=False)

    def folder(self, name: str) -> pathlib.Path:
        """Where to build the output folder ``name`` until commit. The
        writer creates it when it has something to put in it."""
        return self._stage(name, is_dir=True)

    def commit(self) -> None:
        """Rename every staged output into place: folders first, files in
        the order they were staged, so the Markdown that links to a folder
        appears last."""
        order = [s for s in self._staged if s[2]] + [
            s for s in self._staged if not s[2]
        ]
        for part, final, is_dir in order:
            if not part.exists():
                continue  # nothing was written under this name
            if is_dir:
                _swap_dir(part, final)
            else:
                os.replace(part, final)
        self._staged.clear()

    def discard(self) -> None:
        """Delete every staged output; the previous outputs stay as they were."""
        for part, _final, _is_dir in self._staged:
            _remove(part)
        self._staged.clear()


def _remove(path: pathlib.Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists() or path.is_symlink():
        try:
            path.unlink()
        except OSError:
            pass


def _swap_dir(part: pathlib.Path, final: pathlib.Path) -> None:
    """Replace folder ``final`` with ``part``. A directory cannot be renamed
    over an existing one on Windows, so the old folder steps aside first and
    is deleted only once the new one is in place."""
    if not final.exists():
        os.replace(part, final)
        return
    old = final.with_name(final.name + ".old")
    n = 0
    while old.exists():
        n += 1
        old = final.with_name(f"{final.name}.old{n}")
    os.replace(final, old)
    try:
        os.replace(part, final)
    except OSError:
        os.replace(old, final)  # put the complete old output back
        raise
    shutil.rmtree(old, ignore_errors=True)


def write_text_atomic(path: pathlib.Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``path`` through ``<path>.part`` and a rename (apply-math and
    apply-figures rewrite a Markdown file in place)."""
    path = pathlib.Path(path)
    part = path.with_name(path.name + PART)
    try:
        part.write_text(text, encoding=encoding)
        os.replace(part, path)
    except BaseException:
        _remove(part)
        raise


def target(out, name: str, is_dir: bool) -> pathlib.Path:
    """The physical path for output ``name`` under ``out``, which is an
    :class:`Output` or a plain folder."""
    if isinstance(out, Output):
        return out.folder(name) if is_dir else out.file(name)
    return pathlib.Path(out) / name
