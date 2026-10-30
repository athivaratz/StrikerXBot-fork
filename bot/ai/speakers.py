"""Names for the system prompt.

Ids stay stable when a display name changes, so the model can tell people apart.
"""

from bot.storage import Turn


def display_name(speaker_name: str) -> str:
    cleaned = " ".join(speaker_name.split()) if speaker_name else ""
    return cleaned or "Someone"


def people_block(turns: list[Turn], speaker_id: int, speaker_name: str) -> str:
    """The person talking now wins. Their old nickname should not stick."""
    names: dict[int, str] = {}
    for row in turns:
        names[row.user_id] = display_name(row.speaker)
    names[speaker_id] = display_name(speaker_name)
    lines = ["People in this chat"]
    for user_id, name in names.items():
        lines.append(f"- id {user_id}: {name}")
    return "\n".join(lines)
