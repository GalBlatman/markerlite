"""Cancel: a cooperative token checked between pages and files, a running
Tesseract killed at once, and no output left by the cancelled file."""

import pathlib
import subprocess
import sys
import threading
import time

import pytest

import markerlite
from markerlite import api, cli, extraction
from markerlite.cancel import Cancelled, CancelToken
from markerlite.gui_logic import finish_status, run_batch, snapshot_options

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF = ROOT / "tests" / "fixtures" / "hard.pdf"


def _snapshot(folder):
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


def test_running_subprocess_is_killed_on_cancel():
    token = CancelToken()
    threading.Timer(0.3, token.cancel).start()
    started = time.monotonic()
    with pytest.raises(Cancelled):
        token.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=60)
    assert time.monotonic() - started < 5


def test_cancel_between_pages_leaves_previous_output(tmp_path, monkeypatch):
    markerlite.convert(PDF, tmp_path)
    before = _snapshot(tmp_path)
    token = CancelToken()
    real = extraction.extract_page
    seen = []

    def page_then_cancel(page, idx, *args, **kwargs):
        seen.append(idx)
        if idx == 0:
            token.cancel()  # the user clicks Cancel during page 1
        return real(page, idx, *args, **kwargs)

    monkeypatch.setattr(api, "extract_page", page_then_cancel)
    with pytest.raises(Cancelled):
        markerlite.convert(PDF, tmp_path, cancel=token)
    assert seen == [0]  # stopped before page 2
    assert _snapshot(tmp_path) == before
    assert not [p for p in tmp_path.iterdir() if ".part" in p.name]


def test_ocr_page_is_cancelled_mid_tesseract(monkeypatch):
    """A cancel during OCR kills Tesseract and is not mistaken for an OCR
    failure (which _ocr_page would turn into 'no text')."""
    import pymupdf

    token = CancelToken()
    monkeypatch.setattr(extraction, "discover_tesseract", lambda: sys.executable)
    sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
    real_run = token.run
    monkeypatch.setattr(token, "run", lambda args, **kw: real_run(sleeper, **kw))
    doc = pymupdf.open()
    doc.new_page()
    threading.Timer(0.3, token.cancel).start()
    started = time.monotonic()
    with pytest.raises(Cancelled):
        extraction._ocr_page(doc[0], 0, cancel=token)
    assert time.monotonic() - started < 5


def test_batch_cancel_keeps_finished_and_skips_rest(tmp_path):
    files = [tmp_path / f"{n}.pdf" for n in "abc"]
    token = CancelToken()
    events, logged = [], []

    def fake_convert(pdf, outdir, *args, cancel=None):
        if pdf.name == "b.pdf":
            token.cancel()
            cancel.check()
        md = outdir / (pdf.stem + ".md")
        md.write_text("x", encoding="utf-8")
        return md, {"stats": {"pages": 1}}

    opts = snapshot_options(False, False, False, "fixed", str(tmp_path))
    outcome = run_batch(
        files,
        opts,
        fake_convert,
        token,
        events.append,
        lambda d, line: logged.append(line),
    )
    assert [p.name for p in outcome["done"]] == ["a.pdf"]
    assert [p.name for p in outcome["cancelled"]] == ["b.pdf"]
    assert [p.name for p in outcome["skipped"]] == ["c.pdf"]
    assert any(line.startswith("b.pdf: CANCELLED") for line in logged)
    assert any(line.startswith("c.pdf: SKIPPED") for line in logged)
    assert ("skipped", str(files[2])) in events
    assert (
        finish_status(outcome, "summary")
        == "Cancelled \u00b7 1 converted \u00b7 1 skipped"
    )
    assert finish_status({"done": files}, "summary") == "summary"


def test_cli_ctrl_c_names_cancelled_and_skipped(tmp_path, monkeypatch, capsys):
    def interrupted(path, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "convert", interrupted)
    monkeypatch.setattr(
        sys, "argv", ["markerlite", "a.pdf", "b.pdf", "-o", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 130
    err = capsys.readouterr().err
    assert "cancelled: a.pdf" in err and "skipped: b.pdf" in err


def test_cancel_token_is_not_swallowed_by_except_exception():
    assert not issubclass(Cancelled, Exception)
    with pytest.raises(subprocess.TimeoutExpired):
        CancelToken().run(
            [sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2
        )


def test_cancel_feedback_is_immediate_and_sticky():
    from markerlite.gui_logic import CANCELLING, busy_status, cancel_pressed

    assert cancel_pressed(True) == (True, CANCELLING, "disabled")
    assert cancel_pressed(False) == (False, None, None)
    # a progress event that arrives after the press does not overwrite it
    assert busy_status("a.pdf", cancelling=True) == CANCELLING
    assert busy_status("a.pdf", cancelling=False) == "Converting a.pdf"
