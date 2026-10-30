"""Cog loading and slash-command sync, without connecting to Discord."""

import asyncio
from typing import Any

import discord
from discord import app_commands

import bot.main as main


def _names(commands: list[object]) -> list[str]:
    return sorted(getattr(command, "name") for command in commands)


def _child_names(command: object) -> list[str]:
    # Group.commands is a property that returns a list.
    raw = getattr(command, "commands")
    return sorted(child.name for child in raw)


async def _load() -> dict[str, Any]:
    bot = main.StrikerXBot(command_prefix="!", help_command=None, intents=main.intents)
    order: list[tuple[str, int | None]] = []
    original = bot.tree.copy_global_to

    def copy_global_to(*, guild: discord.abc.Snowflake) -> None:
        order.append(("copy", guild.id))
        original(guild=guild)

    async def sync(*, guild: discord.abc.Snowflake | None = None) -> list[object]:
        order.append(("sync", None if guild is None else guild.id))
        return []

    bot.tree.copy_global_to = copy_global_to  # type: ignore[method-assign]
    bot.tree.sync = sync  # type: ignore[method-assign]
    await bot.setup_hook()
    tree = bot.tree
    return {
        "names": _names(tree.get_commands()),
        "role": _child_names(tree.get_command("role")),
        "order": order,
        "clear": tree.get_command("clear"),
        "role_cmd": tree.get_command("role"),
        "memory": tree.get_command("memory"),
        "persona": tree.get_command("persona"),
        "introduce": tree.get_command("introduce"),
        "introduce_clear": tree.get_command("introduce-clear"),
        "extensions": set(bot.extensions),
    }


def _run() -> dict[str, Any]:
    return asyncio.run(_load())


def test_setup_loads_ai_commands_and_syncs_once(monkeypatch) -> None:
    monkeypatch.setattr(main, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(main, "DEV_GUILD_ID", None)
    loaded = _run()
    assert loaded["names"] == [
        "ask",
        "clear",
        "help",
        "introduce",
        "introduce-clear",
        "memory",
        "pdf-to-image",
        "persona",
        "role",
    ]
    assert loaded["role"] == ["add", "remove", "replace"]
    memory = loaded["memory"]
    persona = loaded["persona"]
    assert _child_names(memory) == ["clear", "view", "wipe-channel"]
    assert _child_names(persona) == ["reset", "set", "show"]
    assert loaded["order"] == [("sync", None)]
    assert set(main.BASE_COGS).issubset(loaded["extensions"])
    assert set(main.AI_COGS).issubset(loaded["extensions"])
    _assert_access(loaded)


def test_setup_skips_ai_commands_without_a_key(monkeypatch) -> None:
    monkeypatch.setattr(main, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(main, "DEV_GUILD_ID", None)
    loaded = _run()
    assert loaded["names"] == ["clear", "help", "pdf-to-image", "role"]
    assert "introduce" not in loaded["names"]
    assert "introduce-clear" not in loaded["names"]
    assert loaded["memory"] is None
    assert loaded["persona"] is None
    assert loaded["order"] == [("sync", None)]
    assert set(main.BASE_COGS).issubset(loaded["extensions"])
    assert set(main.AI_COGS).isdisjoint(loaded["extensions"])


def test_setup_syncs_to_the_dev_guild(monkeypatch) -> None:
    monkeypatch.setattr(main, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(main, "DEV_GUILD_ID", 4242)
    loaded = _run()
    assert loaded["order"] == [("copy", 4242), ("sync", 4242)]
    assert "ask" not in loaded["names"]


def _assert_access(loaded: dict[str, Any]) -> None:
    clear = loaded["clear"]
    role = loaded["role_cmd"]
    assert isinstance(clear, app_commands.Command)
    assert isinstance(role, app_commands.Group)
    assert clear.guild_only is True
    assert clear.default_permissions is not None
    assert clear.default_permissions.manage_messages is True
    assert role.guild_only is True
    assert role.default_permissions is not None
    assert role.default_permissions.manage_roles is True
    memory = loaded["memory"]
    persona = loaded["persona"]
    assert isinstance(memory, app_commands.Group)
    assert isinstance(persona, app_commands.Group)
    wipe = memory.get_command("wipe-channel")
    set_cmd = persona.get_command("set")
    reset = persona.get_command("reset")
    assert wipe is not None and wipe.guild_only is True
    assert set_cmd is not None and set_cmd.guild_only is True
    assert reset is not None and reset.guild_only is True
    introduce = loaded["introduce"]
    introduce_clear = loaded["introduce_clear"]
    assert isinstance(introduce, app_commands.Command)
    assert isinstance(introduce_clear, app_commands.Command)
    assert introduce.guild_only is True
    assert introduce_clear.guild_only is True
