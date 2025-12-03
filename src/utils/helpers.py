"""Различные вспомогательные функции."""

from __future__ import annotations


_SOCKET_SCHEMES = ("unix://", "tcp://", "npipe://", "http://", "https://", "ssh://")


def normalize_socket_path(raw_value: str) -> str:
    """Возвращает путь сокета с корректным префиксом unix://."""

    value = raw_value.strip()
    if not value:
        return value
    lowered = value.lower()
    if lowered.startswith(_SOCKET_SCHEMES):
        return value
    if value.startswith("/"):
        return f"unix://{value}"
    return value
