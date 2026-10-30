"""Slash command that renders one PDF page as a PNG."""

import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.pdf_render import PdfRequestError, render_pdf_page, validate_pdf_request
from bot.utils.command_errors import report_command_error
from bot.utils.discord_send import NO_MENTIONS, send_ephemeral

_TOO_LARGE = "That image is too large to upload. Try a lower dpi."


class PdfCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _send_private_error(
        self,
        interaction: discord.Interaction,
        text: str,
    ) -> None:
        # A public defer makes the first followup edit the thinking message
        # and ignore ephemeral. Drop that message, then send a private reply.
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass
        await interaction.followup.send(
            text,
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )

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
        reason = validate_pdf_request(file.filename, file.size, page)
        if reason is not None:
            await send_ephemeral(interaction, reason)
            return
        # Rendering can take longer than Discord's first-response window.
        await interaction.response.defer()
        data = await file.read()
        try:
            png = await asyncio.to_thread(render_pdf_page, data, page, int(dpi))
        except PdfRequestError as err:
            await self._send_private_error(interaction, str(err))
            return
        image = discord.File(io.BytesIO(png), filename=f"page_{page}.png")
        try:
            await interaction.followup.send(file=image, allowed_mentions=NO_MENTIONS)
        except discord.HTTPException:
            await self._send_private_error(interaction, _TOO_LARGE)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PdfCog(bot))
