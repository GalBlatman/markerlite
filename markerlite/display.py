"""Safe display of names and messages that come from outside.

A PDF's file name, and the text of an exception raised while converting it,
can hold control characters. Written raw into the run log, a console or a
status line, a line feed forges a new log line, a carriage return overwrites
the one before it, and an escape sequence recolours or rewrites a terminal.
``safe_display`` renders such characters visibly, so what is displayed is
always one inert line. Paths used for file-system work stay as they are;
only the text shown to a person goes through here.
"""

from __future__ import annotations

import unicodedata

_NAMED = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
# Characters that end or reorder a displayed line without being C0 or C1
# controls: line and paragraph separators, and the bidirectional overrides
# and isolates that can make a name read differently from what it is.
_EXTRA = set("  ‪‫‬‭‮⁦⁧⁨⁩")


def _escape(ch: str) -> str:
    if ch in _NAMED:
        return _NAMED[ch]
    code = ord(ch)
    return f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}"


def safe_display(value: object) -> str:
    """``value`` as one printable line: every C0 and C1 control character
    (including DEL), line and paragraph separator and bidirectional control
    is replaced by a visible escape such as ``\\n`` or ``\\x1b``."""
    text = str(value)
    return "".join(
        _escape(ch) if unicodedata.category(ch) == "Cc" or ch in _EXTRA else ch
        for ch in text
    )
