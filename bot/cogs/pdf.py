"""Slash command that renders one PDF page as a PNG."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.pdf_command import run_pdf_command
from bot.utils.command_errors import report_command_error


class PdfCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="pdf-to-image",
        description="Render one page of a PDF as a PNG",
    )
    @app_commands.describe(
        file="The PDF to render",
        page="Page number, starting at 1",
        dpi="Dots per inch, from 72 to 300",
    )
    async def pdf_to_image(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        page: int,
        dpi: app_commands.Range[int, 72, 300] = 150,
    ) -> None:
        await run_pdf_command(interaction, file, page, int(dpi))

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PdfCog(bot))
