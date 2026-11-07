# Approval contract

## Review state

A draft binds a UUID, exact recipient, context snapshot and SHA-256 fingerprint, text, monotonically increasing version, status, and creation timestamp. The browser edits locally and saves automatically about 1.2 seconds after typing stops; **Send** also saves before the final confirmation opens. Each save of changed text increments the version, and a first save of typed text creates the version 1 pending draft. Saves run one at a time, and each starts from the draft's current version on the server, so no save can use an older one. Autosave pauses while the send dialog is open and never approves anything. Approval is unavailable while unsaved edits differ from the saved draft. A reply the user types with no draft becomes a version 1 pending draft through POST /api/drafts/typed, without the model, and is refused if messages arrived after the conversation they were reading. API approval carries the saved version; the backend resolves its exact text and immutable recipient.

Allowed transitions:

- pending → pending (saved edit increments version)
- pending → pending (user chooses Use latest messages; context and fingerprint update and version increments)
- pending → rejected
- pending → stale (context no longer matches)
- pending → sending (approval audit committed)
- sending → sent (connector acknowledges success)
- sending → uncertain (exception, unrecognized receipt, or restart before completion)
- uncertain → sent (the exact text is found as an outgoing message timestamped at or after approval)
- uncertain → discarded (the user chooses Discard draft or Try again)

In demo mode the approve endpoint dispatches nothing and changes nothing: after the same pending-version check it returns the draft as it is, with no status change, event or send, so sample chats stay unread. `rejected`, `stale`, `sent`, and `discarded` are terminal. A duplicate approval returns 409. Reject does not call the sending adapter. **Clear** and replacing a draft use reject. **Undo** after either puts the old text back in the box; it does not revive the rejected draft, and the restored text is saved as a new pending draft like any other edit. No endpoint sends text it is handed: typed text and edits are only saved, and approve takes a version and sends the stored body. The Cmd+Enter shortcut in the reply box only opens the final confirmation, the same as the Send button; only the dialog's confirm button calls approve.

## Saved drafts list

A draft leaves the saved list only when it reaches `sent`, meaning the connector acknowledged the send or the message was found in Messages, or `discarded`, meaning the user chose to move on from an interrupted send. `uncertain` stays listed until one of those happens, and `pending`, `rejected`, and `stale` stay listed too. This only hides the draft: the row, the approval event, and the send event stay on disk, and approving a sent draft again still returns 409.

The dashboard shows drafts on their chat in the inbox. A chat stays listed while it has unread messages, a pending draft, or an `uncertain` send. `rejected` and `stale` drafts stay in the API list but are not shown.

## New messages after drafting

The inbox warns when a pending draft is behind the conversation, but the warning is advice: approval still rereads the conversation and marks a draft `stale` if it changed. To move a draft forward, the user chooses **Use latest messages**, which rereads the chat, stores the new context and fingerprint, keeps the saved text, and increments the version. It sends nothing and carries no approval. A failed read changes nothing. The user still reviews and confirms that new version, and any message after that invalidates it again.

## Dispatch checks

1. Authenticate the request and reject untrusted browser origins.
2. Require pending status and exact version.
3. Require an exact recipient in the current contacts (`.env` or added in the dashboard) in live mode and the live-send configuration switch. Removing a contact blocks approval of its pending drafts. Adding it back approves nothing.
4. Reread context and compare its fingerprint; if reading fails, send nothing. If context differs, mark stale and require a fresh review.
5. Persist approved recipient, version, body, and fingerprint, plus sending intent, before calling the connector.
6. Resume the graph, then make one send attempt with the stored approved text.
7. Record receipt, or mark uncertain. An uncertain draft is never resent.

## Interrupted sends

The dashboard rereads the chat about four times over 30 seconds for each `uncertain` draft, and again whenever it reconnects. These checks only read. If the exact text appears as an outgoing message timestamped at or after approval, the draft becomes `sent`; an older identical message does not count.

If it is not found, the user chooses **Try again** or **Discard draft**. Try again checks once more and, if the message is still missing, creates a new pending draft with the same text and retires the old one. That draft has no approval and needs the normal review, confirmation, and dispatch checks. Nothing resends without that explicit choice.

Finding the message shows Messages recorded it, not that it was delivered. Not finding it does not prove it failed, so a late arrival followed by Try again can still produce a second text. Matching can also miss messages the connector cuts short or escapes.

## Practical boundaries

The supported runtime is one local API process with one worker. An asyncio lock is not cross-process coordination. Do not run replicas or multiple uvicorn workers. Multi-worker deployment is outside the local MVP.

There is a short unavoidable interval between the last context read and Messages accepting the send; the upstream interface has no atomic compare-and-send primitive. This app cannot promise no message arrives during that interval. Fingerprints cover the connector's returned 50-message window, not the full database. Changes in read metadata can conservatively invalidate drafts.

Exactly-once delivery is not claimed. A connector may send and then time out. Such outcomes become uncertain and are never automatically retried. A crash after marking sending but before actual dispatch may also produce uncertainty. A successful receipt means connector acknowledgment, not recipient delivery or read confirmation.

## Dashboard confirmation

**Send** saves the reply box and opens a native modal with a snapshot of the exact saved recipient, body, and version; it does not approve or dispatch. Only Confirm & send calls the existing approval endpoint with that snapshot version. Cancel/Escape return to editing without another request; the saved version stays. Confirmation is disabled while sending or when live sending is disabled. The dialog closes if refreshed draft data changes version/text/recipient/status, and the backend remains authoritative for all checks. Demo mode uses explicit simulated-send labels.

## Automatic preparation

Opting into draft preparation authorizes reading configured unread conversations and generating saved proposals only. It grants no approval authority. Existing pending edits and uncertain outcomes block automatic replacement; conversations a sent reply already answered are skipped. A rejected draft is not a saved draft, so turning automatic preparation on drafts every unread chat that has no pending draft, passing its rejected texts to the model so the new draft differs. Turning it on starts over for every unread chat. Every prepared draft uses the same exact-version, recipient, body, fingerprint, and final confirmation checks before sending.

## Discard and regeneration target

The current reject action already removes approval authority and retains a terminal record. A future discard label should retain this behavior rather than physically deleting approval or dispatch evidence. Explicit regeneration creates a fresh pending review; it cannot inherit approval from any earlier draft. Up to 5 rejected drafts for the same fingerprint are passed to the model as untrusted data so it writes something different; redrafts run at temperature 1.0 with at most 3 model calls, and an output that still repeats one is refused rather than shown. Per-chat automatic-drafting permission authorizes preparation only, never sending, and is still planned.
