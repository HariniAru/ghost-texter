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
        assert prepare()["reason"] == "already_reviewed"
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
