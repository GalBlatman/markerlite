"""Static sanity check for markerlite_gui.py - run before committing.

Catches editing the App class and losing a method that __init__ (or anything
else) still calls, which otherwise only shows up as an AttributeError when a
person launches the window. Pure AST and regex: no display, no Tk, no
dependencies, so it runs anywhere in well under a second.

    python check_gui.py
"""
import ast
import pathlib
import re
import sys

src = (pathlib.Path(__file__).resolve().parent / "markerlite_gui.py").read_text(encoding="utf-8")
tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App")
methods = {m.name for m in cls.body if isinstance(m, ast.FunctionDef)}

# Every `self.<name>(` is a call on the App instance. Tk variables are used as
# `self.var.get()` - attribute access followed by a call - which this pattern
# deliberately does not match.
called = set(re.findall(r"self\.(_?[A-Za-z_]+)\(", src))
missing = sorted(called - methods)
if missing:
    print("FAIL markerlite_gui.py: App calls methods that do not exist:", ", ".join(missing))
    sys.exit(1)
print(f"OK: App defines {len(methods)} methods; all {len(called)} self-calls resolve.")
