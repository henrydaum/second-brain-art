from canvas.runtime import CanvasRuntime
from pipeline.database import Database


def test_canvas_runtime_ensures_schema(tmp_path):
    db = Database(str(tmp_path / "canvas.db"))
    runtime = CanvasRuntime(db)

    canvas_id = runtime.create_canvas()

    row = db.conn.execute(
        "SELECT state_json FROM canvas_states WHERE canvas_id = ?",
        (canvas_id,),
    ).fetchone()
    assert row is not None

    db.conn.execute(
        "INSERT INTO technique_events (ts, kind, slug, image_path, chain_position, weight) "
        "VALUES (1, 'generate', 'demo', NULL, 'background', 1.0)"
    )
    db.conn.execute(
        "INSERT INTO technique_scores (slug, link_opens, updated_at) VALUES ('demo', 1, 1)"
    )
    db.conn.commit()
