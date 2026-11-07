---
name: verify-demo
description: Run or verify Ghost Texter in the real app using only synthetic data, through a throwaway demo server. Use whenever a change needs checking beyond unit tests, when asked to run, start, screenshot, or walk through the app, and before driving it with a browser or Playwright. Use this instead of starting uvicorn directly.
---

# Verify in demo mode

Start the app only through `scripts/run-demo.sh`. Starting uvicorn from the repo root loads the user's `.env`, which may be configured for live Messages with sending on.

## API check

From the repo root:

```sh
.claude/skills/verify-demo/scripts/run-demo.sh
```

This covers inbox, conversation, draft, deduplication, edit, version conflicts, reopen, reject, a new draft, and demo Send (which does nothing and leaves the chat unread). Exit codes:

- `0`: the walkthrough passed.
- `1`: a step failed. Report which one.
- `3`: the script refused to run. Report the reason and stop.

If port 8001 is in use, the script refuses because that may be the live backend. Ask the user to stop it. Do not stop it yourself or look for a way around the check.

## Browser check

The API check does not cover the UI. For UI changes, also write a browser script and pass it as the command:

```sh
(cd frontend && npm run build)
.claude/skills/verify-demo/scripts/run-demo.sh <command that runs the browser script>
```

The backend serves `frontend/dist`, so build first or the browser tests stale UI. The script must read `GHOST_DEMO_URL` and `GHOST_DEMO_TOKEN` from its environment, and it must not start a server or connect to any other address.

Walk the acceptance flow from `docs/PROJECT_PLAN.md`: refresh → open conversation → summary → generate → edit and save → leave and reopen → discard → generate an alternative → press Send and confirm. The final button must read **Confirm simulated send**, and pressing it must change nothing: the chat stays in the unread inbox. If it reads **Confirm & send**, stop immediately: that is the live workflow.

If no browser tooling is installed, say the UI was not verified. Do not install it without asking.

## Limits

- Stale context, connection failures, and uncertain sends cannot be triggered in the demo. They are covered by fake-connector tests in `backend/tests/`, so run `uv run pytest` as well.
- A pass shows the demo flow works. It does not prove a real iMessage read or send, and those are never part of this skill.
- When a walkthrough step no longer matches intended behavior, update `scripts/api_walkthrough.py` in the same change and say so.
