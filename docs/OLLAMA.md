# Ollama setup

## Installed on this Mac

Ollama 0.40.6 is installed at `/Applications/Ollama.app`. The official installer installed the application but its system CLI link required sudo. The user-owned link at `~/.local/bin/ollama` supplies the command without sudo or shell profile edits.

Verified local server: `http://127.0.0.1:11434`. `ollama --version`, `ollama list`, and `/api/version` work. Hardware detection reports Apple M4 with Metal acceleration; physical unified memory is 16 GB. The initial installation was verified without a model; qwen3:4b was subsequently downloaded after local experimentation was selected. No account sign-in or API-key use was performed.

The server was started for this session. After restarting the computer, start it with `ollama serve` if it is not already running. Do not start a second instance when port 11434 is occupied.

## Recommended starting point for Ghost Texter

Local `qwen3:4b` is a small starting model for summaries and reply drafting, with a 2.5 GB quantized download. Quality and latency must be evaluated on synthetic conversations before using live message history. Larger models and longer contexts require additional memory; 32B is unsuitable for comfortable use on this 16 GB Mac. The local service defaults to a 4096-token context on this hardware, so the eventual integration must bound prompt size.

After choosing local inference:

```sh
ollama pull qwen3:4b
ollama run qwen3:4b
```

No API key is needed for local inference. Model requests run on this Mac, using its memory and electricity, without per-request cloud API charges.

## Optional cloud route

Start with `gemma4:cloud` in the CLI if choosing the free starter cloud option. Free cloud usage is limited; check current account eligibility/usage and pricing. Other models may require a subscription or purchased credits. The user must perform sign-in themselves:

```sh
ollama signin
ollama run gemma4:cloud
```

For direct application calls, the user can create their own key at https://ollama.com/settings/keys. The direct API base URL is `https://ollama.com/api`; cloud model names are those returned by the cloud model list (for example `gemma4:31b`), not necessarily the CLI's `:cloud` alias.

Cloud requests send conversation context to Ollama servers. Its docs currently state that cloud structured outputs are not supported. Ghost Texter currently relies on structured reply/summary validation, so cloud integration would need a separately tested output-parsing path.

## Ghost Texter integration

Local `qwen3:4b` is downloaded. Ghost Texter talks to a local Ollama server and validates every summary and reply against a schema. Current workspace configuration uses:

```dotenv
GHOST_LLM=true
GHOST_MODEL=qwen3:4b
GHOST_OLLAMA_URL=http://127.0.0.1:11434
GHOST_SEND_ENABLED=false
```

No credential of any kind is used. The adapter accepts only loopback HTTP URLs, disables HTTP proxies/redirects, rejects cloud aliases, and has no fallback to another provider. Thinking is disabled, temperature is zero, context is 8192 tokens, and generation is bounded to 512 tokens. An input-size guard rejects oversized prompts; character length is only an approximate token safeguard. Structured output is validated against the existing Pydantic schema before use. Errors never authorize sending.

Test with synthetic data (no Messages access):

```sh
uv run python -m ghost.check_ai
```

Then restart the FastAPI backend so it loads the updated provider. Open a conversation to generate a local summary, and request a draft. A new draft replaces what is in the reply box, after asking.

For general experimentation, use the same server independently of this project:

```sh
ollama run qwen3:4b
ollama list
ollama ps
ollama stop qwen3:4b
```

Inside chat, `/bye` exits. `ollama stop` frees model memory; the server can remain running. Try other small local models later by pulling them and changing GHOST_MODEL, then rerun the synthetic check. Cloud integration remains unimplemented and requires user-managed sign-in; the local provider does not use it.

## Official references read

- https://docs.ollama.com/llms.txt
- https://docs.ollama.com/quickstart.md
- https://docs.ollama.com/cloud.md
- https://docs.ollama.com/gpu.md
- https://docs.ollama.com/api/introduction.md
- https://docs.ollama.com/llms-full.txt (structured outputs, context length, macOS)
- https://ollama.com/library/qwen3:4b
- https://ollama.com/pricing
