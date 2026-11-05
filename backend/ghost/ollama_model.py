"""Local-only structured Ollama requests; no credentials or cloud fallback."""

import json
import urllib.error
import urllib.parse
import urllib.request


class AIConfigurationError(RuntimeError):
    pass


class LocalOllama:
    def __init__(self, settings, schema=None):
        self.settings = settings
        self.schema = schema
        url = urllib.parse.urlsplit(settings.ollama_url)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise AIConfigurationError(
                "GHOST_OLLAMA_URL must be an HTTP loopback address. Cloud inference is not enabled."
            )
        if ":cloud" in settings.model or not settings.model.strip():
            raise AIConfigurationError("Choose a downloaded local Ollama model, such as qwen3:4b.")

    def with_structured_output(self, schema):
        return LocalOllama(self.settings, schema)

    def invoke(self, messages):
        if self.schema is None:
            raise AIConfigurationError("Ollama requests require a validated output schema.")
        if sum(len(content) for _, content in messages) > 24000:
            raise AIConfigurationError(
                "Local model input is too long. Shorten your voice examples or conversation context."
            )
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": role if role != "human" else "user", "content": content}
                for role, content in messages
            ],
            "format": self.schema.model_json_schema(),
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 512},
        }
        payload["messages"].append(
            {
                "role": "user",
                "content": "Answer the task above using the conversation data. Return a JSON object "
                "matching this schema: " + json.dumps(self.schema.model_json_schema()),
            }
        )
        request = urllib.request.Request(
            self.settings.ollama_url.rstrip("/") + "/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            # Do not route private local prompts through an HTTP proxy or redirect.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(request, timeout=180) as response:
                result = json.load(response)
            if result.get("done_reason") == "length":
                raise AIConfigurationError(
                    "Local model output was cut short. Try a shorter conversation."
                )
            return self.schema.model_validate_json(result["message"]["content"])
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise AIConfigurationError(
                    "Local model is missing. Run ollama pull with your GHOST_MODEL value."
                ) from None
            raise AIConfigurationError(
                "Ollama request failed. Check the local server and model configuration."
            ) from None
        except (urllib.error.URLError, TimeoutError):
            raise AIConfigurationError(
                "Cannot reach Ollama or request timed out. Run ollama serve and check the model."
            ) from None
        except (ValueError, KeyError, TypeError):
            raise AIConfigurationError(
                "Ollama returned an invalid structured reply. Nothing was sent."
            ) from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
