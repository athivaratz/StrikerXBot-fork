"""Text and delete helpers for the memory commands.

The cog stays thin, and tests can call these without Discord.
"""

import discord
from discord import app_commands

from bot.ai.chat import label_turn
from bot.ai.persona import DEFAULT_PERSONA
from bot.storage import Store, Turn
from bot.utils.discord_send import send_ephemeral

_PREVIEW = 300
_SNIPPET = 100


def strip_speaker_label(speaker: str, user_text: str) -> str:
    """A display name can contain ": ", so the prefix has to be exact."""
    prefix = label_turn(speaker, "")
    if user_text.startswith(prefix):
        return user_text[len(prefix):]
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
        lines.append(shorten(strip_speaker_label(row.speaker, row.user_text)))
    return "\n".join(lines)


def format_deleted(count: int, scope: str) -> str:
    if scope == "everywhere":
        return f"Deleted {count} of your stored messages."
    return f"Deleted {count} of your stored messages in this channel."


def format_wiped(count: int) -> str:
    return f"Deleted {count} stored messages in this channel."


def format_persona_show(custom: str | None) -> str:
    if custom is None:
        kind = "This server uses the default persona."
        body = DEFAULT_PERSONA
    else:
        kind = "This server uses a custom persona."
        body = custom
    return f"{kind}\n{shorten(body, _PREVIEW)}"


def permission_label(name: str) -> str:
    # Discord calls this flag Manage Server. The API name is manage_guild.
    if name == "manage_guild":
        return "Manage Server"
    return name.replace("_", " ").title()


async def delete_own_turns(
    store: Store, user_id: int, channel_id: int, scope: str
) -> int:
    if scope == "everywhere":
        return await store.delete_user_turns(user_id, None)
    return await store.delete_user_turns(user_id, channel_id)


async def wipe_channel(store: Store, channel_id: int) -> int:
    return await store.delete_channel_turns(channel_id)


async def report_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Map permission and DM failures to one-line replies."""
    cause: BaseException = error
    if isinstance(error, app_commands.CommandInvokeError):
        cause = error.original
    if isinstance(cause, app_commands.MissingPermissions):
        names = ", ".join(permission_label(name) for name in cause.missing_permissions)
        await send_ephemeral(
            interaction,
            f"You need the {names} permission to use this command.",
        )
        return
    if isinstance(cause, app_commands.NoPrivateMessage):
        await send_ephemeral(interaction, "This command only works in a server.")
        return
    print(type(cause).__name__)
    await send_ephemeral(interaction, "Something went wrong with that command.")
