from bot.ai.message_text import name_mentions, strip_bot_mention, with_reply_context


def test_strip_bot_mention_both_forms():
    assert strip_bot_mention("<@5> hi", 5) == "hi"
    assert strip_bot_mention("<@!5> hi", 5) == "hi"
    assert strip_bot_mention(" <@5> <@!5> ", 5) == ""


def test_name_mentions_replaces_both_forms():
    text = strip_bot_mention("<@1> ping <@9> and <@!8>", 1)
    named = name_mentions(text, [(9, "Ann"), (8, "Bee")])
    assert named == "ping @Ann (id 9) and @Bee (id 8)"


def test_reply_snippet_cuts_at_200_characters():
    long = "a" * 201
    cut = with_reply_context("hi", "Ann", 4, long)
    assert cut == 'Replying to Ann (id 4): "' + ("a" * 200) + '..."\nhi'
    exact = with_reply_context("hi", "Ann", 4, "b" * 200)
    assert exact == 'Replying to Ann (id 4): "' + ("b" * 200) + '"\nhi'
