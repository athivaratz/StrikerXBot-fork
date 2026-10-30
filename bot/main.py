import discord
from discord.ext import commands
from bot.config import (
    DEV_GUILD_ID,
    JOIN_ROLE_ID,
    OPENROUTER_API_KEY,
    OVERWRITE_ROLE_ID_1,
    OVERWRITE_ROLE_ID_2,
    PRIVACY_VOICE_CHANNEL_ID,
    TOKEN,
)
from web.keepalive import server_on

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True


# AI cogs stay in their own list so a missing key can skip them without skipping sync.
BASE_COGS: tuple[str, ...] = (
    "bot.cogs.help",
    "bot.cogs.moderation",
    "bot.cogs.pdf",
    "bot.cogs.status",
)
AI_COGS: tuple[str, ...] = (
    "bot.cogs.ai",
    "bot.cogs.memory",
    "bot.cogs.introduce",
)


class StrikerXBot(commands.Bot):
    async def setup_hook(self) -> None:
        for name in BASE_COGS:
            await self.load_extension(name)
        if OPENROUTER_API_KEY:
            for name in AI_COGS:
                await self.load_extension(name)
        else:
            print("OPENROUTER_API_KEY is not set. AI chat will not load.")
        await self._sync_commands()

    async def _sync_commands(self) -> None:
        try:
            if DEV_GUILD_ID is None:
                synced = await self.tree.sync()
                print(f"Synced {len(synced)} slash commands globally.")
                return
            # A guild sync shows new commands immediately. Global sync can take time.
            guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash commands to guild {DEV_GUILD_ID}.")
        except discord.HTTPException as err:
            print(f"Slash command sync failed with status {err.status}.")


# commands.Bot requires a prefix. Slash commands do not use it.
client = StrikerXBot(command_prefix="!", help_command=None, intents=intents)
temp_channels = {}

async def create_private_channel(member):
    if member.bot:
        return

    guild = member.guild
    channel_name = f"private-{member.name.lower()}"
    category = discord.utils.get(guild.categories, name=f"🔒-{member.name}")

    if not category:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(OVERWRITE_ROLE_ID_1): discord.PermissionOverwrite(view_channel=True, connect=True),
            guild.get_role(OVERWRITE_ROLE_ID_2): discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_permissions=True, connect=True),
        }
        category = await guild.create_category(f"🔒-{member.name}", overwrites=overwrites)
        await guild.create_text_channel(channel_name, category=category)

@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))
    for guild in client.guilds:
        for member in guild.members:
            if not member.bot:
                await create_private_channel(member)

@client.event
async def on_member_join(member):
    role_id = JOIN_ROLE_ID
    role = member.guild.get_role(role_id)

    if not member.bot:
        await create_private_channel(member)
    
    if role is None:
        print("Can't found a role on this server.")
        return
    try:
        await member.add_roles(role)
        print("Already set the first role for user in server!")
    except discord.Forbidden:
        print("Bot don't have a high role to change it.")
    return

@client.event
async def on_voice_state_update(member, before, after):
    guild = member.guild

    if after.channel and after.channel.id == PRIVACY_VOICE_CHANNEL_ID:
        category = after.channel.category
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(OVERWRITE_ROLE_ID_1): discord.PermissionOverwrite(view_channel=True, connect=True),
            guild.get_role(OVERWRITE_ROLE_ID_2): discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_permissions=True, connect=True),
        }
        voice_name = f"{member.display_name}'s voice room"
        new_voice = await guild.create_voice_channel(
            name=voice_name, category=category, overwrites=overwrites
        )
        await member.move_to(new_voice)
        text_name = f"{member.name}'s room"
        new_text = await guild.create_text_channel(
            name=text_name, category=category, overwrites=overwrites
        )
        
        temp_channels[new_voice.id] = new_text

    if before.channel and before.channel.id != PRIVACY_VOICE_CHANNEL_ID:
        if len(before.channel.members) == 0:
            if before.channel.name.startswith(f"{member.display_name}"):
                await before.channel.delete()
                if before.channel.id in temp_channels:
                    await temp_channels[before.channel.id].delete()
                    del temp_channels[before.channel.id]

def main():
    server_on()
    client.run(TOKEN)