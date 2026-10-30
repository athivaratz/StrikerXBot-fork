"""Slash commands for the name the bot uses in this server.

Loaded with the other AI cogs, and only when an API key is set.
"""

import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.ai.alias import AliasError, validate_alias
from bot.ai.history import current_store
from bot.utils.command_errors import report_command_error
from bot.utils.discord_send import send_ephemeral

_SERVER_ONLY = "This command only works in a server."


class IntroduceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="introduce", description="Tell the bot what to call you")
    @app_commands.guild_only()
    @app_commands.describe(name="The name to use in this server")
    async def introduce(self, interaction: discord.Interaction, name: str) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await send_ephemeral(interaction, _SERVER_ONLY)
            return
        try:
            alias = validate_alias(name)
        except AliasError as err:
            await send_ephemeral(interaction, str(err))
            return
        await current_store().set_alias(
            guild_id, interaction.user.id, alias, time.time()
        )
        await send_ephemeral(
            interaction, f"Got it. I will call you {alias} in this server."
        )

    @app_commands.command(
        name="introduce-clear",
        description="Forget the name you gave the bot",
    )
    @app_commands.guild_only()
    async def introduce_clear(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await send_ephemeral(interaction, _SERVER_ONLY)
            return
        removed = await current_store().clear_alias(guild_id, interaction.user.id)
        if removed:
            await send_ephemeral(
                interaction, "Done. I will use your display name again."
            )
            return
        await send_ephemeral(interaction, "You have not set a name in this server.")

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(IntroduceCog(bot))
