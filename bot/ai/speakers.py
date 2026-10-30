"""Names for the system prompt.

Ids stay stable when a display name changes, so the model can tell people apart.
A saved name is the one to say. The display name stays beside it so a rename
on Discord is still visible.
"""

from bot.storage import Turn


def display_name(speaker_name: str) -> str:
    cleaned = " ".join(speaker_name.split()) if speaker_name else ""
    return cleaned or "Someone"


def speaker_ids(turns: list[Turn], speaker_id: int) -> list[int]:
    """The person talking now is included even on their first message in the channel."""
    ids = [speaker_id]
    for row in turns:
        if row.user_id not in ids:
            ids.append(row.user_id)
    return ids


def people_block(
    turns: list[Turn],
    speaker_id: int,
    speaker_name: str,
    aliases: dict[int, str] | None = None,
) -> str:
    """The person talking now wins. Their old nickname should not stick."""
    saved = aliases or {}
    names: dict[int, str] = {}
    for row in turns:
        names[row.user_id] = display_name(row.speaker)
    names[speaker_id] = display_name(speaker_name)
    lines = ["People in this chat"]
    for user_id, name in names.items():
        lines.append(_person_line(user_id, name, saved.get(user_id)))
    return "\n".join(lines)


def _person_line(user_id: int, name: str, alias: str | None) -> str:
    if alias:
        return f"- id {user_id}: {alias} (display name {name})"
    return f"- id {user_id}: {name}"
