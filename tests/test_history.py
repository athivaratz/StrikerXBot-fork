import asyncio

from bot import config
from bot.ai import history as history_mod
from bot.ai.chat import label_turn, use_store
from bot.ai.history import MAX_TURNS, load_context, record_turn, turns_to_messages
from bot.ai.speakers import people_block
from bot.storage import Store, Turn


def test_label_turn_names_the_speaker():
    assert label_turn("Ann", 4, "hi") == "Ann (id 4): hi"
    assert label_turn("Ann\nBee", 4, "hi") == "Ann Bee (id 4): hi"
    assert label_turn("   ", 4, "hi") == "Someone (id 4): hi"


def test_context_is_the_last_ten_oldest_first(tmp_path):
    use_store(Store(tmp_path / "history.db"))

    async def seed() -> list[Turn]:
        for index in range(MAX_TURNS + 2):
            await record_turn(1, None, 4, "Ann", f"Ann: {index}", f"reply {index}")
        return await load_context(1)

    rows = asyncio.run(seed())
    assert len(rows) == MAX_TURNS
    assert rows[0].user_text == "Ann: 2"
    assert rows[-1].assistant_text == "reply 11"
    messages = turns_to_messages(rows[:1])
    assert messages == [
        {"role": "user", "content": "Ann: 2"},
        {"role": "assistant", "content": "reply 2"},
    ]


def test_context_respects_history_days_and_purge(tmp_path, monkeypatch):
    use_store(Store(tmp_path / "history.db"))
    clock = [1_700_000_000.0]
    monkeypatch.setattr(history_mod, "now", lambda: clock[0])
    monkeypatch.setattr(config, "AI_HISTORY_DAYS", 2)
    store = history_mod.current_store()

    async def seed() -> list[Turn]:
        await store.add_turn(
            3, None, 1, "Ann", "Ann: old", "old reply", clock[0] - 3 * 86400
        )
        await store.add_turn(3, None, 1, "Ann", "Ann: new", "new reply", clock[0])
        return await load_context(3)

    rows = asyncio.run(seed())
    assert [(row.user_text, row.assistant_text) for row in rows] == [
        ("Ann: new", "new reply")
    ]

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


def test_people_block_keeps_the_current_name():
    older = Turn(1, 1, 9, 4, "Ann", "Ann: hi", "ok", 1.0)
    renamed = Turn(2, 1, 9, 4, "Annie", "Annie: hi", "ok", 2.0)
    other = Turn(3, 1, 9, 8, "Bee", "Bee: yo", "ok", 3.0)
    block = people_block([older, renamed, other], 4, "Ann")
    assert "- id 4: Ann" in block.splitlines()
    assert "Annie" not in block
    assert "- id 8: Bee" in block
