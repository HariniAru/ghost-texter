"""Only the approval service may call send. The LLM never receives tools."""

import os
import re
from typing import Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel


class MessagingError(RuntimeError):
    """Safe, actionable connector error; never includes private tool output."""


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


class Messenger(Protocol):
    async def unread(self, recipients: list[str]) -> list[Conversation]: ...
    async def read(self, recipient: str) -> str: ...
    async def send(self, recipient: str, text: str) -> str: ...


class DemoMessenger:
    def __init__(self):
        self.history = {
            "alex@example.test": "You: hey! how has your week been?\nAlex: pretty good! coffee tomorrow at 10?",
            "maya@example.test": "You: send me the photos when you can :)\nMaya: just sent them! how was the trip?",
        }
        self.unread_messages = {
            r: [history.splitlines()[-1]] for r, history in self.history.items()
        }
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
            rows = MESSAGE_ROW.findall(result)
            if rows:
                conversations.append(
                    Conversation(
                        recipient=recipient,
                        preview=rows[0],
                        unread_count=len(rows),
                        count_capped=len(rows) == 50,
                    )
                )
            elif "No messages found in the specified time period." not in result:
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
            raise MessagingError(
                "No readable history returned for this chat on this Mac. Check the exact phone number/email and local Messages sync."
            )
        return result

    async def send(self, recipient, text):
        result = await self.call("tool_send_message", {"recipient": recipient, "message": text})
        # Fail closed: unknown tool responses require reconciliation, never automatic retry.
        if not re.search(r"(?m)^Message (?:sent|delivered) successfully via ", result):
            raise RuntimeError(
                "Unrecognized send receipt; verify in Messages before taking further action."
            )
        return result
