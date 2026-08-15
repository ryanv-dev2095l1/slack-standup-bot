import sqlite3
from pathlib import Path


INIT_SQL = """
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standup_date TEXT NOT NULL,
    slack_uid TEXT NOT NULL,
    prompt_ts TEXT,
    response_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(standup_date, slack_uid)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standup_date TEXT UNIQUE NOT NULL,
    channel_id TEXT NOT NULL,
    message_ts TEXT NOT NULL,
    content_md TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(standup_date);
"""


class Storage:
    """Lightweight SQLite wrapper for daily standup entries."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        # FIXME: sqlite busy timeout needs tuning if collector runs concurrent Slack threads
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(INIT_SQL)

    def save_prompt(self, standup_date: str, slack_uid: str, prompt_ts: str):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO prompts (standup_date, slack_uid, prompt_ts, status)
                VALUES (?, ?, ?, 'pending')
                ON CONFLICT(standup_date, slack_uid) DO UPDATE SET
                    prompt_ts = excluded.prompt_ts,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (standup_date, slack_uid, prompt_ts),
            )

    def save_response(self, standup_date: str, slack_uid: str, text: str):
        status = "skipped" if text.strip().lower() in ("skip", "off", "vacation", "pto", "ooo") else "completed"
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE prompts
                SET response_text = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE standup_date = ? AND slack_uid = ?
                """,
                (text, status, standup_date, slack_uid),
            )

    def get_prompt(self, standup_date: str, slack_uid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM prompts WHERE standup_date = ? AND slack_uid = ?",
                (standup_date, slack_uid),
            ).fetchone()
            return dict(row) if row else None

    def get_responses_for_date(self, standup_date: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT slack_uid, response_text, status, prompt_ts FROM prompts WHERE standup_date = ?",
                (standup_date,),
            ).fetchall()
            return [dict(r) for r in rows]

    def save_digest(self, standup_date: str, channel_id: str, message_ts: str, content_md: str):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO digests (standup_date, channel_id, message_ts, content_md)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(standup_date) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    message_ts = excluded.message_ts,
                    content_md = excluded.content_md
                """,
                (standup_date, channel_id, message_ts, content_md),
            )

    def get_digest(self, standup_date: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM digests WHERE standup_date = ?",
                (standup_date,),
            ).fetchone()
            return dict(row) if row else None
