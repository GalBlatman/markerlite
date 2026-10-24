"""Static display-boundary guard, without fake Tk widgets."""

import ast
from pathlib import Path

from markerlite.display import display_text

ROOT = Path(__file__).resolve().parents[1]


def test_multiline_display_escapes_pdf_controls_and_keeps_layout():
    assert (
        display_text("caption\x1b\nsource\u202e\t") == "caption\\x1b\nsource\\u202e\\t"
    )


def test_gui_text_sinks_require_safe_display_funnel():
    tree = ast.parse((ROOT / "markerlite_gui.py").read_text())
    bad = []

    def check(value):
        if isinstance(value, ast.Constant):
            return
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in {"safe_display", "display_text"}
        ):
            return
        bad.append(value.lineno)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg in {"text", "label"}:
                check(keyword.value)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "title" and node.args:
                check(node.args[0])
            if (
                node.func.attr == "insert"
                and len(node.args) >= 2
                and ast.unparse(node.func.value) not in {"sys.path", "self.tree"}
            ):
                check(node.args[1])
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "messagebox"
            ):
                for arg in node.args:
                    check(arg)
    assert bad == [], f"unsafe GUI display at lines {bad}"
