import asyncio

from bot.storage import Store
from bot.storage_profiles import get_aliases


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


class _NoQuery:
    def execute(self, sql: str, *_args: object) -> None:
        raise AssertionError(sql)


def test_aliases_are_stored_per_guild(tmp_path):
    store = Store(tmp_path / "aliases.db")

    async def run():
        missing = await store.get_alias(1, 4)
        await store.set_alias(1, 4, "Pim", 1.0)
        saved = await store.get_alias(1, 4)
        await store.set_alias(1, 4, "Pimmy", 2.0)
        replaced = await store.get_alias(1, 4)
        await store.set_alias(1, 8, "Bee", 3.0)
        await store.set_alias(2, 4, "Ann", 4.0)
        mixed = await store.get_aliases(1, [4, 8, 9])
        other = await store.get_alias(2, 4)
        empty = await store.get_aliases(1, [])
        cleared = await store.clear_alias(1, 4)
        gone = await store.get_alias(1, 4)
        again = await store.clear_alias(1, 4)
        return (
            missing,
            saved,
            replaced,
            mixed,
            other,
            empty,
            cleared,
            gone,
            again,
        )

    missing, saved, replaced, mixed, other, empty, cleared, gone, again = asyncio.run(
        run()
    )
    assert missing is None
    assert saved == "Pim"
    assert replaced == "Pimmy"
    assert mixed == {4: "Pimmy", 8: "Bee"}
    assert other == "Ann"
    assert empty == {}
    assert cleared is True
    assert gone is None
    assert again is False
    assert get_aliases(_NoQuery(), 1, []) == {}  # type: ignore[arg-type]
