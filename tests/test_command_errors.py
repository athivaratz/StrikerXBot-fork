"""Slash-command error replies stay private."""

import asyncio

import discord
from discord import app_commands

from bot.utils.command_errors import report_command_error


class _Response:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def is_done(self) -> bool:
        return self.kwargs is not None

    async def send_message(self, text: str, **kwargs: object) -> None:
        self.kwargs = {"text": text, **kwargs}


class _Interaction:
    def __init__(self) -> None:
        self.response = _Response()


def _cooldown(retry_after: float) -> app_commands.CommandOnCooldown:
    return app_commands.CommandOnCooldown(
        app_commands.checks.Cooldown(1, 15.0),
        retry_after,
    )


def test_cooldown_reply_rounds_up_and_stays_ephemeral() -> None:
    interaction = _Interaction()
    asyncio.run(report_command_error(interaction, _cooldown(1.2)))
    sent = interaction.response.kwargs
    assert sent is not None
    assert sent["text"] == "Try again in 2 seconds."
    assert sent["ephemeral"] is True
    mentions = sent["allowed_mentions"]
    assert isinstance(mentions, discord.AllowedMentions)
    assert mentions.everyone is False
    assert mentions.users is False
    assert mentions.roles is False
    assert mentions.replied_user is False
