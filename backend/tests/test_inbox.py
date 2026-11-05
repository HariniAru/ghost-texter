import asyncio
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger, MacMessages
from ghost.workflow import summarize


@pytest.fixture
def workspace(tmp_path):
    messenger = DemoMessenger()
    app = create_app(Settings(data_dir=tmp_path, api_token="test-token", _env_file=None), messenger)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger


def test_inbox_and_summary_are_read_only_and_rejection_preserves_unread(workspace):
    client, messenger = workspace
    before = dict(messenger.unread_messages)
    rows = client.get("/api/inbox").json()
    assert {r["recipient"] for r in rows} == set(messenger.history)
    assert all(r["unread_count"] == 1 for r in rows)
    detail = client.get("/api/conversation", params={"recipient": rows[0]["recipient"]})
    assert detail.status_code == 200
    assert detail.json()["summary_kind"] == "excerpt"
    assert "coffee tomorrow" in detail.json()["summary"]
    assert client.get("/api/drafts").json() == []
    d = client.post("/api/drafts", json={"recipient": rows[0]["recipient"]}).json()
    assert client.post(f"/api/drafts/{d['id']}/reject", json={"version": 1}).status_code == 200
    assert client.get("/api/inbox").json() == rows
    assert messenger.unread_messages == before
    assert messenger.sent == []


def test_inbox_filters_read_conversations(workspace):
    client, messenger = workspace
    messenger.unread_messages["alex@example.test"] = []
    assert [r["recipient"] for r in client.get("/api/inbox").json()] == ["maya@example.test"]
    messenger.unread_messages.clear()
    assert client.get("/api/inbox").json() == []


def test_summary_cache_refreshes_only_when_context_changes(workspace, monkeypatch):
    client, messenger = workspace
    summary = Mock(return_value={"summary": "A coffee invitation.", "summary_kind": "ai"})
    monkeypatch.setattr("ghost.main.summarize", summary)
    for _ in range(2):
        assert (
            client.get("/api/conversation", params={"recipient": "alex@example.test"}).status_code
            == 200
        )
    assert summary.call_count == 1
    messenger.history["alex@example.test"] += "\nAlex: how about 11?"
    assert (
        client.get("/api/conversation", params={"recipient": "alex@example.test"}).status_code
        == 200
    )
    assert summary.call_count == 2
    assert not messenger.sent


def test_inbox_auth_scope_and_failure_are_explicit(workspace):
    client, messenger = workspace
    assert client.get("/api/inbox", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert (
        client.get("/api/conversation", params={"recipient": "unknown@example.test"}).status_code
        == 422
    )

    async def denied(*args):
        raise RuntimeError("Permission denied")

    messenger.unread = denied
    assert client.get("/api/inbox").status_code == 502
    messenger.read = denied
    assert (
        client.get("/api/conversation", params={"recipient": "alex@example.test"}).status_code
        == 502
    )
    assert not messenger.sent


def test_live_inbox_uses_only_allowlisted_recipients(tmp_path):
    messenger = DemoMessenger()
    settings = Settings(
        data_dir=tmp_path,
        api_token="test-token",
        mode="imessage",
        allowed_recipients=["maya@example.test"],
        _env_file=None,
    )
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        assert [r["recipient"] for r in client.get("/api/inbox").json()] == ["maya@example.test"]
        assert (
            client.get("/api/conversation", params={"recipient": "alex@example.test"}).status_code
            == 403
        )
    assert not messenger.sent


def test_mcp_unread_scope_preview_and_capped_count():
    adapter = MacMessages(Settings(_env_file=None))
    calls = []

    async def call(name, arguments):
        calls.append((name, arguments))
        if arguments["chat_id"] == "read@example.test":
            return "<untrusted-mcp-output>\nNo messages found in the specified time period.\n</untrusted-mcp-output>"
        return "\n".join(f"[2026-10-17 10:00:00] Alex: message {i}" for i in range(50))

    adapter.call = call
    rows = asyncio.run(adapter.unread(["alex@example.test", "read@example.test"]))
    assert len(rows) == 1
    assert rows[0].unread_count == 50 and rows[0].count_capped
    assert rows[0].preview.endswith("message 0")
    assert all(name == "tool_get_recent_messages" and args["unread_only"] for name, args in calls)
    assert all("contact" not in args for _, args in calls)


def test_mcp_unread_errors_do_not_look_like_empty_inbox():
    adapter = MacMessages(Settings(_env_file=None))

    async def call(*args):
        return "Error accessing messages: denied"

    adapter.call = call
    with pytest.raises(RuntimeError):
        asyncio.run(adapter.unread(["alex@example.test"]))


def test_ai_summary_uses_structured_output_without_tools(monkeypatch):
    model = Mock()
    model.with_structured_output.return_value.invoke.return_value.text = "Alex asks about coffee."
    factory = Mock(return_value=model)
    monkeypatch.setattr("ghost.workflow.ChatOpenAI", factory)
    result = summarize(
        "Alex: coffee tomorrow?",
        Settings(llm=True, openai_api_key="synthetic-test-key", _env_file=None),
    )
    assert result == {"summary": "Alex asks about coffee.", "summary_kind": "ai"}
    assert (
        "coffee tomorrow?"
        in model.with_structured_output.return_value.invoke.call_args.args[0][1][1]
    )
    model.bind_tools.assert_not_called()


def test_incompatible_connector_error_reaches_dashboard(workspace):
    from ghost.messaging import MessagingError

    client, messenger = workspace

    async def incompatible(*args):
        raise MessagingError("Installed Messages MCP is incompatible. Use the pinned revision.")

    messenger.unread = incompatible
    response = client.get("/api/inbox")
    assert response.status_code == 502
    assert "incompatible" in response.json()["detail"]
