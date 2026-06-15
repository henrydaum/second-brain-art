"""Aspect-ratio support: pool hash identity, dimension model, set_aspect action,
and a non-square render smoke test through the technique sandbox."""
import tempfile
from pathlib import Path

from PIL import Image

from canvas.canvas import Canvas, DEFAULT_SIZE
from canvas.render import pool_hash
from canvas.state import CanvasState
from canvas.action_map import create_canvas_action


# ── dimension model ──────────────────────────────────────────────────

def test_default_canvas_is_square():
    c = Canvas()
    assert c.width == c.height == DEFAULT_SIZE
    assert c.size == DEFAULT_SIZE  # long-edge alias


def test_size_is_long_edge():
    assert Canvas(width=1024, height=576).size == 1024
    assert Canvas(width=576, height=1024).size == 1024


def test_from_dict_tolerates_legacy_size_key():
    c = Canvas.from_dict({"size": 800, "palette_id": "x", "layers": []})
    assert c.width == 800 and c.height == 800


def test_roundtrip_preserves_dimensions():
    c = Canvas(width=1024, height=576)
    assert Canvas.from_dict(c.to_dict()).width == 1024
    assert Canvas.from_dict(c.to_dict()).height == 576


def test_set_dimensions_clamps():
    c = Canvas()
    c.set_dimensions(50, 99999)
    from canvas.canvas import MIN_SIZE, MAX_SIZE
    assert c.width == MIN_SIZE and c.height == MAX_SIZE


# ── pool hash identity ───────────────────────────────────────────────

def test_pool_hash_depends_on_aspect():
    layers = [{"slug": "x", "kind": "background", "controls": {}}]
    square = Canvas(width=1024, height=1024, layers=layers)
    wide = Canvas(width=1024, height=576, layers=layers)
    tall = Canvas(width=576, height=1024, layers=layers)
    hashes = {pool_hash(square), pool_hash(wide), pool_hash(tall)}
    assert len(hashes) == 3  # every aspect is its own cache folder


def test_pool_hash_stable_for_same_dims():
    a = Canvas(width=1024, height=576, layers=[{"slug": "y", "kind": "background", "controls": {}}])
    b = Canvas(width=1024, height=576, layers=[{"slug": "y", "kind": "background", "controls": {}}])
    assert pool_hash(a) == pool_hash(b)


# ── set_aspect action ────────────────────────────────────────────────

def test_set_aspect_landscape_anchors_long_edge():
    cs = CanvasState(canvas=Canvas())  # 1024 square
    action = create_canvas_action(cs, "set_aspect", {"ratio_w": 16, "ratio_h": 9})
    result = action.enact()
    assert result.ok
    assert cs.canvas.width == 1024
    assert cs.canvas.height == round(1024 * 9 / 16)  # 576


def test_set_aspect_portrait_anchors_long_edge():
    cs = CanvasState(canvas=Canvas())
    create_canvas_action(cs, "set_aspect", {"ratio_w": 9, "ratio_h": 16}).enact()
    assert cs.canvas.height == 1024
    assert cs.canvas.width == round(1024 * 9 / 16)


def test_set_aspect_rejects_bad_ratio():
    cs = CanvasState(canvas=Canvas())
    assert not create_canvas_action(cs, "set_aspect", {"ratio_w": 0, "ratio_h": 9}).enact().ok


# ── non-square render smoke (subprocess sandbox) ─────────────────────

def _record_for(stem: str):
    from plugins.BaseTechnique import BaseTechnique
    from plugins.techniques.helpers.technique_store import to_technique_record
    path = Path(__file__).resolve().parents[1] / "plugins" / "techniques" / f"technique_{stem}.py"
    ns = {"__name__": "__test__"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns, ns)
    inst = next(v() for v in ns.values()
                if isinstance(v, type) and v is not BaseTechnique and issubclass(v, BaseTechnique))
    inst._source_path = str(path)
    return to_technique_record(inst)


def test_non_square_render_outputs_exact_dimensions():
    from plugins.helpers.palettes import get_palette, DEFAULT_PALETTE_ID
    from plugins.techniques.helpers.technique_runner import run_technique

    W, H = 1024, 576
    palette = get_palette(DEFAULT_PALETTE_ID)
    rec = _record_for("color_field")  # canvas.new()-based background
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "bg.png"
        run_technique(rec, params={}, palette=palette, width=W, height=H,
                      seed=1, input_image_path=None, output_image_path=out,
                      timeout_s=60.0, memory_mb=1024, worker_pool=None)
        assert Image.open(out).size == (W, H)
