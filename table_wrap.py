"""Compatibility imports for markerlite's wrapped-cell recovery."""

from markerlite.table_wrap import (  # noqa: F401
    _html_words,
    _ruled_bounds,
    _words,
    recover_wrapped_lines,
)

__all__ = ["recover_wrapped_lines"]
