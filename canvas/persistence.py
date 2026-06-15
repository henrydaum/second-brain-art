"""SQLite persistence for CanvasState.

One row per canvas in ``canvas_states`` (canvas_id PK, state_json blob,
updated_at). State_json is the output of ``CanvasState.to_dict()``, so any
future change to the dataclass shape only needs to keep that contract
backward-compatible.

The canvas_id is also the share-link id — /share/{canvas_id} resolves
through the same primary key.
"""

from __future__ import annotations

import json
import logging
import time

from canvas.state import CanvasState

logger = logging.getLogger("CanvasPersistence")


def ensure_schema(db) -> None:
    """Create the canvas/art tables if they don't exist.

    Canvas owns its own schema (the kernel DB knows nothing about it) — this is
    called once when the CanvasRuntime is constructed with a db. Covers the
    canvas editing/persistence tables, the public pool-hash content store, the
    user→canvas action ledger (saves/shares/etc.), and the technique popularity
    counters fed by those actions.
    """
    if db is None:
        return
    with db.lock:
        db.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS canvas_states (
                canvas_id  TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS canvas_pools (
                pool_hash  TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_canvas_actions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL,
                pool_hash TEXT NOT NULL,
                action    TEXT NOT NULL,
                ts        REAL NOT NULL,
                meta_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_uca_action_pool
                ON user_canvas_actions (action, pool_hash, ts);
            CREATE INDEX IF NOT EXISTS idx_uca_user_action
                ON user_canvas_actions (user_id, action, ts);

            CREATE TABLE IF NOT EXISTS technique_scores (
                slug        TEXT PRIMARY KEY,
                shares      INTEGER NOT NULL DEFAULT 0,
                downloads   INTEGER NOT NULL DEFAULT 0,
                remixes     INTEGER NOT NULL DEFAULT 0,
                saves       INTEGER NOT NULL DEFAULT 0,
                link_opens  INTEGER NOT NULL DEFAULT 0,
                generations INTEGER NOT NULL DEFAULT 0,
                updated_at  REAL
            );

            CREATE TABLE IF NOT EXISTS technique_events (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ts             REAL NOT NULL,
                kind           TEXT NOT NULL,
                slug           TEXT NOT NULL,
                image_path     TEXT,
                chain_position TEXT,
                weight         REAL NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_technique_events_slug_kind
                ON technique_events (slug, kind, ts);
            CREATE INDEX IF NOT EXISTS idx_technique_events_image_kind
                ON technique_events (image_path, kind, ts);
            """
        )
        try:
            db.conn.execute("ALTER TABLE technique_scores ADD COLUMN link_opens INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        db.conn.commit()
    logger.info("canvas schema ensured")


def save(db, cs: CanvasState) -> None:
	"""Upsert one CanvasState into the ``canvas_states`` table."""
	now = time.time()
	payload = json.dumps(cs.to_dict(), separators=(",", ":"))
	with db.lock:
		db.conn.execute(
			"INSERT INTO canvas_states (canvas_id, state_json, updated_at) "
			"VALUES (?, ?, ?) "
			"ON CONFLICT(canvas_id) DO UPDATE SET "
			"  state_json = excluded.state_json, updated_at = excluded.updated_at",
			(cs.canvas_id, payload, now),
		)
		db.conn.commit()
	logger.debug("save canvas_id=%s", cs.canvas_id)


def load(db, canvas_id: str) -> CanvasState | None:
	"""Fetch and rehydrate one CanvasState, or None if not found."""
	with db.lock:
		row = db.conn.execute(
			"SELECT state_json FROM canvas_states WHERE canvas_id = ?",
			(canvas_id,),
		).fetchone()
	if not row:
		return None
	try:
		data = json.loads(row["state_json"])
	except (TypeError, ValueError):
		logger.exception("canvas_states.state_json invalid for id=%s", canvas_id)
		return None
	return CanvasState.from_dict(data)


def list_ids(db) -> list[str]:
	"""All persisted canvas ids, newest-updated first."""
	with db.lock:
		rows = db.conn.execute(
			"SELECT canvas_id FROM canvas_states ORDER BY updated_at DESC"
		).fetchall()
	return [r["canvas_id"] for r in rows]


def delete(db, canvas_id: str) -> None:
	"""Remove one canvas from persistence. No-op if absent."""
	with db.lock:
		db.conn.execute("DELETE FROM canvas_states WHERE canvas_id = ?", (canvas_id,))
		db.conn.commit()
	logger.debug("delete canvas_id=%s", canvas_id)


# =================================================================
# canvas_pools — public content identity, keyed by pool_hash
# =================================================================

def save_pool(db, *, pool_hash: str, state: dict) -> None:
	"""Idempotent insert into canvas_pools keyed by pool_hash.

	``state`` is the canvas portion (size / palette_id / layers) — the
	render-determining state, not the full CanvasState envelope. Repeat
	calls with the same hash are no-ops (INSERT OR IGNORE).
	"""
	now = time.time()
	payload = json.dumps(state, separators=(",", ":"))
	with db.lock:
		db.conn.execute(
			"INSERT OR IGNORE INTO canvas_pools (pool_hash, state_json, created_at) "
			"VALUES (?, ?, ?)",
			(pool_hash, payload, now),
		)
		db.conn.commit()
	logger.debug("save_pool pool_hash=%s", pool_hash)


def load_pool(db, pool_hash: str) -> dict | None:
	"""Return the canvas-state dict associated with ``pool_hash`` or None."""
	with db.lock:
		row = db.conn.execute(
			"SELECT state_json FROM canvas_pools WHERE pool_hash = ?",
			(pool_hash,),
		).fetchone()
	if not row:
		return None
	try:
		return json.loads(row["state_json"])
	except (TypeError, ValueError):
		logger.exception("canvas_pools.state_json invalid for pool_hash=%s", pool_hash)
		return None
