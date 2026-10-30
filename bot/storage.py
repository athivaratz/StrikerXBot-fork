"""Async access to the local SQLite file.

Each call opens its own connection in a worker thread. sqlite3 connections
are tied to the thread that created them, so they are closed before return.
"""

import asyncio
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from bot import storage_meta as meta
from bot import storage_turns as turns
from bot.storage_sql import Turn, ensure_schema, insert_turn, open_connection

T = TypeVar("T")

__all__ = ["Store", "Turn"]


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._ready = False
        # _call runs in worker threads, so the first setup must be serialized.
        self._lock = threading.Lock()

    def _prepare(self, conn: sqlite3.Connection) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            ensure_schema(conn)
            self._ready = True

    def _call(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        conn = open_connection(self.path)
        try:
            self._prepare(conn)
            result = fn(conn)
            conn.commit()
            return result
        finally:
            conn.close()

    async def _run(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        return await asyncio.to_thread(self._call, fn)

    async def add_turn(
        self,
        channel_id: int,
        guild_id: int | None,
        user_id: int,
        speaker: str,
        user_text: str,
        assistant_text: str,
        created_at: float,
    ) -> None:
        await self._run(
            lambda conn: insert_turn(
                conn,
                channel_id,
                guild_id,
                user_id,
                speaker,
                user_text,
                assistant_text,
                created_at,
            )
        )

    async def recent_turns(
        self, channel_id: int, limit: int, newer_than: float
    ) -> list[Turn]:
        return await self._run(
            lambda conn: turns.recent_turns(conn, channel_id, limit, newer_than)
        )

    async def purge_older_than(self, cutoff: float) -> int:
        return await self._run(lambda conn: turns.purge_older_than(conn, cutoff))

    async def count_user_turns(self, user_id: int, channel_id: int) -> int:
        return await self._run(
            lambda conn: turns.count_user_turns(conn, user_id, channel_id)
        )

    async def last_user_turns(
        self, user_id: int, channel_id: int, limit: int
    ) -> list[Turn]:
        return await self._run(
            lambda conn: turns.last_user_turns(conn, user_id, channel_id, limit)
        )

    async def delete_user_turns(self, user_id: int, channel_id: int | None) -> int:
        return await self._run(
            lambda conn: turns.delete_user_turns(conn, user_id, channel_id)
        )

    async def delete_channel_turns(self, channel_id: int) -> int:
        return await self._run(lambda conn: turns.delete_channel_turns(conn, channel_id))

    async def delete_all_turns(self) -> int:
        """Used by tests to empty the current file without picking a cutoff."""
        return await self._run(turns.delete_all_turns)

    async def get_tokens(self, user_id: int, day: str) -> int:
        return await self._run(lambda conn: meta.get_tokens(conn, user_id, day))

    async def add_tokens(self, user_id: int, day: str, tokens: int) -> None:
        await self._run(lambda conn: meta.add_tokens(conn, user_id, day, tokens))

    async def get_persona(self, guild_id: int) -> str | None:
        return await self._run(lambda conn: meta.get_persona(conn, guild_id))

    async def set_persona(
        self, guild_id: int, text: str, updated_by: int, when: float
    ) -> None:
        await self._run(
            lambda conn: meta.set_persona(conn, guild_id, text, updated_by, when)
        )

    async def reset_persona(self, guild_id: int) -> bool:
        return await self._run(lambda conn: meta.reset_persona(conn, guild_id))
