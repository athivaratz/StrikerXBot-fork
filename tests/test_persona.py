import asyncio

import pytest

from bot.ai import chat as chat_mod
from bot.ai.history import current_store
from bot.ai.persona import DEFAULT_PERSONA, MAX_PERSONA_LENGTH, PersonaError, validate_persona
from bot.ai.provider import ChatReply
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
    ) -> ChatReply:
        seen.append(messages)
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

    assert seen[0][0] == {"role": "system", "content": "Custom voice"}
    assert seen[0][-1] == {"role": "user", "content": "Ann: hi"}
    assert seen[1][0]["content"] == DEFAULT_PERSONA
    assert seen[2][0]["content"] == DEFAULT_PERSONA
