"""Вспомогательные функции проверки Docker соединений."""

from __future__ import annotations

from typing import Any, Dict

from src.connections.models import Connection
from src.docker_api.client import DockerClientWrapper
from src.docker_api.exceptions import DockerAPIError


def get_docker_version(connection: Connection) -> str:
    """Пытается получить версию Docker."""

    client = DockerClientWrapper(connection)
    raw_client = client.get_raw_client()
    try:
        version_info: Dict[str, Any] = raw_client.version()  # pragma: no cover
        return str(version_info.get("Version", "unknown"))
    except Exception as exc:  # pragma: no cover
        raise DockerAPIError(str(exc)) from exc
