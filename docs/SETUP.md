# Setup

Follow the root README for the working demo. Launch all commands from the repo root unless specified otherwise. The API token is generated on first backend startup and persisted in `data/api-token` with owner-only file permissions. It is required on all API endpoints. The browser keeps it in session storage; Lock workspace removes it.

## Personalized AI drafts

For local AI, follow OLLAMA.md; no API key is required. For OpenAI, set `GHOST_LLM_PROVIDER=openai`, `GHOST_LLM=true`, and `OPENAI_API_KEY` in `.env`. Optionally set `GHOST_MODEL`. Restart the backend. Add writing samples in My voice. For OpenAI, the selected conversation, your style, and your examples will be sent to the model provider; no message tools are exposed to the model. Without LLM mode, replies are deliberately canned placeholders and do not claim to imitate you.

## iMessage through Mac Messages MCP

The adapter targets carterlasalle/mac_messages_mcp's stdio tools, not any arbitrary Messages MCP implementation. It reads direct conversations via `tool_get_recent_messages` with an exact `chat_id` scope and sends via `tool_send_message`. Group chats and attachments are not supported in this release.

1. Install uv and ensure `uvx` is on the backend process's PATH.
2. Grant the launching Terminal app Full Disk Access in macOS System Settings → Privacy & Security. Restart that app. Messages must be signed in. Sending also requires Automation access to Messages; macOS may prompt on first use.
3. Set these values in `.env`, using your actual recipient:

```dotenv
GHOST_MODE=imessage
GHOST_MCP_COMMAND=uv
GHOST_MCP_ARGS=["run","--no-project","--with","git+https://github.com/carterlasalle/mac_messages_mcp.git@8eae89d9d9eae97333f4401ef47393d5e35f58ab","python","backend/ghost/mcp_server.py"]
GHOST_ALLOWED_RECIPIENTS=["+14155550123"]
GHOST_SEND_ENABLED=false
```

4. Restart the backend. The Unread inbox checks your allowlisted recipients for unread inbound messages. Select a conversation to see recent context and a summary, then request a draft. Use Refresh inbox for new messages. Existing drafts remain in Draft history. The adapter retrieves up to the latest 50 messages, with a fixed starting date. It uses the recipient as the exact existing Messages chat identifier, including outgoing context. If this identifier does not resolve on your connector version, reads fail closed; no broader contact-search fallback is used. Review context and draft. Permission errors fail closed.
5. When ready to use the app for real sends, set `GHOST_SEND_ENABLED=true` and restart. The dashboard's **Approve & send** button authorizes the exact saved reply. Every later message still needs approval.

Use exact E.164 phone numbers or emails, never fuzzy contact names. Adding a recipient is a local configuration change. The application checks unread messages only for allowlisted recipients. It does not enumerate all conversations, mark messages read, or automatically send anything. Unread counts show up to 50 messages (50+ when capped). With AI disabled, the summary area shows a labeled message excerpt instead. Run it on the Mac with Messages access, outside Linux Docker.

The MCP is launched via uv from the pinned official GitHub revision above, through the project wrapper. The PyPI 1.1.0 package inspected during diagnosis advertises only hours/contact/chat_id for recent reads; newer unread/date/pagination arguments were silently ignored. Do not substitute that older package launcher. The adapter now checks the advertised schema before invoking a tool and reports incompatible versions explicitly. It also handles escaped timestamped transcript separators while retaining the untrusted-data envelope. No live sends are performed by the project test suite.

Read-only validation on the configured Mac retrieved 50 history rows; the selected chat reported zero unread rows at that time. Read availability and unread status are separate checks. To test the inbox, leave a new incoming message unread in Messages, then refresh.

## Troubleshooting

- 401: paste the token from the configured data directory; restart the server after changing environment configuration.
- 409: the draft version or conversation changed. Refresh and generate a new draft if stale.
- 502 on draft: check your model API key, MCP executable, and macOS permissions.
- Uncertain send: verify the recipient's conversation in Messages. The same draft cannot be retried. Do not create another draft until you have checked whether delivery occurred.
- The dashboard appears missing: run `npm ci && npm run build` inside frontend before starting the API, or use the Vite development server.

