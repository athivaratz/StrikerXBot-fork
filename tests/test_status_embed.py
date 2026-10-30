"""Status embed layout, without a Discord connection."""

from datetime import datetime, timezone

import discord

from bot.services.host_info import HostSnapshot
from bot.services.status_embed import build_status_embed

_USER = "only-owner-sees-this"


def _snapshot(**overrides: object) -> HostSnapshot:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    data: dict[str, object] = {
        "os_name": "Ubuntu",
        "kernel": "6.12.0",
        "arch": "x86_64",
        "board": "Test Board",
        "cpu_model": "Test CPU",
        "cpu_count": 4,
        "cpu_percent": 10.0,
        "load": (0.1, 0.2, 0.3),
        "temperature_c": 40.0,
        "mem_used": 512 * 1024 * 1024,
        "mem_total": 2 * 1024 ** 3,
        "mem_percent": 70.0,
        "bot_rss": 80 * 1024 * 1024,
        "disk_used": 1024 ** 3,
        "disk_total": 4 * 1024 ** 3,
        "disk_free": 3 * 1024 ** 3,
        "disk_percent": 90.0,
        "boot_time": now.timestamp() - (3 * 86400 + 4 * 3600),
        "python_version": "3.13.0",
        "discord_version": "2.7.1",
        "pid": 123,
        "host_user": _USER,
        "timezone": "Asia/Bangkok",
    }
    data.update(overrides)
    return HostSnapshot(**data)  # type: ignore[arg-type]


def _embed(**overrides: object) -> discord.Embed:
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    kwargs: dict[str, object] = {
        "ws_ms": 42.0,
        "bot_uptime_s": 7 * 60 + 13,
        "now": now,
        "guilds": 2,
        "users": 9,
        "channels": 14,
        "show_user": False,
    }
    kwargs.update(overrides)
    return build_status_embed(_snapshot(), **kwargs)  # type: ignore[arg-type]


def test_status_embed_names_each_field() -> None:
    embed = _embed()
    assert embed.title == "Bot status"
    assert embed.description == "Ubuntu · x86_64 · 6.12.0\nTest Board"
    assert [field.name for field in embed.fields] == [
        "Latency",
        "Bot Uptime",
        "System Uptime",
        "🟢 CPU",
        "🟡 Memory",
        "🔴 Disk",
        "Discord",
        "Runtime",
        "Host",
    ]
    assert embed.footer.text == "StrikerXBot · Ubuntu"
    values = {field.name: field.value for field in embed.fields}
    assert values["Bot Uptime"] == "7m 13s\n433s"
    assert values["System Uptime"] == "3d 4h\n273600s"
    assert "2 guilds" in values["Discord"]
    assert all(len(field.value) <= 1024 for field in embed.fields)


def test_status_embed_hides_the_host_user_unless_asked() -> None:
    hidden = _embed()
    shown = _embed(show_user=True)
    hidden_text = "\n".join(field.value for field in hidden.fields)
    shown_host = next(field.value for field in shown.fields if field.name == "Host")
    assert _USER not in hidden_text
    assert _USER not in (hidden.description or "")
    assert _USER not in (hidden.footer.text or "")
    assert _USER in shown_host
    assert "Asia/Bangkok" in shown_host


def test_status_embed_shows_na_for_a_non_finite_latency() -> None:
    embed = _embed(ws_ms=float("inf"))
    latency = next(field.value for field in embed.fields if field.name == "Latency")
    assert latency == "n/a"


def test_status_embed_clips_a_long_field() -> None:
    embed = build_status_embed(
        _snapshot(cpu_model="M" * 5000),
        ws_ms=float("nan"),
        bot_uptime_s=1,
        now=datetime(2026, 10, 30, tzinfo=timezone.utc),
        guilds=0,
        users=0,
        channels=0,
        show_user=False,
    )
    assert all(len(field.value) <= 1024 for field in embed.fields)
    latency = next(field.value for field in embed.fields if field.name == "Latency")
    assert latency == "n/a"


def test_status_embed_skips_an_unknown_board() -> None:
    embed = build_status_embed(
        _snapshot(board=None),
        ws_ms=10,
        bot_uptime_s=1,
        now=datetime(2026, 10, 30, tzinfo=timezone.utc),
        guilds=1,
        users=1,
        channels=1,
        show_user=False,
    )
    assert embed.description == "Ubuntu · x86_64 · 6.12.0"
