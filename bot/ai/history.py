"""Per-channel locks and stored turns.

The lock is held across the provider call so two replies in one channel
cannot save out of order. Idle locks are dropped past a cap so the map
cannot grow for every channel the process ever sees.
"""

import asyncio
import time
from collections.abc import Callable

from bot import config
from bot.storage import Store

MAX_TURNS = 10
_LOCK_CAP = 200
_PURGE_EVERY = 60 * 60
_DAY_SECONDS = 24 * 60 * 60

_store: Store | None = None
_locks: dict[int, asyncio.Lock] = {}
_registry = asyncio.Lock()
_last_purge: float | None = None
now: Callable[[], float] = time.time


def bind_store(store: Store) -> None:
    global _store, _last_purge
    _store = store
    _locks.clear()
    _last_purge = None


def current_store() -> Store:
    if _store is None:
        raise RuntimeError("No store is bound.")
    return _store


def clear_history() -> None:
    """Tests share one process, so they need a way to drop locks and turns."""
    global _last_purge
    _locks.clear()
    _last_purge = None
    if _store is None:
        return
    asyncio.run(_store.delete_all_turns())


def _trim_locks(keep: int) -> None:
    if len(_locks) <= _LOCK_CAP:
        return
    for channel_id, lock in list(_locks.items()):
        if channel_id == keep or lock.locked():
            continue
        del _locks[channel_id]
        if len(_locks) <= _LOCK_CAP:
            return


async def lock_for(channel_id: int) -> asyncio.Lock:
    async with _registry:
        lock = _locks.get(channel_id)
        if lock is None:
            lock = asyncio.Lock()
            _locks[channel_id] = lock
        _trim_locks(channel_id)
        return lock


async def purge_if_due() -> None:
    """Drop expired turns on write, at most once an hour."""
    global _last_purge
    current = now()
    async with _registry:
        if _last_purge is not None and current - _last_purge < _PURGE_EVERY:
            return
        _last_purge = current
    cutoff = current - config.AI_HISTORY_DAYS * _DAY_SECONDS
    await current_store().purge_older_than(cutoff)


async def load_context(channel_id: int) -> list[tuple[str, str]]:
    cutoff = now() - config.AI_HISTORY_DAYS * _DAY_SECONDS
    rows = await current_store().recent_turns(channel_id, MAX_TURNS, cutoff)
    pairs: list[tuple[str, str]] = []
    for row in rows:
        pairs.append(("user", row.user_text))
        pairs.append(("assistant", row.assistant_text))
    return pairs


async def record_turn(
    channel_id: int,
    guild_id: int | None,
    user_id: int,
    speaker: str,
    user_text: str,
    assistant_text: str,
) -> None:
    await purge_if_due()
    await current_store().add_turn(
        channel_id,
        guild_id,
        user_id,
        speaker,
        user_text,
        assistant_text,
        now(),
    )