## Inspect one chat directly from the backend

No running FastAPI or frontend process is needed. Run from the repository root; this reads the current `.env` on each invocation. The command does not send, invoke a model, mark messages read, or write a message archive. It intentionally displays the selected message in your terminal, so do not share that output if private.

```sh
uv run python -m ghost.inspect_chat --recipient "+14155550123"
```

Replace the example with an exact recipient already in `GHOST_ALLOWED_RECIPIENTS`. If exactly one recipient is configured, omit `--recipient` to use it without putting the number in shell history:

```sh
uv run python -m ghost.inspect_chat
```

Default behavior prints only the latest unread incoming message. If none is returned, the command separately checks history availability and reports a count without showing history contents. To compare against the latest message of any read status (which may be outgoing), explicitly run:

```sh
uv run python -m ghost.inspect_chat --latest
```

Exit codes: 0 = displayed a matching message, 1 = no unread incoming messages but chat history is readable, 2 = configuration/connector/history error. Unread filtering uses the database's message-level read flag; it should not be assumed equivalent to a conversation badge or manual Mark as Unread. Demo mode uses synthetic messages.

## Duplicate chat addresses

Messages can store multiple chat rows for the same phone/email (for example old and current service threads). Upstream exact identifier lookup uses an unordered LIMIT 1. The project now launches the pinned MCP through `backend/ghost/mcp_server.py`, which selects the exact-match thread with the latest message activity, with a deterministic row-ID tie break. It does not fall back to fuzzy contacts or merge group history. Database reads remain inside the MCP process through the upstream read-only helper. The wrapper depends on the pinned upstream private lookup function, so validate it when updating the MCP revision.

This selects one most recently active thread; it does not merge all historical threads for a person or combine phone and email identities. The CLI and app use the same lookup. Restart the backend after updating .env; CLI commands load the current configuration on every run.


## Validate AI before using private conversations

For local Ollama, configure the provider as described in OLLAMA.md. For OpenAI, add `OPENAI_API_KEY` to the root `.env` locally; do not paste it into chat or commit it. Keep `GHOST_SEND_ENABLED=false`. The following command forces AI on for its own synthetic test only, even while `GHOST_LLM=false`:

```sh
uv run python -m ghost.check_ai
```

It makes two model requests using synthetic messages and a synthetic voice profile: one summary and one draft. It never opens Messages, loads your saved profile, persists a draft, or sends anything. A successful run prints the summary/reply and confirms the graph paused for approval. Missing credentials fail before network access. Authentication, billing, model access, or network failures return a sanitized error. This test uses API credits only with the OpenAI provider; Ollama runs locally.

After it passes, set `GHOST_LLM=true`, restart the backend, and open one selected conversation. Its latest context will go to the selected model for a summary (local Ollama or OpenAI); drafting additionally sends your saved voice profile. Add representative examples in My voice. Reject any old pending sample draft before requesting an AI draft for unchanged context, because pending reviews are deduplicated. Inspect summary accuracy and edit/reject replies as needed. Live sending remains a separate future test.

## Keep the unread inbox current

Enable **Auto-refresh every 30 seconds** in the inbox toolbar. It defaults to off and resets when you lock/reload the workspace. While the dashboard is open, it refreshes only the allowlisted unread list. Manual Refresh inbox uses the same list-only operation. Neither action reloads your selected conversation/summary or replaces unsaved draft edits. Select a conversation again to fetch its current messages/summary once edits are saved. Timer ticks are skipped while another action or send confirmation is active, and slow requests never overlap.

The status line shows the last successful refresh. On failure, the previous inbox remains visible with an error; a later successful refresh clears it. No messages are marked read or sent, and no model calls/draft generation are triggered by polling. Browser/OS throttling and computer sleep can delay the 30-second schedule. There is no background refresh when the dashboard is closed.
