import sqlite3

from ghost.mcp_server import find_latest_chat


def test_duplicate_address_selects_latest_activity_not_first_or_highest_rowid():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE chat (display_name TEXT, chat_identifier TEXT, room_name TEXT, style INTEGER);
      CREATE TABLE message (date INTEGER);
      CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
      INSERT INTO chat VALUES ('old', '+14155550123', NULL, 45);
      INSERT INTO chat VALUES ('current', '+14155550123', NULL, 45);
      INSERT INTO chat VALUES ('empty', '+14155550123', NULL, 45);
      INSERT INTO chat VALUES ('other', '+14155550999', NULL, 45);
      INSERT INTO message VALUES (100), (900), (999);
      INSERT INTO chat_message_join VALUES (1,1), (2,2), (4,3);
    """)

    def query(sql, args):
        return [dict(row) for row in db.execute(sql, args)]

    assert find_latest_chat(query, "+14155550123")["display_name"] == "current"
    assert find_latest_chat(query, "+14155550000") is None
    assert find_latest_chat(query, "' OR 1=1 --") is None
    db.close()


def test_lookup_preserves_group_identifier_variants_and_handles_errors():
    calls = []

    def query(sql, args):
        calls.append(args)
        return [{"error": "database unavailable"}]

    assert find_latest_chat(query, "chat123") is None
    assert {"chat123", "iMessage;-;chat123", "iMessage;+;chat123"} <= set(calls[0])
    assert find_latest_chat(query, "") is None
    assert len(calls) == 1
