import asyncio
import sqlite3

import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger, MacMessages

PHONE = "+14155550123"
OTHER = "+14155550999"
ENV_ADDRESS = "maya@example.test"


def live_settings(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path,
        api_token="test-token",
        mode="imessage",
        send_enabled=True,
        allowed_recipients=[ENV_ADDRESS],
        _env_file=None,
    )
    return Settings(**{**values, **overrides})


def fake_messenger():
    messenger = DemoMessenger()
    for address in (PHONE, OTHER):
        messenger.history[address] = "You: hey\nSam: coffee tomorrow?"
        messenger.unread_messages[address] = ["Sam: coffee tomorrow?"]
    return messenger


@pytest.fixture
def live(tmp_path):
    messenger = fake_messenger()
    with TestClient(create_app(live_settings(tmp_path), messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        yield client, messenger


def add(client, number, name="Sam"):
    return client.post("/api/contacts", json={"name": name, "number": number})


def addresses(client):
    return [row["address"] for row in client.get("/api/contacts").json()]


def test_added_contact_is_read_by_inbox_and_nothing_else_is(live):
    client, messenger = live
    assert client.get("/api/contacts").json() == [
        {"name": "", "address": ENV_ADDRESS, "source": "env"}
    ]
    assert [r["recipient"] for r in client.get("/api/inbox").json()] == [ENV_ADDRESS]
    assert client.get("/api/conversation", params={"recipient": PHONE}).status_code == 403

    response = add(client, PHONE)
    assert response.status_code == 200
    assert {"name": "Sam", "address": PHONE, "source": "app"} in response.json()
    assert client.get("/api/status").json()["recipients"] == [ENV_ADDRESS, PHONE]
    assert {r["recipient"] for r in client.get("/api/inbox").json()} == {ENV_ADDRESS, PHONE}
    assert client.get("/api/conversation", params={"recipient": PHONE}).status_code == 200
    # OTHER has a chat on this Mac but was never added, so it stays out of reach.
    assert client.get("/api/conversation", params={"recipient": OTHER}).status_code == 403
    assert OTHER not in {r["recipient"] for r in client.get("/api/inbox").json()}
    assert messenger.sent == []


def test_number_formatting_is_removed_and_the_name_is_kept(live):
    client, _ = live
    assert add(client, " +1 (415) 555-0123 ", name="  Sam Lee ").status_code == 200
    assert addresses(client) == [ENV_ADDRESS, PHONE]
    assert client.get("/api/contacts").json()[1]["name"] == "Sam Lee"


def test_adding_a_saved_number_again_updates_its_name(live):
    client, _ = live
    add(client, PHONE, name="Sam")
    assert add(client, PHONE, name="Sammy").status_code == 200
    assert addresses(client) == [ENV_ADDRESS, PHONE]
    assert client.get("/api/contacts").json()[1]["name"] == "Sammy"


def test_a_contact_from_env_can_be_named_but_still_not_removed_here(tmp_path):
    settings = live_settings(tmp_path, allowed_recipients=[PHONE])
    with TestClient(create_app(settings, fake_messenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        assert add(client, PHONE, name="Sam").status_code == 200
        assert client.get("/api/contacts").json() == [
            {"name": "Sam", "address": PHONE, "source": "env"}
        ]
        assert client.delete("/api/contacts", params={"address": PHONE}).status_code == 409


@pytest.mark.parametrize(
    "number", ["4155550123", "Sam", "+0123456", "sam@example.test", "'; DROP TABLE contacts; --"]
)
def test_only_full_phone_numbers_are_accepted(live, number):
    client, messenger = live
    reads = []
    original = messenger.read

    async def read(recipient):
        reads.append(recipient)
        return await original(recipient)

    messenger.read = read
    assert add(client, number).status_code == 422
    assert reads == []
    assert addresses(client) == [ENV_ADDRESS]


@pytest.mark.parametrize("body", [{"number": PHONE}, {"name": "   ", "number": PHONE}])
def test_a_name_is_required(live, body):
    client, _ = live
    assert client.post("/api/contacts", json=body).status_code == 422
    assert addresses(client) == [ENV_ADDRESS]


def test_contacts_saved_before_names_existed_are_kept(tmp_path):
    db = sqlite3.connect(tmp_path / "ghost.sqlite")
    db.execute(
        "CREATE TABLE contacts (address TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    db.execute("INSERT INTO contacts(address) VALUES (?)", (PHONE,))
    db.commit()
    db.close()
    with TestClient(create_app(live_settings(tmp_path), fake_messenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        assert {"name": "", "address": PHONE, "source": "app"} in client.get("/api/contacts").json()
        add(client, PHONE, name="Sam")
        assert {"name": "Sam", "address": PHONE, "source": "app"} in (
            client.get("/api/contacts").json()
        )


def test_number_without_a_chat_is_refused_and_not_saved(live):
    client, _ = live
    response = add(client, "+14155550100")
    assert response.status_code == 422
    assert response.json()["detail"] == "Chat not found with this contact."
    assert addresses(client) == [ENV_ADDRESS]


@pytest.mark.parametrize(
    "reply",
    [
        "No group chat found with chat_id '+14155550100'.",
        "No messages found in the specified time period.",
    ],
)
def test_connector_reporting_no_chat_is_chat_not_found(tmp_path, reply):
    connector = MacMessages(Settings(_env_file=None))

    async def call(name, arguments):
        return reply

    connector.call = call
    with TestClient(create_app(live_settings(tmp_path), connector)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        response = add(client, "+14155550100")
        assert response.status_code == 422
        assert response.json()["detail"] == "Chat not found with this contact."
        assert addresses(client) == [ENV_ADDRESS]


def test_a_permission_error_is_not_reported_as_a_missing_chat(tmp_path):
    connector = MacMessages(Settings(_env_file=None))

    async def call(name, arguments):
        return "Error getting messages: denied"

    connector.call = call
    with TestClient(create_app(live_settings(tmp_path), connector)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        response = add(client, "+14155550100")
        assert response.status_code == 422
        assert "Chat not found" not in response.json()["detail"]
        assert addresses(client) == [ENV_ADDRESS]


def test_connector_failure_during_add_saves_nothing(live):
    client, messenger = live

    async def denied(recipient):
        raise OSError("private connector detail")

    messenger.read = denied
    response = add(client, PHONE)
    assert response.status_code == 502
    assert "private connector detail" not in response.text
    assert addresses(client) == [ENV_ADDRESS]


def test_contact_list_is_bounded(tmp_path):
    messenger = fake_messenger()
    many = [f"+1415555{i:04d}" for i in range(51)]
    for address in many:
        messenger.history[address] = "Sam: hi"
    with TestClient(create_app(live_settings(tmp_path), messenger)) as client:
        client.headers["Authorization"] = "Bearer test-token"
        for address in many[:49]:
            assert add(client, address).status_code == 200
        # The .env address counts, so the list is now full.
        assert len(addresses(client)) == 50
        assert add(client, many[49]).status_code == 422
        assert len(addresses(client)) == 50
        # A full list can still rename someone already on it.
        assert add(client, many[0], name="Renamed").status_code == 200


def test_removing_a_contact_revokes_reading_drafting_and_sending(live):
    client, messenger = live
    add(client, PHONE)
    draft = client.post("/api/drafts", json={"recipient": PHONE}).json()

    response = client.delete("/api/contacts", params={"address": PHONE})
    assert response.status_code == 200
    assert PHONE not in [row["address"] for row in response.json()]

    assert client.get("/api/conversation", params={"recipient": PHONE}).status_code == 403
    assert client.post("/api/drafts", json={"recipient": PHONE}).status_code == 403
    assert client.post("/api/inbox/prepare", json={"recipient": PHONE}).status_code == 403
    assert client.post("/api/profile/suggestions", json={"recipient": PHONE}).status_code == 403
    assert client.post(f"/api/drafts/{draft['id']}/refresh", json={"version": 1}).status_code == 403
    assert client.post(f"/api/drafts/{draft['id']}/approve", json={"version": 1}).status_code == 403
    assert messenger.sent == []
    assert PHONE not in {r["recipient"] for r in client.get("/api/inbox").json()}
    # The saved draft stays visible and pending, not silently deleted.
    assert client.get("/api/drafts").json()[0]["status"] == "pending"

    # Adding the contact back does not approve anything by itself.
    add(client, PHONE)
    assert messenger.sent == []
    assert client.post(f"/api/drafts/{draft['id']}/approve", json={"version": 1}).status_code == 200
    assert messenger.sent == [(PHONE, draft["text"])]


def test_env_contacts_cannot_be_removed_here_and_unknown_is_404(live):
    client, _ = live
    response = client.delete("/api/contacts", params={"address": ENV_ADDRESS})
    assert response.status_code == 409
    assert ".env" in response.json()["detail"]
    assert addresses(client) == [ENV_ADDRESS]
    assert client.delete("/api/contacts", params={"address": PHONE}).status_code == 404


def test_contacts_survive_restart(tmp_path):
    settings = live_settings(tmp_path)
    with TestClient(create_app(settings, fake_messenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        add(client, PHONE)
    with TestClient(create_app(settings, fake_messenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        assert addresses(client) == [ENV_ADDRESS, PHONE]


def test_voice_settings_for_a_removed_contact_do_not_block_saving(live):
    client, _ = live
    add(client, PHONE)
    profile = client.get("/api/profile").json()
    profile["recipients"][PHONE] = {"style": "curt", "examples": [], "pairs": []}
    assert client.put("/api/profile", json=profile).status_code == 200
    client.delete("/api/contacts", params={"address": PHONE})

    # PUT is a full replacement, so the dashboard sends the removed contact's voice back.
    profile = client.get("/api/profile").json()
    profile["style"] = "new default"
    assert client.put("/api/profile", json=profile).status_code == 200
    assert client.get("/api/profile").json()["recipients"][PHONE]["style"] == "curt"

    # Keeping old settings grants nothing, and new unknown addresses are still refused.
    assert client.get("/api/conversation", params={"recipient": PHONE}).status_code == 403
    profile["recipients"][OTHER] = {"style": "x", "examples": [], "pairs": []}
    assert client.put("/api/profile", json=profile).status_code == 403


def test_demo_mode_lists_synthetic_contacts_and_refuses_changes(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="test-token", _env_file=None)
    with TestClient(create_app(settings, DemoMessenger())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        rows = client.get("/api/contacts").json()
        assert {row["source"] for row in rows} == {"demo"}
        assert add(client, PHONE).status_code == 403
        address = rows[0]["address"]
        assert client.delete("/api/contacts", params={"address": address}).status_code == 403
        assert len(client.get("/api/contacts").json()) == len(rows)


def test_contact_routes_require_auth_and_trusted_origin(live):
    client, _ = live
    wrong = {"Authorization": "Bearer wrong"}
    assert client.get("/api/contacts", headers=wrong).status_code == 401
    body = {"name": "Sam", "number": PHONE}
    assert client.post("/api/contacts", json=body, headers=wrong).status_code == 401
    assert (
        client.delete("/api/contacts", params={"address": PHONE}, headers=wrong).status_code == 401
    )
    untrusted = {"Origin": "https://evil.example"}
    assert client.post("/api/contacts", json=body, headers=untrusted).status_code == 403
    assert addresses(client) == [ENV_ADDRESS]


def test_mcp_unread_treats_a_missing_chat_as_no_unread_but_still_reports_errors():
    adapter = MacMessages(Settings(_env_file=None))

    async def call(name, arguments):
        if arguments["chat_id"] == "gone@example.test":
            return "No group chat found with chat_id 'gone@example.test'."
        return "[2026-10-17 10:00:00] Alex: hello"

    adapter.call = call
    rows = asyncio.run(adapter.unread(["gone@example.test", "alex@example.test"]))
    assert [row.recipient for row in rows] == ["alex@example.test"]

    async def failing(name, arguments):
        return "Error getting messages: denied"

    adapter.call = failing
    with pytest.raises(RuntimeError):
        asyncio.run(adapter.unread(["alex@example.test"]))
