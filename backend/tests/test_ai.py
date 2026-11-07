from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from ghost.check_ai import check
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger
from ghost.ollama_model import AIConfigurationError
from ghost.workflow import Reply, Summary


def test_synthetic_ai_check_generates_structured_summary_and_paused_draft(monkeypatch):
    model = Mock()

    def structured(schema):
        text = (
            "Alex asks about coffee." if schema is Summary else "hey! what time were you thinking?"
        )
        return SimpleNamespace(invoke=Mock(return_value=schema(text=text)))

    model.with_structured_output.side_effect = structured
    monkeypatch.setattr("ghost.workflow.create_model", lambda *_, **__: model)
    summary, reply = check(Settings(_env_file=None))
    assert summary == "Alex asks about coffee."
    assert reply == "hey! what time were you thinking?"
    assert [c.args[0] for c in model.with_structured_output.call_args_list] == [Summary, Reply]
    model.bind_tools.assert_not_called()


def test_model_configuration_error_is_actionable_in_api_and_never_sends(tmp_path, monkeypatch):
    def unavailable(*_, **__):
        raise AIConfigurationError("Ollama is not running. Start it with ollama serve.")

    monkeypatch.setattr("ghost.workflow.create_model", unavailable)
    settings = Settings(data_dir=tmp_path, api_token="test", llm=True, _env_file=None)
    messenger = DemoMessenger()
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer test"
        response = client.get("/api/conversation", params={"recipient": "alex@example.test"})
        assert response.status_code == 502
        assert "Ollama is not running" in response.json()["detail"]
        response = client.post("/api/drafts", json={"recipient": "alex@example.test"})
        assert response.status_code == 502
        assert "Ollama is not running" in response.json()["detail"]
        assert client.get("/api/drafts").json() == []
    assert not messenger.sent
