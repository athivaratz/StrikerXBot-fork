import asyncio

from bot import config
from bot.ai import history as history_mod
from bot.ai.chat import label_turn, use_store
from bot.ai.history import MAX_TURNS, load_context, record_turn
from bot.storage import Store


def test_label_turn_names_the_speaker():
    assert label_turn("Ann", "hi") == "Ann: hi"
    assert label_turn("Ann\nBee", "hi") == "Ann Bee: hi"
    assert label_turn("   ", "hi") == "Someone: hi"


def test_context_is_the_last_ten_oldest_first(tmp_path):
    use_store(Store(tmp_path / "history.db"))

    async def seed() -> list[tuple[str, str]]:
        for index in range(MAX_TURNS + 2):
            await record_turn(1, None, 4, "Ann", f"Ann: {index}", f"reply {index}")
        return await load_context(1)

    pairs = asyncio.run(seed())
    assert len(pairs) == MAX_TURNS * 2
    assert pairs[0] == ("user", "Ann: 2")
    assert pairs[-1] == ("assistant", "reply 11")


def test_context_respects_history_days_and_purge(tmp_path, monkeypatch):
    use_store(Store(tmp_path / "history.db"))
    clock = [1_700_000_000.0]
    monkeypatch.setattr(history_mod, "now", lambda: clock[0])
    monkeypatch.setattr(config, "AI_HISTORY_DAYS", 2)
    store = history_mod.current_store()

    async def seed() -> list[tuple[str, str]]:
        await store.add_turn(
            3, None, 1, "Ann", "Ann: old", "old reply", clock[0] - 3 * 86400
        )
        await store.add_turn(3, None, 1, "Ann", "Ann: new", "new reply", clock[0])
        return await load_context(3)

    assert asyncio.run(seed()) == [("user", "Ann: new"), ("assistant", "new reply")]

    async def purge_once() -> list[str]:
        await history_mod.purge_if_due()
        rows = await store.recent_turns(3, 10, -1.0)
        return [row.user_text for row in rows]

    assert asyncio.run(purge_once()) == ["Ann: new"]

    async def skip_inside_the_hour() -> tuple[list[str], list[str]]:
        await store.add_turn(
            3, None, 1, "Ann", "Ann: aged", "x", clock[0] - 3 * 86400
        )
        await history_mod.purge_if_due()
        during = await store.recent_turns(3, 10, -1.0)
        clock[0] += 3601
        await history_mod.purge_if_due()
        after = await store.recent_turns(3, 10, -1.0)
        return (
            [row.user_text for row in during],
            [row.user_text for row in after],
        )

    during, after = asyncio.run(skip_inside_the_hour())
    assert during == ["Ann: aged", "Ann: new"]
    assert after == ["Ann: new"]
