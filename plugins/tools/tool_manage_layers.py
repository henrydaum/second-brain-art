"""manage_layers: agent-side control over the canvas chain (delete/move/clear).

Routes through the new CanvasRuntime: ``context.canvas.handle_action(...)``
for the mutation, then ``render_canvas(...)`` to refresh the image (unless
the action cleared the chain, in which case there's nothing to render).
"""

from __future__ import annotations

import logging

from events.event_bus import bus
from events.event_channels import CANVAS_CHANGED
from canvas.render import bus_progress, render_canvas
from plugins.BaseTool import BaseTool, ToolResult

logger = logging.getLogger("ManageLayers")

# Aspect-ratio presets the user picks from in the web UI (Settings). Stored in
# landscape (w >= h) form; flip the two terms for portrait. Kept in sync with
# ASPECT_PRESETS in plugins/frontends/web/app.js. set_aspect also accepts any
# positive ratio_w:ratio_h, but these are the standard choices to offer.
ASPECT_PRESETS = ["1:1", "5:4", "4:3", "3:2", "16:10", "16:9", "25:16", "21:9"]


def _snap_after(cs, render_result) -> dict:
	"""Build the canvas-dict shape the frontend (and old callers) expect."""
	if render_result is None:
		return {
			"path": None,
			"chain": list(cs.canvas.layers),
			"size": cs.canvas.size,
			"width": cs.canvas.width,
			"height": cs.canvas.height,
			"palette_id": cs.canvas.palette_id,
			"canvas_id": cs.canvas_id,
		}
	return {
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
	}


def _enact_and_render(context, action_type: str, payload: dict) -> ToolResult:
	"""Mutate via context.canvas, then render if the chain still has layers."""
	session_key = getattr(context, "session_key", None) or "local"
	canvas_rt = getattr(context, "canvas", None)
	technique_registry = getattr(context, "technique_registry", None)
	if canvas_rt is None:
		return ToolResult.failed("canvas runtime not available on context")
	cs = canvas_rt.for_session(session_key)
	db = getattr(context, "db", None)
	def rerender(state):
		if not state.canvas.layers:
			return None
		if technique_registry is None:
			raise RuntimeError("technique registry not available; cannot re-render")
		return render_canvas(
			state,
			technique_loader=technique_registry.get_record,
			db=db,
			on_event=bus_progress(getattr(context, "session_key", None), float((getattr(context, "config", {}) or {}).get("technique_timeout_s") or 30)),
			worker_pool=(getattr(context, "services", None) or {}).get("technique_worker_pool"),
		)
	try:
		result, render_result = canvas_rt.render_actions(
			cs.canvas_id, [(action_type, payload)], rerender,
		)
	except Exception as e:
		logger.exception("manage_layers render crashed: action=%s", action_type)
		return ToolResult.failed(str(e))
	if not result.ok:
		msg = result.error.message if result.error else (result.message or f"{action_type} failed")
		return ToolResult.failed(msg)
	if not cs.canvas.layers:
		snap = _snap_after(cs, None)
		if session_key:
			bus.emit(CANVAS_CHANGED, {"session_key": session_key, "action": action_type})
		return ToolResult(data={"canvas": snap, "chain": []}, llm_summary="")

	snap = _snap_after(cs, render_result)
	if session_key:
		bus.emit(CANVAS_CHANGED, {"session_key": session_key, "action": action_type, "canvas": snap})
	return ToolResult(
		data={"canvas": snap, "chain": snap["chain"]},
		llm_summary="",
		attachment_paths=[snap["path"]],
	)


