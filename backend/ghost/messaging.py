"""Only the approval service may call send. The LLM never receives tools."""

import os
import re
from datetime import datetime
from typing import Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel


class MessagingError(RuntimeError):
    """Safe, actionable connector error; never includes private tool output."""


NO_CHAT = re.compile(r"No (?:group )?chat found|No messages found in the specified time period\.")


class ChatNotFound(MessagingError):
    """The connector looked for this exact chat and has no messages for it."""


def normalize_transcript(text):
    # The MCP security envelope escapes transcript line breaks as literal \n.
    # Restore only timestamped row separators, never arbitrary escapes/instructions.
    return re.sub(r"\\n(?=\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\])", "\n", text)


class Conversation(BaseModel):
    recipient: str
    preview: str
    unread_count: int
    count_capped: bool = False


MESSAGE_ROW = re.compile(r"(?m)^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\].*$")

# The connector's paging note, appended to the oldest row when the limit is reached.
PAGING_NOTE = re.compile(
    r"(?:\\n|\n)\(Showing \d+ message\(s\) from offset \d+; older messages may exist"
    r" - call again with offset=\d+\.\)"
)
# Time, sender, then tags such as [iMessage] or [tapback: loved], which can contain ": " themselves.
ROW_HEAD = re.compile(r"(\[[^\]]+\] .*?(?: \[[^\]]*\])*): ")
TAPBACK_TAG = re.compile(r"\[tapback:[^\]]*\]")
# A trailing attachment list, the inline image placeholder, and attachment- or reaction-only bodies.
ATTACHMENT_NOISE = re.compile(
    r"\s*\[attachments: .*\]$|\ufffc|^\s*(?:\[attachment\]|\(reaction\))\s*$"
)


def text_only(transcript):
    """Keep only text messages: drop reactions, attachment-only rows, and the paging note."""
    lines = []
    for line in PAGING_NOTE.sub("", transcript).split("\n"):
        if MESSAGE_ROW.match(line):
            head = ROW_HEAD.match(line)
            body = ATTACHMENT_NOISE.sub("", line[head.end() :]).strip() if head else ""
            if not body or TAPBACK_TAG.search(head[1]):
                continue
            line = head[0] + body
        lines.append(line)
    return "\n".join(lines)


OUTGOING_ROW = re.compile(
    r"(?m)^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] You(?: \[[^\]]*\])*: (.*)$"
)


def sent_since(context, text, since):
    # Exact outgoing text at or after `since`, so an older identical text is not proof.
    # The connector writes line breaks and tabs in a body as literal \n and \t.
    wanted = re.sub(r"\r\n|\r|\n", r"\\n", text).replace("\t", r"\t").strip()
    return any(
        body.strip() == wanted and datetime.strptime(sent, "%Y-%m-%d %H:%M:%S") >= since
        for sent, body in OUTGOING_ROW.findall(context)
    )


class Messenger(Protocol):
    async def unread(self, recipients: list[str]) -> list[Conversation]: ...
    async def read(self, recipient: str) -> str: ...
    async def send(self, recipient: str, text: str) -> str: ...


def unread_tail(history):
    # A demo chat's unread messages are the other person's messages after your last reply.
    lines = history.splitlines()
    mine = [i for i, line in enumerate(lines) if line.startswith("You:")]
    return lines[mine[-1] + 1 :] if mine else lines


class DemoMessenger:
    def __init__(self):
        self.history = {
            "alex@example.test": "You: hey! how has your week been?\nAlex: pretty good! coffee tomorrow at 10?",
            "maya@example.test": "You: send me the photos when you can :)\nMaya: just sent them! how was the trip?",
            # Banter, for testing a per-person voice that differs from the default.
            "jordan@example.test": "Jordan: bro you still owe me $20 from pizza\nYou: lol i paid you back\n"
            "Jordan: you did NOT\nJordan: also are you coming to mom's on sunday or not",
            # Several unread messages, with a question that needs a real answer.
            "priya@example.test": "You: thanks again for helping me move!\nPriya: of course! my turn next month haha\n"
            "Priya: btw are you free saturday afternoon? need a second opinion on apartments\n"
            "Priya: around 2pm if that works",
        }
        self.unread_messages = {r: unread_tail(h) for r, h in self.history.items()}
        self.sent = []

    async def unread(self, recipients):
        return [
            Conversation(
                recipient=r,
                preview=self.unread_messages[r][-1],
                unread_count=len(self.unread_messages[r]),
            )
            for r in recipients
            if self.unread_messages.get(r)
        ]

    async def read(self, recipient):
        return self.history.get(recipient, "")

    async def send(self, recipient, text):
        self.sent.append((recipient, text))
        self.history[recipient] += "\nYou: " + text
        return "Simulated send; no message left this app."


class MacMessages:
    def __init__(self, settings):
        self.params = StdioServerParameters(command=settings.mcp_command, args=settings.mcp_args)

    async def call(self, name, arguments):
        # Upstream stderr may contain contact identifiers; never mirror it into app logs.
        with open(os.devnull, "w") as errlog:
            async with stdio_client(self.params, errlog=errlog) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    available = await session.list_tools()
                    tool = next((t for t in available.tools if t.name == name), None)
                    if tool is None or set(arguments) - set(tool.inputSchema.get("properties", {})):
                        raise MessagingError(
                            "Installed Messages MCP is incompatible with this app. "
                            "Use the pinned GHOST_MCP_ARGS in .env.example and restart the backend."
                        )
                    result = await session.call_tool(name, arguments)
                    text = "\n".join(c.text for c in result.content if c.type == "text")
                    if result.isError or not text:
                        raise MessagingError(
                            "MCP operation failed; check connector permissions/configuration."
                        )
                    return normalize_transcript(text)

    async def unread(self, recipients):
        conversations = []
        for recipient in recipients:
            result = await self.call(
                "tool_get_recent_messages",
                {
                    "chat_id": recipient,
                    "start_date": "2001-01-01",
                    "limit": 50,
                    "unread_only": True,
                },
            )
            # Reactions and attachment-only messages do not make a chat unread here.
            rows = MESSAGE_ROW.findall(text_only(result))
            if rows:
                conversations.append(
                    Conversation(
                        recipient=recipient,
                        preview=rows[0],
                        unread_count=len(rows),
                        count_capped=len(MESSAGE_ROW.findall(result)) == 50,
                    )
                )
            elif not NO_CHAT.search(result):
                # Empty and permission/schema errors must not look like a quiet inbox.
                raise MessagingError(
                    "Unable to read unread messages. Check Full Disk Access and the exact configured chat address."
                )
        return conversations

    async def read(self, recipient):
        # Fixed start avoids a moving time window invalidating unchanged conversations.
        result = await self.call(
            "tool_get_recent_messages",
            {
                "chat_id": recipient,
                "start_date": "2001-01-01",
                "limit": 50,
            },
        )

        # Exact chat scope includes outgoing context and avoids mixing group messages
        # from a contact. Refuse unknown/empty/error prose instead of drafting from it.
        if not re.search(r"(?m)^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]", result):
            error = ChatNotFound if NO_CHAT.search(result) else MessagingError
            raise error(
                "No readable history returned for this chat on this Mac. Check the exact phone number/email and local Messages sync."
            )
        return text_only(result)

    async def send(self, recipient, text):
        result = await self.call("tool_send_message", {"recipient": recipient, "message": text})
        # Fail closed: unknown tool responses require reconciliation, never automatic retry.
        if not re.search(r"(?m)^Message (?:sent|delivered) successfully via ", result):
            raise RuntimeError(
                "Unrecognized send receipt; verify in Messages before taking further action."
            )
        return result
