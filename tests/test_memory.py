import asyncio

from bot.ai.memory_tools import delete_own_turns, wipe_channel
from bot.storage import Store


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
