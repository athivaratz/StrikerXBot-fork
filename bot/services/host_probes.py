"""Small host probes. Each one returns a fallback when the source is missing."""

import getpass
import os
import platform
import time
from pathlib import Path

import psutil

_BOARD_PATHS: tuple[Path, ...] = (
    Path("/sys/firmware/devicetree/base/model"),
    Path("/sys/class/dmi/id/product_name"),
)
_CPUINFO = Path("/proc/cpuinfo")
_THERMAL = Path("/sys/class/thermal/thermal_zone0/temp")
_LOCALTIME = Path("/etc/localtime")
_ETC_TIMEZONE = Path("/etc/timezone")
_CPU_KEYS = ("model name", "Model")


def _text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    text = raw.replace(b"\x00", b"").decode("utf-8", errors="replace").strip()
    return text or None


def read_os_name() -> str:
    try:
        name = platform.freedesktop_os_release()["PRETTY_NAME"].strip()
    except (OSError, KeyError):
        name = platform.system().strip()
    return name or "unknown"


def read_board(paths: tuple[Path, ...] = _BOARD_PATHS) -> str | None:
    """Tests pass temp paths. The defaults are the usual Linux board files."""
    for path in paths:
        found = _text(path)
        if found:
            return found
    return None


def read_cpu_model() -> str:
    text = _text(_CPUINFO) or ""
    found: dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        name = key.strip()
        model = value.strip()
        if name in _CPU_KEYS and model and name not in found:
            found[name] = model
    for name in _CPU_KEYS:
        if name in found:
            return found[name]
    return platform.processor().strip() or "unknown"


def read_load_average() -> tuple[float, float, float] | None:
    try:
        one, five, fifteen = os.getloadavg()
    except (OSError, AttributeError):
        return None
    return (float(one), float(five), float(fifteen))


def read_temperature_c() -> float | None:
    try:
        groups = psutil.sensors_temperatures()
    except (AttributeError, OSError, NotImplementedError):
        groups = {}
    for entries in groups.values():
        for entry in entries:
            if entry.current is not None:
                return float(entry.current)
    raw = _text(_THERMAL)
    if raw is None:
        return None
    try:
        return float(raw) / 1000.0
    except ValueError:
        return None


def read_timezone() -> str:
    try:
        target = os.readlink(_LOCALTIME)
    except OSError:
        target = ""
    marker = "zoneinfo/"
    if marker in target:
        zone = target.split(marker, 1)[1].strip()
        if zone:
            return zone
    text = _text(_ETC_TIMEZONE)
    if text:
        return text.splitlines()[0].strip()
    if time.tzname and time.tzname[0]:
        return time.tzname[0]
    return "unknown"


def read_host_user() -> str:
    try:
        name = getpass.getuser().strip()
    except OSError:
        return "unknown"
    return name or "unknown"
