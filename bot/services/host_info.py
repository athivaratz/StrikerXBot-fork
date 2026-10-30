"""Host facts for /status.

collect() is synchronous. The cog runs it in a thread so the event loop stays free.
"""

import os
import platform
from dataclasses import dataclass

import discord
import psutil

from bot.services.host_probes import (
    _cpu_model,
    _host_user,
    _load_average,
    _os_name,
    _temperature_c,
    _timezone_name,
    read_board,
)


@dataclass(frozen=True)
class HostSnapshot:
    os_name: str
    kernel: str
    arch: str
    board: str | None
    cpu_model: str
    cpu_count: int
    cpu_percent: float
    load: tuple[float, float, float] | None
    temperature_c: float | None
    mem_used: int
    mem_total: int
    mem_percent: float
    bot_rss: int
    disk_used: int
    disk_total: int
    disk_free: int
    disk_percent: float
    boot_time: float
    python_version: str
    discord_version: str
    pid: int
    host_user: str
    timezone: str


def collect() -> HostSnapshot:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    count = psutil.cpu_count() or os.cpu_count() or 1
    return HostSnapshot(
        os_name=_os_name(),
        kernel=platform.release() or "unknown",
        arch=platform.machine() or "unknown",
        board=read_board(),
        cpu_model=_cpu_model(),
        cpu_count=int(count),
        cpu_percent=float(psutil.cpu_percent(interval=None)),
        load=_load_average(),
        temperature_c=_temperature_c(),
        mem_used=int(memory.used),
        mem_total=int(memory.total),
        mem_percent=float(memory.percent),
        bot_rss=int(psutil.Process().memory_info().rss),
        disk_used=int(disk.used),
        disk_total=int(disk.total),
        disk_free=int(disk.free),
        disk_percent=float(disk.percent),
        boot_time=float(psutil.boot_time()),
        python_version=platform.python_version(),
        discord_version=discord.__version__,
        pid=os.getpid(),
        host_user=_host_user(),
        timezone=_timezone_name(),
    )
