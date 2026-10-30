"""Apply /role add, remove, and replace after the hierarchy check."""

import discord

from bot.services.roles import check_role_change, plan_replace
from bot.utils.discord_send import send_ephemeral

_SERVER = "This command only works in a server."
_NO_BOT = "I could not find my member on this server."
_FORBIDDEN = "I do not have a high enough role to change that."


def _audit(user: discord.abc.User) -> str:
    return f"/role by {user}"


def _context(
    interaction: discord.Interaction,
) -> tuple[discord.Member, discord.Member, discord.Guild] | str:
    guild = interaction.guild
    actor = interaction.user
    if guild is None or not isinstance(actor, discord.Member):
        return _SERVER
    bot_member = guild.me
    if bot_member is None:
        return _NO_BOT
    return actor, bot_member, guild


async def _apply(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role,
    action: str,
    actor: discord.Member,
    bot_member: discord.Member,
    guild: discord.Guild,
) -> str:
    audit = _audit(interaction.user)
    if action == "add":
        await member.add_roles(role, reason=audit)
        return f"Added {role.name} to {member.display_name}."
    if action == "remove":
        await member.remove_roles(role, reason=audit)
        return f"Removed {role.name} from {member.display_name}."
    remove, skip = plan_replace(actor, member, bot_member, guild)
    if remove:
        await member.remove_roles(*remove, reason=audit)
    await member.add_roles(role, reason=audit)
    text = f"Set {member.display_name}'s role to {role.name}."
    if skip:
        names = ", ".join(item.name for item in skip)
        text = f"{text} Skipped {names}."
    return text


async def edit_member_role(
    interaction: discord.Interaction,
    member: discord.Member,
    role: discord.Role,
    action: str,
) -> None:
    found = _context(interaction)
    if isinstance(found, str):
        await send_ephemeral(interaction, found)
        return
    actor, bot_member, guild = found
    reason = check_role_change(actor, member, role, bot_member, guild)
    if reason is not None:
        await send_ephemeral(interaction, reason)
        return
    try:
        text = await _apply(interaction, member, role, action, actor, bot_member, guild)
    except discord.Forbidden:
        await send_ephemeral(interaction, _FORBIDDEN)
        return
    await send_ephemeral(interaction, text)
