"""Tie limits, history, and the provider into one reply.

Why one function: the cog should not know the order of those checks.
"""

import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timezone

import aiohttp

from bot.ai.persona import DEFAULT_PERSONA
from bot.ai.provider import chat
from bot.ai.rate_limit import RequestLimit, TokenBudget, gate
from bot.config import (
    AI_DAILY_TOKEN_BUDGET,
    AI_MODEL,
    AI_REQUESTS_PER_MINUTE,
    OPENROUTER_API_KEY,
    OWNER_IDS,
)

MAX_TURNS = 10
MAX_CHANNELS = 200

_history: OrderedDict[int, list[tuple[str, str]]] = OrderedDict()
_locks: dict[int, asyncio.Lock] = {}
_registry = asyncio.Lock()

limiter = RequestLimit(AI_REQUESTS_PER_MINUTE, time.monotonic)
budget = TokenBudget(AI_DAILY_TOKEN_BUDGET, lambda: datetime.now(timezone.utc))


def clear_history() -> None:
    """Tests share one process, so they need a way to empty the map."""
    _history.clear()
    _locks.clear()


def label_turn(speaker_name: str, text: str) -> str:
    """Prefix the speaker so people in one channel are not mixed together."""
    cleaned = " ".join(speaker_name.split()) if speaker_name else ""
    name = cleaned or "Someone"
    return f"{name}: {text}"


def remember(channel_id: int, user_line: str, assistant_text: str) -> None:
    """Keep the last 10 turns, and drop the oldest channel past the cap."""
    turns = _history.get(channel_id)
    if turns is None:
        turns = []
        _history[channel_id] = turns
    turns.append(("user", user_line))
    turns.append(("assistant", assistant_text))
    overflow = len(turns) - (MAX_TURNS * 2)
    if overflow > 0:
        del turns[:overflow]
    _history.move_to_end(channel_id)
    while len(_history) > MAX_CHANNELS:
        old_id, _ = _history.popitem(last=False)
        _locks.pop(old_id, None)


async def _lock_for(channel_id: int) -> asyncio.Lock:
    async with _registry:
        lock = _locks.get(channel_id)
        if lock is None:
            lock = asyncio.Lock()
            _locks[channel_id] = lock
        return lock


async def run_chat(
    user_id: int, channel_id: int, speaker_name: str, text: str
) -> str:
    """Hold the channel lock for the whole call, including the HTTP wait."""
    lock = await _lock_for(channel_id)
    async with lock:
        return await _reply(user_id, channel_id, speaker_name, text)


async def _reply(
    user_id: int, channel_id: int, speaker_name: str, text: str
) -> str:
    blocked = gate(user_id, OWNER_IDS, limiter, budget)
    if blocked is not None:
        return blocked
    messages: list[dict[str, str]] = [
        {"role": "system", "content": DEFAULT_PERSONA}
    ]
    for role, content in _history.get(channel_id, []):
        messages.append({"role": role, "content": content})
    user_line = label_turn(speaker_name, text)
    messages.append({"role": "user", "content": user_line})
    async with aiohttp.ClientSession() as session:
        reply = await chat(
            messages,
            AI_MODEL,
            session=session,
            api_key=OPENROUTER_API_KEY,
        )
    remember(channel_id, user_line, reply.text)
    budget.add(user_id, reply.prompt_tokens + reply.completion_tokens)
    return reply.text
