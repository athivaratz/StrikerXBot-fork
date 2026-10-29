from bot.ai.chunker import split_for_discord

FENCE = "`" * 3


def test_short_text_stays_one_chunk():
    assert split_for_discord("hello") == ["hello"]


def test_splits_on_a_blank_line():
    text = ("a" * 40) + "\n\n" + ("b" * 40)
    assert split_for_discord(text, limit=50) == ["a" * 40, "b" * 40]


def test_fence_that_fits_stays_intact():
    prefix = ("a" * 30) + "\n"
    block = FENCE + "\n" + ("b" * 30) + "\n" + FENCE
    tail = "\n" + ("c" * 40)
    chunks = split_for_discord(prefix + block + tail, limit=50)
    assert block in chunks
    assert all(len(chunk) <= 50 for chunk in chunks)
