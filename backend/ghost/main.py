import asyncio
import hashlib
import re
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from ghost.config import Settings
from ghost.messaging import (
    MESSAGE_ROW,
    ChatNotFound,
    DemoMessenger,
    MacMessages,
    MessagingError,
    sent_since,
)
from ghost.ollama_model import AIConfigurationError
from ghost.store import Store
from ghost.voice import Profile, resolve_profile, suggest_pairs
from ghost.workflow import RepeatedDraft, build_graph, summarize

MAX_CONTACTS = 50
CHAT_NOT_FOUND = "Chat not found with this contact."
NEW_MESSAGES = "New messages came in, so nothing was sent. Read them, then send again."
FOUND_RECEIPT = "The send was interrupted, but this message was found in Messages."


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


class CreateDraft(BaseModel):
    recipient: str = Field(min_length=3, max_length=200)


class ReplyText(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Reply cannot be blank")
        return value


class EditDraft(ReplyText):
    version: int = Field(ge=1)


class TypedDraft(ReplyText):
    recipient: str = Field(min_length=3, max_length=200)
    # The conversation the user was looking at when they wrote this.
    fingerprint: str = Field(min_length=1, max_length=200)


class Decision(BaseModel):
    version: int = Field(ge=1)


class AddContact(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    number: str = Field(min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()


def normalize_number(value):
    # Only removes formatting. Never guesses a country code or matches a contact name.
    return re.sub(r"[\s().-]", "", value)


def is_phone_number(value):
    return bool(re.fullmatch(r"\+[1-9]\d{6,14}", value))


def is_exact_address(address):
    return is_phone_number(address) or bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address))


def create_app(settings=None, messenger=None):
    settings = settings or Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_path = settings.data_dir / "api-token"
    if not settings.api_token:
        if not token_path.exists():
            token_path.write_text(secrets.token_urlsafe(32))
            token_path.chmod(0o600)
        settings.api_token = token_path.read_text().strip()
    store = Store(settings.data_dir / "ghost.sqlite")
    checkpoint_db = sqlite3.connect(settings.data_dir / "workflow.sqlite", check_same_thread=False)
    graph = build_graph(SqliteSaver(checkpoint_db), settings)
    messenger = messenger or (DemoMessenger() if settings.mode == "demo" else MacMessages(settings))
    lock = asyncio.Lock()
    summaries = {}  # One snapshot per recipient; restart clears this cache.
    recent = {}  # The last messages read per recipient, so a summary needs no second read.

    @asynccontextmanager
    async def lifespan(app):
        yield
        store.db.close()
        checkpoint_db.close()

    app = FastAPI(title="Ghost Texter", lifespan=lifespan)
    app.state.store = store
    app.state.messenger = messenger

    async def authorize(request: Request, authorization: str = Header(default="")):
        # Reject cross-origin browser mutations, even if a token is accidentally disclosed.
        origin = request.headers.get("origin")
        if origin and origin not in {
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8001",
            "http://localhost:8001",
        }:
            raise HTTPException(403, "Untrusted origin")
        if not secrets.compare_digest(authorization, "Bearer " + settings.api_token):
            raise HTTPException(401, "Enter your local API token")

    def current(draft_id, version):
        row = store.one(draft_id)
        if not row:
            raise HTTPException(404, "Draft not found")
        if row["status"] != "pending" or row["version"] != version:
            raise HTTPException(409, "Draft changed or already resolved. Refresh and review again.")
        return row

    def uncertain(draft_id):
        row = store.one(draft_id)
        if not row:
            raise HTTPException(404, "Draft not found")
        if row["status"] != "uncertain":
            raise HTTPException(409, "Draft changed or already resolved. Refresh and review again.")
        return row

    def found_in_messages(row, context):
        since = store.approved_at(row["id"])
        return since is not None and sent_since(context, row["text"], since)

    def mark_found(row):
        store.db.execute(
            "UPDATE drafts SET status='sent', receipt=? WHERE id=?", (FOUND_RECEIPT, row["id"])
        )
        store.event(row["id"], "sent", {"receipt": FOUND_RECEIPT, "found_in_messages": True})
        store.db.commit()
        return store.one(row["id"])

    def config(draft_id):
        return {"configurable": {"thread_id": draft_id}}

    def live_recipients():
        # Exact addresses from .env plus those the user added on the dashboard.
        return list(dict.fromkeys([*settings.allowed_recipients, *store.contacts()]))

    def recipients():
        return list(messenger.history) if settings.mode == "demo" else live_recipients()

    def allowed(recipient):
        if settings.mode == "demo":
            if recipient not in messenger.history:
                raise HTTPException(422, "Choose a demo recipient")
        elif recipient not in live_recipients() or not is_exact_address(recipient):
            raise HTTPException(403, "This exact phone number or email is not in your contacts")

    def contact_rows():
        if settings.mode == "demo":
            return [{"name": "", "address": a, "source": "demo"} for a in messenger.history]
        names = store.contact_names()
        return [
            {
                "name": names.get(address, ""),
                "address": address,
                "source": "env" if address in settings.allowed_recipients else "app",
            }
            for address in live_recipients()
        ]

    def editable_contacts():
        if settings.mode == "demo":
            raise HTTPException(403, "Demo mode uses synthetic contacts")

    @app.get("/api/status", dependencies=[Depends(authorize)])
    async def status():
        return {
            "mode": settings.mode,
            "llm": settings.llm,
            "send_enabled": settings.send_enabled,
            "recipients": recipients(),
        }

    @app.get("/api/contacts", dependencies=[Depends(authorize)])
    async def contacts():
        return contact_rows()

    @app.post("/api/contacts", dependencies=[Depends(authorize)])
    async def add_contact(body: AddContact):
        editable_contacts()
        number = normalize_number(body.number)
        if not is_phone_number(number):
            raise HTTPException(
                422,
                f"Could not add '{body.number}'. Use a full number with its country code, "
                "like +14155550123.",
            )
        async with lock:
            existing = live_recipients()
            if number not in existing:
                if len(existing) >= MAX_CONTACTS:
                    raise HTTPException(422, f"Keep at most {MAX_CONTACTS} contacts")
                # Catch typos now. The text is discarded.
                try:
                    context = await messenger.read(number)
                except ChatNotFound as exc:
                    raise HTTPException(422, CHAT_NOT_FOUND) from exc
                except MessagingError as exc:
                    raise HTTPException(422, f"Could not add {number}. {exc}") from exc
                except Exception:
                    raise HTTPException(
                        502, "Could not check this number. Check MCP permissions/configuration."
                    )
                if not context.strip():
                    raise HTTPException(422, CHAT_NOT_FOUND)
            store.add_contact(number, body.name)
            return contact_rows()

    @app.delete("/api/contacts", dependencies=[Depends(authorize)])
    async def remove_contact(address: str):
        editable_contacts()
        async with lock:
            if address in settings.allowed_recipients:
                raise HTTPException(
                    409, "This contact is set in .env. Remove it there and restart."
                )
            if address not in store.contacts():
                raise HTTPException(404, "Contact not found")
            store.remove_contact(address)
            summaries.pop(address, None)
            return contact_rows()

    @app.get("/api/inbox", dependencies=[Depends(authorize)])
    async def inbox():
        targets = recipients()
        # Keep the existing allowlist boundary. Do not enumerate unrelated conversations.
        for recipient in targets:
            allowed(recipient)
        try:
            conversations = await messenger.unread(targets)
        except (MessagingError, AIConfigurationError) as exc:
            raise HTTPException(502, str(exc)) from exc
        except Exception:
            raise HTTPException(
                502, "Unable to load unread conversations. Check MCP permissions/configuration."
            )
        # A chat you replied to from this app is done until they write again: hide it while
        # its newest unread message was part of the conversation a sent reply answered.
        answered = [
            (row["recipient"], row["context"])
            for row in store.all()
            if row["status"] == "sent" and settings.mode != "demo"
        ]
        return [
            c
            for c in conversations
            if not any(r == c.recipient and c.preview in context for r, context in answered)
        ]

    @app.get("/api/conversation", dependencies=[Depends(authorize)])
    async def conversation(recipient: str, summary: bool = True):
        # summary=false returns the messages at once; the page then asks for the summary.
        allowed(recipient)
        async with lock:
            try:
                context = await messenger.read(recipient)
                if not context.strip():
                    raise HTTPException(422, "No conversation context available")
                digest = fingerprint(context)
                cached = summaries.get(recipient)
                if not cached or cached["fingerprint"] != digest:
                    if not summary:
                        recent[recipient] = context
                        return {
                            "recipient": recipient,
                            "context": context,
                            "fingerprint": digest,
                            "summary": None,
                            "summary_kind": None,
                        }
                    cached = {
                        "fingerprint": digest,
                        **await asyncio.to_thread(summarize, context, settings),
                    }
                    summaries[recipient] = cached
            except HTTPException:
                raise
            except (MessagingError, AIConfigurationError) as exc:
                raise HTTPException(502, str(exc)) from exc
            except Exception:
                raise HTTPException(
                    502, "Unable to load conversation or summary. Check MCP/model configuration."
                )
            return {"recipient": recipient, "context": context, **cached}

    @app.get("/api/conversation/summary", dependencies=[Depends(authorize)])
    async def conversation_summary(recipient: str, digest: str = Query(alias="fingerprint")):
        # Summarizes the messages the page just loaded. Read only, and outside the send lock.
        allowed(recipient)
        cached = summaries.get(recipient)
        if cached and cached["fingerprint"] == digest:
            return cached
        context = recent.get(recipient)
        if not context or fingerprint(context) != digest:
            raise HTTPException(409, "Conversation changed. Open it again.")
        try:
            result = await asyncio.to_thread(summarize, context, settings)
        except AIConfigurationError as exc:
            raise HTTPException(502, str(exc)) from exc
        except Exception:
            raise HTTPException(502, "Unable to generate a summary. Check the model configuration.")
        summaries[recipient] = {"fingerprint": digest, **result}
        return summaries[recipient]

    @app.get("/api/drafts", dependencies=[Depends(authorize)])
    async def drafts():
        return store.saved()

    @app.get("/api/profile", dependencies=[Depends(authorize)])
    async def profile():
        return Profile.model_validate(store.profile())

    @app.put("/api/profile", dependencies=[Depends(authorize)])
    async def update_profile(body: Profile):
        # Saved voice settings can outlive a removed contact and grant no access. PUT is a
        # full replacement, so only addresses new to the profile must be current contacts.
        saved = store.profile().get("recipients", {})
        for recipient in body.recipients:
            if recipient not in saved:
                allowed(recipient)
        async with lock:
            store.db.execute(
                "INSERT OR REPLACE INTO profile VALUES (1,?)", (body.model_dump_json(),)
            )
            store.db.commit()
        return body

    @app.post("/api/profile/suggestions", dependencies=[Depends(authorize)])
    async def voice_suggestions(body: CreateDraft):
        allowed(body.recipient)
        try:
            context = await messenger.read(body.recipient)
        except Exception:
            raise HTTPException(502, "Could not read this chat. No voice examples were saved.")
        return {"pairs": suggest_pairs(context, demo=settings.mode == "demo")}

    async def prepare_draft(body: CreateDraft, automatic=False):
        allowed(body.recipient)
        async with lock:
            try:
                existing = [row for row in store.all() if row["recipient"] == body.recipient]
                if automatic:
                    # Automatic work never replaces pending/edited drafts or retries uncertainty.
                    protected = next(
                        (
                            row
                            for row in existing
                            if row["status"] in {"pending", "sending", "uncertain"}
                        ),
                        None,
                    )
                    if protected:
                        return {"created": False, "reason": "existing_review", "draft": protected}
                    if not await messenger.unread([body.recipient]):
                        return {"created": False, "reason": "not_unread", "draft": None}
                context = await messenger.read(body.recipient)
                if not context.strip():
                    raise HTTPException(422, "No conversation context available")
                if automatic:
                    rows = MESSAGE_ROW.findall(context)
                    latest = rows[0] if rows else context.splitlines()[-1]
                    # Ignore old unread messages when the latest readable event is our reply.
                    if re.match(r"^(?:\[.*?\] )?You(?: \[.*?\])*:", latest):
                        return {"created": False, "reason": "latest_outgoing", "draft": None}
                    # A chat whose current messages a sent reply already answered needs no draft.
                    # Drafts the user rejected do not block this: turning automatic drafts on
                    # prepares every unread chat without a saved draft, avoiding rejected texts.
                    answered = next(
                        (
                            row
                            for row in existing
                            if row["status"] == "sent"
                            and row["fingerprint"] == fingerprint(context)
                        ),
                        None,
                    )
                    if answered:
                        return {"created": False, "reason": "already_sent", "draft": answered}
                for row in existing:
                    if (
                        row["recipient"] == body.recipient
                        and row["fingerprint"] == fingerprint(context)
                        and row["status"] == "pending"
                    ):
                        return row
                # Drafts already discarded for these exact messages, newest first. New messages or
                # a sent reply change the fingerprint, so this starts empty again.
                avoid = [
                    row["text"]
                    for row in existing
                    if row["fingerprint"] == fingerprint(context) and row["status"] == "rejected"
                ][:5]
                draft_id = str(uuid.uuid4())
                result = await asyncio.to_thread(
                    graph.invoke,
                    {
                        "context": context,
                        "avoid": avoid,
                        **resolve_profile(store.profile(), body.recipient),
                    },
                    config(draft_id),
                )
            except HTTPException:
                raise
            except RepeatedDraft:
                raise HTTPException(
                    502,
                    "Failed to generate a response draft. Try again.",
                )
            except (MessagingError, AIConfigurationError) as exc:
                raise HTTPException(502, str(exc)) from exc
            except Exception:
                raise HTTPException(
                    502,
                    "Unable to read conversation or generate draft. Check MCP/model configuration.",
                )
            store.db.execute(
                "INSERT INTO drafts(id,recipient,context,fingerprint,text) VALUES (?,?,?,?,?)",
                (
                    draft_id,
                    body.recipient,
                    context,
                    fingerprint(context),
                    result["text"],
                ),
            )
            store.event(draft_id, "drafted", {"version": 1, "automatic": automatic})
            store.db.commit()
            draft = store.one(draft_id)
            return {"created": True, "reason": "created", "draft": draft} if automatic else draft

    @app.post("/api/drafts", dependencies=[Depends(authorize)])
    async def create(body: CreateDraft):
        return await prepare_draft(body)

    async def start_review(recipient, context, text, **event):
        # The user's own text enters the same review pause as a model draft, without the model.
        draft_id = str(uuid.uuid4())
        await asyncio.to_thread(graph.invoke, {"context": context, "text": text}, config(draft_id))
        store.db.execute(
            "INSERT INTO drafts(id,recipient,context,fingerprint,text) VALUES (?,?,?,?,?)",
            (draft_id, recipient, context, fingerprint(context), text),
        )
        store.event(draft_id, "drafted", {"version": 1, **event})
        return draft_id

    @app.post("/api/drafts/typed", dependencies=[Depends(authorize)])
    async def typed(body: TypedDraft):
        # Saves a reply the user wrote. Sending it still needs the normal approval.
        allowed(body.recipient)
        async with lock:
            if any(
                row["recipient"] == body.recipient
                and row["status"] in {"pending", "sending", "uncertain"}
                for row in store.all()
            ):
                raise HTTPException(409, "This chat already has a saved draft.")
            try:
                context = await messenger.read(body.recipient)
                if fingerprint(context) != body.fingerprint:
                    raise HTTPException(409, NEW_MESSAGES)
                draft_id = await start_review(body.recipient, context, body.text, typed=True)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(502, "Could not check Messages. Your reply was not saved.")
            store.db.commit()
            return store.one(draft_id)

    @app.post("/api/inbox/prepare", dependencies=[Depends(authorize)])
    async def auto_prepare(body: CreateDraft):
        return await prepare_draft(body, automatic=True)

    @app.patch("/api/drafts/{draft_id}", dependencies=[Depends(authorize)])
    async def edit(draft_id: str, body: EditDraft):
        async with lock:
            current(draft_id, body.version)
            store.db.execute(
                "UPDATE drafts SET text=?, version=version+1 WHERE id=?",
                (body.text, draft_id),
            )
            store.event(draft_id, "edited", {"version": body.version + 1, "text": body.text})
            store.db.commit()
            return store.one(draft_id)

    @app.post("/api/drafts/{draft_id}/reject", dependencies=[Depends(authorize)])
    async def reject(draft_id: str, body: Decision):
        async with lock:
            current(draft_id, body.version)
            store.db.execute("UPDATE drafts SET status='rejected' WHERE id=?", (draft_id,))
            store.event(draft_id, "rejected", {"version": body.version})
            store.db.commit()
            await asyncio.to_thread(
                graph.invoke, Command(resume={"action": "reject"}), config(draft_id)
            )
            return store.one(draft_id)

    @app.post("/api/drafts/{draft_id}/refresh", dependencies=[Depends(authorize)])
    async def refresh_context(draft_id: str, body: Decision):
        # Keeps the saved text but binds a new version to the latest messages. Never sends.
        async with lock:
            row = current(draft_id, body.version)
            allowed(row["recipient"])
            try:
                context = await messenger.read(row["recipient"])
            except Exception:
                raise HTTPException(502, "Could not read this chat. Your draft was not changed.")
            if not context.strip():
                raise HTTPException(422, "No conversation context available")
            digest = fingerprint(context)
            store.db.execute(
                "UPDATE drafts SET context=?, fingerprint=?, version=version+1 WHERE id=?",
                (context, digest, draft_id),
            )
            store.event(
                draft_id, "context_updated", {"version": body.version + 1, "fingerprint": digest}
            )
            store.db.commit()
            return store.one(draft_id)

    @app.post("/api/drafts/{draft_id}/verify", dependencies=[Depends(authorize)])
    async def verify(draft_id: str):
        # Read only: looks for an interrupted send in Messages. Never sends.
        async with lock:
            row = uncertain(draft_id)
            allowed(row["recipient"])
            try:
                context = await messenger.read(row["recipient"])
            except Exception:
                raise HTTPException(502, "Could not check Messages.")
            return mark_found(row) if found_in_messages(row, context) else row

    @app.post("/api/drafts/{draft_id}/retry", dependencies=[Depends(authorize)])
    async def retry(draft_id: str):
        # Checks once more, then makes a new pending draft. Sending still needs its own approval.
        async with lock:
            row = uncertain(draft_id)
            allowed(row["recipient"])
            try:
                context = await messenger.read(row["recipient"])
                if found_in_messages(row, context):
                    return mark_found(row)
                new_id = await start_review(
                    row["recipient"], context, row["text"], retry_of=draft_id
                )
            except Exception:
                raise HTTPException(502, "Could not check Messages. Nothing was sent.")
            store.db.execute("UPDATE drafts SET status='discarded' WHERE id=?", (draft_id,))
            store.event(draft_id, "discarded", {"retried_as": new_id})
            store.db.commit()
            return store.one(new_id)

    @app.post("/api/drafts/{draft_id}/discard", dependencies=[Depends(authorize)])
    async def discard(draft_id: str):
        async with lock:
            uncertain(draft_id)
            store.db.execute("UPDATE drafts SET status='discarded' WHERE id=?", (draft_id,))
            store.event(draft_id, "discarded", {})
            store.db.commit()
            return store.one(draft_id)

    @app.post("/api/drafts/{draft_id}/approve", dependencies=[Depends(authorize)])
    async def approve(draft_id: str, body: Decision):
        async with lock:
            row = current(draft_id, body.version)
            allowed(row["recipient"])
            if settings.mode == "demo":
                # Demo Send does nothing: no dispatch, no status change, no event. The sample
                # chats stay unread so they can be tried again.
                return store.one(draft_id)
            if not settings.send_enabled:
                raise HTTPException(403, "Live sending is disabled in configuration")
            try:
                latest = await messenger.read(row["recipient"])
            except Exception:
                raise HTTPException(502, "Conversation recheck failed. Nothing sent.")
            if fingerprint(latest) != row["fingerprint"]:
                store.db.execute("UPDATE drafts SET status='stale' WHERE id=?", (draft_id,))
                store.event(draft_id, "stale", {"version": body.version})
                store.db.commit()
                raise HTTPException(409, NEW_MESSAGES)
            # Durable approval records exact recipient, text, version, and context fingerprint.
            # Commit intent before dispatch. Duplicate requests and restarts cannot repeat it.
            store.db.execute("UPDATE drafts SET status='sending' WHERE id=?", (draft_id,))
            store.event(
                draft_id,
                "approved",
                {k: row[k] for k in ("recipient", "text", "version", "fingerprint")},
            )
            store.db.commit()
            try:
                await asyncio.to_thread(
                    graph.invoke,
                    Command(
                        resume={
                            "action": "approve",
                            "text": row["text"],
                            "version": row["version"],
                        }
                    ),
                    config(draft_id),
                )
                receipt = await messenger.send(row["recipient"], row["text"])
            except Exception:
                store.db.execute("UPDATE drafts SET status='uncertain' WHERE id=?", (draft_id,))
                store.event(draft_id, "uncertain", {})
                store.db.commit()
                raise HTTPException(
                    502,
                    "Send outcome unknown. Checking Messages to see whether it went through.",
                )
            store.db.execute(
                "UPDATE drafts SET status='sent', receipt=? WHERE id=?",
                (receipt, draft_id),
            )
            store.event(draft_id, "sent", {"receipt": receipt})
            store.db.commit()
            return store.one(draft_id)

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
    return app
