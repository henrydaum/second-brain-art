"""execute_technique: run a canvas technique (agent-facing adapter onto the new CanvasRuntime).

Routes the agent's "add a layer + render" request through the new canvas
state machine: ``context.canvas.for_session(...)`` → ``handle_action("add_layer", ...)``
→ ``render_canvas(...)``. Old layered-canvas / cs.enact("run_technique") path is
gone from this tool; the conversation-side canvas system remains in place
but is no longer driven from here.
"""

from __future__ import annotations

import logging

from events.event_bus import bus
from events.event_channels import CANVAS_CHANGED
from canvas.render import bus_progress, render_canvas
from plugins.BaseTool import BaseTool, ToolResult
from plugins.techniques.helpers import technique_error_log, technique_scoring
from plugins.techniques.helpers.technique_runner import TechniqueRunError

logger = logging.getLogger("TechniqueTools")

# Tools that let the agent author new techniques (as opposed to just searching,
# reading, or executing existing ones). Gated separately in the workflow prompt.
_TECHNIQUE_AUTHORING_TOOLS = ("create_technique", "update_technique", "delete_technique")


def _has_tool(registry, name: str) -> bool:
    """Return whether ``name`` is a tool visible to the current session."""
    if registry is None:
        return False
    try:
        return any(getattr(t, "name", "") == name for t in registry._visible_tools())
    except Exception:
        return name in (getattr(registry, "tools", {}) or {})


def _technique_authoring_tools(registry) -> list[str]:
    """Authoring tool names currently in scope, in a stable order."""
    return [name for name in _TECHNIQUE_AUTHORING_TOOLS if _has_tool(registry, name)]


def _technique_workflow(registry) -> str:
    can_search = _has_tool(registry, "search_techniques")
    can_read = _has_tool(registry, "read_technique")
    can_guide = _has_tool(registry, "read_technique_guide")
    can_execute = _has_tool(registry, "execute_technique")
    author_tools = _technique_authoring_tools(registry)
    lines = ["""## Canvas technique workflow
Your name is Second Brain. Second Brain makes generative, algorithmic art — not literal illustration. Treat every canvas request as a prompt for an abstract algorithmic interpretation, not a representational depiction. For example, a "flower" is a Vogel spiral of palette-blended cells, not stacked petals. Second Brain plays to their strengths: math, code, and procedural generation.

Workflow:
"""]
    steps = []
    if can_search:
        steps.append("Call `search_techniques` with the subject. Search returns only techniques visible to this session; when community techniques are disabled, community-authored techniques will not appear.")
    if can_read:
        steps.append("Use `read_technique` to inspect a promising hit or clone a nearby technique when authoring is enabled.")
    if can_execute:
        steps.append("If a strong match exists, call `execute_technique`.")
    if author_tools:
        steps.append(f"Technique authoring is enabled for this session. You may use the available authoring tools: {', '.join(author_tools)}.")
        if can_guide:
            steps.append("Call `read_technique_guide` once per session before the first new technique if you need the template, helpers, or composition guidance.")
        if _has_tool(registry, "create_technique"):
            steps.append("If no match exists, pick an algorithmic technique before writing code, then call `create_technique` with a complete BaseTechnique class and execute the returned slug.")
    else:
        steps.append("Technique authoring is not enabled for this session. Do not say you can create, edit, or delete techniques; work with search, read, execution, and layer controls that are available.")
    lines.extend(f"{i}. {s}" for i, s in enumerate(steps, 1))
    lines.append("""

Techniques (good-for hints — formulas live in the encyclopedia above):
- vogel_spiral -- flowers, sunflowers, galaxies, star fields, seed-pod patterns
- fbm / value_noise -- clouds, terrain, atmospheres, fog, organic textures, ray fields
- radial_falloff -- suns, moons, vignettes, centered radiant subjects
- flow_field -- wind, hair, currents, smoke, motion, fur, weather
- lindenmayer + turtle_segments -- trees, branches, ferns, coral, lightning, roots
- voronoi_assign -- cells, cracked glass, abstract portraits, stained glass, basalt
- wave_field -- water, ripples, sound, interference, reflections
- attractor_points (de Jong, Clifford) -- organic abstract forms, smoke, dust
- jittered_grid -- skylines, crowds, forests-from-far, tiled mosaics
- rule_of_thirds -- horizon and focal-point placement for any composition

When in doubt, prefer noise, gradients, and procedural patterns in palette tones over explicit shapes. Compose multiple techniques (e.g. fbm background + vogel foreground + radial vignette) rather than drawing literal features.

The canvas is not always square — the user can pick an aspect ratio. When authoring, read `canvas.width`/`canvas.height` and center on `(width/2, height/2)` rather than assuming a single side length; `canvas.size` is just the long edge. Each rendered snapshot reports the live `width`×`height`, so check it when planning a composition.

You always follow through. If you start authoring, updating, testing, or executing techniques, keep using the available tools until the canvas is rendered, a tool limit blocks you, or a specific user decision is required. Do not stop on status-only text like "let me try", "fixing now", or "I'll test this"; pair that narration with the actual tool call in the same response. Iteration is normal, but save "you can always say what to change" for the final rendered result.""")
    return "\n".join(lines)


