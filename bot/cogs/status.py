"""Public /status health check."""

import asyncio
import time
from datetime import datetime, timezone

import discord
import psutil
from discord import app_commands
from discord.ext import commands

from bot.config import OWNER_IDS
from bot.services.host_info import collect
from bot.services.status_embed import build_status_embed
from bot.utils.command_errors import report_command_error
from bot.utils.discord_send import NO_MENTIONS


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.started = time.monotonic()
        # The first interval=None sample is always 0.0, so take it at load.
        psutil.cpu_percent(interval=None)

    @app_commands.command(name="status", description="Show bot and host status")
    @app_commands.checks.cooldown(1, 15.0)
    async def status(self, interaction: discord.Interaction) -> None:
        snapshot = await asyncio.to_thread(collect)
        guilds = self.bot.guilds
        embed = build_status_embed(
            snapshot,
            ws_ms=self.bot.latency * 1000,
            bot_uptime_s=time.monotonic() - self.started,
            now=datetime.now(timezone.utc),
            guilds=len(guilds),
            users=sum(guild.member_count or 0 for guild in guilds),
            channels=sum(len(guild.channels) for guild in guilds),
            show_user=interaction.user.id in OWNER_IDS,
        )
        await interaction.response.send_message(embed=embed, allowed_mentions=NO_MENTIONS)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot))
