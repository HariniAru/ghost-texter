# Ghost Texter

@AGENTS.md

The rules in AGENTS.md are binding. This file adds the product outline, current status, and code map.

## What this is

A single-user, local macOS tool for catching up on and replying to iMessages:

1. Find unread messages in the chats listed in `GHOST_ALLOWED_RECIPIENTS` and show them in an inbox.
2. Pull the latest 50 messages of a conversation and show a quick summary as a refresher.
3. Draft a reply in the user's voice, automatically or on request, which the user can edit or regenerate.
4. Keep unsent drafts so the user can come back to them. A draft leaves the saved list once it is properly sent.
5. Learn voice from a default profile plus examples per person. For example, replies to the user's brother are curt with a lot of banter, so his profile should not sound like the default.

Nothing is ever sent without explicit approval of the exact saved text.

## Feature status

`docs/PROJECT_FLOW.md` is the target and `docs/PROJECT_PLAN.md` tracks gaps. Do not describe a target as shipped.

| Feature | Today | Gap |
| --- | --- | --- |
| Unread inbox | `GET /api/inbox` checks each address in `GHOST_ALLOWED_RECIPIENTS`; manual refresh or opt-in 30s browser timer | None for now. Keep the allowlist: expanding to all chats is a later decision, after everything is verified working |
| 50-message context and summary | `GET /api/conversation`; AI summary of up to three sentences, or a labeled excerpt when AI is off; cached per recipient and fingerprint | None |
| Automatic drafts | Browser queue behind one global toggle, off by default | Replace with saved per-chat opt-in |
| Edit | Save increments the version | None |
| Regenerate | Only by rejecting, then drafting again. `POST /api/drafts` returns the existing pending draft for an unchanged snapshot | Add explicit regeneration informed by rejected alternatives. Ollama runs at temperature 0, so an unchanged prompt will tend to repeat the same text |
| Saved drafts | Draft history shows every draft of every status and survives restarts | Remove `sent` drafts from the list (see below) |
| Voice | Default style and examples, paired examples, exact-address overrides, reviewed import from a chat | None |

### Sent drafts

Decided, not yet built: once a draft reaches `sent`, it has become a real message and is no longer needed, so it is removed from the saved drafts list. `GET /api/drafts` and Draft history currently return it, and `frontend/src/App.tsx` finds the open draft in that same list to show the send receipt, so the receipt must keep working.

- Only a connector-acknowledged `sent` qualifies. `uncertain` must stay visible, because the user has to check Messages before doing anything else.
- Removing a draft from the list is not the same as deleting dispatch evidence. Keep the approval and send records on disk.

## Code map

Backend, in `backend/ghost/`:

- `main.py`: `create_app` factory holding all routes, auth, the allowlist check, and approve/dispatch.
- `workflow.py`: LangGraph draft → `interrupt` review graph, plus `summarize`. Dispatch stays out of the graph so replay cannot resend.
- `messaging.py`: `Messenger` protocol (`unread`, `read`, `send`), `DemoMessenger`, `MacMessages`.
- `voice.py`: profile validation, `resolve_profile`, and the deterministic `suggest_pairs` import.
- `store.py`: SQLite drafts, events, and profile tables. It is the authority for text, versions, and status. Startup turns any leftover `sending` into `uncertain`.
- `ollama_model.py`: loopback-only structured Ollama client.
- `mcp_server.py`: wrapper around the pinned Messages MCP that picks the most recently active exact-match thread.
- `config.py`: `GHOST_*` settings.
- `check_ai.py`: synthetic model smoke test.
- `inspect_chat.py`: read-only terminal view of a chat.

Frontend, in `frontend/src/`:

- `App.tsx`: nearly all the UI.
- `VoiceEditor.tsx`: My voice.
- `SendConfirmation.tsx`: final send dialog.
- `useInboxRefresh.ts`, `useAutoPrepare.ts`: browser timers and the draft queue. There is no server-side background worker.

Draft statuses: `pending` → `rejected` | `stale` | `sending`, then `sending` → `sent` | `uncertain`. All except `pending` and `sending` are terminal.

## Commands

Run from the repo root unless noted.

```sh
uv sync --extra dev
uv run pytest
uv run pytest backend/tests/test_voice.py -k <name>
uv run ruff check backend
cd frontend && npm ci && npm test && npm run build
cd frontend && npx vitest run src/App.test.tsx
```

To run the app for verification, use the `verify-demo` skill. Do not start uvicorn directly, because that loads the user's `.env`. Before calling work done on drafts, approval, sending, automatic preparation, or the model prompt, run the `approval-safety-check` skill.

Backend changes and `.env` changes need a backend restart.

## Things that are easy to get wrong

- The root `.env` and `data/` may hold live settings, tokens, and private messages. Do not open them. A plain backend start uses that `.env`, and `ghost.inspect_chat` prints real messages in live mode, so neither is a safe way to verify a change.
- New tests must pass `_env_file=None` and `data_dir=tmp_path` to `Settings`, and use a fake messenger, as the existing tests do.
- Transcript order differs by source: MCP is newest first and demo is oldest first. Anything that parses context must handle both; see `suggest_pairs` and `MESSAGE_ROW`.
- Fingerprints hash the whole 50-message window. `stale` is only set during approval, so a pending draft can be out of date until then.
- Voice resolution: recipient style is added to the default style, but any recipient examples replace the default examples. Keys are exact addresses, so a person's phone number and Apple ID email are separate profiles.
- `PUT /api/profile` is a full replacement. Clients must send back the fields they did not edit.
- `config.py` defaults to the OpenAI provider and `gpt-4.1-mini`. The Ollama default comes from `.env.example`, so set the provider explicitly in code and tests.
- Trusted browser origins are hardcoded in `authorize` in `main.py`, on ports 8001 and 5173. A server on another port gets a 403 on browser UI actions, which is why `verify-demo` uses 8001. Do not widen the list just to make testing easier.
- Update `docs/API.md` and `docs/APPROVAL_CONTRACT.md` when routes or draft lifecycle rules change, including the sent-draft change above.
