import asyncio

import discord

from bot.cogs.ai import send_text
from bot.utils.discord_send import NO_MENTIONS


def test_send_text_disables_mentions():
    calls = []

    async def fake_send(text: str, **kwargs) -> None:
        calls.append(kwargs)

    asyncio.run(send_text(fake_send, "hi @everyone"))
    asyncio.run(send_text(fake_send, "again"))
    expected = discord.AllowedMentions.none()
    assert len(calls) == 2
    for kwargs in calls:
        mentions = kwargs["allowed_mentions"]
        assert mentions is NO_MENTIONS
        assert mentions.everyone == expected.everyone
        assert mentions.users == expected.users
        assert mentions.roles == expected.roles
        assert mentions.replied_user == expected.replied_user
