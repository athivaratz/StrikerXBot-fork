"""Token totals and guild persona rows."""

import sqlite3


def get_tokens(conn: sqlite3.Connection, user_id: int, day: str) -> int:
    row = conn.execute(
        "SELECT tokens FROM token_usage WHERE user_id = ? AND day = ?",
        (user_id, day),
    ).fetchone()
    if row is None:
        return 0
    return int(row["tokens"])


def add_tokens(conn: sqlite3.Connection, user_id: int, day: str, tokens: int) -> None:
    conn.execute(
        """
        INSERT INTO token_usage (user_id, day, tokens) VALUES (?, ?, ?)
        ON CONFLICT (user_id, day) DO UPDATE SET tokens = tokens + excluded.tokens
        """,
        (user_id, day, tokens),
    )


def get_persona(conn: sqlite3.Connection, guild_id: int) -> str | None:
    row = conn.execute(
        "SELECT text FROM guild_persona WHERE guild_id = ?",
        (guild_id,),
    ).fetchone()
    if row is None:
        return None
    return str(row["text"])


def set_persona(
    conn: sqlite3.Connection,
    guild_id: int,
    text: str,
    updated_by: int,
    updated_at: float,
) -> None:
    conn.execute(
        """
        INSERT INTO guild_persona (guild_id, text, updated_by, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (guild_id) DO UPDATE SET
            text = excluded.text,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
        """,
        (guild_id, text, updated_by, updated_at),
    )


def reset_persona(conn: sqlite3.Connection, guild_id: int) -> bool:
    cursor = conn.execute("DELETE FROM guild_persona WHERE guild_id = ?", (guild_id,))
    return cursor.rowcount > 0
