"""Canvas dataclass — pure data + pure mutations.

Backs ``CanvasState``. No frontend, no PIL, no subprocess, no disk I/O,
no rendering, no seed handling. The state-machine wrapper in
``canvas/state.py`` owns event history and dispatch; this file owns the
shape and the small set of legal in-place mutations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from plugins.helpers.palettes import DEFAULT_PALETTE_ID

DEFAULT_SIZE = 1024
MIN_SIZE = 256
MAX_SIZE = 2048
MAX_CHAIN_LENGTH = 6


@dataclass
class Canvas:
	"""One canvas: palette, dimensions (width × height), ordered layer chain.

	Resolution is **long-edge anchored**: an aspect ratio is realized by
	keeping the longer dimension at the base size and shrinking the shorter
	one. A square is simply ``width == height``.
	"""

	width: int = DEFAULT_SIZE
	height: int = DEFAULT_SIZE
	palette_id: str = DEFAULT_PALETTE_ID
	layers: list[dict] = field(default_factory=list)

	@property
	def size(self) -> int:
		"""Legacy scalar: the long edge. Kept for callers that predate
		non-square canvases; new code should read ``width``/``height``."""
		return max(int(self.width), int(self.height))

	# ── serialization ────────────────────────────────────────────────

	def to_dict(self) -> dict[str, Any]:
		"""Serialize to a JSON-safe dict."""
		return {
			"width": self.width,
			"height": self.height,
			"palette_id": self.palette_id,
			"layers": list(self.layers),
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any] | None) -> "Canvas":
		"""Restore from a dict produced by ``to_dict``."""
		if not data:
			return cls()
		# Tolerate a legacy square ``size`` key (→ width == height == size).
		legacy = int(data.get("size") or DEFAULT_SIZE)
		return cls(
			width=int(data.get("width") or legacy),
			height=int(data.get("height") or legacy),
			palette_id=str(data.get("palette_id") or DEFAULT_PALETTE_ID),
			# Tolerate the old ``last_chain`` key during the rename window.
			layers=list(data.get("layers") or data.get("last_chain") or []),
		)

	# ── pure mutations ───────────────────────────────────────────────

	def apply_palette(self, palette_id: str) -> None:
		"""Set the canvas palette and propagate to layers that declared one."""
		self.palette_id = palette_id
		for step in self.layers:
			if "palette" in (step.get("controls") or {}):
				step["controls"]["palette"] = palette_id

	def apply_control(self, chain_index: int, name: str, value: Any) -> None:
		"""Update one control on one layer.

		A per-layer palette override stays local to its layer; it must not
		mutate the canvas-wide ``palette_id`` (that is what ``apply_palette``
		is for). Otherwise every layer still resolving against the canvas
		fallback would silently follow one layer's edit.
		"""
		if not (0 <= chain_index < len(self.layers)):
			raise ValueError(f"chain_index {chain_index} out of range (len={len(self.layers)})")
		step = dict(self.layers[chain_index])
		controls = dict(step.get("controls") or {})
		controls[name] = value
		step["controls"] = controls
		self.layers[chain_index] = step

	def delete_entry(self, chain_index: int) -> None:
		"""Remove the layer at ``chain_index``."""
		if not (0 <= chain_index < len(self.layers)):
			raise ValueError(f"chain_index {chain_index} out of range (len={len(self.layers)})")
		del self.layers[chain_index]

	def move_entry(self, from_index: int, to_index: int) -> None:
		"""Reorder layers. Layer 0 must remain a background."""
		n = len(self.layers)
		if not (0 <= from_index < n) or not (0 <= to_index < n):
			raise ValueError(f"index out of range (len={n})")
		if from_index != to_index and (from_index == 0 or to_index == 0):
			raise ValueError("layer 0 must be a background; reorder rejected")
		step = self.layers.pop(from_index)
		self.layers.insert(to_index, step)

	def push_chain_entry(self, entry: dict) -> None:
		"""Append a filter/object, or replace layer 0 with a new background.

		Background swaps preserve any filters/objects layered on top — only
		index 0 changes. Index 0 is always a background (enforced by
		``move_entry``), so this is safe.
		"""
		kind = entry.get("kind")
		if kind == "background":
			if self.layers:
				self.layers[0] = dict(entry)
			else:
				self.layers = [dict(entry)]
		elif kind in ("filter", "object"):
			self.layers = list(self.layers) + [dict(entry)]
		else:
			raise ValueError(f"unknown chain entry kind: {kind!r}")

	def set_size(self, size: int) -> None:
		"""Set a square canvas, each edge clamped to MIN_SIZE..MAX_SIZE."""
		edge = max(MIN_SIZE, min(MAX_SIZE, int(size)))
		self.width = self.height = edge

	def set_dimensions(self, width: int, height: int) -> None:
		"""Set canvas width and height independently, each clamped to MIN/MAX."""
		self.width = max(MIN_SIZE, min(MAX_SIZE, int(width)))
		self.height = max(MIN_SIZE, min(MAX_SIZE, int(height)))

	def reset(self) -> None:
		"""Clear the chain. Palette and dimensions preserved."""
		self.layers = []
