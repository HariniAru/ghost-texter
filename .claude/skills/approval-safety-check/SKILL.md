---
name: approval-safety-check
description: Audit a Ghost Texter change against the approval and send safety rules. Use before calling work done whenever a change touches drafts, approval, rejection, regeneration, sending, automatic preparation, the Messenger interface, the model prompt, draft storage or status, or the send confirmation UI, including backend/ghost/main.py, store.py, messaging.py, workflow.py, frontend/src/App.tsx, SendConfirmation.tsx, and useAutoPrepare.ts.
---

# Approval safety check

Check the change and report. Do not fix anything during the check. The rules come from `AGENTS.md` and `docs/APPROVAL_CONTRACT.md`; if this list disagrees with them, they win, so say so.

Do not read `.env` or `data/`, and do not run the app against live settings. This check needs neither.

## Steps

1. Read `docs/APPROVAL_CONTRACT.md`.
2. Find the change with `git status --short` and `git diff`, plus `git diff --cached` if anything is staged. Read new files in full. If the repo has no commits, ask which files to review.
3. Read the full current code around each changed path. A rule can break far from the edited line.
4. Run the searches below and explain every unexpected hit.
5. Mark each rule PASS, FAIL, or N/A, with `file:line` evidence for PASS and FAIL.
6. Run `uv run pytest` and `uv run ruff check backend`. If frontend files changed, also run `npm test` in `frontend/`.
7. Report. Any FAIL means the change is not ready. Say so plainly, even if all tests pass.

## Searches

From the repo root. Each should only match the location named.

```sh
grep -rn "\.send(" backend/ghost              # Real dispatch only in approve() in main.py
grep -rn "tool_send_message" backend/ghost    # Only MacMessages.send in messaging.py
grep -rnE "bind_tools|tools=|create_agent|AgentExecutor" backend/ghost  # No matches
grep -rnE "(^|[^a-z_])print\(|logging\.|logger\." backend/ghost --include='*.py'  # Only intentional CLI output in check_ai.py and inspect_chat.py
grep -rn "/approve\|'approve'" frontend/src --include='*.tsx' --include='*.ts' --exclude='*.test.*'  # Only the send confirmation path in App.tsx
```

## Rules

**Who can send**

1. The only route to `messenger.send` is the approve endpoint. Automatic preparation, regeneration, refresh, and startup cannot reach it.
2. The model has no tools, credentials, or approval authority, and its output never becomes a backend action.
3. Message text and voice examples stay untrusted data in prompts, never instructions.
4. No endpoint sends text it is handed. Typed text and edits are only saved. Approve takes only a version, and the body comes from the stored draft.

**What gets approved**

5. Approval binds the saved version, exact recipient, exact body, and conversation fingerprint.
6. Saving an edit increments the version, and only a pending draft at the exact version can be edited, rejected, or approved.
7. A new, typed, or regenerated draft starts as a fresh pending review and inherits no approval.
8. The UI cannot approve while unsaved edits differ from the saved text. Only **Confirm & send** in the dialog calls approve, and opening the dialog sends nothing.

**Checks before dispatch, in this order**

9. Authenticate and reject untrusted origins.
10. Live mode requires an exact allowlisted recipient and `send_enabled`.
11. Reread the conversation. A failed read sends nothing. A changed fingerprint marks the draft `stale` and sends nothing.
12. Commit the approval event and `sending` status before the graph resume and the connector call.

**Dispatch**

13. Dispatch stays outside graph nodes, so replay cannot resend.
14. Exactly one send attempt. No retry, loop, or fallback on any path.
15. Any exception or unrecognized receipt becomes `uncertain`, which is never resent. Startup converts leftover `sending` to `uncertain`. `uncertain` only moves to `sent` when the exact outgoing text is found at or after approval, or to `discarded` by the user's choice. Try again creates a new pending draft that needs its own approval.
16. `rejected`, `stale`, `sent`, and `discarded` never change. A duplicate approval returns 409.

**Scope and privacy**

17. Reads stay within the contacts list in live mode (`GHOST_ALLOWED_RECIPIENTS` plus addresses the user added on the dashboard), by exact address. Only the add-contact check may read an address before it is saved, and it must discard the text. No contact search, fuzzy matching, or enumerating other chats. Expanding this to all chats is a future decision the user must make explicitly.
18. Automatic preparation preserves pending, `sending`, and `uncertain` reviews, and does not redraft a conversation a sent reply already answered. A rejected draft does not block it.
19. Voice data changes only through explicit save, recipients' examples do not leak into other recipients' drafts, and nothing is learned silently.
20. Message contents and tokens are not logged. Connector errors stay sanitized, and upstream stderr stays suppressed.

**Draft list and records**

21. Only `sent` and `discarded` drafts leave the saved list. `uncertain` stays visible until it is found in Messages or the user acts on it.
22. Hiding or discarding a draft does not delete approval or dispatch evidence.

**Tests and docs**

23. Tests use synthetic messages and fake connectors, with `_env_file=None` and `data_dir=tmp_path`. No test can reach Messages.
24. Each changed rule has a test that would fail if the rule broke. For a behavior change, check this by reading the assertion, not just the test name.
25. `docs/API.md` and `docs/APPROVAL_CONTRACT.md` are updated if routes, configuration, or lifecycle rules changed.

## Report format

- **Verdict:** Ready, or Not ready with the number of failures.
- **Failures:** rule number, `file:line`, and a concrete way it could send the wrong thing, send twice, or expose private data.
- **Passed and N/A:** rule numbers, with evidence for the rules this change touches.
- **Test results:** the actual counts and any failure output.
- **Not checked:** anything you could not verify, such as behavior only a real iMessage send would show.
