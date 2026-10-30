"""Shared Discord send options.

Every path must refuse @everyone, roles, and user pings.
"""

from collections.abc import Awaitable, Callable

import discord

NO_MENTIONS = discord.AllowedMentions.none()


async def send_text(send: Callable[..., Awaitable[None]], text: str) -> None:
    """Discord would otherwise ping anyone the model echoes."""
    await send(text, allowed_mentions=NO_MENTIONS)


async def send_ephemeral(interaction: discord.Interaction, text: str) -> None:
    """Slash replies stay visible only to the caller."""
    kwargs = {"ephemeral": True, "allowed_mentions": NO_MENTIONS}
    if interaction.response.is_done():
        await interaction.followup.send(text, **kwargs)
        return
    await interaction.response.send_message(text, **kwargs)
