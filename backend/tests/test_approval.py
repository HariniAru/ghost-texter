import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger


@pytest.fixture
def workspace(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", _env_file=None)
    messenger = DemoMessenger()
    app = create_app(settings, messenger)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger, app


def draft(client):
    response = client.post("/api/drafts", json={"recipient": "alex@example.test"})
    assert response.status_code == 200, response.text
    return response.json()


def test_no_send_until_explicit_approval_and_exact_edited_text(workspace):
    client, messenger, app = workspace
    d = draft(client)
    assert not messenger.sent
    edited = client.patch(
        "/api/drafts/" + d["id"],
        json={"version": 1, "text": "hey! can we do 11 instead?"},
    ).json()
    assert not messenger.sent
    assert (
        client.post("/api/drafts/" + d["id"] + "/approve", json={"version": 1}).status_code == 409
    )
    sent = client.post("/api/drafts/" + d["id"] + "/approve", json={"version": edited["version"]})
    assert sent.status_code == 200
    assert messenger.sent == [("alex@example.test", "hey! can we do 11 instead?")]
    assert (
        client.post("/api/drafts/" + d["id"] + "/approve", json={"version": 2}).status_code == 409
    )
    assert len(messenger.sent) == 1
    events = app.state.store.db.execute(
        "SELECT payload FROM events WHERE action='approved'"
    ).fetchone()[0]
    assert "hey! can we do 11 instead?" in events


def test_reject_never_sends(workspace):
    client, messenger, _ = workspace
    d = draft(client)
    assert (
        client.post(f"/api/drafts/{d['id']}/reject", json={"version": 1}).json()["status"]
        == "rejected"
    )
    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 409
    assert messenger.sent == []


def test_conversation_changes_invalidate_approval(workspace):
    client, messenger, _ = workspace
    d = draft(client)
    messenger.history[d["recipient"]] += "\nAlex: actually tomorrow no longer works"
    response = client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1})
    assert response.status_code == 409
    assert client.get("/api/drafts").json()[0]["status"] == "stale"
    assert messenger.sent == []


def test_send_failure_is_not_retryable(workspace):
    client, messenger, _ = workspace
    d = draft(client)

    async def timeout(*args):
        raise TimeoutError("Could have sent before connection failed")

    messenger.send = timeout
    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 502
    assert client.get("/api/drafts").json()[0]["status"] == "uncertain"
    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 409


def test_auth_origin_validation_and_duplicate_drafts(workspace):
    client, _, _ = workspace
    assert client.get("/api/drafts", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert (
        client.post(
            "/api/drafts",
            json={"recipient": "alex@example.test"},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post("/api/drafts", json={"recipient": "somebody@example.test"}).status_code == 422
    )
    d = draft(client)
    assert draft(client)["id"] == d["id"]
    assert (
        client.patch(f"/api/drafts/{d['id']}", json={"version": 1, "text": "  "}).status_code == 422
    )


def test_pending_draft_and_checkpoint_survive_restart(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", _env_file=None)
    with TestClient(create_app(settings)) as first:
        first.headers["Authorization"] = "Bearer test-token"
        d = draft(first)
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as second:
        second.headers["Authorization"] = "Bearer test-token"
        assert second.get("/api/drafts").json()[0]["id"] == d["id"]
        assert second.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 200
        assert len(messenger.sent) == 1


def test_live_send_disabled_even_with_approval(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        api_token="test-token",
        mode="imessage",
        allowed_recipients=["alex@example.test"],
        _env_file=None,
    )
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        d = draft(client)
        assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 403
        assert messenger.sent == []


def test_enabled_live_path_commits_exact_approval_before_fake_dispatch(tmp_path):
    import json
    import sqlite3

    settings = Settings(
        data_dir=tmp_path,
        api_token="test-token",
        mode="imessage",
        allowed_recipients=["alex@example.test"],
        send_enabled=True,
        _env_file=None,
    )
    messenger = DemoMessenger()  # No real connector is instantiated.
    calls = []

    async def send(recipient, text):
        # A separate connection proves intent was committed before external dispatch.
        with sqlite3.connect(tmp_path / "ghost.sqlite") as db:
            status = db.execute("SELECT status FROM drafts").fetchone()[0]
            approval = json.loads(
                db.execute("SELECT payload FROM events WHERE action='approved'").fetchone()[0]
            )
        assert status == "sending"
        assert approval["recipient"] == recipient
        assert approval["text"] == text
        assert approval["version"] == 2
        calls.append((recipient, text))
        return "Synthetic connector acknowledgment"

    messenger.send = send
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        d = draft(client)
        response = client.patch(
            f"/api/drafts/{d['id']}", json={"version": 1, "text": "hey! can we do 11 instead?"}
        )
        assert response.status_code == 200
        assert not calls
        response = client.post(f"/api/drafts/{d['id']}/approve", json={"version": 2})
        assert response.status_code == 200 and response.json()["status"] == "sent"
        assert calls == [("alex@example.test", "hey! can we do 11 instead?")]
        assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 2}).status_code == 409
        assert len(calls) == 1
