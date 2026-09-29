#!/usr/bin/env python3
"""Compatibility entry point for source checkouts.

The implementation lives in the ``markerlite`` package. Existing commands
(``python markerlite.py``) and imports continue to use the same public API.
"""

from markerlite import *  # noqa: F401,F403
from markerlite.cli import main


if __name__ == "__main__":
    main()
