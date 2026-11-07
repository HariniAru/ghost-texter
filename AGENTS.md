# Ghost Texter — contributor instructions

Read docs/ARCHITECTURE.md, docs/APPROVAL_CONTRACT.md, and docs/PROJECT_PLAN.md before changing behavior.

## Non-negotiable behavior

- Every real send requires the user's explicit approval of a saved draft version, exact recipient, exact body, and conversation fingerprint.
- The model drafts text only. Never give it messaging tools, sending credentials, approval authority, or instructions to send.
- Edits increment version. Changed conversation context invalidates pending approval.
- Persist approval and sending intent before dispatch. Never automatically retry a send with an uncertain outcome.
- Do not send real texts while developing or testing. Tests must use synthetic messages and fake connectors.
- Do not read private message databases or copy secrets from neighboring repos. The user's live data is accessed only through the configured MCP adapter when they choose live mode.
- Never log message contents or tokens. Local databases contain private text and are excluded from git.
- Run one backend process and one worker only. This version uses an in-process lock for dispatch serialization.

## MVP scope

Use docs/PROJECT_FLOW.md as the product scope and docs/PROJECT_PLAN.md to distinguish shipped behavior from planned work. Keep the stack to Python/FastAPI, LangGraph, React/TypeScript/Vite, local SQLite, Ollama, and the Mac Messages MCP adapter. Do not add RAG, vector databases, additional agents, database services, cloud hosting, or messaging platforms for this MVP. LangChain integrations are acceptable where already useful; no additional orchestration layer is needed.

Voice personalization scope is defined in docs/VOICE_PERSONALIZATION.md: retain global defaults, support paired incoming/user-response examples and exact-recipient overrides, then add explicit reviewed import from allowlisted chat windows. Never silently learn from messages or save extracted examples without user review. Treat only identifiable user-authored outgoing text as response examples; skip ambiguous data. Keep examples scoped, bounded, editable, and local; no RAG or fine-tuning.

Prioritize per-chat opt-in draft preparation and explicit regeneration informed by rejected alternatives. Automatic drafts never imply automatic sends. Keep lightweight local persistence for saved drafts, workflow checkpoints, and approval/send state; do not replace it with volatile state just to reduce the stack. Distinguish hiding/discarding a draft from deleting dispatch evidence.

## Project conventions

Python backend lives in backend/ghost; React/TypeScript dashboard in frontend/src. Keep project reference Markdown under docs/ except this file, the root README, and the `impeccable` skill's PRODUCT.md and DESIGN.md, which the skill reads from the repo root (its `.impeccable/` folder lives there too). Maintain the common Messenger interface when adding platforms. Favor explicit small services over additional agents.

Use `uv sync --extra dev`, `uv run pytest`, `uv run ruff check backend`, and `cd frontend && npm ci && npm test && npm run build`. Update docs for configuration, API, or approval-contract changes. Check dependency lockfiles into source control. Do not modify sibling projects.
