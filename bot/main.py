import os
import discord
import pymupdf
import io
from datetime import date
from bot.config import (
    JOIN_ROLE_ID,
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

client = discord.Client(intents=intents)
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
async def on_message(message):
    if message.author == client.user:
            return
    if message.content.startswith('-bye'):
        await message.channel.send("Goodbye! I will see you later!")
        return
    if message.content.startswith("-hello"): 
        await message.channel.send("Hey, There!")
        return
    if message.content.startswith('-help'):
        await message.channel.send("What can I help you? Please tell me.")
        return
    if message.content.startswith('-today'):
        await message.channel.send(f"Date: {date.today()}")
        return
    if message.content.startswith('-clear'):
        if message.author.guild_permissions.manage_messages:
              delete = await message.channel.purge(limit=100)
              await message.channel.send(f"Cleared {len(delete)} messages.")
        else:
            await message.channel.send("You don't have permission to do this.")
        return
    if message.content.startswith('-role') and message.author.guild_permissions.manage_messages:
        parts = message.content.split()
        if len(parts) < 3:
            await message.channel.send("Invalid Command! Use this instead `-role @User <Role_ID>`.")
            return
        if message.mentions:
            target_member = message.mentions[0]
        else:
            user_id_str = ''.join(filter(str.isdigit, parts[1]))
            if user_id_str.isdigit():
                target_member = message.guild.get_member(int(user_id_str))
            else:
                target_member = None
        if target_member is None:
            # await message.channel.send("Can't found a memberin this server!")
            target_member = await message.guild.fetch_member(int(user_id_str))

        try:
            role_id = int(parts[2])
        except ValueError:
            await message.channel.send("Role ID must be integer!")
            return
        role = message.guild.get_role(role_id)
    
        if role is None:
            await message.channel.send("Can't find a role on this server.")
            return
        try:
            roles_to_remove = [r for r in target_member.roles if r != message.guild.default_role]
            if roles_to_remove:
                await target_member.remove_roles(*roles_to_remove)
            await target_member.add_roles(role)
            await message.channel.send(f"Already increased role {role.name} to {target_member.mention}!")
        except discord.Forbidden:
            await message.channel.send("Bot don't have a high enough role to change it.")
        return
    if message.content.startswith('-pdf-to-image'):
        parts = message.content.split()  
        if message.attachments and message.attachments[0].filename.endswith('.pdf') and len(parts) > 1 and parts[1].isdigit():
            page = int(parts[1])
            pdf_attachment = message.attachments[0]
            pdf_filename = "temp.pdf"
            await pdf_attachment.save(pdf_filename)

            try:            
                doc = pymupdf.open(pdf_filename)
            
                if 1 <= page <= len(doc):
                    page_obj = doc[page - 1]
                    pix = page_obj.get_pixmap(dpi=300)
                    image_bytes = pix.tobytes("png")
                    image_file = discord.File(io.BytesIO(image_bytes), filename=f"output_page_{page}.png")
                    await message.channel.send(file=image_file)
                else:
                    await message.channel.send(f"This file have {len(doc)} pages. Please provide a correct number!")
            finally:
                if os.path.exists(pdf_filename):
                    os.remove(pdf_filename)           
        else:
            await message.channel.send("Please provided correct code: -pdf-to-image <number_page>")
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