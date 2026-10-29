from bot.ai import chat as chat_mod
from bot.ai.chat import MAX_CHANNELS, MAX_TURNS, clear_history, label_turn, remember


def test_label_turn_names_the_speaker():
    assert label_turn("Ann", "hi") == "Ann: hi"
    assert label_turn("Ann\nBee", "hi") == "Ann Bee: hi"
    assert label_turn("   ", "hi") == "Someone: hi"


def test_history_keeps_ten_turns():
    clear_history()
    for index in range(MAX_TURNS + 2):
        remember(1, f"Ann: {index}", f"reply {index}")
    turns = chat_mod._history[1]
    assert len(turns) == MAX_TURNS * 2
    assert turns[0] == ("user", "Ann: 2")
    clear_history()


def test_history_drops_the_oldest_channel():
    clear_history()
    for channel_id in range(MAX_CHANNELS + 1):
        remember(channel_id, "Ann: hi", "yo")
    assert 0 not in chat_mod._history
    assert MAX_CHANNELS in chat_mod._history
    assert len(chat_mod._history) == MAX_CHANNELS
    clear_history()
