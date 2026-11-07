import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app, fingerprint
from ghost.messaging import DemoMessenger

ALEX = "alex@example.test"


@pytest.fixture
def chat(tmp_path, monkeypatch):
    """Fake connector, plus a model that fails the test if a typed reply ever calls it."""

    def no_model(*_, **__):
        raise AssertionError("A typed reply must not call the model")

    monkeypatch.setattr("ghost.workflow.create_model", no_model)
    settings = Settings(
        data_dir=tmp_path,
        api_token="test-token",
        mode="imessage",
        allowed_recipients=[ALEX],
        send_enabled=True,
        llm=True,
        _env_file=None,
    )
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger


def typed(client, messenger, text="My own words", recipient=ALEX, seen=None):
    return client.post(
        "/api/drafts/typed",
        json={
            "recipient": recipient,
            "text": text,
            "fingerprint": seen or fingerprint(messenger.history[ALEX]),
        },
    )


def test_a_typed_reply_waits_for_approval_and_sends_exactly_that_text(chat):
    client, messenger = chat
    row = typed(client, messenger).json()
    assert (row["status"], row["version"], row["text"]) == ("pending", 1, "My own words")
    assert messenger.sent == []
    approved = client.post(f"/api/drafts/{row['id']}/approve", json={"version": 1})
    assert approved.json()["status"] == "sent"
    assert messenger.sent == [(ALEX, "My own words")]


def test_a_typed_reply_can_be_edited_and_cleared_like_any_draft(chat):
    client, messenger = chat
    row = typed(client, messenger).json()
    edited = client.patch(f"/api/drafts/{row['id']}", json={"version": 1, "text": "Better"}).json()
    assert edited["version"] == 2
    assert client.post(f"/api/drafts/{row['id']}/approve", json={"version": 1}).status_code == 409
    cleared = client.post(f"/api/drafts/{row['id']}/reject", json={"version": 2}).json()
    assert cleared["status"] == "rejected"
    assert messenger.sent == []


def test_a_typed_reply_is_refused_if_messages_arrived_since_it_was_written(chat):
    client, messenger = chat
    seen = fingerprint(messenger.history[ALEX])
    messenger.history[ALEX] += "\nAlex: actually, Friday?"
    response = typed(client, messenger, seen=seen)
    assert response.status_code == 409
    assert "New messages came in" in response.json()["detail"]
    assert client.get("/api/drafts").json() == []


def test_a_typed_reply_never_replaces_a_saved_draft(chat):
    client, messenger = chat
    first = typed(client, messenger).json()
    response = typed(client, messenger, text="Something else")
    assert response.status_code == 409
    assert client.get("/api/drafts").json() == [first]


def test_a_typed_reply_needs_a_contact_and_real_text(chat):
    client, messenger = chat
    assert typed(client, messenger, recipient="stranger@example.test").status_code == 403
    assert typed(client, messenger, text="   ").status_code == 422
    assert client.get("/api/drafts").json() == []


def test_automatic_drafts_leave_a_typed_reply_alone(chat):
    client, messenger = chat
    row = typed(client, messenger).json()
    prepared = client.post("/api/inbox/prepare", json={"recipient": ALEX}).json()
    assert prepared["reason"] == "existing_review"
    assert prepared["draft"]["id"] == row["id"]


def test_the_new_messages_error_keeps_the_text_for_a_fresh_send(chat):
    client, messenger = chat
    row = typed(client, messenger).json()
    messenger.history[ALEX] += "\nAlex: actually, Friday?"
    approved = client.post(f"/api/drafts/{row['id']}/approve", json={"version": 1})
    assert approved.status_code == 409
    assert "New messages came in" in approved.json()["detail"]
    assert messenger.sent == []
    assert typed(client, messenger).json()["status"] == "pending"
