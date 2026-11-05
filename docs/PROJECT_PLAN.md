# Project plan

Product scope is defined in [PROJECT_FLOW.md](PROJECT_FLOW.md). Focus on finishing and presenting the single-user local approval workflow, not adding infrastructure.

## Implemented

- FastAPI API, React/TypeScript dashboard, synthetic demo, and allowlisted Mac Messages MCP adapter.
- Manual unread inbox refresh and opt-in 30-second browser refresh, preserving selected context and unsaved editor text.
- Up to 50 recent messages per exact-address thread, summary/excerpt, manual editable reply generation, and style examples.
- Saved drafts and versions, rejection, draft history, LangGraph durable review pause, and local SQLite persistence.
- Paired voice examples, exact-recipient styles, and reviewed deterministic import from the existing chat window; no silent learning.
- Local Ollama summaries/drafts; existing optional OpenAI compatibility.
- A global opt-in serial browser preparation queue, preserving pending drafts and skipping previously reviewed unchanged context. This is not yet per-chat opt-in.
- Exact-version/recipient/body/context approval checks, final confirmation dialog, persisted dispatch intent, duplicate protection, and uncertain-outcome handling.
- Local API token, origin restrictions, synthetic tests, lint, and frontend build checks.
- User-reported successful live reading and sending. Automated tests use synthetic connectors only.

## Next small implementation steps

1. Replace the global automatic-drafting toggle with per-chat opt-in controls. Store choices locally, scope them to configured recipients, and keep refresh independent. Test that enabling one chat cannot generate drafts for another and that pending edits remain untouched.
2. Make rejection/discard and explicit regeneration clear in the UI. Supply rejected alternatives for the same snapshot to generation, request a different response, and handle repeated identical output without unbounded retries. Preserve rejection/dispatch records internally. Current rejection is retained in history; current manual generation can create another draft but does not yet use rejected text to avoid repetition.
3. Audit unsaved-edit navigation and discard warnings across inbox/history/locking. Retain saved drafts across restart without adding a separate database service or bookmark model.
4. Finish the GitHub demo: verify clean synthetic setup, record the core flow, add representative screenshots/architecture explanation, and check tracked files for private data. Keep the existing test/build commands reproducible; add a small CI workflow if needed.

## MVP acceptance walkthrough

With synthetic data: refresh → open conversation → summary → generate → edit/save → leave and reopen saved draft → discard → generate a different alternative → confirm simulated send. Enable automatic preparation for one chat and verify other chats remain manual. Exercise stale context, connection failure, duplicate approval, and uncertain dispatch with fake connectors. No development step requires sending a real text.

## Deferred

No RAG, extra agents, database services, cloud deployment, multi-worker operation, additional messaging platforms, full contact merging, group chats, or server-side monitoring. A future uncertain-send reconciliation UI and retention controls may improve usability but must not weaken the current no-retry rule. See APPROVAL_CONTRACT.md for runtime boundaries.
