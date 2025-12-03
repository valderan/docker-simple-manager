"""Функции для работы с томами Docker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from docker.errors import DockerException

from src.docker_api.client import DockerClientWrapper


def list_volumes(client: DockerClientWrapper) -> List[Dict[str, str | float | int]]:
    """Возвращает список томов со всеми метаданными для UI."""

    raw = client.get_raw_client()
    usage_map = _load_usage_data(raw)
    volumes = []
    for volume in raw.volumes.list():  # pragma: no cover - docker отсутствует
        attrs = getattr(volume, "attrs", {})
        volumes.append(
            {
                "name": volume.name,
                "driver": attrs.get("Driver"),
                "mountpoint": attrs.get("Mountpoint"),
                "created": _format_created(attrs.get("CreatedAt")),
                "size": usage_map.get(volume.name, 0),
            }
        )
    return volumes


def remove_volume(client: DockerClientWrapper, name: str, force: bool = False) -> None:
    """Удаляет том."""

    raw = client.get_raw_client()
    raw.volumes.get(name).remove(force=force)  # pragma: no cover


def _load_usage_data(raw_client: Any) -> Dict[str, int]:
    """Возвращает словарь размеров томов."""

    usage: Dict[str, int] = {}
    try:
        df_data = raw_client.api.df()
    except (DockerException, AttributeError):  # pragma: no cover - зависит от окружения
        return usage
    for item in df_data.get("Volumes") or []:
        name = item.get("Name")
        usage_data = item.get("UsageData") or {}
        if name:
            usage[name] = usage_data.get("Size", 0) or 0
    return usage


def _format_created(value: str | None) -> str:
    """Приводит дату создания тома к дружелюбному виду."""

    if not value:
        return "N/A"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return "N/A"
    now = datetime.now(timezone.utc)
    delta = now - timestamp
    days = delta.days
    if days < 1:
        return "just now"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    if months == 1:
        return "1 month ago"
    return f"{months} months ago"
