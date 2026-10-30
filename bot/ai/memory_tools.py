"""Text and delete helpers for the memory commands.

The cog stays thin, and tests can call these without Discord.
"""

from bot.ai.persona import DEFAULT_PERSONA
from bot.ai.speakers import display_name
from bot.storage import Store, Turn

_PREVIEW = 300
_SNIPPET = 100


def strip_speaker_label(speaker: str, user_id: int, user_text: str) -> str:
    """The label may hold a saved /introduce name instead of the display name.

    Only the id part is fixed, so look for that. A display name can contain
    ": ", which is why the old format still needs the exact prefix.
    """
    marker = f" (id {user_id}): "
    position = user_text.find(marker)
    if position != -1:
        return user_text[position + len(marker):]
    legacy = f"{display_name(speaker)}: "
    if user_text.startswith(legacy):
        return user_text[len(legacy):]
    return user_text


def shorten(text: str, limit: int = _SNIPPET) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def format_view(count: int, rows: list[Turn]) -> str:
    if count == 0:
        return "You have no stored messages in this channel."
    lines = [f"You have {count} stored messages in this channel."]
    for row in rows:
        lines.append(
            shorten(strip_speaker_label(row.speaker, row.user_id, row.user_text))
        )
    return "\n".join(lines)


def format_deleted(count: int, scope: str) -> str:
    if scope == "everywhere":
        return f"Deleted {count} of your stored messages."
    return f"Deleted {count} of your stored messages in this channel."


def format_wiped(count: int) -> str:
    return f"Deleted {count} stored messages in this channel."


def format_persona_set(count: int) -> str:
    return (
        "Persona updated. Cleared "
        f"{count} stored messages in this server so replies follow the new persona."
    )


def format_persona_reset(count: int) -> str:
    return (
        "Persona reset to the default. Cleared "
        f"{count} stored messages in this server."
    )


def format_persona_show(custom: str | None) -> str:
    if custom is None:
        kind = "This server uses the default persona."
        body = DEFAULT_PERSONA
    else:
        kind = "This server uses a custom persona."
        body = custom
    return f"{kind}\n{shorten(body, _PREVIEW)}"


async def delete_own_turns(
    store: Store, user_id: int, channel_id: int, scope: str
) -> int:
    if scope == "everywhere":
        return await store.delete_user_turns(user_id, None)
    return await store.delete_user_turns(user_id, channel_id)


async def wipe_channel(store: Store, channel_id: int) -> int:
    return await store.delete_channel_turns(channel_id)


async def change_persona(
    store: Store, guild_id: int, text: str, updated_by: int, when: float
) -> int:
    """Old replies are in the old voice, and the model copies them."""
    await store.set_persona(guild_id, text, updated_by, when)
    return await store.delete_guild_turns(guild_id)


async def reset_persona_and_history(store: Store, guild_id: int) -> tuple[bool, int]:
    """A server already on the default has nothing to clear."""
    removed = await store.reset_persona(guild_id)
    if not removed:
        return False, 0
    count = await store.delete_guild_turns(guild_id)
    return True, count
