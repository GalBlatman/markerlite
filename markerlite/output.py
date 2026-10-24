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
import tempfile
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
        """Back up the complete old set before publishing any staged output.

        A failed backup or swap restores all previous targets, including files
        already swapped. A failed restore retains its backup for recovery.
        """
        order = [s for s in self._staged if s[2]] + [
            s for s in self._staged if not s[2]
        ]
        order = [s for s in order if s[0].exists()]
        if not order:
            self._staged.clear()
            return
        backup_dir = pathlib.Path(
            tempfile.mkdtemp(prefix=".markerlite-backup-", dir=self.outdir)
        )
        backups = []
        installed = []
        try:
            for index, (_part, final, _is_dir) in enumerate(order):
                if final.exists() or final.is_symlink():
                    backup = backup_dir / str(index)
                    backups.append((backup, final))
                    os.replace(final, backup)
            for part, final, _is_dir in order:
                installed.append(final)
                os.replace(part, final)
        except BaseException:
            for final in reversed(installed):
                _remove(final)
            try:
                for backup, final in reversed(backups):
                    if backup.exists() or backup.is_symlink():
                        os.replace(backup, final)
            except BaseException as exc:
                self.discard()
                raise RuntimeError(
                    f"output rollback failed; previous output retained in {backup_dir}"
                ) from exc
            self.discard()
            _remove(backup_dir)
            raise
        _remove(backup_dir)
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


def write_text_atomic(path: pathlib.Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``path`` through ``<path>.part`` and a rename (apply-math and
    apply-figures rewrite a Markdown file in place)."""
    path = pathlib.Path(path)
    output = Output(path.parent)
    try:
        output.file(path.name).write_text(text, encoding=encoding)
        output.commit()
    except BaseException:
        output.discard()
        raise


def target(out, name: str, is_dir: bool) -> pathlib.Path:
    """The physical path for output ``name`` under ``out``, which is an
    :class:`Output` or a plain folder."""
    if isinstance(out, Output):
        return out.folder(name) if is_dir else out.file(name)
    return pathlib.Path(out) / name
