# Minimal MVP product scope

This document replaces the original broad stack proposal. It describes the agreed target; see PROJECT_PLAN.md for implementation gaps. Do not interpret target behavior as already shipped.

## Purpose

Help one user catch up on allowlisted direct iMessage conversations, prepare replies in their voice, and send only after explicit review. Demonstrate a bounded, stateful LangGraph workflow with human approval and a backend-controlled MCP adapter.

## User flow

1. Connect to the local dashboard. The backend reads only configured exact recipient addresses through the Messages MCP adapter. Current live reads cover up to 50 recent messages from the most recently active matching thread, not every thread belonging to a contact. Phone numbers and Apple ID emails remain separate identities.
2. Refresh the unread inbox manually, or opt into periodic refresh while the dashboard is open. Reading here does not mark messages read. Refreshing the list preserves the open conversation and unsaved edits.
3. Open a conversation to see recent messages and a short summary of that fetched window. Label the summary as partial context, not the entire chat history. Synthetic demo mode works without Messages access; AI-disabled mode shows an excerpt.
4. Press **Draft a reply** to generate an editable proposal. Alternatively, opt into automatic draft preparation for that individual chat. Enabling one chat must not enable the others. Automatic preparation handles new unread context, preserves pending edits, and never sends.
5. Edit and save a draft to return to it later. Current persistence saves generated drafts automatically; a separate save/bookmark mechanism is unnecessary for the MVP. Warn before discarding unsaved edits.
6. Discard an unwanted pending draft, then explicitly generate an alternative. Retain rejected alternatives internally for the same conversation snapshot so regeneration can request different wording or approach without inventing new facts. Do not promise every model output will be unique: detect identical output and report that no new alternative was produced rather than retrying indefinitely. Automatic preparation must not regenerate a rejected unchanged snapshot without user action.
7. Review the exact saved recipient and body, then explicitly confirm sending. The backend rechecks version and context, saves intent, and makes one send attempt. A changed conversation requires a fresh draft/review. An uncertain result requires checking Messages; never automatically retry it.

## Consolidated stack

| Component | Responsibility |
| --- | --- |
| Python + FastAPI + Pydantic | Local API, validated inputs/outputs, approval and dispatch checks |
| LangGraph | Draft → durable human-review pause → decision; no dispatch inside replayable graph nodes |
| React + TypeScript + Vite | Inbox, summary, editor, opt-ins, and final send confirmation |
| SQLite + SQLite graph checkpointer | Local saved drafts, versions, decisions, dispatch state, and workflow resume |
| Ollama | Local summaries and replies; no hosted inference account required |
| MCP Python SDK + Mac Messages adapter | Allowlisted reads and backend-controlled approved sends |
| Pytest, Ruff, Vitest, TypeScript/Vite build | Synthetic safety tests and implementation checks |

The model receives context and style examples, not messaging tools or approval authority. Existing optional OpenAI integration may remain; it is not part of the required free local setup. LangChain model integrations may remain where useful; a separate agent executor or retrieval layer adds no needed behavior.

## My voice extension

Target: repeatable incoming-message/my-response cards, global defaults plus optional exact-recipient styles, and explicit reviewed example import from the existing allowlisted message window. Only user-authored replies inform the response style. Import requires preview and save; refresh and sending never silently train or update the profile. These features are implemented; saving the edited profile is explicit, and deterministic import does not call a model. See [VOICE_PERSONALIZATION.md](VOICE_PERSONALIZATION.md).

## Persistence boundary

No external database server or full message archive is needed. Keep the existing local SQLite storage: saved drafts must survive restarts, and approval/send state must survive crashes to prevent accidental retries. Context snapshots and rejected alternatives are private local data. Discard means remove from the active review queue, not erase the evidence needed to protect an in-flight or uncertain send. True history erasure and automated retention policies are outside this MVP.

## Essential completion criteria

- Clear loading, empty, error, and retry states; failures never masquerade as an empty inbox or successful send.
- Preserve unsaved edits and bind approval to exact saved content and recipient.
- Disable duplicate sends; surface stale context and uncertain outcomes clearly.
- Per-chat automatic drafting defaults off, with clear indication of enabled chats. Document whether settings survive reload; persist per-chat choices locally for the target MVP. Auto-refresh remains a separate control.
- Synthetic demo with no credentials or live Messages permissions, concise setup, and a short recorded walkthrough for GitHub.
- Exclude tokens, environment secrets, message data, local databases, and checkpoints from source control.

## Outside this MVP

RAG, embeddings/vector databases, multi-agent systems, PostgreSQL/ORM/migrations, cloud deployment, server-side monitoring, full contact identity merging, group chats, attachments, scheduled or automatic sending, and additional messaging platforms. Do not expand scope to demonstrate more frameworks.
