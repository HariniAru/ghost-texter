---
target: the inbox
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/harini/Desktop/interviewing/ghost-texter/frontend/src/App.tsx"
target_fingerprint: "sha256:c16525e5bc5eeb996bb9162590397ab8a0e00cfde7287d3180662a370acf34ee"
target_path: /Users/harini/Desktop/interviewing/ghost-texter/frontend/src/App.tsx
timestamp: 2026-11-06T05-25-51Z
slug: frontend-src-app-tsx
closed: true
---
⚠️ DEGRADED: single-context (no sub-agents used: this session starts them only on explicit request; no browser tool available, so no screenshots or overlay)

# Critique: the inbox (frontend/src/App.tsx)

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Local spinners and notes are clear, but the key chat states are 9px text at 2.9:1 |
| 2 | Match System / Real World | 3 | Plain language apart from "Draft v1" version wording |
| 3 | User Control and Freedom | 3 | Clear, Back to editing and Esc exist, but Clear has no undo |
| 4 | Consistency and Standards | 3 | Refresh inbox is solid green like Send, against the Quiet Fill Rule |
| 5 | Error Prevention | 4 | Final confirmation, stale-context lock, replace warning |
| 6 | Recognition Rather Than Recall | 2 | Selected chat nearly invisible; "draft ready" hidden in 9px grey |
| 7 | Flexibility and Efficiency | 2 | No shortcuts, no jump to the next chat after a send |
| 8 | Aesthetic and Minimalist Design | 2 | Two paragraphs of small print and an opt-in block above the first chat |
| 9 | Error Recovery | 3 | Errors beside the control, text kept |
| 10 | Help and Documentation | 2 | Help is always-on small print, not placed where needed |
| **Total** | | **27/40** | **Acceptable** |

## Design Specificity Verdict
Review: generic layout (sidebar, toolbar, two card columns); product character lives only in the copy. Fonts are declared (Manrope, DM Sans) and never loaded.
Deterministic scan: impeccable detect found 0 issues in App.tsx (source patterns only; it missed all contrast findings, which need a rendered page).
Overlays: none (no browser available).

## Overall Impression
Calm and safe, with the best loading states in the product. The state that matters (which chat needs you) is the smallest and faintest text on screen.

## What's Working
- Progress and errors appear where the work is.
- The reply box is always present with Clear, Draft a reply and Send; the send path is the safest part.
- Restrained tonal palette, no gradients or shadows.

## Priority Issues
- [P1] Chat state and selection are hard to see. Selected row #eef2e7 is 1.13:1 against its card; notes are 9px at 2.9:1. Fix: stronger selected style plus aria-current; 12px notes at 4.5:1 with a state dot. Command: /impeccable layout the conversation list
- [P1] Explanations push the list down. Header, toolbar, status paragraph and auto-prepare block sit above the first chat. Fix: one quiet "Updated" line, options in a disclosure. Command: /impeccable distill
- [P1] Contrast debt unpaid. PRODUCT.md requires WCAG AA; helper text, notes, draft label, eyebrow, previews and secondary buttons measure 2.6-3.8:1. Fix: one secondary text color near #5d6b59 (5.6:1 on cards, 4.9:1 on sidebar). Command: /impeccable audit, then /impeccable polish
- [P2] Reply box last and below the fold when Recent messages is open. Fix: compact scrollable messages with the reply card directly beneath. Command: /impeccable layout the open conversation
- [P2] Weak send ending. Receipt appears at page top while the reply card becomes a placeholder. Fix: "Sent to <name>" in the reply card's place, offer the next unread chat. Command: /impeccable clarify, then /impeccable delight

## Persona Red Flags
Alex: no Send shortcut, no next-chat jump, auto-refresh resets to off on load.
Sam: color-only selection with no aria-current; most secondary text fails 4.5:1; reply box disabled while drafting drops focus.
Riley: typed text is saved only on Send or leaving the chat, so a refresh loses it; Clear and Draft a reply discard text with no undo.

## Minor Observations
- Refresh inbox and Send are both solid green.
- Draft a reply (main value action) is tonal.
- Native confirm dialog for replace warning.
- Ghost glyph is the only expressive element.
- Under 650px the list scrolls at 260px and the reply box stays last.

## Questions to Consider
- If the ghost drafts quietly, why does the screen show how it works instead of what needs you?
- What if the selected chat's reply box came first and history sat behind it?
- Does a calm tool need to explain "reading does not mark as read" every day?
