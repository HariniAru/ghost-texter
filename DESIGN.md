---
name: Ghost Texter
description: A calm, private desk for clearing unread texts and approving every reply.
colors:
  fern-ink: "#264e3d"
  desk-ink: "#243b33"
  morning-page: "#f6f7f2"
  morning-sidebar: "#edf0e7"
  morning-card: "#fffefa"
  paper-white: "#ffffff"
  sage-line: "#e0e5dc"
  sage-field: "#dce2d9"
  sage-tint: "#dce5d4"
  leaf-text: "#305638"
  sage-text: "#5d6b59"
  field-edge: "#869580"
  badge-wash: "#e9eee3"
  focus-leaf: "#7c9c74"
  clay-error: "#a14f3e"
  clay-wash: "#fff0e9"
  receipt-wash: "#e9f2e3"
typography:
  display:
    fontFamily: "Manrope, sans-serif"
    fontSize: "39px"
    fontWeight: 800
    letterSpacing: "-3px"
  headline:
    fontFamily: "Manrope, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    letterSpacing: "-1px"
  title:
    fontFamily: "Manrope, sans-serif"
    fontSize: "17px"
    fontWeight: 600
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "14px"
    lineHeight: 1.65
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "1.8px"
rounded:
  xs: "4px"
  sm: "8px"
  md: "9px"
  lg: "12px"
  xl: "15px"
  pill: "20px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "25px"
  xl: "45px"
components:
  button-primary:
    backgroundColor: "{colors.fern-ink}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
  button-secondary:
    backgroundColor: "{colors.morning-sidebar}"
    textColor: "{colors.sage-text}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
  nav-item-active:
    backgroundColor: "{colors.sage-tint}"
    textColor: "{colors.leaf-text}"
    rounded: "{rounded.md}"
    padding: "12px 18px"
  card:
    backgroundColor: "{colors.morning-card}"
    textColor: "{colors.desk-ink}"
    rounded: "{rounded.xl}"
    padding: "25px"
  input:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.desk-ink}"
    rounded: "{rounded.sm}"
    padding: "12px"
  badge:
    backgroundColor: "{colors.badge-wash}"
    textColor: "{colors.sage-text}"
    rounded: "{rounded.pill}"
    padding: "8px 11px"
---

# Design System: Ghost Texter

## Overview

**Creative North Star: "The Quiet Desk"**

Ghost Texter looks like a tidy desk where a backlog gets cleared calmly. Surfaces are pale, sage-tinted paper (Morning Desk), text is a deep green-black, and a single ink color (Fern Ink) marks the actions that move work forward. Nothing glows, drops a shadow or animates for show. It is calm, soft, plain and careful: calm in its low-contrast surfaces and generous space, soft in its rounded corners, plain in its lack of ornament, and careful in how clearly it separates drafting from sending.

The product is a single-user tool for catching up on iMessages and approving every reply, so the interface stays out of the way. Structure comes from a fixed sidebar, hairline borders and tonal steps between page, sidebar and card. The one place the design slows the user down on purpose is the send confirmation, which is a plain modal over a dim green-black backdrop.

The look is not a glossy gradient SaaS dashboard, not a dark neon or cyber interface, and not a clone of a messaging app. These are confirmed rejections. Chat bubbles appear only inside the conversation card, as small calm shapes in the app's own two greens.

**Key Characteristics:**
- Flat surfaces: no shadows anywhere; depth comes from tonal steps and 1px sage borders.
- One accent: Fern Ink solid fills for forward actions, tonal sage for everything demoted.
- Soft geometry: 8px to 15px corner radii on everything, pill-shaped badges, round avatars.
- Small, quiet type: nothing is below 12px, and most interface text is 12px to 14px, with Manrope reserved for the brand and headings.
- Progress shows in place: a small spinner on the control or area that is loading, never across the page.

## Colors

A single deep green on pale green-tinted neutrals, with one clay red for errors.

