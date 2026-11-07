# Voice personalization

## Current behavior

The People tab supports global instructions and standalone examples on a Default voice card, plus paired incoming/reply cards, exact-recipient overrides, and reviewed deterministic chat import on each person's card, through the existing local profile storage. Voice settings are optional and collapsed by default. Each card's changes require its own Save my voice and do not save other cards' edits.

## Experience

- Keep a global default style and existing standalone examples.
- Add repeatable example cards with **Incoming message** and **My response** fields. Users can add, edit, or remove cards and explicitly save their changes.
- Open **Customize voice** on the **Default voice** card or a person's card. A recipient can have optional additional instructions and their own example cards, e.g. a sibling versus a friend. No contact lookup or relationship classification is required.
- Add **Suggest examples from this chat** for an allowlisted recipient. Read up to the existing 50-message context window through the configured MCP adapter. Preview candidate incoming/user-response pairs and optionally suggested style notes; let the user edit, select, and save them. Nothing becomes part of the saved voice automatically.
- Keep saved examples editable and removable. Drafts already generated remain unchanged; future drafts use the saved profile.

## Small implementation design

Extend the existing local profile storage and Pydantic validation; no new database service, vector index, training pipeline, or agent is needed. Preserve backward compatibility with existing `style` and `examples` data. Add bounded paired examples and recipient overrides keyed by exact allowed address. The implemented API/schema is documented in API.md.

Resolve drafting instructions as global style plus recipient-specific additions. Use recipient-specific examples when available, otherwise global examples. Do not mix examples from unrelated recipient profiles. Keep existing standalone examples supported and limit the combined prompt size. Use a small deterministic selection (for example, the first saved examples within a fixed budget), not semantic retrieval. Summary generation does not need style examples.

For extraction, normalize transcript direction and chronological order before matching examples. Treat only messages identified as sent by the user as their response examples. Never infer the user's voice from incoming text. Use adjacent incoming/outgoing text exchanges within the fetched exact chat window; skip ambiguous direction, missing/attachment-only text, and unsupported formats. For a run of incoming messages, the current conservative extractor uses only the immediately preceding incoming row. Multiline text beyond its first row is not imported; review every suggestion against the chat before saving. If no reliable pair exists, explain that and offer manual entry instead of inventing examples. Synthetic fixtures must cover newest-first MCP transcripts and oldest-first demo data.

Prefer deterministic candidate extraction first. Model-generated style notes are deferred; current import does not call a model. Store approved excerpts and scope, not another full chat archive. Avoid duplicate imports. Do not treat conversation summaries or inferred personal facts as style memory.

## Consent and boundaries

Permission to read a chat for a reply is not automatic permission to retain it as a style example. Import is a separate user action with a preview and explicit save. The current Messages MCP window limit remains in force; no direct database reads, silent historical backfill, automatic learning on refresh/send, or contact identity merging.

Ollama keeps model processing local. If an optional remote provider is configured, extraction that calls that model sends the selected text to it; disclose that before the action. Deterministic extraction need not call a model at all. Saved excerpts can include another person's private text: show exactly what will be retained and support removing it from the active profile. Existing draft snapshots/checkpoints may still contain previously used text; removing a profile example is not full historical erasure.

Phone numbers and Apple ID emails are distinct scopes even if they belong to the same person. Per-recipient voice settings must not expand the messaging allowlist. Conversation text and examples are untrusted data, never instructions that can authorize tools or sending.

## Acceptance checks

- Existing global profiles still load; paired cards persist through restart and remain editable/removable.
- Recipient A's examples never appear in recipient B's draft inputs; missing overrides fall back to defaults.
- Nonallowlisted imports are refused; all import tests use synthetic connectors.
- Only identifiable user-authored responses become response examples; ambiguous transcripts are skipped.
- Preview/cancel leaves the saved profile unchanged; saving keeps only selected examples within explicit limits.
- Refresh, approval, rejection, and automatic drafting do not silently change saved profiles.
- Profile changes do not rewrite pending drafts, grant approval, or bypass version/context checks.

## Limits and scope

Up to 20 pairs per voice, 2,000 characters per pair field, 30 standalone examples of up to 4,000 characters, 2,000 style characters, and 50 recipient overrides. Draft input selects pairs first, then standalone examples within a shared 8,000-character example budget. Global style is combined with recipient additions; recipient examples replace global examples when any are present. Pending drafts are not rewritten.

This is few-shot prompting with reviewed local examples, not model fine-tuning or RAG. Paired manual examples, per-recipient overrides, and reviewed chat import are implemented. Defer continuous learning, automatic relationship inference, cross-chat retrieval, and inferred personal-memory systems.
