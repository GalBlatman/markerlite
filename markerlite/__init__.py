"""Offline, deterministic PDF-to-Markdown conversion."""

from . import model as model
from . import extraction as extraction
from . import classification as classification
from . import render as render_module
from . import tables as tables
from . import processors as processors

# Provenance suppression lives with extraction but uses the one suppression
# recorder owned by processors. Binding it after both modules load avoids a
# circular import without changing either moved function body.
extraction._suppress_block = processors._suppress_block

from . import figures as figures
from . import stats as stats
from . import api as api
from . import cli as cli
from . import table_wrap as table_wrap

_MODULES = (
    model, extraction, classification, render_module, tables, processors,
    figures, stats, api, cli, table_wrap,
)

# Preserve the practical v0.1.14 module surface, including private helpers
# used by the regression and audit scripts. Public stability is required for
# convert(); these re-exports also make the mechanical split low-risk.
for _module in _MODULES:
    for _name in dir(_module):
        if not _name.startswith("__"):
            globals()[_name] = getattr(_module, _name)

del _module, _name
