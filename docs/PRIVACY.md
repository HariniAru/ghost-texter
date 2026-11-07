# Privacy and data

The app runs on your Mac and checks unread messages for configured recipients and fetches recent context for the selected allowlisted direct conversation in live mode. Demo mode uses synthetic history. No live account access is needed for tests.

Domain records, exact reply text, context snapshots, edits, approval events, writing examples, and graph state are stored under `GHOST_DATA_DIR` (default `data/`). These files are excluded from git. They are not encrypted by this app. Use FileVault and keep this directory private; avoid cloud-synced directories if inappropriate. The API token is stored separately with owner-only permissions. Do not expose the backend beyond loopback.

When `GHOST_LLM=true`, the chosen conversation window goes to the selected model for a summary. Requests use the local Ollama loopback server without credentials or a cloud fallback; drafting also includes your voice profile. Unchanged summaries are cached in memory until restart or a context change. Otherwise no model call occurs. Tracing is not enabled by this application. Do not enable external LangSmith tracing for private messages without considering what it captures. The UI uses local/system fonts and no analytics.

Messages and MCP responses are untrusted data. They cannot authorize sends. The LLM has no tools; generated instructions never become backend actions. Only an authenticated user request can approve the current saved draft version.

To erase local history, stop the backend and delete the configured data directory, including SQLite WAL/SHM companions. This also removes graph checkpoints and the generated token; restarting creates a new workspace. There is no automatic retention policy or per-conversation deletion UI yet.

## Voice example import

Paired examples, recipient-specific style profiles, and reviewed chat import are implemented. Import reads only the configured chat window after an explicit action, previews incoming/user-response excerpts, and persists only user-selected examples after save. No automatic learning on refresh or sending. Imported incoming text is also private data; stored examples must be editable/removable. Removing a profile example will not erase existing draft snapshots or graph checkpoints. See [VOICE_PERSONALIZATION.md](VOICE_PERSONALIZATION.md).
