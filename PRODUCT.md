# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One person: the owner, using the dashboard alone on their own Mac. They open it in short bursts to clear unread iMessages and send replies that sound like them. It is a single-user, local tool. It is not shared, hosted or multi-user, and the design should not imply otherwise.

## Product Purpose

Ghost Texter catches the owner up on iMessages from chosen contacts and helps them reply. It shows an inbox of unread chats, a short summary of each conversation, and a reply box that can be filled with an AI draft in the owner's voice. Success is a cleared inbox with replies the owner actually approved, fast and without worry about anything sending by accident.

## Positioning

Drafts are written by a local model (Ollama) in the owner's own voice, with a default voice plus per-person examples, and nothing is ever sent without the owner's explicit approval of the exact saved text. Nothing leaves the Mac for drafting, and the model has no ability to send.

## Operating Context

- A local web dashboard served on 127.0.0.1, opened with a local API token.
- Two modes with the same screens: demo (synthetic chats; Send does nothing, so the samples stay unread) and live (real iMessages through the Messages connector).
- Two tabs only. Inbox lists unread chats from added contacts, with a per-chat summary, the recent messages and a Your reply box (Clear, Draft a reply, Send). People holds the contacts and each person's optional voice settings.
- Send opens a final confirmation dialog showing the exact recipient and text. Only its confirm button sends.
- Interrupted sends are checked against Messages automatically, and the owner chooses Try again or Discard draft if the message is not found.

## Capabilities and Constraints

- Contacts are limited to people the owner added (name and exact number or email). The app does not browse other chats.
- Drafting is optional and can be switched off, in which case a sample reply and a plain excerpt are shown instead of AI output.
- Draft statuses and approval rules are fixed by the approval contract in docs/APPROVAL_CONTRACT.md. A visual redesign must not change them.
- Loading states are local: opening a chat, generating a summary and drafting each show progress in their own place, not across the whole page.

## Brand Commitments

- The name "Ghost Texter" and the "g." mark stay.
- The send confirmation step stays: Send opens a final confirmation, and only its confirm button sends.
- The two tabs (Inbox, People) and the Your reply box with Clear, Draft a reply and Send stay.
- Nothing else about the current look, layout or copy is binding.

## Evidence on Hand

- Demo mode has four synthetic contacts and chats (Alex, Maya, Jordan, Priya) for trying the interface.
- There are no testimonials, customers, benchmarks or marketing claims, and none should be invented.
- Live data is private message text. Screenshots and examples must use demo data only.

## Product Principles

1. Approval is never ambiguous. The owner always knows what exact text goes to whom before it sends.
2. Progress shows where the work is. A spinner belongs on the control or area that is loading, never across the page.
3. The reply box is the center. Reading context, drafting and sending all orbit one always-present box.
4. Calm over busy. This is a tool for clearing a backlog quickly, not a place to linger.
5. Private by default. Nothing in the interface suggests sharing, syncing or leaving the Mac.

## Accessibility & Inclusion

Laptop-first, usable on narrow browser windows. Meet WCAG AA contrast and full keyboard use, including the send confirmation dialog.
