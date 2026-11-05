"""User-invoked, read-only terminal inspection. Never sends or calls a model."""

import argparse
import asyncio
import sys

from ghost.config import Settings
from ghost.messaging import MESSAGE_ROW, DemoMessenger, MacMessages, MessagingError


async def inspect_chat(settings, messenger, recipient, latest=False):
    permitted = list(messenger.history) if settings.mode == "demo" else settings.allowed_recipients
    if recipient not in permitted:
        raise MessagingError("Recipient is not in GHOST_ALLOWED_RECIPIENTS. Update .env first.")
    if latest:
        context = await messenger.read(recipient)
        rows = MESSAGE_ROW.findall(context)
        # MCP returns newest first; the synthetic demo history is oldest first.
        message = rows[0] if rows else context.splitlines()[-1]
        return "Latest message (any read status; may be outgoing):\n" + message, 0
    conversations = await messenger.unread([recipient])
    if conversations:
        return "Latest unread incoming message:\n" + conversations[0].preview, 0
    # Confirm that the exact chat is readable; an empty unread result alone isn't sufficient.
    context = await messenger.read(recipient)
    count = len(MESSAGE_ROW.findall(context)) or len(context.splitlines())
    return (
        f"No unread incoming messages reported for this chat.\n"
        f"History read succeeded ({count} messages in the fetched window).\n"
        "Unread means the MCP database's message-level read flag, not merely a chat badge.\n"
        "Use --latest to display the latest message regardless of its read status.",
        1,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipient", help="Exact allowlisted E.164 phone number or email")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Show latest message, including read/outgoing messages",
    )
    args = parser.parse_args()
    try:
        settings = Settings()
        messenger = DemoMessenger() if settings.mode == "demo" else MacMessages(settings)
        recipients = (
            list(messenger.history) if settings.mode == "demo" else settings.allowed_recipients
        )
        recipient = args.recipient
        if not recipient:
            if len(recipients) != 1:
                parser.error(
                    "Specify --recipient, or configure exactly one allowed recipient in .env."
                )
            recipient = recipients[0]
        output, code = asyncio.run(inspect_chat(settings, messenger, recipient, args.latest))
    except MessagingError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        # Configuration errors can contain private values; never dump tracebacks/tool output.
        print(
            "Inspection failed. Check .env, the MCP launcher, and macOS permissions.",
            file=sys.stderr,
        )
        return 2
    # Intentional terminal display requested by the user, never an application log or archive.
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
