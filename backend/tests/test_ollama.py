import io
import json
import urllib.error
from unittest.mock import Mock

import pytest
from ghost.config import Settings
from ghost.ollama_model import AIConfigurationError, LocalOllama
from ghost.workflow import Reply, create_model


def settings(**kwargs):
    return Settings(model="qwen3:4b", _env_file=None, **kwargs)


def test_the_model_is_always_the_local_ollama_client():
    assert isinstance(create_model(settings()), LocalOllama)


def test_local_structured_request_has_no_credentials_tools_or_thinking(monkeypatch):
    captured = []

    def open_request(request, timeout):
        captured.append(request)
        return io.BytesIO(
            json.dumps(
                {"message": {"content": '{"text":"hey! what time?"}'}, "done_reason": "stop"}
            ).encode()
        )

    monkeypatch.setattr(
        "ghost.ollama_model.urllib.request.build_opener", lambda *args: Mock(open=open_request)
    )
    reply = LocalOllama(settings()).with_structured_output(Reply).invoke([("human", "coffee?")])
    assert reply.text == "hey! what time?"
    payload = json.loads(captured[0].data)
    assert payload["think"] is False
    assert payload["messages"][0]["role"] == "user"
    assert payload["format"]["properties"]["text"]["type"] == "string"
    assert "tools" not in payload
    assert not captured[0].has_header("Authorization")


@pytest.mark.parametrize(
    "url", ["https://ollama.com", "http://example.com", "http://user:secret@localhost:11434"]
)
def test_cloud_urls_rejected(url):
    with pytest.raises(AIConfigurationError, match="loopback"):
        LocalOllama(settings(ollama_url=url))


def test_cloud_model_alias_rejected():
    s = settings()
    s.model = "gemma4:cloud"
    with pytest.raises(AIConfigurationError, match="local Ollama model"):
        LocalOllama(s)


def test_malformed_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "ghost.ollama_model.urllib.request.build_opener",
        lambda *args: Mock(open=lambda *a, **kw: io.BytesIO(b'{"message":{"content":"not json"}}')),
    )
    with pytest.raises(AIConfigurationError, match="invalid structured reply"):
        LocalOllama(settings()).with_structured_output(Reply).invoke([("human", "hi")])


def test_missing_model_has_actionable_error(monkeypatch):
    opener = Mock()
    opener.open.side_effect = urllib.error.HTTPError("local", 404, "missing", {}, None)
    monkeypatch.setattr("ghost.ollama_model.urllib.request.build_opener", lambda *args: opener)
    with pytest.raises(AIConfigurationError, match="ollama pull"):
        LocalOllama(settings()).with_structured_output(Reply).invoke([("human", "hi")])
