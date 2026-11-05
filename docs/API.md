# Local API

All `/api` routes require `Authorization: Bearer <local token>`. JSON request/response bodies. No CORS is enabled; the dashboard uses a same-origin API or Vite proxy. Bind only to loopback.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | /api/status | Mode, AI status, live-send switch, allowed recipients |
| GET | /api/inbox | Unread conversations for configured recipients; preview, count (up to 50), count_capped |
| GET | /api/conversation?recipient=… | Recent context, fingerprint, summary, and summary_kind (ai or excerpt) |
| GET | /api/drafts | All drafts and conversation snapshots |
| POST | /api/drafts | Read recipient context and create a paused review; `{recipient}` |
| POST | /api/inbox/prepare | Opt-in automatic preparation for one recipient; `{recipient}` |
| PATCH | /api/drafts/{id} | Save an edit; `{version, text}`; returns incremented version |
| POST | /api/drafts/{id}/approve | Approve and attempt dispatch; `{version}` |
| POST | /api/drafts/{id}/reject | Reject without dispatch; `{version}` |
| GET | /api/profile | Current style instructions and user-written examples |
| PUT | /api/profile | Replace profile; `{style, examples: string[]}` |

Pending drafts for the same recipient and identical context are deduplicated. Creating a new pending draft after rejection is allowed. 401 means authentication failure, 403 disabled operation or untrusted origin, 404 unknown draft, 409 stale version/status/context, 422 invalid input, and 502 connector/model failure or uncertain dispatch. Validation errors use FastAPI's standard detail array. Interactive API docs are at `/docs`.

Inbox loading and summary generation never create drafts, send messages, or mark messages read. Summary responses are cached in memory per recipient and context fingerprint; unchanged selections do not repeat model calls. Refresh checks unread status on demand or through an opt-in 30-second browser timer. This only calls GET /api/inbox; conversation summaries remain selection actions; automatic drafting is a separate opt-in. An MCP failure returns 502 rather than an empty inbox.

Automatic preparation returns `{created, reason, draft}`. It preserves any pending/sending/uncertain review for that recipient (`existing_review`), rechecks unread status (`not_unread`), skips a latest outgoing message (`latest_outgoing`), and skips any previously reviewed identical fingerprint (`already_reviewed`). Otherwise it creates a normal paused draft (`created`). Manual drafting after rejection remains available. This endpoint never approves or sends.

## Voice profiles

GET /api/profile returns `{style, examples, pairs, recipients}`; PUT replaces that profile after validation. `pairs` contains `{incoming, response}` objects. `recipients` maps exact allowlisted addresses to `{style, examples, pairs}` overrides. Old `{style, examples}` payloads still work with empty new fields; PUT remains a full replacement, so clients editing extended profiles must retain the other fields. Recipient overrides cannot grant messaging access. Global style plus recipient additions inform new drafts; nonempty recipient examples replace global examples, otherwise defaults apply.

POST /api/profile/suggestions accepts `{recipient}` and returns `{pairs}` extracted from the current chat window. It requires authentication and an allowed recipient, calls only the read adapter, and does not call a model or persist anything. The dashboard previews/edits/selects candidates, adds them to the local editor, then explicitly saves through PUT /api/profile. No reliable pair yields an empty list; read failure yields 502. Limits and extraction boundaries are in [VOICE_PERSONALIZATION.md](VOICE_PERSONALIZATION.md).
