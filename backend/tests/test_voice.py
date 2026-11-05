import json

import pytest
from fastapi.testclient import TestClient
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger
from ghost.voice import Profile, resolve_profile, suggest_pairs
from pydantic import ValidationError


def test_old_profile_and_recipient_isolation():
    old = {"style": "warm", "examples": ["default example"]}
    assert resolve_profile(old, "a")["examples"] == ["default example"]
    profile = Profile(
        **old,
        recipients={"a": {"style": "brief", "pairs": [{"incoming": "hi", "response": "a only"}]}},
    ).model_dump()
    assert resolve_profile(profile, "a") == {
        "style": "warm\nRecipient-specific preferences: brief",
        "examples": [],
        "pairs": [{"incoming": "hi", "response": "a only"}],
    }
    assert "a only" not in json.dumps(resolve_profile(profile, "b"))
    assert (
        len(json.dumps(resolve_profile({"style": "warm", "examples": ["x" * 4000] * 30}, "a")))
        < 8500
    )
    with pytest.raises(ValidationError):
        Profile(style="warm", pairs=[{"incoming": " ", "response": "hello"}])


def test_extraction_direction_dedup_and_ambiguous_data():
    transcript = "[2026-10-20 11:00:00] You [iMessage]: sure!\n[2026-10-20 10:00:00] Alex [iMessage] [read]: coffee?"
    pair = {"incoming": "coffee?", "response": "sure!"}
    assert suggest_pairs(transcript) == [pair]
    assert suggest_pairs("Alex: coffee?\nYou: sure!", demo=True) == [pair]
    assert suggest_pairs("Alex: coffee?\nYou: sure!") == []
    assert suggest_pairs("Alex: hi\nunsupported\nYou: hey", demo=True) == []
    assert suggest_pairs("Alex: [Attachment]\nYou: nice", demo=True) == []
    assert suggest_pairs("You: hi\nAlex: hey", demo=True) == []


def test_profile_preview_is_read_only_persists_and_never_sends(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        api_token="test",
        mode="imessage",
        allowed_recipients=["alex@example.test"],
        _env_file=None,
    )
    messenger = DemoMessenger()
    messenger.history["alex@example.test"] = (
        "[2026-10-20 11:00:00] You [iMessage]: sure!\n[2026-10-20 10:00:00] Alex [iMessage]: coffee?"
    )
    profile = {
        "style": "warm",
        "examples": ["legacy"],
        "pairs": [],
        "recipients": {
            "alex@example.test": {
                "style": "brief",
                "pairs": [{"incoming": "hi", "response": "hey"}],
            }
        },
    }
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test"
        assert client.put("/api/profile", json=profile).status_code == 200
        before = client.get("/api/profile").json()
        result = client.post("/api/profile/suggestions", json={"recipient": "alex@example.test"})
        assert result.json()["pairs"] == [{"incoming": "coffee?", "response": "sure!"}]
        assert client.get("/api/profile").json() == before
        assert (
            client.post(
                "/api/profile/suggestions", json={"recipient": "other@example.test"}
            ).status_code
            == 403
        )
        assert client.get("/api/drafts").json() == []
        profile["recipients"]["alex@example.test"]["pairs"] = result.json()["pairs"]
        assert client.put("/api/profile", json=profile).status_code == 200
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test"
        assert (
            client.get("/api/profile").json()["recipients"]["alex@example.test"]["pairs"]
            == result.json()["pairs"]
        )
    assert messenger.sent == []


def test_drafting_receives_only_resolved_voice_and_keeps_review_pause(tmp_path, monkeypatch):
    from ghost import workflow

    prompts = []

    class FakeModel:
        def with_structured_output(self, schema):
            self.schema = schema
            return self

        def invoke(self, messages):
            prompts.append(json.loads(messages[-1][1]))
            return self.schema(text="synthetic reply")

    monkeypatch.setattr(workflow, "create_model", lambda _: FakeModel())
    messenger = DemoMessenger()
    settings = Settings(data_dir=tmp_path, api_token="test", llm=True, _env_file=None)
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test"
        profile = {
            "style": "warm",
            "examples": ["default wording"],
            "recipients": {
                "alex@example.test": {
                    "style": "brief",
                    "pairs": [{"incoming": "question", "response": "alex-only wording"}],
                }
            },
        }
        assert client.put("/api/profile", json=profile).status_code == 200
        for recipient in ["alex@example.test", "maya@example.test"]:
            response = client.post("/api/drafts", json={"recipient": recipient})
            assert response.json()["status"] == "pending"
        assert (
            prompts[0]["incoming_and_user_response_examples"][0]["response"] == "alex-only wording"
        )
        assert "alex-only wording" not in json.dumps(prompts[1])
        assert prompts[1]["user_written_examples"] == ["default wording"]
    assert messenger.sent == []
