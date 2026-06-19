"""Stable layer ids: minted at creation, preserved across mutations, excluded
from the render cache key, and backfilled for layers that predate them.

These ids let the web frontend track a layer by identity (e.g. which sliders
sweep in a video) instead of by its shifting chain position."""

from canvas.canvas import Canvas
from canvas.render import pool_hash
from canvas.state import CanvasState
from canvas.action_map import create_canvas_action


def _add(cs, slug, kind):
    result = create_canvas_action(cs, "add_layer", {"technique_slug": slug, "kind": kind}).enact()
    assert result.ok, result
    return cs.canvas.layers[-1]


def test_add_layer_mints_id():
    cs = CanvasState(canvas=Canvas())
    layer = _add(cs, "color_field", "background")
    assert layer.get("id")


def test_same_technique_gets_distinct_ids():
    cs = CanvasState(canvas=Canvas())
    _add(cs, "color_field", "background")
    a = _add(cs, "noise", "filter")
    b = _add(cs, "noise", "filter")  # same technique, different layer
    assert a["id"] != b["id"]


def test_id_stable_across_apply_control():
    cs = CanvasState(canvas=Canvas())
    layer = _add(cs, "color_field", "background")
    before = layer["id"]
    create_canvas_action(cs, "set_control", {"chain_index": 0, "name": "scale", "value": 2}).enact()
    assert cs.canvas.layers[0]["id"] == before


def test_id_stable_across_move():
    cs = CanvasState(canvas=Canvas())
    _add(cs, "color_field", "background")
    mover = _add(cs, "noise", "filter")   # index 1
    _add(cs, "noise", "filter")            # index 2
    moved_id = mover["id"]
    create_canvas_action(cs, "move_layer", {"from_index": 1, "to_index": 2}).enact()
    assert cs.canvas.layers[2]["id"] == moved_id  # followed its layer to the new slot


def test_pool_hash_ignores_layer_id():
    """Two otherwise-identical canvases that differ only by layer id must share a
    render cache folder — ids are per-canvas identity, not content identity."""
    base = {"slug": "y", "kind": "background", "controls": {}}
    a = Canvas(width=1024, height=576, layers=[{**base, "id": "AAAA"}])
    b = Canvas(width=1024, height=576, layers=[{**base, "id": "BBBB"}])
    assert pool_hash(a) == pool_hash(b)


def test_from_dict_backfills_missing_ids():
    c = Canvas.from_dict({"layers": [{"slug": "x", "kind": "background", "controls": {}}]})
    assert c.layers[0].get("id")


def test_from_dict_preserves_existing_ids():
    c = Canvas.from_dict({"layers": [{"id": "keepme", "slug": "x", "kind": "background", "controls": {}}]})
    assert c.layers[0]["id"] == "keepme"