### Primary
- **Fern Ink** (#264e3d): the solid fill of every default button, the checkbox accent, and the 2px ring around the selected conversation. It marks actions that move work forward (Draft, Send, Add, Save, Confirm).

### Neutral
- **Desk Ink** (#243b33): body text and dialog text, a green-black that reads softer than pure black.
- **Morning Page** (#f6f7f2): the page background.
- **Morning Sidebar** (#edf0e7): the sidebar and the demoted, secondary button fill.
- **Morning Card** (#fffefa): cards, the conversation list and the send dialog.
- **Paper White** (#ffffff): input and textarea fields, and text on Fern Ink.
- **Sage Line** (#e0e5dc) and **Sage Field** (#dce2d9): card borders and the send dialog edge. **Sage Tint** (#dce5d4) fills the active nav item, with **Leaf Text** (#305638) on top.
- **Sage Text** (#5d6b59): all secondary text: paragraphs, helper text, labels, notes, demoted button text and badges. It measures 4.6:1 or better on every surface it sits on.
- **Field Edge** (#869580): the border of inputs and the reply box, at 3.2:1 so a field is visibly a field.
- **Focus Leaf** (#7c9c74): the 2px focus outline on fields.
- **Badge Wash** (#e9eee3): the fill of status and mode badges, with Sage Text on it.

### Status
- **Clay Error** (#a14f3e) on **Clay Wash** (#fff0e9): errors and warnings. **Receipt Wash** (#e9f2e3) marks confirmations such as a send receipt.

### Named Rules
**The Quiet Fill Rule.** Solid Fern Ink marks actions that move work forward. Actions that undo or step back (Clear, Back to editing, Discard draft) use the tonal secondary style.

**The AA Floor Rule.** Secondary text is Sage Text (#5d6b59) or darker, never paler. Every text pair in the inbox is at least 4.5:1, and field borders are at least 3:1. The old pale tints (#8c9783, #8e9b81, #9aa48e, #7c897b, #7b856e, #738077) were retired because they measured 2.6 to 4.1:1.

Every color is a CSS variable on `:root` in `style.css`, named for its role (`--fern`, `--sage-text`, `--sage-tint`, `--paper`, `--line`, `--clay` and so on), so a palette change is one edit. The ghost drawing reads the same variables.

## Typography

**Display Font:** Manrope (with sans-serif)
**Body Font:** DM Sans (with sans-serif)

**Character:** A geometric heading face over a friendly humanist body face, both set small and tight. Both ship with the app as local variable font files (`@fontsource-variable`), so nothing loads from outside the Mac, and `system-ui` is the fallback.

### Hierarchy
- **Display** (800, 39px, tight -3px tracking): the "g." brand mark in the sidebar. The login mark is 70px and the login heading 43px.
- **Headline** (600, 30px, -1px tracking): the page heading in the main header. 26px under 1000px.
- **Title** (600, 17px): card and section headings.
- **Body** (400, 14px, 1.65 line height): paragraphs. Conversation previews are 13px and conversation notes 12px. Messages are 14px at 1.5 line height in chat bubbles.
- **Label** (700, 12px, tracking up to 1.8px): small capital labels such as "YOUR REPLY".

### Named Rules
**The Small and Soft Rule.** Interface text is small and low in weight contrast. Size and color separate levels, not heavy weights, which are reserved for buttons (600), headings and the brand.

## Layout

A fixed 245px sidebar beside a fluid main area, with 45px of vertical and 48px of horizontal padding. The Inbox opens with a heading and mode badge, then one toolbar row (a quiet "Updated" status on the left, **Options** and **Refresh inbox** on the right), then a two-column grid: the conversation list at about one third of the width and the open conversation at about two thirds, with a 20px gap and a 540px minimum height. The open conversation stacks its cards vertically with a 20px gap: the history card (name, summary and the Recent messages block) above the reply card. On windows wider than 1000px the grid is as tall as the window minus the header (at least 480px) and each pane scrolls on its own: the list on the left, and on the right the history card, while the reply card stays at the bottom, always fully visible and never covering the messages. The People tab is a single column capped at 740px, with a card per person.

Spacing rhythm: 8px (list padding), 12px (button and field padding), 18px, 20px (gaps), 25px (card padding), 45px (page padding). Density is relaxed, with large gaps between groups and small text inside them.

Responsive behavior: at 1000px and below the sidebar narrows to 190px, the Inbox becomes one column, and the conversation list caps at 260px tall and scrolls. At 650px and below the sidebar becomes a top bar, the brand text and footer hide, padding drops to 15px, and the Options panel opens from the left edge so it stays on screen.

## Elevation & Depth

Flat. There are no box shadows anywhere. Depth comes from tonal steps (page, then sidebar, then card) and 1px sage borders. The only layered element is the send confirmation dialog, which sits over a dim green-black backdrop (#152b24 at about 37% opacity). Hover is a slight dimming (brightness 0.94) of the element itself, not a lift or glow.

### Named Rules
**The Hairline Rule.** Surfaces are separated by tone and a 1px sage border, never by a shadow.

## Shapes

Everything is softly rounded. Cards and the dialog use 15px, groups of fields 12px, previews and message blocks 10px, buttons and conversation rows 9px, fields and callouts 8px, count chips 4px, and badges are pills (20px). Avatars and the status dot are circles. Borders are 1px in a sage tone.

## Components

Soft and unhurried: rounded, padded, quiet on hover, with one solid color reserved for forward motion.

### Buttons
- **Shape:** gently rounded (9px), 12px by 18px padding, weight 600.
- **Primary:** solid Fern Ink with white text. This is the default button style.
- **Secondary:** Morning Sidebar fill with Sage Text, for Refresh inbox, Clear, Draft a reply, Back to editing, Discard draft and other demoted actions.
- **Hover / Disabled:** hover dims by about 6%; disabled drops to 45% opacity with a not-allowed cursor.
- **Drafting:** the button stays fully opaque, shows a small spinner and the text "Drafting…", and uses a progress cursor.

### Navigation
- **Style:** full-width text buttons in the sidebar with a small count chip. Inactive items are transparent with muted green text (13px); the active item fills with Sage Tint and Leaf Text.
- **Mobile:** under 650px the sidebar becomes a top bar and the nav items stay at 12px.

### Cards / Containers
- **Corner Style:** 15px.
- **Background:** Morning Card, on a Morning Page background.
- **Border:** 1px Sage Line. No shadow.
- **Internal Padding:** 25px for review cards, 8px around the conversation list, 18px under 650px.

### Conversation Rows
Each row is a transparent button with a round sage avatar holding the initial, a 14px semibold name, a 13px preview cut at two lines, and a 12px semibold state line with a dot: dark green for draft saved, grey for unread, red for needs attention (new messages since the draft, or message not found), and a hollow ring while a send is being checked. The selected row has a Sage Tint fill, a 2px Fern Ink ring and `aria-current`. A loading row swaps its state line for a spinner and "Loading…".

### Inputs / Fields
- **Style:** white fill, 1px Field Edge border, 8px radius, 12px padding. The reply box is a full-width textarea at least 145px tall with 1.7 line height.
- **Focus:** a 2px Focus Leaf outline.
- **Disabled and read-only:** the reply box locks while a draft is being written or a chat is loading.

### Options
A quiet text button beside Refresh inbox that opens a bordered, flat panel (no shadow) with the two automatic settings and their consent notes. It closes with its own button, Escape (focus returns to the button) or a click outside it.
- **Badges:** pill-shaped Badge Wash with Sage Text at 12px, used for status and mode.
- **Errors:** Clay Wash with Clay Error text, 8px radius, 14px padding.
- **Receipts:** Receipt Wash, same shape, for confirmations.

### Send Confirmation
A native dialog, 560px wide at most, with 15px corners, Morning Card fill and 28px padding, over a dim backdrop. It lists the recipient in bold, the exact saved reply in a 16px Fern Ink bubble with white text (the same shape as your own messages in the conversation, with plain "To" and "Your reply" labels), a short reminder, and two buttons: **Back to editing** (secondary, focused first) and the confirm button (primary).

### People
A full-width add-contact row, then a Default voice card (with the small ghost) and a grid of person cards, each with an initial avatar, name, address, a voice status dot ("Personal voice" filled, "Uses default voice" hollow), a small Remove button and a Customize voice button. The button opens that voice in a pop-up (a native dialog like the send confirmation, 680px wide) so the cards never move: Save my voice, its status and Close are pinned in the header, and closing with unsaved edits asks whether to discard them.

### Keyboard
In the reply box, Cmd+Enter (or Ctrl+Enter) opens the send confirmation and Cmd+Shift+Enter drafts a reply. The shortcut is named in the box's placeholder and declared on both buttons. It never sends: only the dialog's confirm button does.

### Icons
Three drawn icons (Inbox, People, Send) in `Icons.tsx`: 24px grid, 2px rounded outline in the current text color, no fill, shown at 16px beside their labels. No unicode arrows or glyphs stand in for icons.

### Ghost Mark
A small drawn ghost (44px wide), flat, in Sage Tint with a 2px Fern Ink outline, used in empty and finished states, as the dot of the "g." brand mark (19px), and on the Draft a reply button while drafting. Open dots for eyes mean there is still work (first use, nothing chosen yet, another conversation waiting); closed arcs mean the inbox is clear; half-closed eyes mean it is drafting, with a slow 2px bob that stops for reduced motion. On the sent card it rises 10px into place once over 0.7s and then rests. Only the drafting ghost loops, and it holds still for people who prefer reduced motion. It is decoration only and hidden from assistive technology.

### Reply Box Status
The small line above the box (right-aligned, 12px Sage Text; Clay Error and semibold when a save failed) says what is happening to the text: "Not saved yet", "Saving…" while a save is pending, "Couldn't save yet" if one failed, or "Saved". Version numbers are never shown anywhere in the interface. After Clear or a replaced draft, a one-line "Reply cleared. Undo" (or "Replaced with a new draft. Undo") sits under the box with Undo as an underlined Fern Ink text button. It goes away when you type or open another chat.

### Sent Card
After a send, the right pane shows a centered card in place of the reply: a 17px heading ("Sent to Alex."; demo Send does nothing, so this card only appears for real sends), at most one supporting line, and one solid button for the next conversation ("Next conversation: Maya"). With nothing left, it says "That's everything for now." The ghost mark sits above the heading. It is announced as a status and stays until another chat is opened. A send that is confirmed while another chat is open appears as a one-line banner above the page instead.

## Do's and Don'ts

### Do:
- **Do** keep surfaces flat and separate them with tone and a 1px Sage Line border.
- **Do** use solid Fern Ink only for actions that move work forward, and the tonal secondary style for demoted actions.
- **Do** keep the reply box in the same card as the messages it answers: the unread messages sit directly above it, earlier messages fold above them, and the summary is its own short card at the top. Scroll the messages, not the reply. Their messages are Sage Tint bubbles on the left and yours are solid Fern Ink with white text on the right. Unread ones carry a thin outline so they stand apart from earlier ones, and the unread label carries when the first one arrived ("Today 9:05") when Messages gives times.
- **Do** show progress where the work is: a small spinner on the control or area that is loading.
- **Do** keep the send confirmation as the only path to a real send, with the exact recipient and text visible.
- **Do** keep text at 4.5:1 or better against its background and field borders at 3:1.
- **Do** make the selected conversation unmistakable: Sage Tint fill, 2px Fern Ink ring and `aria-current`.
- **Do** load or bundle the fonts the stylesheet names, or choose a pair that actually ships.

### Don't:
- **Don't** add box shadows, glows or gradients.
- **Don't** drift toward a glossy gradient SaaS dashboard, a dark neon or cyber look, or a clone of a messaging app (bubbles stay inside the conversation card).
- **Don't** dim or disable the whole page for a task that affects one control.
- **Don't** introduce a text color paler than Sage Text, or bring back the retired pale tints.
- **Don't** use heavy weights for emphasis in body text; use size and color.
