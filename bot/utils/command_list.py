"""Turn command-like objects into the /help text.

Groups carry a `commands` list. Leaves do not. Tests can pass fakes.
"""


def format_command_list(commands: list[object]) -> str:
    lines: list[str] = []
    for command in commands:
        children = getattr(command, "commands", None)
        if isinstance(children, list):
            for child in children:
                lines.append(f"/{command.name} {child.name}: {child.description}")
            continue
        lines.append(f"/{command.name}: {command.description}")
    lines.sort()
    if not lines:
        return "No commands are registered."
    return "\n".join(lines)
