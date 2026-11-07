from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger
from ghost.workflow import build_graph
from langgraph.checkpoint.memory import MemorySaver

ALEX = "alex@example.test"

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


def stamp(delta=timedelta()):
    return (datetime.now() + delta).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def failed_send(tmp_path):
    """A draft whose send raised, so its outcome is unknown. Fake connector only."""
    settings = Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None)
    messenger = DemoMessenger()
    messenger.history[ALEX] = f"[{stamp(timedelta(days=-1))}] Alex [iMessage]: coffee?"
    attempts = []

    async def interrupted(recipient, text):
        attempts.append((recipient, text))
        raise TimeoutError("connection dropped")

    messenger.send = interrupted
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        row = client.post("/api/drafts", json={"recipient": ALEX}).json()
        assert (
            client.post(f"/api/drafts/{row['id']}/approve", json={"version": 1}).status_code == 502
        )
        assert client.get("/api/drafts").json()[0]["status"] == "uncertain"
        yield client, messenger, row, attempts


def appeared(messenger, row, text=None, who="You [iMessage]", when=None):
    messenger.history[ALEX] = (
        f"[{when or stamp()}] {who}: {text or row['text']}\n" + messenger.history[ALEX]
    )


def post(client, row, action):
    return client.post(f"/api/drafts/{row['id']}/{action}")


def test_a_found_message_counts_as_sent_without_sending_again(failed_send):
    client, messenger, row, attempts = failed_send
    appeared(messenger, row)
    result = post(client, row, "verify").json()
    assert result["status"] == "sent"
    assert "found in Messages" in result["receipt"]
    assert client.get("/api/drafts").json() == []
    assert len(attempts) == 1
    assert client.post(f"/api/drafts/{row['id']}/approve", json={"version": 1}).status_code == 409
    assert post(client, row, "verify").status_code == 409


def test_nothing_found_stays_uncertain(failed_send):
    client, _, row, attempts = failed_send
    assert post(client, row, "verify").json()["status"] == "uncertain"
    assert len(attempts) == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"when": stamp(timedelta(minutes=-10))},
        {"who": "Alex [iMessage]"},
        {"text": "something else entirely"},
    ],
)
def test_older_incoming_or_different_messages_are_not_proof(failed_send, kwargs):
    client, messenger, row, _ = failed_send
    appeared(messenger, row, **kwargs)
    assert post(client, row, "verify").json()["status"] == "uncertain"


def test_a_multi_line_reply_matches_the_connector_format(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None)
    messenger = DemoMessenger()

    async def interrupted(recipient, text):
        raise TimeoutError

    messenger.send = interrupted
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        row = client.post("/api/drafts", json={"recipient": ALEX}).json()
        client.patch(f"/api/drafts/{row['id']}", json={"version": 1, "text": "first\nsecond"})
        client.post(f"/api/drafts/{row['id']}/approve", json={"version": 2})
        messenger.history[ALEX] += f"\n[{stamp()}] You: first\\nsecond"
        assert post(client, row, "verify").json()["status"] == "sent"


def test_try_again_makes_a_new_draft_that_still_needs_approval(failed_send):
    client, messenger, row, attempts = failed_send
    fresh = post(client, row, "retry").json()
    assert fresh["id"] != row["id"]
    assert (fresh["status"], fresh["version"], fresh["text"]) == ("pending", 1, row["text"])
    assert len(attempts) == 1
    assert [d["id"] for d in client.get("/api/drafts").json()] == [fresh["id"]]

    sends = []

    async def works(recipient, text):
        sends.append((recipient, text))
        return "Message sent successfully via iMessage"

    messenger.send = works
    assert client.post(f"/api/drafts/{fresh['id']}/approve", json={"version": 1}).status_code == 200
    assert sends == [(ALEX, row["text"])]


def test_try_again_does_not_resend_if_the_message_has_since_appeared(failed_send):
    client, messenger, row, attempts = failed_send
    appeared(messenger, row)
    assert post(client, row, "retry").json()["status"] == "sent"
    assert client.get("/api/drafts").json() == []
    assert len(attempts) == 1


def test_try_again_changes_nothing_if_the_chat_cannot_be_read(failed_send):
    client, messenger, row, _ = failed_send

    async def denied(recipient):
        raise OSError("private connector detail")

    messenger.read = denied
    response = post(client, row, "retry")
    assert response.status_code == 502
    assert "private connector detail" not in response.text
    assert [d["status"] for d in client.get("/api/drafts").json()] == ["uncertain"]


def test_discard_hides_the_draft_but_keeps_the_record(failed_send):
    client, _, row, attempts = failed_send
    assert post(client, row, "discard").json()["status"] == "discarded"
    assert client.get("/api/drafts").json() == []
    store = client.app.state.store
    assert store.one(row["id"])["status"] == "discarded"
    actions = [
        r[0] for r in store.db.execute("SELECT action FROM events WHERE draft_id=?", (row["id"],))
    ]
    assert {"approved", "uncertain", "discarded"} <= set(actions)
    assert len(attempts) == 1
    for action in ("verify", "retry", "discard"):
        assert post(client, row, action).status_code == 409


def test_these_actions_only_apply_to_an_uncertain_draft(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", **LIVE, _env_file=None)
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        row = client.post("/api/drafts", json={"recipient": ALEX}).json()
        for action in ("verify", "retry", "discard"):
            assert post(client, row, action).status_code == 409
        assert client.get("/api/drafts").json()[0]["status"] == "pending"
        assert messenger.sent == []
        assert client.post("/api/drafts/missing/verify").status_code == 404


def test_trying_again_never_calls_the_model(monkeypatch):
    def no_model(*_, **__):
        raise AssertionError("model called")

    monkeypatch.setattr("ghost.workflow.create_model", no_model)
    graph = build_graph(MemorySaver(), Settings(llm=True, _env_file=None))
    state = graph.invoke(
        {"context": "x", "text": "my own words"}, {"configurable": {"thread_id": "t"}}
    )
    assert state["text"] == "my own words"
