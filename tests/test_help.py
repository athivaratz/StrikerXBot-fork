"""The /help listing is built from command-like objects."""

from types import SimpleNamespace

from bot.utils.command_list import format_command_list


def test_format_command_list_expands_groups_and_sorts() -> None:
    commands = [
        SimpleNamespace(name="help", description="List this bot's commands"),
        SimpleNamespace(
            name="role",
            description="Edit roles",
            commands=[
                SimpleNamespace(name="remove", description="Take a role from a member"),
                SimpleNamespace(name="add", description="Give a member a role"),
            ],
        ),
        SimpleNamespace(name="clear", description="Delete recent messages"),
    ]
    text = format_command_list(commands)
    assert text.splitlines() == [
        "/clear: Delete recent messages",
        "/help: List this bot's commands",
        "/role add: Give a member a role",
        "/role remove: Take a role from a member",
    ]


def test_format_command_list_when_nothing_is_registered() -> None:
    assert format_command_list([]) == "No commands are registered."