class ManageLayers(BaseTool):
	name = "manage_layers"
	description = (
		"Edit the canvas layer chain (max 6 layers: 1 background + up to 5 "
		"filters/objects). action=delete removes layer at chain_index (0 is the "
		"background — deleting it clears the canvas). action=move reorders from "
		"from_index to to_index; layer 0 must stay a background. action=clear "
		"wipes the canvas entirely. action=set_control updates one control on "
		"one layer (chain_index, name, value) — use read_technique on the layer's "
		"slug first to see the control declarations (Slider min/max/step, Enum "
		"options, Bool, Pan, Text) which are the source of truth for valid "
		"names and values. action=set_aspect reshapes the whole canvas to the "
		"aspect ratio ratio_w:ratio_h — the same control the user has. It is "
		"long-edge anchored: the longer side keeps the current resolution and "
		"the shorter is scaled down, so picking a ratio re-renders the existing "
		"chain at the new shape. Pass ratio_w>ratio_h for landscape, "
		"ratio_w<ratio_h for portrait, ratio_w==ratio_h for square. Common "
		"presets (the ones the user sees): 1:1, 5:4, 4:3, 3:2, 16:10, 16:9, "
		"25:16, 21:9 (flip the two numbers for portrait). Surviving layers are "
		"replayed end-to-end to rebuild the image."
	)
	max_calls = 4
	parameters = {
		"type": "object",
		"properties": {
			"action": {"type": "string", "enum": ["delete", "move", "clear", "set_control", "set_aspect"]},
			"chain_index": {"type": "integer", "description": "Target layer index for delete or set_control."},
			"from_index": {"type": "integer", "description": "Source layer index for move."},
			"to_index": {"type": "integer", "description": "Destination layer index for move."},
			"name": {"type": "string", "description": "Control name for set_control — must match a control declared on the layer's technique (see read_technique)."},
			"value": {"description": "New control value for set_control. Type depends on the control (number for Slider, string for Enum/Text/Palette, bool for Bool)."},
			"ratio_w": {"type": "number", "description": "Aspect-ratio width term for set_aspect (e.g. 16 in 16:9). Must be > 0."},
			"ratio_h": {"type": "number", "description": "Aspect-ratio height term for set_aspect (e.g. 9 in 16:9). Must be > 0."},
		},
		"required": ["action"],
	}

	def agent_prompt_for(self, ctx) -> str:
		"""Tell the agent the available aspect-ratio presets and palette catalog."""
		lines = [
			"## Canvas aspect ratio",
			"Call `manage_layers` with `action=set_aspect`, `ratio_w=<w>`, `ratio_h=<h>` "
			"to reshape the canvas (long-edge anchored — re-renders the current chain at "
			"the new shape). Use `ratio_w>ratio_h` for landscape, `ratio_w<ratio_h` for "
			"portrait, equal for square. The standard presets the user picks from: "
			+ ", ".join(ASPECT_PRESETS)
			+ " (flip the two numbers for portrait, e.g. 9:16). Any positive ratio also "
			"works if the user asks for something custom.",
			"",
		]
		try:
			from plugins.helpers.palettes import list_palettes
			palettes = list_palettes()
		except Exception:
			palettes = []
		if palettes:
			lines += [
				"## Available palettes",
				"The canvas has a fixed catalog of palettes. To change the palette on a layer, the layer's technique must expose a `palette` control (use read_technique on its slug to check — look for `palette = Palette()`). Then call `manage_layers` with `action=set_control`, `chain_index=<n>`, `name=\"palette\"`, `value=\"<id>\"`. Use the `id` slug below, not the display name. Match a user's color request (e.g. \"red/orange/yellow\", \"neon\", \"earthy\") to the closest palette by its kind and hex colors.",
				"",
				"Format: `id (Name) — kind: primary secondary tertiary accent / bg background`",
				"",
			]
			for p in palettes:
				lines.append(f"- {p.id} ({p.name}) — {p.kind}: {p.primary} {p.secondary} {p.tertiary} {p.accent} / bg {p.background}")
		return "\n".join(lines)

	def run(self, context, **kwargs) -> ToolResult:
		"""Dispatch on the ``action`` argument to the matching canvas action."""
		action = str(kwargs.get("action") or "").lower()
		if action == "clear":
			result = _enact_and_render(context, "clear", {})
			if result.data:
				result.llm_summary = "Cleared the canvas."
			return result
		if action == "delete":
			idx = int(kwargs.get("chain_index", -1))
			result = _enact_and_render(context, "remove_layer", {"chain_index": idx})
			if result.data:
				result.llm_summary = f"Deleted layer {idx}."
			return result
		if action == "move":
			fi = int(kwargs.get("from_index", -1))
			ti = int(kwargs.get("to_index", -1))
			result = _enact_and_render(context, "move_layer", {"from_index": fi, "to_index": ti})
			if result.data:
				result.llm_summary = f"Moved layer {fi} to position {ti}."
			return result
		if action == "set_control":
			idx = int(kwargs.get("chain_index", -1))
			name = str(kwargs.get("name") or "")
			value = kwargs.get("value")
			result = _enact_and_render(context, "set_control", {"chain_index": idx, "name": name, "value": value})
			if result.data:
				result.llm_summary = f"Set {name}={value!r} on layer {idx}."
			return result
		if action == "set_aspect":
			try:
				rw = float(kwargs.get("ratio_w"))
				rh = float(kwargs.get("ratio_h"))
			except (TypeError, ValueError):
				return ToolResult.failed("set_aspect requires numeric 'ratio_w' and 'ratio_h'.")
			result = _enact_and_render(context, "set_aspect", {"ratio_w": rw, "ratio_h": rh})
			if result.data:
				canvas = result.data.get("canvas") or {}
				w, h = canvas.get("width"), canvas.get("height")
				result.llm_summary = f"Set canvas aspect to {rw:g}:{rh:g} ({w}x{h})."
			return result
		return ToolResult.failed(f"Unknown action '{action}'. Use delete, move, clear, set_control, or set_aspect.")
