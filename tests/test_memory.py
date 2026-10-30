import asyncio

from bot.ai.memory_tools import (
    change_persona,
    delete_own_turns,
    format_view,
    reset_persona_and_history,
    strip_speaker_label,
    wipe_channel,
)
from bot.storage import Store, Turn


def test_clear_own_rows_and_wipe_channel(tmp_path):
    store = Store(tmp_path / "memory.db")

    async def run():
        await store.add_turn(1, 9, 7, "Ann", "Ann: a", "ra", 1)
        await store.add_turn(1, 9, 8, "Bee", "Bee: b", "rb", 2)
        await store.add_turn(2, 9, 7, "Ann", "Ann: c", "rc", 3)
        await store.add_turn(2, 9, 8, "Bee", "Bee: d", "rd", 4)
        removed = await delete_own_turns(store, 7, 1, "channel")
        ann_here = await store.count_user_turns(7, 1)
        ann_there = await store.count_user_turns(7, 2)
        bee_here = await store.count_user_turns(8, 1)
        everywhere = await delete_own_turns(store, 7, 1, "everywhere")
        ann_left = await store.count_user_turns(7, 2)
        wiped = await wipe_channel(store, 1)
        channel_one = await store.recent_turns(1, 10, -1.0)
        channel_two = await store.recent_turns(2, 10, -1.0)
        return (
            removed,
            ann_here,
            ann_there,
            bee_here,
            everywhere,
            ann_left,
            wiped,
            channel_one,
            channel_two,
        )

    (
        removed,
        ann_here,
        ann_there,
        bee_here,
        everywhere,
        ann_left,
        wiped,
        channel_one,
        channel_two,
    ) = asyncio.run(run())
    assert removed == 1
    assert ann_here == 0
    assert ann_there == 1
    assert bee_here == 1
    assert everywhere == 1
    assert ann_left == 0
    assert wiped == 1
    assert channel_one == []
    assert [turn.user_id for turn in channel_two] == [8]


def test_view_strips_exact_label_when_name_contains_colon():
    row = Turn(
        id=1,
        channel_id=1,
        guild_id=9,
        user_id=7,
        speaker="Ann: Bee",
        user_text="Ann: Bee: hi: there",
        assistant_text="ok",
        created_at=1.0,
    )
    shown = format_view(1, [row])
    assert shown.splitlines()[-1] == "hi: there"


def test_strip_speaker_label_handles_id_and_legacy_prefixes():
    assert strip_speaker_label("Ann", 4, "Ann (id 4): hi") == "hi"
    assert strip_speaker_label("Ann", 4, "Ann: hi") == "hi"
    assert strip_speaker_label("Ann: Bee", 7, "Ann: Bee: hi: there") == "hi: there"


def test_delete_guild_turns_leaves_other_guilds(tmp_path):
    store = Store(tmp_path / "guilds.db")

    async def run():
        await store.add_turn(1, 9, 7, "Ann", "Ann: a", "ra", 1)
        await store.add_turn(1, 9, 8, "Bee", "Bee: b", "rb", 2)
        await store.add_turn(2, 10, 7, "Ann", "Ann: c", "rc", 3)
        await store.add_turn(3, None, 7, "Ann", "Ann: dm", "rd", 4)
        removed = await store.delete_guild_turns(9)
        left_here = await store.recent_turns(1, 10, -1.0)
        left_other = await store.recent_turns(2, 10, -1.0)
        left_dm = await store.recent_turns(3, 10, -1.0)
        return removed, left_here, left_other, left_dm

    removed, left_here, left_other, left_dm = asyncio.run(run())
    assert removed == 2
    assert left_here == []
    assert [turn.guild_id for turn in left_other] == [10]
    assert left_dm[0].guild_id is None


def test_change_persona_clears_that_guild(tmp_path):
    store = Store(tmp_path / "persona.db")

    async def run():
        await store.add_turn(1, 9, 7, "Ann", "Ann: a", "ra", 1)
        await store.add_turn(2, 9, 8, "Bee", "Bee: b", "rb", 2)
        await store.add_turn(3, 10, 7, "Ann", "Ann: c", "rc", 3)
        cleared = await change_persona(store, 9, "New voice", 1, 5.0)
        persona = await store.get_persona(9)
        here = await store.recent_turns(1, 10, -1.0)
        also = await store.recent_turns(2, 10, -1.0)
        other = await store.recent_turns(3, 10, -1.0)
        return cleared, persona, here, also, other

    cleared, persona, here, also, other = asyncio.run(run())
    assert cleared == 2
    assert persona == "New voice"
    assert here == []
    assert also == []
    assert [turn.guild_id for turn in other] == [10]


def test_reset_without_custom_persona_keeps_turns(tmp_path):
    store = Store(tmp_path / "reset.db")

    async def run():
        await store.add_turn(1, 9, 7, "Ann", "Ann: a", "ra", 1)
        removed, cleared = await reset_persona_and_history(store, 9)
        left = await store.recent_turns(1, 10, -1.0)
        return removed, cleared, left

    removed, cleared, left = asyncio.run(run())
    assert removed is False
    assert cleared == 0
    assert len(left) == 1
