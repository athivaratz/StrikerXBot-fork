"""Build the public /status embed.

The embed names resources and versions. It leaves out the hostname and addresses.
"""

import math
from datetime import datetime

import discord

from bot.services.host_info import HostSnapshot
from bot.services.status_format import (
    format_bytes,
    format_duration,
    latency_label,
    level,
    level_dot,
    usage_bar,
)

_RANK = {"ok": 0, "busy": 1, "high": 2}
_COLOUR = {
    "ok": discord.Colour.green(),
    "busy": discord.Colour.yellow(),
    "high": discord.Colour.red(),
}


def _clip(text: str, limit: int = 1024) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _line(text: str) -> str:
    flat = " ".join(text.split())
    return _clip(flat, 180)


def _latency(ws_ms: float) -> str:
    # Gateway latency stays non-finite until the bot has connected.
    if not math.isfinite(ws_ms):
        return "n/a"
    return f"{round(ws_ms)} ms · {latency_label(ws_ms)}"


def _uptime(seconds: float) -> str:
    whole = max(0, int(seconds))
    return f"{format_duration(whole)}\n{whole}s"


def _meter(percent: float) -> str:
    return f"`{usage_bar(percent)}` {percent:.1f}%"


def _cpu(snapshot: HostSnapshot) -> str:
    cores = "1 core" if snapshot.cpu_count == 1 else f"{snapshot.cpu_count} cores"
    lines = [_meter(snapshot.cpu_percent), _line(snapshot.cpu_model)]
    if snapshot.load is None:
        lines.append(cores)
    else:
        one, five, fifteen = snapshot.load
        lines.append(f"{cores} · load {one:.2f} {five:.2f} {fifteen:.2f}")
    if snapshot.temperature_c is not None:
        lines.append(f"{snapshot.temperature_c:.1f}°C")
    return "\n".join(lines)


def _memory(snapshot: HostSnapshot) -> str:
    used = format_bytes(snapshot.mem_used)
    total = format_bytes(snapshot.mem_total)
    rss = format_bytes(snapshot.bot_rss)
    return f"{_meter(snapshot.mem_percent)}\n{used} / {total}\nbot {rss}"


def _disk(snapshot: HostSnapshot) -> str:
    used = format_bytes(snapshot.disk_used)
    total = format_bytes(snapshot.disk_total)
    free = format_bytes(snapshot.disk_free)
    return f"{_meter(snapshot.disk_percent)}\n{used} / {total}\nfree {free}"


def _description(snapshot: HostSnapshot) -> str:
    head = f"{_line(snapshot.os_name)} · {_line(snapshot.arch)} · {_line(snapshot.kernel)}"
    if not snapshot.board:
        return _clip(head, 4096)
    return _clip(f"{head}\n{_line(snapshot.board)}", 4096)


def _colour(snapshot: HostSnapshot) -> discord.Colour:
    worst = "ok"
    for percent in (snapshot.cpu_percent, snapshot.mem_percent, snapshot.disk_percent):
        name = level(percent)
        if _RANK[name] > _RANK[worst]:
            worst = name
    return _COLOUR[worst]


def _host(snapshot: HostSnapshot, show_user: bool) -> str:
    lines = [_line(snapshot.timezone)]
    if show_user:
        lines.append(_line(snapshot.host_user))
    return "\n".join(lines)


def build_status_embed(
    snapshot: HostSnapshot,
    *,
    ws_ms: float,
    bot_uptime_s: float,
    now: datetime,
    guilds: int,
    users: int,
    channels: int,
    show_user: bool,
) -> discord.Embed:
    embed = discord.Embed(
        title="Bot status",
        description=_description(snapshot),
        colour=_colour(snapshot),
        timestamp=now,
    )
    runtime = (
        f"Python {snapshot.python_version}\n"
        f"discord.py {snapshot.discord_version}\n"
        f"PID {snapshot.pid}"
    )
    fields = (
        ("Latency", _latency(ws_ms)),
        ("Bot Uptime", _uptime(bot_uptime_s)),
        ("System Uptime", _uptime(now.timestamp() - snapshot.boot_time)),
        (f"{level_dot(snapshot.cpu_percent)} CPU", _cpu(snapshot)),
        (f"{level_dot(snapshot.mem_percent)} Memory", _memory(snapshot)),
        (f"{level_dot(snapshot.disk_percent)} Disk", _disk(snapshot)),
        ("Discord", f"{guilds} guilds\n{users} users\n{channels} channels"),
        ("Runtime", runtime),
        ("Host", _host(snapshot, show_user)),
    )
    for name, value in fields:
        embed.add_field(name=name, value=_clip(value), inline=True)
    embed.set_footer(text=_clip(f"StrikerXBot · {_line(snapshot.os_name)}", 2048))
    return embed
