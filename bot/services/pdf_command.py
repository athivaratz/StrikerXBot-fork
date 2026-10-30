"""Run /pdf-to-image so tests can drive it without a Discord connection.

A public defer leaves a thinking message. The first followup edits that
message and ignores ephemeral, so every failure has to delete it first.
"""

import asyncio
import io
from collections.abc import Callable

import discord

from bot.services.pdf_render import PdfRequestError, render_pdf_page, validate_pdf_request
from bot.utils.discord_send import NO_MENTIONS, send_ephemeral

_TOO_LARGE = "That image is too large to upload. Try a lower dpi."
_DOWNLOAD_FAILED = "I could not download that file. Please try again."
_RENDER_FAILED = "Something went wrong while rendering that page."

RenderPage = Callable[[bytes, int, int], bytes]


async def _send_private_error(interaction: discord.Interaction, text: str) -> None:
    # If Discord refuses the delete, a followup would edit the public message.
    try:
        await interaction.delete_original_response()
    except discord.HTTPException as err:
        print(err.status)
        return
    try:
        await interaction.followup.send(
            text,
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )
    except discord.HTTPException as err:
        print(err.status)


async def run_pdf_command(
    interaction: discord.Interaction,
    file: discord.Attachment,
    page: int,
    dpi: int,
    render: RenderPage = render_pdf_page,
) -> None:
    reason = validate_pdf_request(file.filename, file.size, page)
    if reason is not None:
        await send_ephemeral(interaction, reason)
        return
    # Rendering can take longer than Discord's first-response window.
    await interaction.response.defer()
    try:
        # Read and upload both raise HTTPException, with a different message each.
        try:
            data = await file.read()
        except discord.HTTPException:
            await _send_private_error(interaction, _DOWNLOAD_FAILED)
            return
        png = await asyncio.to_thread(render, data, page, int(dpi))
        image = discord.File(io.BytesIO(png), filename=f"page_{page}.png")
        try:
            await interaction.followup.send(file=image, allowed_mentions=NO_MENTIONS)
        except discord.HTTPException:
            await _send_private_error(interaction, _TOO_LARGE)
    except PdfRequestError as err:
        await _send_private_error(interaction, str(err))
    except Exception as err:
        # The type name is enough. The message can contain file details.
        print(type(err).__name__)
        await _send_private_error(interaction, _RENDER_FAILED)
