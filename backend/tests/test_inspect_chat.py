import asyncio

import pytest
from ghost.config import Settings
from ghost.inspect_chat import inspect_chat
from ghost.messaging import DemoMessenger, MessagingError


def test_prints_only_latest_unread_message_without_sending():
    messenger = DemoMessenger()
    messenger.unread_messages["alex@example.test"] = ["Alex: older unread", "Alex: latest unread"]
    output, code = asyncio.run(
        inspect_chat(Settings(_env_file=None), messenger, "alex@example.test")
    )
    assert code == 0
    assert "Alex: latest unread" in output and "older unread" not in output
    assert not messenger.sent


def test_empty_unread_confirms_history_without_printing_messages():
    messenger = DemoMessenger()
    messenger.unread_messages.clear()
    output, code = asyncio.run(
        inspect_chat(Settings(_env_file=None), messenger, "alex@example.test")
    )
    assert code == 1
    assert "No unread incoming" in output and "History read succeeded" in output
    assert "coffee" not in output
    assert not messenger.sent


def test_latest_opt_in_displays_latest_message():
    messenger = DemoMessenger()
    output, code = asyncio.run(
        inspect_chat(Settings(_env_file=None), messenger, "alex@example.test", latest=True)
    )
    assert code == 0 and output.endswith("Alex: pretty good! coffee tomorrow at 10?")
    assert not messenger.sent


def test_nonallowlisted_recipient_is_rejected_before_read():
    messenger = DemoMessenger()
    settings = Settings(mode="imessage", allowed_recipients=[], _env_file=None)
    with pytest.raises(MessagingError, match="not in GHOST_ALLOWED_RECIPIENTS"):
        asyncio.run(inspect_chat(settings, messenger, "alex@example.test"))
    assert not messenger.sent


def test_connector_failure_is_not_reported_as_empty_unread():
    messenger = DemoMessenger()

    async def fail(*args):
        raise MessagingError("Connector incompatible")

    messenger.unread = fail
    with pytest.raises(MessagingError, match="incompatible"):
        asyncio.run(inspect_chat(Settings(_env_file=None), messenger, "alex@example.test"))
