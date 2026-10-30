"""Slash commands for clearing messages and editing roles."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.role_edit import edit_member_role
from bot.utils.command_errors import report_command_error
from bot.utils.discord_send import NO_MENTIONS


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    role = app_commands.Group(
        name="role",
        description="Add, remove, or replace a member's role",
        guild_only=True,
        default_permissions=discord.Permissions(manage_roles=True),
    )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await report_command_error(interaction, error)

    @app_commands.command(name="clear", description="Delete recent messages in this channel")
    @app_commands.describe(amount="How many messages to delete, from 1 to 100")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(
        manage_messages=True,
        read_message_history=True,
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 100,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if channel is None or not hasattr(channel, "purge"):
            await interaction.followup.send(
                "This command needs a text channel.",
                ephemeral=True,
                allowed_mentions=NO_MENTIONS,
            )
            return
        deleted = await channel.purge(limit=amount)
        await interaction.followup.send(
            f"Cleared {len(deleted)} messages.",
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )

    @role.command(name="add", description="Give a member a role")
    @app_commands.describe(member="Member who receives the role", role="Role to add")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def role_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ) -> None:
        await edit_member_role(interaction, member, role, "add")

    @role.command(name="remove", description="Take a role from a member")
    @app_commands.describe(member="Member who loses the role", role="Role to remove")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def role_remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ) -> None:
        await edit_member_role(interaction, member, role, "remove")

    @role.command(name="replace", description="Replace a member's roles with one role")
    @app_commands.describe(member="Member whose roles change", role="The role they should keep")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def role_replace(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ) -> None:
        await edit_member_role(interaction, member, role, "replace")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
