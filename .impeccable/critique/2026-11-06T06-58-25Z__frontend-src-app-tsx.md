---
target: the inbox
total_score: 32
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:/Users/harini/Desktop/interviewing/ghost-texter/frontend/src/App.tsx"
target_fingerprint: "sha256:495c86f23c79b3375fdd4c96bfe88c1f319faca6d31d7eceea2370e3d24d2d09"
target_path: /Users/harini/Desktop/interviewing/ghost-texter/frontend/src/App.tsx
timestamp: 2026-11-06T06-58-25Z
slug: frontend-src-app-tsx
---
⚠️ DEGRADED: single-context (no sub-agents used: this session starts them only on explicit request; no browser tool, so no live screenshots or overlay; rendered samples only)

# Critique: the inbox (frontend/src/App.tsx), third run

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 4 | Save status, drafting, loading and the sent card all show where the work is |
| 2 | Match System / Real World | 3 | "Saved · v3" still shows version wording |
| 3 | User Control and Freedom | 3 | Undo and Esc exist; a slow draft cannot be cancelled |
| 4 | Consistency and Standards | 3 | Arrow glyphs mean different things: the arrow is both Inbox and Send |
| 5 | Error Prevention | 4 | Final confirmation, stale-context lock, autosave that never sends |
| 6 | Recognition Rather Than Recall | 4 | State dots, selection, save status, Undo |
| 7 | Flexibility and Efficiency | 2 | No Cmd+Enter to open the send confirmation |
| 8 | Aesthetic and Minimalist Design | 3 | One explainer line and the sidebar label remain |
| 9 | Error Recovery | 3 | "Couldn't save yet" gives no reason or fix |
| 10 | Help and Documentation | 3 | Consent note and status line sit where needed |
| **Total** | | **32/40** | **Good (up from 30)** |

## Design Specificity Verdict
Review: much more specific. The ghost with open and closed eyes, the rising sent moment and the calm sage desk belong to this product. Type is still generic: Manrope and DM Sans are declared but not loaded.
Deterministic scan: impeccable detect found 0 issues in App.tsx (source patterns only).
Overlays: none (no browser available).

## Overall Impression
Now feels like a product with a point of view: scannable, typing is safe, sending ends well. Biggest opportunity: the last 10 percent of craft: real type, keyboard speed, honest error messages.

## What's Working
- The ghost: its eyes show whether there is work left, so empty and sent states inform as well as charm.
- Typing is safe: autosave, visible save status, Undo for Clear and replaced drafts.
- Sending ends well: "Sent to Alex." in place of the reply with one button to the next conversation.

## Priority Issues
- [P2] The fonts still never load. Display voice is the platform sans while DESIGN.md promises Manrope and DM Sans. Fix: bundle both locally. Command: /impeccable typeset
- [P2] No keyboard path for repeat use. Fix: Cmd+Enter opens the send confirmation, which still needs the confirm button. Command: /impeccable harden
- [P2] A failed autosave does not say why or what to do, and is not announced to screen readers. Fix: "New messages arrived. Use latest messages to keep your reply." with the existing button, announced as an alert. Command: /impeccable clarify
- [P3] Arrow glyphs stand in for icons; the same arrow marks Inbox and Send. Fix: a small drawn icon set in the same hand as the ghost. Command: /impeccable polish
- [P3] The first-use empty state has no action. Fix: a button that opens People. Command: /impeccable onboard

## Persona Red Flags
Alex: no Cmd+Enter; every send still needs the mouse.
Sam: focus stays in the reply box and Esc closes Options; a failed autosave is not announced.
Riley: refresh mid-reply is safe once a save has landed; if the save failed because new messages arrived, text is lost on refresh and nothing says so; a slow draft cannot be cancelled.

## Minor Observations
- "Based on the latest fetched conversation window. Check the messages below for details." repeats what the layout shows.
- The sidebar "PERSONAL ASSISTANT" label remains.
- 9-11px text remains in eyebrows and the sidebar footer.
- 38 hard-coded colors and no design tokens (technical).

## Questions to Consider
- Could the ghost's eyes carry one more state, such as drowsy while drafting?
- Would a drawn g. wordmark match the ghost better than a system-font one?
- Does Options need a label, or could it be a small drawn gear?
