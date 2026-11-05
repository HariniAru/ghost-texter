from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from ghost.check_ai import check
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger
from ghost.workflow import AIConfigurationError, Reply, Summary, create_model


def test_missing_key_fails_before_network(monkeypatch):
    factory = Mock()
    monkeypatch.setattr("ghost.workflow.ChatOpenAI", factory)
    with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY is missing"):
        create_model(Settings(openai_api_key=None, _env_file=None))
    factory.assert_not_called()


def test_synthetic_ai_check_generates_structured_summary_and_paused_draft(monkeypatch):
    model = Mock()

    def structured(schema):
        text = (
            "Alex asks about coffee." if schema is Summary else "hey! what time were you thinking?"
        )
        return SimpleNamespace(invoke=Mock(return_value=schema(text=text)))

    model.with_structured_output.side_effect = structured
    factory = Mock(return_value=model)
    monkeypatch.setattr("ghost.workflow.ChatOpenAI", factory)
    summary, reply = check(Settings(openai_api_key="synthetic-test-key", _env_file=None))
    assert summary == "Alex asks about coffee."
    assert reply == "hey! what time were you thinking?"
    assert [c.args[0] for c in model.with_structured_output.call_args_list] == [Summary, Reply]
    model.bind_tools.assert_not_called()


def test_missing_ai_key_is_actionable_in_api_and_never_sends(tmp_path):
    settings = Settings(
        data_dir=tmp_path, api_token="test", llm=True, openai_api_key=None, _env_file=None
    )
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test"
        response = client.get("/api/conversation", params={"recipient": "alex@example.test"})
        assert response.status_code == 502
        assert "OPENAI_API_KEY is missing" in response.json()["detail"]
        response = client.post("/api/drafts", json={"recipient": "alex@example.test"})
        assert response.status_code == 502
        assert "OPENAI_API_KEY is missing" in response.json()["detail"]
        assert client.get("/api/drafts").json() == []
    assert not messenger.sent
