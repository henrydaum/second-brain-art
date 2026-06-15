from pipeline.database import DEFAULT_USER_ID, Database
from plugins.frontends.frontend_web import WebFrontend
from runtime.conversation_runtime import ConversationRuntime


def test_web_conversation_is_created_for_bound_user(tmp_path):
    db = Database(str(tmp_path / "web.db"))
    runtime = ConversationRuntime(db=db, services={}, config={"agent_profiles": {}})
    frontend = WebFrontend()
    frontend.bind(runtime, None, {})
    key = frontend.session_key("browser")

    frontend._ensure_conversation(key)

    cid = runtime.sessions[key].conversation_id
    row = db.get_conversation(cid)
    assert row["user_id"] == frontend.default_user_id
    assert row["user_id"] != DEFAULT_USER_ID
    assert runtime.session_user_id(key) == frontend.default_user_id
    frontend.unbind()
