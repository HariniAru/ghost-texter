# Local API

All `/api` routes require `Authorization: Bearer <local token>`. JSON request/response bodies. No CORS is enabled; the dashboard uses a same-origin API or Vite proxy. Bind only to loopback.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | /api/status | Mode, AI status, live-send switch, allowed recipients |
| GET | /api/inbox | Unread conversations for configured recipients; preview, count (up to 50), count_capped. Leaves out a chat whose newest unread message is in the context of a reply sent from the app |
| GET | /api/conversation?recipient=… | Recent context, fingerprint, summary, and summary_kind (ai or excerpt). With `summary=false` it returns at once, with the summary only if already cached for that fingerprint, otherwise `null` |
| GET | /api/conversation/summary?recipient=…&fingerprint=… | Summary for the messages last returned by `summary=false`; 409 if the conversation changed since |
| GET | /api/contacts | Contacts as `{name, address, source}`; source is `env`, `app`, or `demo`; name is blank if none was saved |
| POST | /api/contacts | Add a contact, or rename a saved one; `{name, number}`; returns all contacts |
| DELETE | /api/contacts?address=… | Remove a contact added in the dashboard; returns all contacts |
| GET | /api/drafts | Saved drafts and conversation snapshots, in every status except `sent` |
| POST | /api/drafts | Read recipient context and create a paused review; `{recipient}` |
| POST | /api/inbox/prepare | Opt-in automatic preparation for one recipient; `{recipient}` |
| POST | /api/drafts/typed | Save a reply the user wrote as a pending draft, without the model; `{recipient, text, fingerprint}`, where `fingerprint` is the conversation they were reading. 409 if messages arrived since or the chat already has a saved draft; never sends |
| PATCH | /api/drafts/{id} | Save an edit; `{version, text}`; returns incremented version |
| POST | /api/drafts/{id}/refresh | Keep the saved text and bind a new version to the latest messages; `{version}`; never sends |
| POST | /api/drafts/{id}/verify | For an `uncertain` draft: reread the chat and mark it `sent` if the message is there; never sends |
| POST | /api/drafts/{id}/retry | For an `uncertain` draft: check once more, then return a new pending draft with the same text; never sends |
| POST | /api/drafts/{id}/discard | For an `uncertain` draft: hide it and keep its records |
| POST | /api/drafts/{id}/approve | Approve and attempt dispatch; `{version}`; returns the sent draft, including its receipt. In demo mode it does nothing and returns the draft unchanged (still `pending`, no receipt) |
| POST | /api/drafts/{id}/reject | Reject without dispatch; `{version}`. The dashboard's **Clear** and replacing a draft use this |
| GET | /api/profile | Current style instructions and user-written examples |
| PUT | /api/profile | Replace profile; `{style, examples: string[]}` |

Pending drafts for the same recipient and identical context are deduplicated. Creating a new pending draft after rejection is allowed: POST /api/drafts gives the model up to 5 drafts rejected for the same context fingerprint and returns 502 if the new reply repeats one. 401 means authentication failure, 403 disabled operation or untrusted origin, 404 unknown draft, 409 stale version/status/context, 422 invalid input, and 502 connector/model failure or uncertain dispatch. Validation errors use FastAPI's standard detail array. Interactive API docs are at `/docs`.

Once a draft is `sent` it no longer appears in GET /api/drafts, so the approve, verify, or retry response is the only place a client gets its receipt. `uncertain` drafts stay listed until they are found in Messages, retried, or discarded. Automatic preparation still treats a sent draft as reviewed, so its `already_reviewed` response can carry one.

Inbox loading and summary generation never create drafts, send messages, or mark messages read. Summary responses are cached in memory per recipient and context fingerprint; unchanged selections do not repeat model calls. Refresh checks unread status on demand or through an opt-in 30-second browser timer. This only calls GET /api/inbox; conversation summaries remain selection actions; automatic drafting is a separate opt-in. An MCP failure returns 502 rather than an empty inbox.

Automatic preparation returns `{created, reason, draft}`. It preserves any pending/sending/uncertain review for that recipient (`existing_review`), rechecks unread status (`not_unread`), skips a latest outgoing message (`latest_outgoing`), and skips a conversation a sent reply already answered (`already_sent`). Rejected drafts do not block it; their texts are passed to the model to avoid. Otherwise it creates a normal paused draft (`created`). Manual drafting after rejection remains available. This endpoint never approves or sends.

## Contacts

Contacts decide which chats the app may read, draft for, and send to. The live list is `GHOST_ALLOWED_RECIPIENTS` plus addresses added in the dashboard, which are stored in the local SQLite database. There are at most 50, and every other route checks this list.

POST takes a required name and a full phone number. It removes formatting such as spaces and parentheses, but never guesses a country code or uses the name to find a chat. It reads a new number once to confirm the chat exists on this Mac; the text is discarded and nothing is sent. If the connector reports no chat, POST returns 422 with `Chat not found with this contact.` Other read failures keep their own errors, so a permissions problem does not look like a missing chat. An invalid number (422) or a connector failure (502) saves nothing. Posting a number already on the list only updates its name, including a `.env` number, whose name is stored locally. If that number is later removed from `.env`, it stays a contact until removed in the dashboard. Names are display labels: they grant no access and are not sent to the model. Addresses from `.env` may still be emails. DELETE returns 409 for a `.env` contact, which must be removed from `.env`, and 404 for an unknown address. Both changes return 403 in demo mode, which only lists synthetic recipients, so real addresses are never stored there.

## Voice profiles

GET /api/profile returns `{style, examples, pairs, recipients}`; PUT replaces that profile after validation. `pairs` contains `{incoming, response}` objects. `recipients` maps exact allowlisted addresses to `{style, examples, pairs}` overrides. Old `{style, examples}` payloads still work with empty new fields; PUT remains a full replacement, so clients editing extended profiles must retain the other fields. Recipient overrides cannot grant messaging access, and new override addresses must be current contacts. Overrides for a removed contact are kept, so its voice returns if it is added again. Global style plus recipient additions inform new drafts; nonempty recipient examples replace global examples, otherwise defaults apply.

POST /api/profile/suggestions accepts `{recipient}` and returns `{pairs}` extracted from the current chat window. It requires authentication and an allowed recipient, calls only the read adapter, and does not call a model or persist anything. The dashboard previews/edits/selects candidates, adds them to the local editor, then explicitly saves through PUT /api/profile. No reliable pair yields an empty list; read failure yields 502. Limits and extraction boundaries are in [VOICE_PERSONALIZATION.md](VOICE_PERSONALIZATION.md).
