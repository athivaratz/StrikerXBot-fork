"""Open a SQLite file and insert one chat turn.

Connections are opened by the caller and are not shared across threads.
WAL and the table script are separate so a Store can run them once.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

# WAL lets a short read run while another call is committing.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    guild_id INTEGER,
    user_id INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    user_text TEXT NOT NULL,
    assistant_text TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS turns_channel_created
    ON turns (channel_id, created_at);
CREATE INDEX IF NOT EXISTS turns_user ON turns (user_id);
CREATE TABLE IF NOT EXISTS token_usage (
    user_id INTEGER,
    day TEXT,
    tokens INTEGER NOT NULL,
    PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS guild_persona (
    guild_id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    updated_by INTEGER NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS user_profiles (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);
"""


@dataclass(frozen=True)
class Turn:
    id: int
    channel_id: int
    guild_id: int | None
    user_id: int
    speaker: str
    user_text: str
    assistant_text: str
    created_at: float


def open_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)


def turn_from_row(row: sqlite3.Row) -> Turn:
    guild_id = row["guild_id"]
    return Turn(
        id=row["id"],
        channel_id=row["channel_id"],
        guild_id=None if guild_id is None else guild_id,
        user_id=row["user_id"],
        speaker=row["speaker"],
        user_text=row["user_text"],
        assistant_text=row["assistant_text"],
        created_at=row["created_at"],
    )


def insert_turn(
    conn: sqlite3.Connection,
    channel_id: int,
    guild_id: int | None,
    user_id: int,
    speaker: str,
    user_text: str,
    assistant_text: str,
    created_at: float,
) -> None:
    conn.execute(
        """
        INSERT INTO turns (
            channel_id, guild_id, user_id, speaker,
            user_text, assistant_text, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (channel_id, guild_id, user_id, speaker, user_text, assistant_text, created_at),
    )
