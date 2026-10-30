"""Plain text pieces for the status embed."""


def format_duration(seconds: float) -> str:
    """Hours drop the seconds, and days drop the minutes, so the line stays short."""
    total = max(0, int(seconds))
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def format_bytes(amount: int) -> str:
    """Megabytes below 1 GiB, gigabytes from there, one decimal either way."""
    size = max(0, int(amount))
    gigabyte = 1024 ** 3
    if size < gigabyte:
        return f"{size / (1024 ** 2):.1f} MB"
    return f"{size / gigabyte:.1f} GB"


def usage_bar(percent: float, width: int = 12) -> str:
    clamped = min(100.0, max(0.0, percent))
    filled = round(width * clamped / 100)
    return ("▰" * filled) + ("▱" * (width - filled))


def level(percent: float) -> str:
    if percent < 60:
        return "ok"
    if percent < 85:
        return "busy"
    return "high"


_DOTS = {"ok": "🟢", "busy": "🟡", "high": "🔴"}


def level_dot(percent: float) -> str:
    return _DOTS[level(percent)]


def latency_label(ms: float) -> str:
    if ms < 150:
        return "fast"
    if ms < 300:
        return "ok"
    return "slow"
