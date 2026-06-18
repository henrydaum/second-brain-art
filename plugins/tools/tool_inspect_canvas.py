"""inspect_canvas: stage the current canvas as native vision input for the agent.

The agent otherwise generates blind — ``execute_technique`` shows the rendered
PNG to the human frontend (via ``ToolResult.attachment_paths``) but the model
only receives a text summary. This tool renders the *current* canvas (a cache
hit when nothing changed since the last technique) and stages it through the
mid-turn attachment hook (``runtime.add_turn_attachment``), so the model can
actually see its own work on the next turn and decide what to do next.

Opt-in by design: ``execute_technique`` is unchanged, and inspection only
happens when the agent deliberately calls this tool — keeping native-image
token cost under the agent's control.
"""

from __future__ import annotations

import logging

from attachments import parse_attachment
from canvas.render import render_canvas
from plugins.BaseTool import BaseTool, ToolResult
from plugins.techniques.helpers.technique_runner import TechniqueRunError

logger = logging.getLogger("TechniqueTools")


def _model_supports_image(services: dict) -> bool:
    """Whether the active LLM can natively process image input.

    Mirrors ``agent/system_prompt.py:_model_status``: the image modality counts
    only when the backend advertises the capability *and* lists it among its
    native attachment modalities.
    """
    llm = (services or {}).get("llm")
    if not llm:
        return False
    target = getattr(llm, "active", None) or llm
    caps = getattr(target, "capabilities", {}) or {}
    native = set(getattr(target, "native_attachment_modalities", set()) or set())
    return bool(caps.get("image") and "image" in native)


class InspectCanvas(BaseTool):
    name = "inspect_canvas"
    description = (
        "Render the current canvas and attach it to your next message so you can "
        "visually inspect your own work — composition, colour, layer interaction — "
        "before deciding the next technique. Takes no arguments; shows the canvas "
        "exactly as it currently stands."
    )
    max_calls = 3
    background_safe = True
    parameters = {"type": "object", "properties": {}}

    def agent_prompt_for(self, ctx) -> str:
        """Advertise the tool only when the active model can actually see images."""
        if not _model_supports_image(getattr(ctx, "services", None) or {}):
            return ""
        return (
            "## Inspecting the canvas\n"
            "Call `inspect_canvas` whenever you want to actually see the current "
            "canvas with your own vision before choosing the next technique — to "
            "judge composition, colour, and how layers interact. The rendered image "
            "is attached to your next message. Use it to evaluate and iterate; don't "
            "guess at the result from text summaries alone."
        )

    def run(self, context, **kwargs) -> ToolResult:
        session_key = getattr(context, "session_key", None) or "local"

        if not _model_supports_image(getattr(context, "services", None) or {}):
            return ToolResult.failed(
                "The active model has no native image input, so it cannot see the "
                "canvas. Switch to a vision-capable model (see /llm) or rely on "
                "technique summaries."
            )

        canvas_rt = getattr(context, "canvas", None)
        technique_registry = getattr(context, "technique_registry", None)
        if canvas_rt is None:
            return ToolResult.failed("canvas runtime not available on context")
        if technique_registry is None:
            return ToolResult.failed("technique registry not available on context")

        cs = canvas_rt.current_for_session(session_key)
        if cs is None or not cs.canvas.layers:
            return ToolResult.failed(
                "The canvas is empty — run a background technique first, then inspect."
            )

        try:
            render_result = render_canvas(
                cs,
                technique_loader=technique_registry.get_record,
                db=getattr(context, "db", None),
                worker_pool=(getattr(context, "services", None) or {}).get("technique_worker_pool"),
            )
        except TechniqueRunError as e:
            return ToolResult.failed(str(e))
        except Exception as e:
            logger.exception("inspect_canvas render crashed")
            return ToolResult.failed(str(e))

        runtime = getattr(context, "runtime", None)
        attachment = parse_attachment(
            str(render_result.image_path), file_name="canvas.png",
            services=getattr(context, "services", None),
        )
        staged = runtime.add_turn_attachment(session_key, attachment) if runtime else False
        if not staged:
            return ToolResult.failed("Could not attach the canvas to this session.")

        layers = len(cs.canvas.layers)
        return ToolResult(
            llm_summary=(
                f"Current canvas attached for inspection ({layers} layer(s), "
                f"seed={render_result.seed}). It is included with your next message — "
                "look, then decide."
            ),
            attachment_paths=[str(render_result.image_path)],
        )
