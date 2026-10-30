"""Slash command that renders one PDF page as a PNG."""

import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.pdf_render import PdfRequestError, render_pdf_page, validate_pdf_request
from bot.utils.command_errors import report_command_error
from bot.utils.discord_send import NO_MENTIONS, send_ephemeral


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
        # Rendering can take longer than Discord's first-response window.
        await interaction.response.defer()
        reason = validate_pdf_request(file.filename, file.size, page)
        if reason is not None:
            await send_ephemeral(interaction, reason)
            return
        data = await file.read()
        try:
            png = await asyncio.to_thread(render_pdf_page, data, page, int(dpi))
        except PdfRequestError as err:
            await send_ephemeral(interaction, str(err))
            return
        image = discord.File(io.BytesIO(png), filename=f"page_{page}.png")
        await interaction.followup.send(file=image, allowed_mentions=NO_MENTIONS)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PdfCog(bot))
