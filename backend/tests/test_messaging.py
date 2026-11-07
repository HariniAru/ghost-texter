import asyncio

import pytest
from ghost.config import Settings
from ghost.messaging import MacMessages


def test_read_uses_exact_chat_scope_and_accepts_message_word_error():
    adapter = MacMessages(Settings(_env_file=None))
    calls = []

    async def call(name, args):
        calls.append((name, args))
        return "<untrusted-mcp-output>\n[2026-10-17 10:00:00] Alex: got an error on my laptop\n</untrusted-mcp-output>"

    adapter.call = call
    result = asyncio.run(adapter.read("+14155550123"))
    assert "error on my laptop" in result
    assert calls[0][1]["chat_id"] == "+14155550123"
    assert "contact" not in calls[0][1]


@pytest.mark.parametrize(
    "response",
    [
        "Error accessing messages: denied",
        "No messages found in the specified time period.",
        "Multiple contacts found matching recipient",
    ],
)
def test_read_refuses_error_and_unknown_context(response):
    adapter = MacMessages(Settings(_env_file=None))

    async def call(*args):
        return response

    adapter.call = call
    with pytest.raises(RuntimeError):
        asyncio.run(adapter.read("+14155550123"))


@pytest.mark.parametrize(
    "response,accepted",
    [
        (
            "<untrusted-mcp-output>\nMessage sent successfully via iMessage to Alex\n</untrusted-mcp-output>",
            True,
        ),
        ("Send cancelled: not successfully sent", False),
        ("Error: no success receipt", False),
    ],
)
def test_send_requires_recognized_receipt(response, accepted):
    adapter = MacMessages(Settings(_env_file=None))

    async def call(*args):
        return response

    adapter.call = call
    if accepted:
        assert asyncio.run(adapter.send("+14155550123", "hey")) == response
    else:
        with pytest.raises(RuntimeError):
            asyncio.run(adapter.send("+14155550123", "hey"))


def test_escaped_transcript_separators_are_restored_without_decoding_other_escapes():
    from ghost.messaging import MESSAGE_ROW, normalize_transcript

    payload = (
        "<untrusted-mcp-output>\n"
        r"[2026-10-17 10:00:00] Alex: first\n[2026-10-17 09:00:00] You: literal\ntext\u202e"
        "\n</untrusted-mcp-output>"
    )
    result = normalize_transcript(payload)
    assert len(MESSAGE_ROW.findall(result)) == 2
    assert r"literal\ntext\u202e" in result
    assert "<untrusted-mcp-output>" in result


def test_old_connector_schema_is_rejected_before_calling_tool(monkeypatch):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from ghost.messaging import MessagingError

    session = SimpleNamespace(
        initialize=AsyncMock(),
        list_tools=AsyncMock(
            return_value=SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="tool_get_recent_messages",
                        inputSchema={"properties": {"hours": {}, "contact": {}, "chat_id": {}}},
                    )
                ]
            )
        ),
        call_tool=AsyncMock(),
    )

    @asynccontextmanager
    async def streams(*args, **kwargs):
        yield None, None

    @asynccontextmanager
    async def client(*args):
        yield session

    monkeypatch.setattr("ghost.messaging.stdio_client", streams)
    monkeypatch.setattr("ghost.messaging.ClientSession", client)
    with pytest.raises(MessagingError, match="incompatible"):
        asyncio.run(MacMessages(Settings(_env_file=None)).read("+14155550123"))
    session.call_tool.assert_not_called()


NOISY = (
    "<untrusted-mcp-output>\n"
    "[2026-10-17 10:05:00] You [iMessage] [tapback: loved]: Loved an image\n"
    "[2026-10-17 10:04:00] Sam [iMessage] [unread]: ￼ [attachments: #26129 image/heic (IMG_1.heic)]\n"
    "[2026-10-17 10:03:00] Sam [iMessage] [unread]: [attachment]\n"
    "[2026-10-17 10:02:00] Sam [iMessage] [unread]: look at this ￼ [attachments: #2 image/png (a.png)]\n"
    "[2026-10-17 10:01:00] You [iMessage]: that was so funny\\nseriously"
    "\\n(Showing 50 message(s) from offset 0; older messages may exist - call again with offset=50.)\n"
    "</untrusted-mcp-output>"
)


def test_read_keeps_only_text_messages():
    adapter = MacMessages(Settings(_env_file=None))

    async def call(*args):
        return NOISY

    adapter.call = call
    result = asyncio.run(adapter.read("+14155550123"))
    assert result == (
        "<untrusted-mcp-output>\n"
        "[2026-10-17 10:02:00] Sam [iMessage] [unread]: look at this\n"
        "[2026-10-17 10:01:00] You [iMessage]: that was so funny\\nseriously\n"
        "</untrusted-mcp-output>"
    )


def test_reactions_and_attachments_do_not_count_as_unread():
    adapter = MacMessages(Settings(_env_file=None))

    async def call(*args):
        return NOISY

    adapter.call = call
    [chat] = asyncio.run(adapter.unread(["+14155550123"]))
    assert chat.unread_count == 2
    assert chat.preview.endswith("look at this")

    async def only_reaction(*args):
        return "[2026-10-17 10:05:00] Sam [iMessage] [unread] [tapback: laughed]: Laughed at “ok”"

    adapter.call = only_reaction
    with pytest.raises(RuntimeError):
        asyncio.run(adapter.unread(["+14155550123"]))
