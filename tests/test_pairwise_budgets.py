"""Pairwise analyses stop before work and respond inside their loops."""

from types import SimpleNamespace

import pytest

from markerlite import figures, gate, processors
from markerlite.cancel import Cancelled, CancelToken
from markerlite.model import Page
from markerlite.raster_budget import checked, document_raster_budget, flush_limits


def test_checked_iterator_notices_cancel_during_iteration():
    token = CancelToken()
    with document_raster_budget(token):
        values = checked(range(10))
        assert next(values) == 0
        token.cancel()
        with pytest.raises(Cancelled):
            next(values)


def test_image_placement_cap_avoids_pair_matching(monkeypatch):
    monkeypatch.setattr(figures, "IMAGE_PLACEMENT_MAX_CANDIDATES", 1)
    pm = SimpleNamespace(
        number=0,
        get_images=lambda **kw: [(), ()],
        get_image_info=lambda: [{"bbox": (1, 2, 3, 4)}],
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    with document_raster_budget() as state:
        result = figures._image_infos(pm)
        flush_limits(state, [page])
    assert result[0]["xref"] == 0
    assert page.limit_events[0]["limit"] == "image_placement_candidates"


def test_diagram_cap_does_not_enter_pair_loop(monkeypatch):
    monkeypatch.setattr(gate, "GATE_MAX_BOX_CANDIDATES", 1)
    monkeypatch.setattr(
        gate, "_boxes_touch", lambda *args: pytest.fail("must not pair")
    )
    graphics = {"h": [], "v": [], "curves": [], "boxes": [(1, 1, 3, 3), (5, 5, 7, 7)]}
    result = gate.evaluate(
        graphics,
        (0, 0, 100, 100),
        [[1, 5]],
        ["alpha beta"],
        "<table><tr><td>alpha</td><td>beta</td></tr></table>",
    )
    page = Page(page_idx=0, width=100, height=100, blocks=[])
    gate.record(page, "test", (0, 0, 100, 100), result)
    assert not result["passed"] and "box_candidates" in result["failed"]
    assert page.limit_events[0]["limit"] == "diagram_box_candidates"


def test_furniture_cap_keeps_every_block(monkeypatch):
    monkeypatch.setattr(processors, "FURNITURE_MAX_CANDIDATES", 1)
    blocks = [
        SimpleNamespace(ignore_for_output=False),
        SimpleNamespace(ignore_for_output=False),
    ]
    page = Page(page_idx=0, width=100, height=100, blocks=blocks)
    processors.proc_ignore_common([page])
    processors.proc_marginalia([page])
    assert not any(b.ignore_for_output for b in blocks)
    assert {r["limit"] for r in page.limit_events} == {"furniture_candidates"}
