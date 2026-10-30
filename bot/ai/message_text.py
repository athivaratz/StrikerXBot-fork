"""Turn a Discord message into plain text the model can read.

Raw mention tokens are ids. The model needs the name beside the id.
"""

_SNIPPET = 200


def strip_bot_mention(text: str, bot_id: int) -> str:
    cleaned = text.replace(f"<@{bot_id}>", "")
    cleaned = cleaned.replace(f"<@!{bot_id}>", "")
    return cleaned.strip()


def name_mentions(text: str, people: list[tuple[int, str]]) -> str:
    named = text
    for user_id, name in people:
        label = f"@{name} (id {user_id})"
        named = named.replace(f"<@{user_id}>", label)
        named = named.replace(f"<@!{user_id}>", label)
    return named


def with_reply_context(
    text: str, author_name: str, author_id: int, replied_text: str
) -> str:
    snippet = replied_text
    if len(snippet) > _SNIPPET:
        snippet = snippet[:_SNIPPET] + "..."
    return f'Replying to {author_name} (id {author_id}): "{snippet}"\n{text}'
