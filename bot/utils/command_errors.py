"""Shared slash-command error replies.

Permission failures should name the permission instead of dumping a traceback.
"""

import math

import discord
from discord import app_commands

from bot.utils.discord_send import send_ephemeral


def permission_label(name: str) -> str:
    # Discord calls this flag Manage Server. The API name is manage_guild.
    if name == "manage_guild":
        return "Manage Server"
    return name.replace("_", " ").title()


async def report_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Map permission, cooldown, and DM failures to one-line replies."""
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
    if isinstance(cause, app_commands.BotMissingPermissions):
        names = ", ".join(permission_label(name) for name in cause.missing_permissions)
        await send_ephemeral(
            interaction,
            f"I need the {names} permission in this channel.",
        )
        return
    if isinstance(cause, app_commands.NoPrivateMessage):
        await send_ephemeral(interaction, "This command only works in a server.")
        return
    if isinstance(cause, app_commands.CommandOnCooldown):
        # retry_after is a fraction. Round up so the reply never says 0 while still waiting.
        wait = math.ceil(cause.retry_after)
        await send_ephemeral(interaction, f"Try again in {wait} seconds.")
        return
    print(type(cause).__name__)
    await send_ephemeral(interaction, "Something went wrong with that command.")
