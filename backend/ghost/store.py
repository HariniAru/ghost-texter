import json
import sqlite3
from datetime import datetime, timezone


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS drafts (
          id TEXT PRIMARY KEY, recipient TEXT NOT NULL, context TEXT NOT NULL,
          fingerprint TEXT NOT NULL, text TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
          status TEXT NOT NULL DEFAULT 'pending', receipt TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, draft_id TEXT, action TEXT, payload TEXT,
          created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT);
        CREATE TABLE IF NOT EXISTS contacts (
          address TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP,
          name TEXT NOT NULL DEFAULT '');
        """)
        # Databases created before contacts had names keep their rows, with a blank name.
        if "name" not in {r["name"] for r in self.db.execute("PRAGMA table_info(contacts)")}:
            self.db.execute("ALTER TABLE contacts ADD COLUMN name TEXT NOT NULL DEFAULT ''")
        # A crash during dispatch has an unknown outcome. Never retry automatically.
        self.db.execute("UPDATE drafts SET status='uncertain' WHERE status='sending'")
        self.db.commit()

    def one(self, draft_id):
        row = self.db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        return dict(row) if row else None

    def all(self):
        return [
            dict(r)
            for r in self.db.execute("SELECT * FROM drafts ORDER BY created DESC, rowid DESC")
        ]

    def saved(self):
        # What the user sees. Sent rows are kept as dispatch evidence, and all() still sees
        # them so automatic preparation can skip a snapshot that was already answered.
        return [row for row in self.all() if row["status"] not in {"sent", "discarded"}]

    def event(self, draft_id, action, payload):
        self.db.execute(
            "INSERT INTO events(draft_id, action, payload) VALUES (?,?,?)",
            (draft_id, action, json.dumps(payload)),
        )

    def approved_at(self, draft_id):
        # In local time, to compare with the connector's message timestamps.
        row = self.db.execute(
            "SELECT created FROM events WHERE draft_id=? AND action='approved' "
            "ORDER BY id DESC LIMIT 1",
            (draft_id,),
        ).fetchone()
        if not row:
            return None
        created = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return created.astimezone().replace(tzinfo=None)

    def contacts(self):
        return [r[0] for r in self.db.execute("SELECT address FROM contacts ORDER BY rowid")]

    def contact_names(self):
        return {r["address"]: r["name"] for r in self.db.execute("SELECT * FROM contacts")}

    def add_contact(self, address, name):
        self.db.execute(
            "INSERT INTO contacts(address, name) VALUES (?,?) "
            "ON CONFLICT(address) DO UPDATE SET name=excluded.name",
            (address, name),
        )
        self.db.commit()

    def remove_contact(self, address):
        self.db.execute("DELETE FROM contacts WHERE address=?", (address,))
        self.db.commit()

    def profile(self):
        row = self.db.execute("SELECT data FROM profile WHERE id=1").fetchone()
        return (
            json.loads(row[0])
            if row
            else {
                "style": "Casual, warm, concise. Use my examples for punctuation and capitalization.",
                "examples": [],
            }
        )
