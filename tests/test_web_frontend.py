import http.client
import threading
from pathlib import Path

from pipeline.database import DEFAULT_USER_ID, Database
from plugins.frontends.frontend_web import WEB_AUTHOR_PROFILE, WEB_PROFILE, WebFrontend, _Handler, _Server
from runtime.conversation_runtime import ConversationRuntime


def _frontend(tmp_path):
    db = Database(str(tmp_path / "web.db"))
    runtime = ConversationRuntime(db=db, services={}, config={"agent_profiles": {}})
    frontend = WebFrontend()
    frontend.bind(runtime, None, {})
    return db, runtime, frontend


def test_web_guest_identity_binds_through_kernel_and_is_stable(tmp_path):
    db, runtime, frontend = _frontend(tmp_path)
    key = frontend.session_key("browser")

    frontend._ensure_conversation("browser")
    first_uid = runtime.session_user_id(key)
    frontend._ensure_conversation("browser")

    cid = runtime.sessions[key].conversation_id
    row = db.get_conversation(cid)
    user = db.get_user(first_uid)
    assert row["user_id"] == first_uid
    assert first_uid != DEFAULT_USER_ID
    assert runtime.session_user_id(key) == first_uid
    assert user["frontend"] == "web"
    assert user["external_id"] == frontend._browser_external_id("browser")
    assert user["user_type"] == "guest"
    frontend.unbind()


def test_web_settings_persist_per_browser_guest_and_apply_scope(tmp_path):
    db, runtime, frontend = _frontend(tmp_path)

    assert frontend.update_settings("browser-a", {"technique_authoring_enabled": True})["ok"]
    a_key = frontend.session_key("browser-a")
    b_key = frontend.session_key("browser-b")
    frontend._ensure_conversation("browser-a")
    frontend._ensure_conversation("browser-b")

    assert runtime.user_config(a_key)["technique_authoring_enabled"] is True
    assert runtime.user_config(b_key).get("technique_authoring_enabled") is None
    assert runtime.sessions[a_key].active_agent_profile == WEB_AUTHOR_PROFILE
    assert runtime.sessions[b_key].active_agent_profile == WEB_PROFILE
    frontend.unbind()


def test_saved_canvas_uses_kernel_guest_user_and_archive_is_browser_local(tmp_path):
    db, runtime, frontend = _frontend(tmp_path)
    key = frontend.session_key("browser-a")
    image = tmp_path / "saved.png"
    image.write_bytes(b"png")

    class _CanvasRuntime:
        def for_session(self, _key):
            class _State:
                canvas = type("CanvasObj", (), {"layers": [{"technique_slug": "demo"}]})()
            return _State()

    frontend._canvas_runtime = lambda: _CanvasRuntime()
    frontend._new_canvas_snap = lambda _key, **_kw: {"path": str(image), "pool_hash": "abc123"}
    assert frontend.save_canvas("browser-a")[0]["type"] == "saved"

    uid = runtime.session_user_id(key)
    row = db.conn.execute(
        "SELECT user_id, action FROM user_canvas_actions WHERE pool_hash = 'abc123'"
    ).fetchone()
    assert row["user_id"] == str(uid)
    assert row["action"] == "save"
    assert frontend.archive_listing("browser-a")["total"] == 1
    assert frontend.archive_listing("browser-b")["total"] == 0
    frontend.unbind()


def test_account_page_redirects_to_root_and_file_is_gone(tmp_path):
    _db, _runtime, frontend = _frontend(tmp_path)
    server = _Server(("127.0.0.1", 0), _Handler, frontend, max_global=8, max_per_ip=8)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=2)
    try:
        conn.request("GET", "/account")
        res = conn.getresponse()
        assert res.status == 303
        assert res.getheader("Location") == "/"
    finally:
        conn.close()
        server.shutdown()
        server.server_close()
        frontend.unbind()
    assert not (Path(__file__).parents[1] / "plugins/frontends/web/account.html").exists()
