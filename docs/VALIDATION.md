# Validation

Verified during the initial implementation:

- 44 pytest cases pass, covering exact edited-text dispatch, outdated approvals, repeated approvals, rejection, conversation changes, uncertain outcomes, authentication, cross-origin rejection, duplicate drafts, restart persistence, disabled live sending, scoped MCP read arguments, invalid MCP context, and receipt recognition.
- Unread-inbox tests cover read-only summaries, unchanged unread status after rejection, empty/read conversation filtering, summary caching and invalidation, recipient scope, connector errors, capped counts, and structured AI summarization with a fake model.
- Ruff check and format checks pass for backend code.
- TypeScript check and Vite production build pass.
- Chrome manual check: local token login → synthetic draft → edit reply → save version 2 → approve simulated send. The sent state displays the exact edited text and simulated receipt. Additional unread-inbox browser check: list synthetic unread conversations → open context/excerpt → create a draft → reject; the conversation remains unread.

Additional live read-only validation: the pinned official MCP revision exposes unread/date/pagination parameters; the configured conversation returned 50 history rows and zero unread rows. No private text or recipient addresses were printed. Regression tests cover incompatible schemas, escaped transcript separators, and safe API errors.

Not exercised: real iMessage sends, macOS permission prompts, a paid model request, or automated browser end-to-end tests. The browser test uses synthetic conversations only. Live integration requires the setup and compatibility checks described in SETUP.md.

The read-only `ghost.inspect_chat` CLI is tested with synthetic messages for latest unread output, explicit latest-any-status output, history confirmation without private output, allowlist enforcement, and connector errors. It calls neither the model nor the sending API.

Duplicate-thread regression: synthetic SQLite chat metadata verifies latest-activity selection instead of first/highest-row-ID selection, excludes other recipients, handles empty threads and errors, and preserves group identifier variants. Live metadata-only diagnosis confirmed duplicate exact-address threads with different activity dates; no private message bodies were printed.

After duplicate-thread correction, one configured recipient changed from 2019 history to current history and returned one readable unread message (database metadata counts can include non-rendered rows). A different recipient still returned January 29, 2026; exact and normalized-address/direct-membership metadata checks both found no more recent local message for that identity. That remaining mismatch is unresolved pending confirmation of the newer message on this Mac and its sender address; do not attribute it to ordering or claim sync is fixed.

Follow-up verification in Messages.app identified the remaining January-history mismatch: the visible current conversation uses an Apple ID email, while the tested CLI argument was a phone number. The same contact name can label separate address identities. Do not automatically add contact aliases to the allowlist; configure the actual email explicitly when the user wants that thread. No private email or message body is recorded in this document.

AI activation checks: the synthetic smoke-test command exercises structured summary and draft generation and verifies a LangGraph approval pause using a fake model in tests. Model configuration errors reach API callers without sending.

Local Ollama tests cover schema/JSON validation, loopback-only URLs, rejection of cloud aliases, disabled thinking, requests without credentials/tools, and missing-model errors.

Real local smoke test passed with qwen3:4b: a factual coffee-invitation summary and a short timing question were generated from synthetic messages, then the graph paused for approval. Initial instruction echo was corrected by schema grounding and a clearer summary prompt. Ollama reported 100% GPU use, 8192-token context, and about 3.8 GB model memory. This is a functional smoke test, not a comprehensive quality evaluation.

Final send review: five Vitest/DOM tests cover exact saved-message display, no send on open, cancel/Escape, disabled live sending, simulated confirmation, and controls during dispatch. An enabled-live-mode backend test injects a fake connector and verifies the version-2 approval and sending intent are committed before dispatch, with duplicate approval rejected. Frontend TypeScript/production build passes. No real sends were made.

Inbox auto-refresh validation: 11 frontend tests pass in total. Five hook tests cover default-off behavior, 30-second timing/opt-out, overlapping slow requests and busy pauses, error recovery with preserved last-success data/time, and logout cancellation/late-response rejection. An application integration test verifies manual/automatic unread-list changes preserve selected summary/context and unsaved draft text, without extra conversation requests or any mutating requests. Production TypeScript/Vite build, 44 backend tests, and Ruff pass. These refresh tests use synthetic data and mocked fetch; no real sends or model calls are made.

## Voice personalization update

Validated with 50 synthetic backend tests, 15 frontend tests, Ruff, and the TypeScript/Vite production build. New coverage includes legacy profile fallback, exact-recipient input isolation through actual graph drafting, bounded example selection, persisted paired profiles across app restart, read-only preview, unauthorized import refusal, newest-first MCP and oldest-first demo extraction, and reviewed UI select/edit/cancel/save. No real Messages reads or sends were performed for these checks.
