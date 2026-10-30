"""Slash command that lists whatever is registered on the tree."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.command_errors import report_command_error
from bot.utils.command_list import format_command_list
from bot.utils.discord_send import send_ephemeral


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="List this bot's commands")
    async def help_command(self, interaction: discord.Interaction) -> None:
        # Group.commands is a list, which is the shape the formatter expects.
        listed = format_command_list(list(self.bot.tree.get_commands()))
        await send_ephemeral(interaction, listed)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
