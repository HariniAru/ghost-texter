import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger

# Sends only run outside demo mode, so these tests use live-mode settings with the fake connector.
LIVE = dict(
    mode="imessage",
    send_enabled=True,
    allowed_recipients=[
        "alex@example.test",
        "maya@example.test",
        "jordan@example.test",
        "priya@example.test",
    ],
)


@pytest.fixture
def workspace(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", _env_file=None)
    messenger = DemoMessenger()
    app = create_app(settings, messenger)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger, app


@pytest.fixture
def live_workspace(tmp_path):
    messenger = DemoMessenger()  # Fake connector, with live-mode rules so Send really runs.
    app = create_app(
        Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None), messenger
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger, app


def draft(client):
    response = client.post("/api/drafts", json={"recipient": "alex@example.test"})
    assert response.status_code == 200, response.text
    return response.json()


def test_no_send_until_explicit_approval_and_exact_edited_text(live_workspace):
    client, messenger, app = live_workspace
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


def test_conversation_changes_invalidate_approval(live_workspace):
    client, messenger, _ = live_workspace
    d = draft(client)
    messenger.history[d["recipient"]] += "\nAlex: actually tomorrow no longer works"
    response = client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1})
    assert response.status_code == 409
    assert client.get("/api/drafts").json()[0]["status"] == "stale"
    assert messenger.sent == []


def test_using_latest_messages_keeps_the_text_and_requires_the_new_version(live_workspace):
    client, messenger, app = live_workspace
    d = draft(client)
    newest = "\nAlex: actually can we do 11?"
    messenger.history[d["recipient"]] += newest

    updated = client.post(f"/api/drafts/{d['id']}/refresh", json={"version": 1})
    assert updated.status_code == 200
    row = updated.json()
    assert (row["version"], row["status"], row["text"]) == (2, "pending", d["text"])
    assert newest in row["context"]
    assert row["fingerprint"] != d["fingerprint"]
    assert messenger.sent == []

    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 409
    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 2}).status_code == 200
    assert messenger.sent == [(d["recipient"], d["text"])]
    action = app.state.store.db.execute(
        "SELECT COUNT(*) FROM events WHERE action='context_updated'"
    ).fetchone()[0]
    assert action == 1


def test_a_message_after_using_latest_still_invalidates_approval(live_workspace):
    client, messenger, _ = live_workspace
    d = draft(client)
    messenger.history[d["recipient"]] += "\nAlex: first"
    client.post(f"/api/drafts/{d['id']}/refresh", json={"version": 1})
    messenger.history[d["recipient"]] += "\nAlex: second"
    assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 2}).status_code == 409
    assert client.get("/api/drafts").json()[0]["status"] == "stale"
    assert messenger.sent == []


def test_using_latest_needs_a_pending_draft_at_its_version_and_a_good_read(workspace):
    client, messenger, _ = workspace
    d = draft(client)
    assert client.post(f"/api/drafts/{d['id']}/refresh", json={"version": 9}).status_code == 409

    async def denied(recipient):
        raise OSError("private connector detail")

    original = messenger.read
    messenger.read = denied
    failed = client.post(f"/api/drafts/{d['id']}/refresh", json={"version": 1})
    assert failed.status_code == 502
    assert "private connector detail" not in failed.text
    messenger.read = original
    assert client.get("/api/drafts").json()[0]["version"] == 1

    client.post(f"/api/drafts/{d['id']}/reject", json={"version": 1})
    assert client.post(f"/api/drafts/{d['id']}/refresh", json={"version": 1}).status_code == 409
    assert messenger.sent == []


def test_send_failure_is_not_retryable(live_workspace):
    client, messenger, _ = live_workspace
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
    settings = Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None)
    with TestClient(create_app(settings, DemoMessenger())) as first:
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


def test_sent_draft_leaves_list_but_keeps_receipt_and_evidence(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None)
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        rejected = draft(client)
        client.post(f"/api/drafts/{rejected['id']}/reject", json={"version": 1})
        d = draft(client)
        sent = client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1})
        # The approval response is where the dashboard gets the receipt.
        assert sent.status_code == 200
        assert sent.json()["status"] == "sent" and sent.json()["receipt"]
        assert [row["id"] for row in client.get("/api/drafts").json()] == [rejected["id"]]
        # Leaving the list does not open a path to resending.
        assert client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1}).status_code == 409
        assert len(messenger.sent) == 1
    app = create_app(settings, DemoMessenger())
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        assert [row["id"] for row in client.get("/api/drafts").json()] == [rejected["id"]]
        store = app.state.store
        assert store.one(d["id"])["status"] == "sent"
        actions = [
            row[0]
            for row in store.db.execute(
                "SELECT action FROM events WHERE draft_id=? ORDER BY id", (d["id"],)
            )
        ]
        assert actions == ["drafted", "approved", "sent"]


def test_interrupted_send_stays_listed_as_uncertain(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", _env_file=None)
    app = create_app(settings, DemoMessenger())
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test-token"
        d = draft(client)
        app.state.store.db.execute("UPDATE drafts SET status='sending' WHERE id=?", (d["id"],))
        app.state.store.db.commit()
    with TestClient(create_app(settings, DemoMessenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        rows = client.get("/api/drafts").json()
        assert [(row["id"], row["status"]) for row in rows] == [(d["id"], "uncertain")]


def test_demo_send_does_nothing_at_all(workspace, tmp_path):
    client, messenger, app = workspace
    d = draft(client)
    before = client.get("/api/drafts").json()
    response = client.post(f"/api/drafts/{d['id']}/approve", json={"version": 1})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert messenger.sent == []
    assert client.get("/api/drafts").json() == before
    # No approval or status event was written, so nothing about it can be replayed.
    import sqlite3

    with sqlite3.connect(tmp_path / "ghost.sqlite") as db:
        kinds = [r[0] for r in db.execute("SELECT action FROM events WHERE draft_id=?", (d["id"],))]
    assert "approved" not in kinds and "sent" not in kinds
