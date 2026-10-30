import asyncio

import pytest

from bot.ai import chat as chat_mod
from bot.ai.history import current_store
from bot.ai.persona import (
    CHAT_RULES,
    DEFAULT_PERSONA,
    MAX_PERSONA_LENGTH,
    PersonaError,
    validate_persona,
)
from bot.ai.provider import ChatReply
from bot.ai.reasoning import reasoning_field
from bot.config import AI_MAX_TOKENS, AI_REASONING_EFFORT
from bot.storage import Store


class _Session:
    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


def test_persona_length_cap():
    with pytest.raises(PersonaError):
        validate_persona("")
    with pytest.raises(PersonaError):
        validate_persona("   ")
    assert validate_persona("a" * MAX_PERSONA_LENGTH) == "a" * MAX_PERSONA_LENGTH
    with pytest.raises(PersonaError):
        validate_persona("a" * (MAX_PERSONA_LENGTH + 1))


def test_run_chat_picks_the_system_prompt(tmp_path, monkeypatch):
    store = Store(tmp_path / "chat.db")
    previous = current_store()
    chat_mod.use_store(store)
    seen: list[list[dict[str, str]]] = []

    async def fake_chat(
        messages: list[dict[str, str]],
        model: str,
        *,
        session: object,
        api_key: str,
        max_tokens: int,
        reasoning: dict[str, bool | str],
    ) -> ChatReply:
        seen.append(messages)
        assert max_tokens == AI_MAX_TOKENS
        assert reasoning == reasoning_field(AI_REASONING_EFFORT)
        return ChatReply("pong", 2, 3)

    monkeypatch.setattr(chat_mod, "chat", fake_chat)
    monkeypatch.setattr(chat_mod.aiohttp, "ClientSession", _Session)

    async def run() -> None:
        await store.set_persona(9, "Custom voice", 1, 1.0)
        assert await chat_mod.run_chat(4, 8, "Ann", "hi", guild_id=9) == "pong"
        assert await chat_mod.run_chat(4, 10, "Ann", "hi", guild_id=8) == "pong"
        assert await chat_mod.run_chat(5, 11, "Ann", "hi", guild_id=None) == "pong"
        rows = await store.recent_turns(8, 10, -1.0)
        assert rows[0].guild_id == 9
        assert rows[0].assistant_text == "pong"

    try:
        asyncio.run(run())
    finally:
        chat_mod.use_store(previous)

    custom = seen[0][0]["content"]
    assert custom.startswith("Custom voice")
    assert CHAT_RULES in custom
    assert "id 4: Ann" in custom
    assert custom.index(CHAT_RULES) < custom.index("id 4: Ann")
    assert seen[0][-1] == {"role": "user", "content": "Ann (id 4): hi"}
    assert seen[1][0]["content"].startswith(DEFAULT_PERSONA)
    assert "id 4: Ann" in seen[1][0]["content"]
    assert seen[2][0]["content"].startswith(DEFAULT_PERSONA)
    assert "id 5: Ann" in seen[2][0]["content"]
    assert "Call people by the name shown in the people list." in CHAT_RULES


def test_run_chat_uses_a_saved_name_in_a_guild(tmp_path, monkeypatch):
    store = Store(tmp_path / "alias-chat.db")
    previous = current_store()
    chat_mod.use_store(store)
    seen: list[list[dict[str, str]]] = []
    looked_up: list[int] = []
    original = Store.get_aliases

    async def spy(
        self: Store, guild_id: int, user_ids: list[int]
    ) -> dict[int, str]:
        looked_up.append(guild_id)
        return await original(self, guild_id, user_ids)

    async def fake_chat(
        messages: list[dict[str, str]],
        model: str,
        *,
        session: object,
        api_key: str,
        max_tokens: int,
        reasoning: dict[str, bool | str],
    ) -> ChatReply:
        seen.append(messages)
        return ChatReply("pong", 1, 1)

    monkeypatch.setattr(Store, "get_aliases", spy)
    monkeypatch.setattr(chat_mod, "chat", fake_chat)
    monkeypatch.setattr(chat_mod.aiohttp, "ClientSession", _Session)

    async def run() -> None:
        await store.set_alias(9, 4, "Pim", 1.0)
        assert await chat_mod.run_chat(4, 8, "Ann", "hi", guild_id=9) == "pong"
        assert await chat_mod.run_chat(4, 10, "Ann", "hi", guild_id=None) == "pong"
        rows = await store.recent_turns(8, 10, -1.0)
        assert rows[0].user_text == "Pim (id 4): hi"
        assert rows[0].speaker == "Ann"

    try:
        asyncio.run(run())
    finally:
        chat_mod.use_store(previous)

    assert seen[0][-1] == {"role": "user", "content": "Pim (id 4): hi"}
    assert "Pim (display name Ann)" in seen[0][0]["content"]
    assert seen[1][-1] == {"role": "user", "content": "Ann (id 4): hi"}
    assert "Pim" not in seen[1][0]["content"]
    assert looked_up == [9]
