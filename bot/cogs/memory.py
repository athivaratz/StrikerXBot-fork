"""Slash commands for stored turns and the guild persona.

Loaded with the AI cog, and only when an API key is set.
"""

import time
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.ai.history import current_store
from bot.ai.memory_tools import (
    delete_own_turns,
    format_deleted,
    format_persona_show,
    format_view,
    format_wiped,
    report_command_error,
    wipe_channel,
)
from bot.ai.persona import PersonaError, validate_persona
from bot.utils.discord_send import send_ephemeral

_NEEDS_CHANNEL = "This command needs a channel."
_SERVER_ONLY = "This command only works in a server."


class MemoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    memory = app_commands.Group(
        name="memory",
        description="View or delete your stored AI messages",
    )
    persona = app_commands.Group(
        name="persona",
        description="Show or change this server's AI persona",
    )

    @memory.command(name="view", description="Show your stored messages in this channel")
    async def memory_view(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id
        if channel_id is None:
            await send_ephemeral(interaction, _NEEDS_CHANNEL)
            return
        store = current_store()
        user_id = interaction.user.id
        count = await store.count_user_turns(user_id, channel_id)
        rows = await store.last_user_turns(user_id, channel_id, 3)
        await send_ephemeral(interaction, format_view(count, rows))

    @memory.command(name="clear", description="Delete your stored messages")
    @app_commands.describe(scope="Delete in this channel, or everywhere")
    async def memory_clear(
        self,
        interaction: discord.Interaction,
        scope: Literal["channel", "everywhere"] = "channel",
    ) -> None:
        channel_id = interaction.channel_id
        if channel_id is None:
            await send_ephemeral(interaction, _NEEDS_CHANNEL)
            return
        count = await delete_own_turns(
            current_store(), interaction.user.id, channel_id, scope
        )
        await send_ephemeral(interaction, format_deleted(count, scope))

    @memory.command(
        name="wipe-channel",
        description="Delete every stored message in this channel",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def memory_wipe(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id
        if channel_id is None:
            await send_ephemeral(interaction, _NEEDS_CHANNEL)
            return
        count = await wipe_channel(current_store(), channel_id)
        await send_ephemeral(interaction, format_wiped(count))

    @persona.command(name="show", description="Show the persona used in this server")
    @app_commands.guild_only()
    async def persona_show(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await send_ephemeral(interaction, _SERVER_ONLY)
            return
        custom = await current_store().get_persona(guild_id)
        await send_ephemeral(interaction, format_persona_show(custom))

    @persona.command(name="set", description="Set this server's persona")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def persona_set(self, interaction: discord.Interaction, text: str) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await send_ephemeral(interaction, _SERVER_ONLY)
            return
        try:
            cleaned = validate_persona(text)
        except PersonaError as err:
            await send_ephemeral(interaction, str(err))
            return
        await current_store().set_persona(
            guild_id, cleaned, interaction.user.id, time.time()
        )
        await send_ephemeral(interaction, "Persona updated.")

    @persona.command(name="reset", description="Restore the default persona")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def persona_reset(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await send_ephemeral(interaction, _SERVER_ONLY)
            return
        removed = await current_store().reset_persona(guild_id)
        if removed:
            await send_ephemeral(interaction, "Persona reset to the default.")
            return
        await send_ephemeral(
            interaction, "This server is already using the default persona."
        )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemoryCog(bot))
