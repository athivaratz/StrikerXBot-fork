"""Slash command and mention replies for AI chat.

Why a cog: it stays unloaded when no API key is set, and the bot still starts.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.ai.chat import run_chat
from bot.ai.chunker import split_for_discord
from bot.ai.provider import AIError, NO_ANSWER
from bot.utils.discord_send import NO_MENTIONS, send_text


def _chunks(reply: str) -> list[str]:
    parts = split_for_discord(reply)
    if parts:
        return parts
    return [NO_ANSWER]


class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ask", description="Ask a question")
    async def ask(self, interaction: discord.Interaction, prompt: str) -> None:
        await interaction.response.defer(thinking=True)
        channel_id = interaction.channel_id
        if channel_id is None:
            await send_text(interaction.followup.send, NO_ANSWER)
            return
        reply = await self._answer(
            interaction.user.id,
            channel_id,
            interaction.user.display_name,
            prompt,
            interaction.channel,
            interaction.guild_id,
        )
        for chunk in _chunks(reply):
            await send_text(interaction.followup.send, chunk)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.mention_everyone:
            return
        if self.bot.user is None or self.bot.user not in message.mentions:
            return
        text = message.content.replace(f"<@{self.bot.user.id}>", "")
        text = text.replace(f"<@!{self.bot.user.id}>", "").strip()
        if text == "":
            return
        guild_id = None
        if message.guild is not None:
            guild_id = message.guild.id
        reply = await self._answer(
            message.author.id,
            message.channel.id,
            message.author.display_name,
            text,
            message.channel,
            guild_id,
        )
        chunks = _chunks(reply)
        await send_text(message.reply, chunks[0])
        for chunk in chunks[1:]:
            await send_text(message.channel.send, chunk)

    async def _answer(
        self,
        user_id: int,
        channel_id: int,
        speaker: str,
        text: str,
        channel: discord.abc.Messageable | None,
        guild_id: int | None,
    ) -> str:
        try:
            if channel is None:
                return await run_chat(
                    user_id, channel_id, speaker, text, guild_id=guild_id
                )
            async with channel.typing():
                return await run_chat(
                    user_id, channel_id, speaker, text, guild_id=guild_id
                )
        except AIError as err:
            return str(err)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AICog(bot))
