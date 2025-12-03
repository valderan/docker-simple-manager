"""Обёртка над docker-py с безопасной инициализацией."""

from __future__ import annotations

import logging
from typing import Any, Type

from src.connections.models import Connection
from src.docker_api.exceptions import DockerAPIError

docker: Any
DockerException: Type[Exception]
try:  # pragma: no cover - docker не установлен в тестовом окружении
    import docker as _docker_module
    from docker.errors import DockerException as _DockerException

    docker = _docker_module
    DockerException = _DockerException
except ImportError:  # pragma: no cover - заглушка
    docker = None

    class _FallbackDockerException(Exception):
        """Fallback exception когда docker SDK отсутствует."""

    DockerException = _FallbackDockerException

LOGGER = logging.getLogger(__name__)


class DockerClientWrapper:
    """Управляет созданием и использованием docker API client."""

    def __init__(self, connection: Connection, raw_client: Any | None = None) -> None:
        self.connection = connection  # Сохраняем описание соединения
        self._client = raw_client or self._create_client()  # Создаём docker client

    def _create_client(self) -> Any:
        if docker is None:
            error_message = "Docker SDK not available"
            LOGGER.error(
                "Docker client init error for connection %s (%s): %s",
                self.connection.identifier,
                self.connection.name,
                error_message,
            )
            raise DockerAPIError(error_message)
        try:
            assert docker is not None
            if self.connection.type == "remote" and self.connection.ssh:
                base_url = f"ssh://{self.connection.ssh.host}"
                return docker.DockerClient(base_url=base_url)
            return docker.DockerClient(base_url=self.connection.socket)
        except DockerException as exc:
            LOGGER.error(
                "Docker client init error for connection %s (%s) via %s: %s",
                self.connection.identifier,
                self.connection.name,
                self.connection.socket,
                exc,
            )
            raise DockerAPIError(str(exc)) from exc

    def get_raw_client(self) -> Any:
        """Возвращает внутренний docker client."""

        return self._client

    def ping(self) -> bool:
        """Проверяет доступность Docker."""

        try:
            self._client.ping()
            return True
        except DockerException as exc:
            LOGGER.error("Docker ping failed: %s", exc)
            return False
