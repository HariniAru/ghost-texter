# Approval contract

## Review state

A draft binds a UUID, exact recipient, context snapshot and SHA-256 fingerprint, text, monotonically increasing version, status, and creation timestamp. The browser edits locally, then saves a new version. Approval is unavailable while unsaved edits differ from the saved draft. API approval carries the saved version; the backend resolves its exact text and immutable recipient.

Allowed transitions:

- pending → pending (saved edit increments version)
- pending → rejected
- pending → stale (context no longer matches)
- pending → sending (approval audit committed)
- sending → sent (connector acknowledges success)
- sending → uncertain (exception, unrecognized receipt, or restart before completion)

All resolved statuses are terminal. A duplicate approval returns 409. Reject does not call the sending adapter. No endpoint directly accepts arbitrary send text.

## Dispatch checks

1. Authenticate the request and reject untrusted browser origins.
2. Require pending status and exact version.
3. Require an exact allowlisted recipient in live mode and the live-send configuration switch.
4. Reread context and compare its fingerprint; if reading fails, send nothing. If context differs, mark stale and require a fresh review.
5. Persist approved recipient, version, body, and fingerprint, plus sending intent, before calling the connector.
6. Resume the graph, then make one send attempt with the stored approved text.
7. Record receipt, or mark uncertain and disallow retries.

## Practical boundaries

The supported runtime is one local API process with one worker. An asyncio lock is not cross-process coordination. Do not run replicas or multiple uvicorn workers. Multi-worker deployment is outside the local MVP.

There is a short unavoidable interval between the last context read and Messages accepting the send; the upstream interface has no atomic compare-and-send primitive. This app cannot promise no message arrives during that interval. Fingerprints cover the connector's returned 50-message window, not the full database. Changes in read metadata can conservatively invalidate drafts.

Exactly-once delivery is not claimed. A connector may send and then time out. Such outcomes become uncertain and are never automatically retried. A crash after marking sending but before actual dispatch may also produce uncertainty. Verify in Messages before creating another draft. The app does not yet offer a reconciliation UI. A successful receipt means connector acknowledgment, not recipient delivery or read confirmation.

## Dashboard confirmation

The first Review & send click opens a native modal with a snapshot of the exact saved recipient, body, and version; it does not approve or dispatch. Only Confirm & send calls the existing approval endpoint with that snapshot version. Cancel/Escape return to editing without a request. Confirmation is disabled while sending or when live sending is disabled. The dialog closes if refreshed draft data changes version/text/recipient/status, and the backend remains authoritative for all checks. Demo mode uses explicit simulated-send labels.

## Automatic preparation

Opting into draft preparation authorizes reading configured unread conversations and generating saved proposals only. It grants no approval authority. Existing pending edits and uncertain outcomes block automatic replacement; rejected identical conversation snapshots are not automatically regenerated. Every prepared draft uses the same exact-version, recipient, body, fingerprint, and final confirmation checks before sending.

## Discard and regeneration target

The current reject action already removes approval authority and retains a terminal record. A future discard label should retain this behavior rather than physically deleting approval or dispatch evidence. Explicit regeneration creates a fresh pending review; it cannot inherit approval from any earlier draft. Rejected alternatives may guide wording but remain untrusted data. Per-chat automatic-drafting permission authorizes preparation only, never sending. These UI and regeneration refinements are planned, not implemented by this documentation update.
