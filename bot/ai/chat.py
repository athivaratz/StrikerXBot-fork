"""Tie limits, history, and the provider into one reply.

Why one function: the cog should not know the order of those checks.
"""

import time
from datetime import datetime, timezone

import aiohttp

from bot.ai.history import (
    bind_store,
    clear_history as clear_history,
    current_store,
    load_context,
    lock_for,
    record_turn,
)
from bot.ai.persona import DEFAULT_PERSONA
from bot.ai.provider import chat
from bot.ai.rate_limit import RequestLimit, TokenBudget, gate
from bot.config import (
    AI_DAILY_TOKEN_BUDGET,
    AI_MODEL,
    AI_REQUESTS_PER_MINUTE,
    BOT_DB_PATH,
    OPENROUTER_API_KEY,
    OWNER_IDS,
)
from bot.storage import Store

_db = Store(BOT_DB_PATH)
bind_store(_db)
limiter = RequestLimit(AI_REQUESTS_PER_MINUTE, time.monotonic)
budget = TokenBudget(
    AI_DAILY_TOKEN_BUDGET,
    lambda: datetime.now(timezone.utc),
    _db,
)


def use_store(store: Store) -> None:
    """Point history and the token budget at one database. Tests use this."""
    bind_store(store)
    budget.bind(store)


def label_turn(speaker_name: str, text: str) -> str:
    """Prefix the speaker so people in one channel are not mixed together."""
    cleaned = " ".join(speaker_name.split()) if speaker_name else ""
    name = cleaned or "Someone"
    return f"{name}: {text}"


async def _persona(guild_id: int | None) -> str:
    if guild_id is None:
        return DEFAULT_PERSONA
    custom = await current_store().get_persona(guild_id)
    if custom is None:
        return DEFAULT_PERSONA
    return custom


async def run_chat(
    user_id: int,
    channel_id: int,
    speaker_name: str,
    text: str,
    *,
    guild_id: int | None = None,
) -> str:
    """Hold the channel lock for the whole call, including the HTTP wait."""
    lock = await lock_for(channel_id)
    async with lock:
        return await _reply(user_id, channel_id, speaker_name, text, guild_id)


async def _reply(
    user_id: int,
    channel_id: int,
    speaker_name: str,
    text: str,
    guild_id: int | None,
) -> str:
    blocked = await gate(user_id, OWNER_IDS, limiter, budget)
    if blocked is not None:
        return blocked
    messages: list[dict[str, str]] = [
        {"role": "system", "content": await _persona(guild_id)}
    ]
    for role, content in await load_context(channel_id):
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
    await record_turn(
        channel_id,
        guild_id,
        user_id,
        speaker_name,
        user_line,
        reply.text,
    )
    await budget.add(user_id, reply.prompt_tokens + reply.completion_tokens)
    return reply.text
