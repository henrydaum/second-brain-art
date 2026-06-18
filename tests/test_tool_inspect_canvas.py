"""Contract tests for the built-in inspect_canvas tool.

Verifies the tool renders the current canvas and stages it as an image
attachment for the next LLM call via the mid-turn attachment hook, and that it
refuses cleanly when there's nothing to inspect or the model can't see images.
"""

from __future__ import annotations

from types import SimpleNamespace

import plugins.tools.tool_inspect_canvas as mod
from plugins.tools.tool_inspect_canvas import InspectCanvas
from runtime.hooks import HookRegistry


class _Parser:
    def get_modality(self, ext):
        return "image" if ext == ".png" else "binary"

    def parse(self, path, modality, config=None):
        return None


class _Runtime:
    def __init__(self):
        self.hooks = HookRegistry()
        self.sessions = {"s": SimpleNamespace(key="s")}

    def add_turn_attachment(self, session_key, attachment):
        return self.hooks.stage_attachment(self.sessions.get(session_key), attachment)


def _llm(image=True):
    return SimpleNamespace(
        active=None,
        capabilities={"image": image},
        native_attachment_modalities={"image"} if image else set(),
    )


def _canvas(layers):
    cs = SimpleNamespace(canvas=SimpleNamespace(layers=list(layers)))
    return SimpleNamespace(current_for_session=lambda key: cs)


def _context(runtime, *, layers=(1,), image=True):
    return SimpleNamespace(
        runtime=runtime,
        session_key="s",
        db=None,
        services={"parser": _Parser(), "llm": _llm(image), "technique_worker_pool": None},
        canvas=_canvas(layers),
        technique_registry=SimpleNamespace(get_record=lambda slug: None),
    )


def _stub_render(monkeypatch, tmp_path, seed=7):
    img = tmp_path / "canvas.png"
    img.write_bytes(b"png")
    monkeypatch.setattr(mod, "render_canvas", lambda cs, **kw: SimpleNamespace(image_path=img, seed=seed))
    return img


def test_inspect_canvas_stages_image_for_current_session(monkeypatch, tmp_path):
    img = _stub_render(monkeypatch, tmp_path)
    runtime = _Runtime()
    result = InspectCanvas().run(_context(runtime))
    staged = runtime.hooks.drain_attachments(runtime.sessions["s"])

    assert result.success
    assert str(img) in result.attachment_paths
    assert len(staged) == 1
    assert staged[0].file_name == "canvas.png"
    assert staged[0].modality == "image"


def test_inspect_canvas_refuses_empty_canvas(monkeypatch, tmp_path):
    _stub_render(monkeypatch, tmp_path)
    runtime = _Runtime()
    result = InspectCanvas().run(_context(runtime, layers=()))

    assert not result.success
    assert "empty" in result.error.lower()
    assert runtime.hooks.drain_attachments(runtime.sessions["s"]) == []


def test_inspect_canvas_refuses_without_vision(monkeypatch, tmp_path):
    _stub_render(monkeypatch, tmp_path)
    runtime = _Runtime()
    result = InspectCanvas().run(_context(runtime, image=False))

    assert not result.success
    assert "image" in result.error.lower()
    assert runtime.hooks.drain_attachments(runtime.sessions["s"]) == []


def test_agent_prompt_gated_on_image_capability():
    tool = InspectCanvas()
    assert tool.agent_prompt_for(SimpleNamespace(services={"llm": _llm(True)}))
    assert tool.agent_prompt_for(SimpleNamespace(services={"llm": _llm(False)})) == ""
