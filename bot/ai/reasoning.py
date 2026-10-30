"""Map a configured effort onto OpenRouter's reasoning object.

Why a separate module: the HTTP client stays under its size limit.
"""


def reasoning_field(effort: str) -> dict[str, bool | str]:
    """`off` disables reasoning. Other efforts are sent as given."""
    if effort == "off":
        return {"enabled": False}
    return {"effort": effort}
