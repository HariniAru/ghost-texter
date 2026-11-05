import json
import sqlite3


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
        """)
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

    def event(self, draft_id, action, payload):
        self.db.execute(
            "INSERT INTO events(draft_id, action, payload) VALUES (?,?,?)",
            (draft_id, action, json.dumps(payload)),
        )

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
