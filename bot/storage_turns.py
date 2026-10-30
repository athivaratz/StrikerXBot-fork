"""Read and delete chat turns.

The WHERE text below is fixed in this file. Values stay in placeholders.
"""

import sqlite3

from bot.storage_sql import Turn, turn_from_row

# Newest rows are chosen first, then returned oldest first for the model.
_NEWEST_FIRST = """
SELECT * FROM (
    SELECT * FROM turns
    WHERE {where}
    ORDER BY created_at DESC, id DESC
    LIMIT ?
) ORDER BY created_at ASC, id ASC
"""


def _select(
    conn: sqlite3.Connection,
    where: str,
    params: tuple[object, ...],
    limit: int,
) -> list[Turn]:
    rows = conn.execute(_NEWEST_FIRST.format(where=where), (*params, limit)).fetchall()
    return [turn_from_row(row) for row in rows]


def recent_turns(
    conn: sqlite3.Connection,
    channel_id: int,
    limit: int,
    newer_than: float,
) -> list[Turn]:
    return _select(
        conn,
        "channel_id = ? AND created_at > ?",
        (channel_id, newer_than),
        limit,
    )


def last_user_turns(
    conn: sqlite3.Connection,
    user_id: int,
    channel_id: int,
    limit: int,
) -> list[Turn]:
    return _select(
        conn,
        "user_id = ? AND channel_id = ?",
        (user_id, channel_id),
        limit,
    )


def purge_older_than(conn: sqlite3.Connection, cutoff: float) -> int:
    cursor = conn.execute("DELETE FROM turns WHERE created_at < ?", (cutoff,))
    return cursor.rowcount


def count_user_turns(conn: sqlite3.Connection, user_id: int, channel_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM turns WHERE user_id = ? AND channel_id = ?",
        (user_id, channel_id),
    ).fetchone()
    return int(row["n"])


def delete_user_turns(
    conn: sqlite3.Connection,
    user_id: int,
    channel_id: int | None,
) -> int:
    if channel_id is None:
        cursor = conn.execute("DELETE FROM turns WHERE user_id = ?", (user_id,))
    else:
        cursor = conn.execute(
            "DELETE FROM turns WHERE user_id = ? AND channel_id = ?",
            (user_id, channel_id),
        )
    return cursor.rowcount


def delete_channel_turns(conn: sqlite3.Connection, channel_id: int) -> int:
    cursor = conn.execute("DELETE FROM turns WHERE channel_id = ?", (channel_id,))
    return cursor.rowcount


def delete_guild_turns(conn: sqlite3.Connection, guild_id: int) -> int:
    cursor = conn.execute("DELETE FROM turns WHERE guild_id = ?", (guild_id,))
    return cursor.rowcount


def delete_all_turns(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("DELETE FROM turns")
    return cursor.rowcount
