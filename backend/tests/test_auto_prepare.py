from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger


def test_automatic_preparation_preserves_edits_and_rejection(tmp_path):
    messenger = DemoMessenger()
    app = create_app(
        Settings(
            data_dir=tmp_path,
            api_token="test",
            mode="imessage",
            allowed_recipients=["alex@example.test"],
            send_enabled=True,
            _env_file=None,
        ),
        messenger,
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test"

        def prepare():
            response = client.post("/api/inbox/prepare", json={"recipient": "alex@example.test"})
            assert response.status_code == 200
            return response.json()

        first = prepare()
        assert first["created"] and first["draft"]["status"] == "pending"
        draft = first["draft"]
        client.patch(f"/api/drafts/{draft['id']}", json={"version": 1, "text": "my edit"})
        preserved = prepare()["draft"]
        assert preserved["text"] == "my edit" and preserved["version"] == 2
        client.post(f"/api/drafts/{draft['id']}/reject", json={"version": 2})
        # A rejected draft is not a saved draft, so automatic preparation drafts again.
        again = prepare()
        assert again["created"] and again["draft"]["status"] == "pending"
        assert again["draft"]["id"] != draft["id"]
        assert prepare()["reason"] == "existing_review"  # The new pending draft is protected.
        client.post(f"/api/drafts/{again['draft']['id']}/reject", json={"version": 1})
        messenger.history["alex@example.test"] += "\nAlex: how about Friday?"
        assert prepare()["created"]
        assert messenger.sent == []


def test_automatic_preparation_checks_unread_direction_and_allowlist(tmp_path):
    messenger = DemoMessenger()
    app = create_app(
        Settings(
            data_dir=tmp_path,
            api_token="test",
            mode="imessage",
            allowed_recipients=["alex@example.test"],
            send_enabled=True,
            _env_file=None,
        ),
        messenger,
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test"

        def prepare(recipient="alex@example.test"):
            return client.post("/api/inbox/prepare", json={"recipient": recipient})

        assert prepare("unknown@example.test").status_code == 403
        messenger.unread_messages["alex@example.test"] = []
        assert prepare().json()["reason"] == "not_unread"
        messenger.unread_messages["alex@example.test"] = ["old unread"]
        messenger.history["alex@example.test"] = (
            "[2026-10-18 12:00:00] You [iMessage]: already replied\n"
            "[2026-10-18 11:00:00] Alex [iMessage]: hello"
        )
        assert prepare().json()["reason"] == "latest_outgoing"
        assert client.get("/api/drafts").json() == []
        assert messenger.sent == []


def test_automatic_preparation_does_not_redraft_a_sent_snapshot(tmp_path):
    messenger = DemoMessenger()
    app = create_app(
        Settings(
            data_dir=tmp_path,
            api_token="test",
            mode="imessage",
            allowed_recipients=["alex@example.test"],
            send_enabled=True,
            _env_file=None,
        ),
        messenger,
    )

    # Messages can lag: the read after a send may not show the reply yet.
    async def send_without_transcript_update(recipient, text):
        messenger.sent.append((recipient, text))
        return "Synthetic connector acknowledgment"

    messenger.send = send_without_transcript_update
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer test"
        body = {"recipient": "alex@example.test"}
        draft = client.post("/api/inbox/prepare", json=body).json()["draft"]
        assert (
            client.post(f"/api/drafts/{draft['id']}/approve", json={"version": 1}).status_code
            == 200
        )
        assert client.get("/api/drafts").json() == []
        result = client.post("/api/inbox/prepare", json=body).json()
        assert result["created"] is False and result["reason"] == "already_sent"
        assert client.get("/api/drafts").json() == []
        assert len(messenger.sent) == 1


def test_turning_it_on_drafts_every_unread_chat_that_has_no_saved_draft(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test", _env_file=None)
    with TestClient(create_app(settings, DemoMessenger())) as client:
        client.headers["Authorization"] = "Bearer test"

        def prepare(who):
            return client.post(
                "/api/inbox/prepare", json={"recipient": f"{who}@example.test"}
            ).json()

        saved = client.post("/api/drafts", json={"recipient": "alex@example.test"}).json()
        cleared = client.post("/api/drafts", json={"recipient": "maya@example.test"}).json()
        client.post(f"/api/drafts/{cleared['id']}/reject", json={"version": 1})
        results = {who: prepare(who) for who in ("alex", "maya", "jordan", "priya")}
        # A saved draft is left alone. Every other unread chat gets one, even a cleared one.
        assert results["alex"]["reason"] == "existing_review"
        assert results["alex"]["draft"]["id"] == saved["id"]
        assert all(results[who]["created"] for who in ("maya", "jordan", "priya"))
