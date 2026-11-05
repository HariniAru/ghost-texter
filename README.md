# Ghost Texter

A local personal messaging assistant that drafts replies in your voice and waits for you to edit, approve, or reject each one. Python + FastAPI + LangGraph, React + TypeScript, lightweight local SQLite persistence, Ollama, and a Mac Messages MCP adapter. No database server or cloud model is required.

The default workspace uses synthetic conversations and canned replies. It never accesses Messages or sends a real text. Enable a local Ollama model or OpenAI for personalized drafts; enable the iMessage adapter separately.

## Run locally

Requires Python 3.10+, uv, and Node 22.

```sh
cp .env.example .env
uv sync --extra dev
cd frontend
npm ci
npm run build
cd ..
uv run uvicorn ghost.main:create_app --factory --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001. Run `cat data/api-token` from the repository root and copy the output into the login screen. The **Unread inbox** shows synthetic unread conversations. Select one to see recent messages and an excerpt (or an AI summary when enabled), then click **Draft a reply**. **Refresh inbox** checks for unread changes without replacing your selected conversation or draft. Enable **Auto-refresh every 30 seconds** to keep the list current while the dashboard is open; it defaults to off and shows the last successful update and any connection error. Select a conversation again to reload its messages and summary; **Draft history** retains saved reviews. Use **My voice** to add style preferences and messages you wrote. Save edits, then use Review simulated send and its final confirmation. Demo approvals simulate sends. Live drafts use Review & send and Confirm & send; see the first-send walkthrough.

For development, run `npm run dev` inside frontend in a second terminal; open http://127.0.0.1:5173. The Vite server proxies API calls to port 8001.

Run only one backend worker/process. This is a single-user local application; do not expose it to the network.

## Restart the backend

Restart the backend after changing `.env` or backend code:

1. In the terminal running the backend, press **Ctrl+C** and wait for shutdown to complete.
2. Start it again from the repository root:

   ```sh
   cd /Users/harini/Desktop/interviewing/ghost-texter
   uv run uvicorn ghost.main:create_app --factory --host 127.0.0.1 --port 8001
   ```

3. Leave that terminal running and refresh the browser. If the frontend development server is already running, keep using http://127.0.0.1:5173.

If you see **address already in use**, another process is still using port 8001. Closing a terminal may leave it running. Find it:

```sh
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

Check that it is the backend, then stop its PID (replace `12345` with the actual PID):

```sh
kill -TERM 12345
```

Run `lsof` again to confirm the port is free, then restart using the command above.

The commands under **Verify** run tests, lint checks, and a frontend build; they do not restart the backend. You do not need to rerun the first-time setup or copy `.env.example` over your existing `.env` to restart.

## Inspect a chat from the backend

With one allowlisted recipient configured in `.env`, run from the repo root:

```sh
uv run python -m ghost.inspect_chat
```

This prints the latest unread incoming message without starting the UI or sending anything. Use `--recipient "+14155550123"` to select an allowlisted recipient, or `--latest` to inspect the latest message regardless of read status. See [setup](docs/SETUP.md) for details.

## Test local AI summaries and drafts

See [Ollama setup](docs/OLLAMA.md). With Ollama running and `qwen3:4b` downloaded, set:

```dotenv
GHOST_LLM_PROVIDER=ollama
GHOST_MODEL=qwen3:4b
GHOST_OLLAMA_URL=http://127.0.0.1:11434
GHOST_LLM=true
GHOST_SEND_ENABLED=false
```

Run `uv run python -m ghost.check_ai` to test synthetic summaries and drafts locally, without API credits or Messages access. Restart the backend to use the local model in the dashboard. OpenAI remains optional via `GHOST_LLM_PROVIDER=openai`, its model name, and your own API key.

## Project references

- [Setup and live iMessage configuration](docs/SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [First approved-send walkthrough](docs/FIRST_SEND.md)
- [Approval and dispatch contract](docs/APPROVAL_CONTRACT.md)
- [API](docs/API.md)
- [Privacy and data](docs/PRIVACY.md)
- [Project plan and remaining work](docs/PROJECT_PLAN.md)
- [Research and baseline projects](docs/SOURCES.md)
- [Validation results](docs/VALIDATION.md)
- [Minimal MVP scope and user flow](docs/PROJECT_FLOW.md)
- [Contributor instructions](AGENTS.md)

## Verify

Run these from the repository root to check the code. These checks do not start or restart either server.

```sh
uv run pytest
uv run ruff check backend
cd frontend
npm test
npm run build
```

### Prepare replies automatically

After connecting, enable **Prepare drafts automatically** in Unread inbox to prepare saved replies for configured unread conversations, one at a time. Enable **Auto-refresh every 30 seconds** as well to discover unread changes while the dashboard is open. Both options default to off. New replies show **Draft ready**; open one to edit, approve, or reject normally. Existing pending drafts are preserved, and rejected unchanged conversations are skipped. Model failures pause preparation until **Retry preparation**. Turning preparation off stops new work; an in-progress draft may still finish. No text is sent automatically. Restart the backend after updating to this version, then refresh the dashboard.

## Focused MVP scope

The target is allowlisted messages → recent-window summary → editable reply → explicit approval → send, with manual/automatic inbox refresh and optional automatic drafting **per chat**. See [the agreed flow](docs/PROJECT_FLOW.md).

Two refinements remain: automatic preparation currently uses one global toggle, and manual regeneration does not yet use rejected alternatives to request a different reply. Reject currently retains the draft in history; it does not erase local records. See [the implementation plan](docs/PROJECT_PLAN.md).

Keep SQLite for saved drafts, LangGraph checkpoints, and approval/send state across restarts. No external database, full message archive, RAG, vector database, or additional agents are needed. Existing optional OpenAI support is not required for the local Ollama setup.

### Personalize My voice

In **My voice**, choose **Default voice** or a configured recipient. Add incoming-message/my-response example cards and optional personal style instructions. Recipient examples replace default examples; default instructions still apply.

For a recipient, click **Suggest examples from this chat** to read the recent allowed window without calling a model. Review/edit candidates, select the ones you want, click **Add selected to voice**, then **Save my voice**. Cancel saves nothing. You can edit or remove saved examples later. Changes apply to new drafts, not existing proposals. This is prompting with local examples, not model training or RAG. See [voice personalization](docs/VOICE_PERSONALIZATION.md) for limits.

Restart the backend after updating, then refresh the dashboard to load these features.
