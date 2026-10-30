"""Duration, size, bar, and latency labels for /status."""

from bot.services.status_format import (
    format_bytes,
    format_duration,
    latency_label,
    level,
    level_dot,
    usage_bar,
)


def test_format_duration_uses_the_largest_useful_units() -> None:
    assert format_duration(45) == "45s"
    assert format_duration(7 * 60 + 13) == "7m 13s"
    assert format_duration(3600 + 25 * 60) == "1h 25m"
    assert format_duration(3 * 86400 + 4 * 3600) == "3d 4h"


def test_format_bytes_switches_at_one_gigabyte() -> None:
    assert format_bytes(512 * 1024 * 1024) == "512.0 MB"
    assert format_bytes(1024 ** 3 - 1) == "1024.0 MB"
    assert format_bytes(1024 ** 3) == "1.0 GB"
    assert format_bytes(int(1.5 * 1024 ** 3)) == "1.5 GB"


def test_usage_bar_fills_and_clamps() -> None:
    assert usage_bar(0) == "▱" * 12
    assert usage_bar(50) == ("▰" * 6) + ("▱" * 6)
    assert usage_bar(100) == "▰" * 12
    assert usage_bar(-5) == "▱" * 12
    assert usage_bar(140) == "▰" * 12


def test_level_thresholds() -> None:
    assert level(0) == "ok"
    assert level(59.9) == "ok"
    assert level(60) == "busy"
    assert level(84.9) == "busy"
    assert level(85) == "high"
    assert level_dot(10) == "🟢"
    assert level_dot(70) == "🟡"
    assert level_dot(90) == "🔴"


def test_latency_label_thresholds() -> None:
    assert latency_label(0) == "fast"
    assert latency_label(149.9) == "fast"
    assert latency_label(150) == "ok"
    assert latency_label(299.9) == "ok"
    assert latency_label(300) == "slow"