class ExecuteTechnique(BaseTool):
	name = "execute_technique"
	description = "Run a stored technique on the canvas by slug. Backgrounds start a new chain from a blank palette-background image; filters read the current canvas and replace it; objects read the current canvas and alpha-composite an overlay onto it. filters and objects both require something already on the canvas. Chain cap is 6 layers (1 background + up to 5 filters/objects). Errors include a hint line — read it and adjust before retrying."
	max_calls = 6
	parameters = {
		"type": "object",
		"properties": {"slug": {"type": "string"}, "params": {"type": "object", "default": {}}},
		"required": ["slug"],
	}
	config_settings = [
		("Technique Execution Timeout (s)", "technique_timeout_s",
		 "Wall-clock seconds before a single technique run is killed. Raise for heavy compute; lower to catch runaway loops sooner.",
		 30,
		 {"type": "slider", "range": (5, 180, 35), "is_float": False}),
		("Maximum Canvas Layers", "max_canvas_layers",
		 "Most layers a single canvas may hold (1 background + the rest filters/objects). Backgrounds replace layer 0 and never count against the cap.",
		 6,
		 {"type": "integer"}),
	]

	def agent_prompt_for(self, ctx) -> str:
		"""Canvas technique workflow guidance, gated on which technique tools are in scope."""
		return _technique_workflow(getattr(ctx, "tool_registry", None))

	def run(self, context, **kwargs) -> ToolResult:
		session_key = getattr(context, "session_key", None) or "local"
		slug = str(kwargs.get("slug") or "")
		params = dict(kwargs.get("params") or {})

		canvas_rt = getattr(context, "canvas", None)
		technique_registry = getattr(context, "technique_registry", None)
		if canvas_rt is None:
			return ToolResult.failed("canvas runtime not available on context")
		if technique_registry is None:
			return ToolResult.failed("technique registry not available on context")

		# Resolve the technique so we know its kind (background vs filter) and
		# can fail fast on unknown slugs before mutating state.
		technique_inst = technique_registry.get(slug)
		if technique_inst is None:
			return ToolResult.failed(f"unknown technique: '{slug}'")
		kind = getattr(technique_inst, "kind", None) or "background"

		cs = canvas_rt.for_session(session_key)

		# A filter or object with an empty chain has nothing to read — refuse
		# before we corrupt state. Mirrors the TechniqueRunError the renderer
		# would raise, but at the action layer.
		if kind in ("filter", "object") and not cs.canvas.layers:
			return ToolResult.failed(
				f"{kind.title()} techniques require a background first. "
				f"Run a background technique before this {kind}."
			)

		db = getattr(context, "db", None)
		try:
			max_layers = int((getattr(context, "config", {}) or {}).get("max_canvas_layers") or 6)
			add_result, render_result = canvas_rt.render_actions(
				cs.canvas_id,
				[("add_layer", {"technique_slug": slug, "kind": kind, "controls": params, "max_layers": max_layers})],
				lambda state: render_canvas(
					state,
					technique_loader=technique_registry.get_record,
					db=db,
					on_event=bus_progress(getattr(context, "session_key", None), float((getattr(context, "config", {}) or {}).get("technique_timeout_s") or 30)),
					worker_pool=(getattr(context, "services", None) or {}).get("technique_worker_pool"),
				),
			)
			if not add_result.ok:
				msg = add_result.error.message if add_result.error else "add_layer failed"
				technique_error_log.record_error(db, slug, params, {"error_type": "AddLayerFailed", "message": msg}, session_key=session_key)
				return ToolResult.failed(msg)
		except TechniqueRunError as e:
			diag = dict(getattr(e, "diagnostic", None) or {"error_type": "TechniqueRunError", "message": str(e)})
			technique_error_log.record_error(getattr(context, "db", None), slug, params, diag, session_key=session_key)
			return ToolResult.failed(str(e))
		except Exception as e:
			logger.exception("execute_technique render crashed: slug=%s", slug)
			return ToolResult.failed(str(e))

		snap = {
			"path": str(render_result.image_path),
			"chain": list(cs.canvas.layers),
			"size": cs.canvas.size,
			"width": cs.canvas.width,
			"height": cs.canvas.height,
			"palette_id": cs.canvas.palette_id,
			"canvas_id": cs.canvas_id,
			"pool_hash": render_result.pool_hash,
			"seed": render_result.seed,
			"cache_hit": render_result.cache_hit,
			"warning": render_result.warning,
			"warning_message": render_result.warning_message,
		}
		technique_scoring.record_event(
			getattr(context, "db", None), "generate", snap["chain"], snap["path"],
		)
		bus.emit(CANVAS_CHANGED, {"session_key": session_key, "action": "add_layer", "canvas": snap})
		layer_index = len(cs.canvas.layers)  # newly-added layer's 1-based position
		total = len(cs.canvas.layers)
		cache_tag = ", cached" if render_result.cache_hit else ""
		summary = (
			f"Executed {kind} technique '{slug}' (layer {layer_index}/{total}, "
			f"seed={render_result.seed}{cache_tag})."
		)
		if render_result.warning:
			summary += (
				f"\nWARNING ({render_result.warning}): "
				f"{render_result.warning_message or 'post-render validator flagged this layer'}"
			)
		return ToolResult(
			data={"canvas": snap, "chain": snap["chain"]},
			llm_summary=summary,
			attachment_paths=[snap["path"]],
		)
