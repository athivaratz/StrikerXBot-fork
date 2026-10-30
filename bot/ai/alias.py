"""Check a chosen name before it is stored or shown.

A mention or a markdown mark in a name would be repeated in prompts and in Discord.
"""

MAX_ALIAS_LENGTH = 32

# Discord renders "-# " as small text, so the nudge stays quiet under the reply.
INTRO_REMINDER = (
    "-# You have not introduced yourself yet. "
    "Use /introduce to tell me what to call you."
)

_BLOCKED = set("@<>`\n\r")


class AliasError(ValueError):
    """The text cannot be saved as a name."""


def validate_alias(text: str) -> str:
    cleaned = " ".join(text.split())
    if cleaned == "":
        raise AliasError("Name cannot be empty.")
    if len(cleaned) > MAX_ALIAS_LENGTH:
        raise AliasError(f"Name must be {MAX_ALIAS_LENGTH} characters or fewer.")
    # Check the original text so a newline is still caught after spaces collapse.
    if any(char in _BLOCKED for char in text):
        raise AliasError("Name cannot include @, <, >, `, or a new line.")
    return cleaned


def add_reminder(chunks: list[str], limit: int = 2000) -> list[str]:
    """Keep the caller's list intact. Discord sends the returned copy."""
    if not chunks:
        return [INTRO_REMINDER]
    extra = "\n" + INTRO_REMINDER
    last = chunks[-1]
    if len(last) + len(extra) <= limit:
        return [*chunks[:-1], last + extra]
    return [*chunks, INTRO_REMINDER]
