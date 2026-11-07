# Ghost Texter

@AGENTS.md

The rules in AGENTS.md are binding. This file adds the product outline, current status, and code map.

## What this is

A single-user, local macOS tool for catching up on and replying to iMessages:

1. Find unread messages in the user's contacts and show them in an inbox. Contacts are added on the People tab or listed in `GHOST_ALLOWED_RECIPIENTS`.
2. Pull the latest 50 messages of a conversation and show a quick summary as a refresher.
3. Draft a reply in the user's voice, automatically or on request, which the user can edit or regenerate.
4. Keep unsent drafts so the user can come back to them. A draft leaves the saved list once it is properly sent.
5. Learn voice from a default profile plus examples per person. For example, replies to the user's brother are curt with a lot of banter, so his profile should not sound like the default.

Nothing is ever sent without explicit approval of the exact saved text.

## Feature status

`docs/PROJECT_FLOW.md` is the target and `docs/PROJECT_PLAN.md` tracks gaps. Do not describe a target as shipped.

| Feature | Today | Gap |
| --- | --- | --- |
| Contacts | Add and remove a name and exact phone number on the People tab, stored in SQLite; `.env` addresses still count and can only be removed there | `ghost.inspect_chat` still uses only `.env` |
| Unread inbox | `GET /api/inbox` checks each contact; manual refresh or opt-in 30s browser timer. In live mode a chat is hidden once you send a reply from the app whose context includes its newest unread message, and returns when they write again. Demo mode never hides a chat, because demo Send does nothing | None for now. Keep the contacts boundary: expanding to all chats is a later decision, after everything is verified working |
| 50-message context and summary | `GET /api/conversation`; AI summary of up to three short sentences (about 40 words), or a labeled excerpt when AI is off; cached per recipient and fingerprint | None |
| Automatic drafts | Browser queue behind one global toggle, off by default. Turning it on drafts every unread chat that has no pending draft, including ones whose earlier drafts were rejected | Replace with saved per-chat opt-in |
| Reply box | Sits in one card with the messages it answers (unread messages directly above it, earlier ones in a fold above them; the summary is a separate short card; `thread.ts` splits the text and reads message times for display only). Always shown on an open chat, empty until there is a saved draft. It autosaves about 1.2 seconds after typing stops (one save at a time, each from the server's current version), and **Send** saves it, using `POST /api/drafts/typed` for typed text, before opening the confirmation. **Undo** brings back text that Clear or a new draft replaced. **Cmd+Enter** (or Ctrl+Enter) in the box opens the same confirmation as Send and never sends; **Cmd+Shift+Enter** drafts. A failed autosave shows an alert and keeps the text. Leaving the chat saves it too. Each save increments the version | None |
| Regenerate | **Draft a reply** over an existing draft rejects it and drafts again, after asking if the box has text. **Clear** also rejects. `POST /api/drafts` returns the existing pending draft for an unchanged snapshot The model gets up to 5 rejected drafts for the same fingerprint and is asked for a different reply. With rejected drafts it asks for four replies at temperature 0.8 instead of 0 and uses the first that is not a rejected one; if all repeat, the graph loops back to `draft` (temperature 1.0), up to 3 tries; if every try repeats one, the request fails with a 502, "Failed to generate a response draft. Try again." New messages or a sent reply change the fingerprint, so the list starts again | None |
| Saved drafts | Each inbox chat keeps its pending draft or uncertain send, even with nothing unread, and survives restarts. Rejected and stale drafts stay in `GET /api/drafts` but are not shown | None |
| Voice | Default style and examples, paired examples, exact-address overrides, reviewed import from a chat | None |

### Sent drafts

Demo mode never sends: `approve` returns the pending draft untouched (no dispatch, status change or event), so the sample chats stay unread. Everything below is live mode.

Once a draft reaches `sent` it leaves `GET /api/drafts` and the inbox. The dashboard takes the receipt from the approve response, because the draft is no longer in the list.

- `sent` needs a connector acknowledgment, or the exact text found as an outgoing message at or after approval. `uncertain` stays visible until it is found, retried, or discarded. See `useSendCheck.ts` and "Interrupted sends" in `docs/APPROVAL_CONTRACT.md`.
- Removing a draft from the list is not the same as deleting dispatch evidence. The row and the approval and send records stay on disk.
- Filter with `store.saved()` only for what the user sees. Automatic preparation needs `store.all()`, or it would redraft a snapshot that was already answered.

## Code map

Backend, in `backend/ghost/`:

- `main.py`: `create_app` factory holding all routes, auth, the allowlist check, and approve/dispatch.
- `workflow.py`: LangGraph draft → `interrupt` review graph, plus `summarize`. A draft that repeats a rejected one loops back to `draft`, up to 3 times, then `give_up` fails the request. Dispatch stays out of the graph so replay cannot resend.
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
- `VoiceEditor.tsx`: the Customize voice button on each People card, which opens that voice in a pop-up (`<dialog>`) with Save and Close pinned in its header. Closing with unsaved edits asks first; Discard restores the saved voice. Each card saves only its own edits.
- `ContactsPanel.tsx`: the People tab: an add row, a Default voice card, and a grid of contact cards showing whether each has a personal voice.
- `SendConfirmation.tsx`: final send dialog.
- `useInboxRefresh.ts`, `useAutoPrepare.ts`, `useSendCheck.ts`: browser timers and the draft queue. There is no server-side background worker.

There are two tabs, Inbox and People. Draft statuses: `pending` → `rejected` | `stale` | `sending`, then `sending` → `sent` | `uncertain`, then `uncertain` → `sent` | `discarded`. `rejected`, `stale`, `sent`, and `discarded` are terminal.

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
- Live reads go through `text_only` in `messaging.py`, which drops reactions, attachment-only messages and the connector's paging note, so a chat can show fewer than 50 messages. Reactions also do not make a chat unread.
- Fingerprints hash the whole 50-message window. `stale` is only set during approval, so a pending draft can be out of date until then. The inbox warning is advice only; `POST /api/drafts/{id}/refresh` is the only way to rebind a draft to newer messages.
- Voice resolution: the model sees a recipient's style first, labeled as overriding, followed by the default style; any recipient examples replace the default examples. The prompt names them `voice_rules` and tells the model to follow them strictly, including on a redraft. Keys are exact addresses, so a person's phone number and Apple ID email are separate profiles.
- Prompt order is for speed: every model call uses the one `SYSTEM` prompt, the conversation comes first in the user message and the task last. Ollama then reuses its reading of the 50 messages across the summary, a draft and a redraft (a draft after the summary takes about 2s instead of 6s). Do not put anything that varies, such as the task or voice, ahead of the conversation. `test_prompt.py` checks this.
- Model instructions in `workflow.py` are deliberately terse to save tokens, in the style of the `caveman` skill, but must keep every never/not and ask for normal readable output. Conversation text goes to the model verbatim, with `ensure_ascii=False` so emoji and accents are not escaped. `test_prompt.py` checks both.
- Use `live_recipients()` in `main.py`, not `settings.allowed_recipients`, for anything about who the app may read or send to. Only the source label and the `.env` removal check should read the setting directly.
- `PUT /api/profile` is a full replacement. Clients must send back the fields they did not edit.
- The model is always the local Ollama client (`create_model` in `workflow.py`). `config.py` defaults to `qwen3:4b`; there is no cloud provider.
- Trusted browser origins are hardcoded in `authorize` in `main.py`, on ports 8001 and 5173. A server on another port gets a 403 on browser UI actions, which is why `verify-demo` uses 8001. Do not widen the list just to make testing easier.
- Update `docs/API.md` and `docs/APPROVAL_CONTRACT.md` when routes or draft lifecycle rules change.
- UI redesign work uses the `impeccable` skill (`.claude/skills/impeccable`). It keeps design context in root `PRODUCT.md` and `DESIGN.md` plus `.impeccable/`. A redesign must not change approval behavior: Send still opens the final confirmation, and only its confirm button calls approve. Do not use `/impeccable live` (it can launch an unsandboxed agent) and do not turn on its edit hook without asking.
