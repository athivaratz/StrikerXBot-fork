import asyncio

from bot.storage import Store


def test_store_round_trip(tmp_path):
    store = Store(tmp_path / "nested" / "bot.db")

    async def run():
        await store.add_turn(10, 20, 30, "Ann", "Ann: hi", "hello", 1.5)
        await store.add_turn(10, None, 30, "Ann", "Ann: dm", "yo", 2.5)
        turns = await store.recent_turns(10, 10, 0.0)
        await store.set_persona(20, "Be brief.", 30, 2.0)
        persona = await store.get_persona(20)
        replaced = await store.set_persona(20, "Be shorter.", 31, 3.0)
        updated = await store.get_persona(20)
        reset = await store.reset_persona(20)
        missing = await store.get_persona(20)
        again = await store.reset_persona(20)
        await store.add_tokens(30, "2026-10-30", 5)
        await store.add_tokens(30, "2026-10-30", 7)
        tokens = await store.get_tokens(30, "2026-10-30")
        empty = await store.get_tokens(30, "2026-10-31")
        return (
            turns,
            persona,
            replaced,
            updated,
            reset,
            missing,
            again,
            tokens,
            empty,
        )

    (
        turns,
        persona,
        replaced,
        updated,
        reset,
        missing,
        again,
        tokens,
        empty,
    ) = asyncio.run(run())
    assert [turn.user_text for turn in turns] == ["Ann: hi", "Ann: dm"]
    assert turns[0].assistant_text == "hello"
    assert turns[0].guild_id == 20
    assert turns[1].guild_id is None
    assert persona == "Be brief."
    assert replaced is None
    assert updated == "Be shorter."
    assert reset is True
    assert missing is None
    assert again is False
    assert tokens == 12
    assert empty == 0
