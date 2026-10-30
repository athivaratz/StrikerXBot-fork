"""Tie limits, history, and the provider into one reply.

Why one function: the cog should not know the order of those checks.
"""

import time
from datetime import datetime, timezone

import aiohttp

from bot.ai.history import (
    bind_store,
    current_store,
    load_context,
    lock_for,
    record_turn,
    turns_to_messages,
)
from bot.ai.persona import CHAT_RULES, DEFAULT_PERSONA
from bot.ai.provider import chat
from bot.ai.speakers import display_name, people_block
from bot.ai.rate_limit import RequestLimit, TokenBudget, gate
from bot.ai.reasoning import reasoning_field
from bot.config import (
    AI_DAILY_TOKEN_BUDGET,
    AI_MAX_TOKENS,
    AI_MODEL,
    AI_REASONING_EFFORT,
    AI_REQUESTS_PER_MINUTE,
    BOT_DB_PATH,
    OPENROUTER_API_KEY,
    OWNER_IDS,
)
from bot.storage import Store, Turn

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


def label_turn(speaker_name: str, user_id: int, text: str) -> str:
    """Prefix the speaker so people in one channel are not mixed together."""
    return f"{display_name(speaker_name)} (id {user_id}): {text}"


def _system_prompt(
    persona: str, turns: list[Turn], user_id: int, speaker_name: str
) -> str:
    """Rules sit under the persona so a custom voice cannot drop them."""
    if persona.endswith("\n"):
        head = persona
    else:
        head = f"{persona}\n"
    people = people_block(turns, user_id, speaker_name)
    return f"{head}\n{CHAT_RULES}\n\n{people}"


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
    turns = await load_context(channel_id)
    persona = await _persona(guild_id)
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": _system_prompt(persona, turns, user_id, speaker_name),
        }
    ]
    messages.extend(turns_to_messages(turns))
    user_line = label_turn(speaker_name, user_id, text)
    messages.append({"role": "user", "content": user_line})
    async with aiohttp.ClientSession() as session:
        reply = await chat(
            messages,
            AI_MODEL,
            session=session,
            api_key=OPENROUTER_API_KEY,
            max_tokens=AI_MAX_TOKENS,
            reasoning=reasoning_field(AI_REASONING_EFFORT),
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
