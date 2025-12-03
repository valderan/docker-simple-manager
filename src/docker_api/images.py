"""Функции для работы с образами Docker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from src.docker_api.client import DockerClientWrapper


def list_images(client: DockerClientWrapper) -> List[Dict[str, Any]]:
    """Возвращает список образов (id, tags, size)."""

    raw = client.get_raw_client()
    images = []
    for image in raw.images.list():  # pragma: no cover - docker отсутствует
        attrs = getattr(image, "attrs", {})
        created = attrs.get("Created")
        size = attrs.get("Size", 0) or 0
        created_at = _format_created(created)
        images.append(
            {
                "id": image.short_id if hasattr(image, "short_id") else image.id,
                "tags": image.tags,
                "size": size,
                "created": created_at,
            }
        )
    return images


def remove_image(client: DockerClientWrapper, image_id: str, force: bool = False) -> None:
    """Удаляет образ."""

    raw = client.get_raw_client()
    raw.images.remove(image_id, force=force)  # pragma: no cover


def _format_created(value: str | None) -> str:
    """Преобразует ISO дату Docker в человекочитаемый формат."""

    if not value:
        return "N/A"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "N/A"
    now = datetime.now(timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
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
