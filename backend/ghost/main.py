import asyncio
import hashlib
import re
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from ghost.config import Settings
from ghost.messaging import MESSAGE_ROW, DemoMessenger, MacMessages, MessagingError
from ghost.store import Store
from ghost.voice import Profile, resolve_profile, suggest_pairs
from ghost.workflow import AIConfigurationError, build_graph, summarize


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


class CreateDraft(BaseModel):
    recipient: str = Field(min_length=3, max_length=200)


class EditDraft(BaseModel):
    version: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Reply cannot be blank")
        return value


class Decision(BaseModel):
    version: int = Field(ge=1)


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

    def config(draft_id):
        return {"configurable": {"thread_id": draft_id}}

    def allowed(recipient):
        if settings.mode == "demo":
            if recipient not in messenger.history:
                raise HTTPException(422, "Choose a demo recipient")
        elif recipient not in settings.allowed_recipients or not (
            re.fullmatch(r"\+[1-9]\d{6,14}", recipient)
            or re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient)
        ):
            raise HTTPException(403, "Use an exact allowlisted E.164 phone number or email")

    @app.get("/api/status", dependencies=[Depends(authorize)])
    async def status():
        return {
            "mode": settings.mode,
            "llm": settings.llm,
            "llm_provider": settings.llm_provider,
            "send_enabled": settings.send_enabled,
            "recipients": list(messenger.history)
            if settings.mode == "demo"
            else settings.allowed_recipients,
        }

    @app.get("/api/inbox", dependencies=[Depends(authorize)])
    async def inbox():
        recipients = (
            list(messenger.history) if settings.mode == "demo" else settings.allowed_recipients
        )
        # Keep the existing allowlist boundary. Do not enumerate unrelated conversations.
        for recipient in recipients:
            allowed(recipient)
        try:
            conversations = await messenger.unread(recipients)
        except (MessagingError, AIConfigurationError) as exc:
            raise HTTPException(502, str(exc)) from exc
        except Exception:
            raise HTTPException(
                502, "Unable to load unread conversations. Check MCP permissions/configuration."
            )
        return conversations

    @app.get("/api/conversation", dependencies=[Depends(authorize)])
    async def conversation(recipient: str):
        allowed(recipient)
        async with lock:
            try:
                context = await messenger.read(recipient)
                if not context.strip():
                    raise HTTPException(422, "No conversation context available")
                digest = fingerprint(context)
                cached = summaries.get(recipient)
                if not cached or cached["fingerprint"] != digest:
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

    @app.get("/api/drafts", dependencies=[Depends(authorize)])
    async def drafts():
        return store.all()

    @app.get("/api/profile", dependencies=[Depends(authorize)])
    async def profile():
        return Profile.model_validate(store.profile())

    @app.put("/api/profile", dependencies=[Depends(authorize)])
    async def update_profile(body: Profile):
        for recipient in body.recipients:
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
                    reviewed = next(
                        (row for row in existing if row["fingerprint"] == fingerprint(context)),
                        None,
                    )
                    if reviewed:
                        return {"created": False, "reason": "already_reviewed", "draft": reviewed}
                # De-duplicate pending reviews of the same conversation snapshot.
                for row in existing:
                    if (
                        row["recipient"] == body.recipient
                        and row["fingerprint"] == fingerprint(context)
                        and row["status"] == "pending"
                    ):
                        return row
                draft_id = str(uuid.uuid4())
                result = await asyncio.to_thread(
                    graph.invoke,
                    {"context": context, **resolve_profile(store.profile(), body.recipient)},
                    config(draft_id),
                )
            except HTTPException:
                raise
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

    @app.post("/api/drafts/{draft_id}/approve", dependencies=[Depends(authorize)])
    async def approve(draft_id: str, body: Decision):
        async with lock:
            row = current(draft_id, body.version)
            allowed(row["recipient"])
            if settings.mode != "demo" and not settings.send_enabled:
                raise HTTPException(403, "Live sending is disabled in configuration")
            try:
                latest = await messenger.read(row["recipient"])
            except Exception:
                raise HTTPException(502, "Conversation recheck failed. Nothing sent.")
            if fingerprint(latest) != row["fingerprint"]:
                store.db.execute("UPDATE drafts SET status='stale' WHERE id=?", (draft_id,))
                store.event(draft_id, "stale", {"version": body.version})
                store.db.commit()
                raise HTTPException(409, "Conversation changed. Create and review a fresh draft.")
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
                    "Send outcome unknown. Verify in Messages; this draft cannot be retried.",
                )
            store.db.execute(
                "UPDATE drafts SET status='sent', receipt=? WHERE id=?",
                (receipt, draft_id),
            )
            store.event(draft_id, "sent", {"receipt": receipt})
            store.db.commit()
            return store.one(draft_id)

    from pathlib import Path

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
    return app
