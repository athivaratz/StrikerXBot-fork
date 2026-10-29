"""Split long replies into Discord messages.

Why: Discord rejects a message over 2000 characters, and cutting a code fence
leaves a broken block in the channel.
"""

def _fence_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    index = 0
    while True:
        found = text.find("```", index)
        if found < 0:
            if start is not None:
                ranges.append((start, len(text)))
            return ranges
        if start is None:
            start = found
        else:
            ranges.append((start, found + 3))
            start = None
        index = found + 3


def _range_at(ranges: list[tuple[int, int]], index: int) -> tuple[int, int] | None:
    for start, end in ranges:
        if start < index < end:
            return (start, end)
    return None


def _last_break(text: str, end: int, ranges: list[tuple[int, int]]) -> int | None:
    for separator in ("\n\n", "\n"):
        index = text.rfind(separator, 0, end)
        while index > 0:
            if _range_at(ranges, index) is None:
                return index
            index = text.rfind(separator, 0, index)
    return None


def _opener(text: str, fence_start: int) -> str:
    line_end = text.find("\n", fence_start)
    if line_end < 0:
        return "```"
    return text[fence_start:line_end]


def _pair(text: str, split: int) -> tuple[str, str]:
    left = text[:split].rstrip()
    right = text[split:].lstrip()
    return left, right


def _split_inside_fence(text: str, limit: int, fence_start: int) -> tuple[str, str]:
    opener = _opener(text, fence_start)
    closing = "\n```"
    # The newline that ends the opening line is not a place to cut.
    content_start = fence_start + len(opener)
    if content_start < len(text) and text[content_start] == "\n":
        content_start += 1
    room = limit - len(closing)
    if room <= content_start:
        return text[:limit], text[limit:]
    break_at = text.rfind("\n", content_start, room + 1)
    cut = break_at if break_at >= content_start else room
    left = text[:cut].rstrip() + closing
    right = opener + "\n" + text[cut:].lstrip("\n")
    return left, right


def _cut(text: str, limit: int) -> tuple[str, str]:
    ranges = _fence_ranges(text)
    straddling = _range_at(ranges, limit)
    if straddling is not None:
        fence_start, fence_end = straddling
        if fence_end - fence_start <= limit and fence_start > 0:
            break_at = _last_break(text, fence_start, ranges)
            split = fence_start if break_at is None else break_at
            return _pair(text, split)
        return _split_inside_fence(text, limit, fence_start)
    break_at = _last_break(text, limit, ranges)
    if break_at is not None:
        return _pair(text, break_at)
    return text[:limit], text[limit:]


def split_for_discord(text: str, limit: int = 2000) -> list[str]:
    """Prefer a blank line, then a single line, and keep a short code fence whole."""
    if text == "":
        return []
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        left, right = _cut(remaining, limit)
        if not left or len(right) >= len(remaining):
            left, right = remaining[:limit], remaining[limit:]
        chunks.append(left)
        remaining = right
    return chunks
