"""Names a member picks for one server.

Display names stay on the turn rows. This table is only the chosen name,
so a rename on Discord does not wipe it.
"""

import sqlite3


def get_alias(conn: sqlite3.Connection, guild_id: int, user_id: int) -> str | None:
    row = conn.execute(
        "SELECT alias FROM user_profiles WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return str(row["alias"])


def get_aliases(
    conn: sqlite3.Connection, guild_id: int, user_ids: list[int]
) -> dict[int, str]:
    # An empty IN () is invalid SQL, so skip the query.
    if len(user_ids) == 0:
        return {}
    # The id list changes size, so the placeholder list has to match it.
    marks = ", ".join(["?"] * len(user_ids))
    sql = (
        "SELECT user_id, alias FROM user_profiles "
        "WHERE guild_id = ? AND user_id IN (" + marks + ")"
    )
    rows = conn.execute(sql, (guild_id, *user_ids)).fetchall()
    return {int(row["user_id"]): str(row["alias"]) for row in rows}


def set_alias(
    conn: sqlite3.Connection,
    guild_id: int,
    user_id: int,
    alias: str,
    updated_at: float,
) -> None:
    conn.execute(
        """
        INSERT INTO user_profiles (guild_id, user_id, alias, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (guild_id, user_id) DO UPDATE SET
            alias = excluded.alias,
            updated_at = excluded.updated_at
        """,
        (guild_id, user_id, alias, updated_at),
    )


def clear_alias(conn: sqlite3.Connection, guild_id: int, user_id: int) -> bool:
    cursor = conn.execute(
        "DELETE FROM user_profiles WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    return cursor.rowcount > 0
