"""Утилиты чтения системных метрик при помощи psutil."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass(slots=True)
class SystemMetrics:
    """Контейнер с основными системными метриками."""

    ram: str
    cpu: str


def read_system_metrics() -> SystemMetrics:
    """Возвращает сведения об использовании RAM и CPU."""

    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    return SystemMetrics(
        ram=f"{memory.percent:.1f}% ({_format_bytes(memory.used)}/{_format_bytes(memory.total)})",
        cpu=f"{cpu_percent:.1f}%",
    )


def _format_bytes(value: float) -> str:
    """Форматирует байты в удобочитаемый вид."""

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024.0
        index += 1
    return f"{size:.1f} {units[index]}"
