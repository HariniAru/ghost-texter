"""Launch the pinned Messages MCP with deterministic exact-chat lookup.

Kept dependency-free so uv can execute this file in the upstream MCP environment.
All database access remains inside the MCP process through its read-only helper.
"""


def find_latest_chat(query, chat_id):
    chat_id = str(chat_id).strip()
    if not chat_id:
        return None
    variants = {chat_id}
    if chat_id.startswith("chat"):
        variants.update({f"iMessage;-;{chat_id}", f"iMessage;+;{chat_id}"})
    elif chat_id.startswith("iMessage;"):
        short_id = chat_id.rsplit(";", 1)[-1]
        if short_id.startswith("chat"):
            variants.add(short_id)
    values = tuple(sorted(variants))
    placeholders = ",".join("?" for _ in values)
    rows = query(
        f"""
        SELECT c.ROWID, c.display_name, c.chat_identifier, c.room_name, c.style
        FROM chat c
        WHERE c.chat_identifier IN ({placeholders}) OR c.room_name IN ({placeholders})
        ORDER BY (
          SELECT MAX(CAST(m.date AS INTEGER)) FROM chat_message_join j
          JOIN message m ON m.ROWID=j.message_id WHERE j.chat_id=c.ROWID
        ) DESC, c.ROWID DESC
        LIMIT 1
        """,
        values + values,
    )
    if not rows or "error" in rows[0]:
        return None
    return rows[0]


def main():
    from mac_messages_mcp import messages, server

    # Upstream LIMIT 1 has no ordering: duplicate iMessage/SMS threads can pick
    # years-old history. Preserve exact matching, but choose latest activity.
    messages._find_chat_by_identifier = lambda chat_id: find_latest_chat(
        messages.query_messages_db, chat_id
    )
    server.mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
