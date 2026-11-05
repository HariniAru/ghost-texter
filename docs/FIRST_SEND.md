# First approved send

The review workflow is ready for a user-performed test. Development tests use only synthetic messages and fake connectors; they do not prove real delivery or grant macOS Automation access.

## Review first

1. Leave `GHOST_SEND_ENABLED=false` while evaluating local summaries and drafts.
2. Choose a single intended recipient already in the allowlist, using the exact address of the desired thread (phone and Apple ID email are separate identities).
3. Generate a draft, edit it, and save the edit. The editor shows its saved version.
4. Click **Review & send**. The dialog displays the exact recipient, saved text, and version. With live sending disabled, the final button stays disabled. **Back to editing** or Escape cancels without approving.

## User-performed live test

1. When ready to send a real message, set `GHOST_SEND_ENABLED=true` in the root `.env` and restart the backend. This is separate from enabling AI and doesn't authorize any automatic sends.
2. Reopen/review the intended saved draft. If the conversation changed, create a fresh draft. Do not use an old draft whose content is no longer appropriate.
3. Click **Review & send**, inspect the exact address and saved reply, then click **Confirm & send** only when you want that real message sent.
4. macOS may request permission for the launching terminal/editor to automate Messages. Complete that prompt yourself if expected.
5. Verify the result in Messages. The app's receipt is a connector acknowledgment, not a promise of delivery or reading.
6. Set `GHOST_SEND_ENABLED=false` and restart the backend afterward if you want to return to read/draft-only use.

The backend rechecks draft version, recipient allowlist, and conversation context at dispatch. If the saved version changes while the dialog is open, the dialog is dismissed. A backend conflict requires a fresh review. Once a send request starts, cancellation is unavailable; closing the page cannot reliably cancel Messages automation.

If status becomes uncertain, check Messages before doing anything else. Do not retry by making a replacement draft until you know whether the first send happened. This version does not provide an uncertain-send reconciliation UI.

## Demo validation

In a separate demo workspace, **Review simulated send** opens the same review step. Its final **Confirm simulated send** records a simulated send only. Keep live and demo data directories separate when switching modes.
