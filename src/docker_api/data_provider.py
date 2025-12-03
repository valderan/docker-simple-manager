"""Менеджер доступа к данным Docker для интерфейса.

Файл описывает класс, который объединяет `ConnectionManager` и функции из
`src.docker_api` для безопасного получения списков контейнеров, образов,
томов и сборок, а также для выполнения базовых действий (start/stop/remove).
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, List, Optional

from src.connections.manager import ConnectionManager
from src.connections.models import Connection
from src.docker_api import builds, containers, images, volumes
from src.docker_api.client import DockerClientWrapper
from src.docker_api.exceptions import DockerAPIError
from src.settings.registry import SettingsRegistry

LOGGER = logging.getLogger(__name__)


class DockerDataProvider:
    """Предоставляет высокоуровневый API для работы с Docker-данными."""

    def __init__(self, connection_manager: ConnectionManager, settings: SettingsRegistry) -> None:
        self._connection_manager = connection_manager
        self._settings = settings

    # ------------------------------------------------------------------ helpers
    def _get_connection(self, connection_id: str) -> Optional[Connection]:
        """Возвращает объект соединения или None, если идентификатор неверен."""

        try:
            return self._connection_manager.get_connection(connection_id)
        except KeyError:
            LOGGER.error("Connection %s not found", connection_id)
            return None

    def _create_client(self, connection_id: str) -> DockerClientWrapper:
        """Создаёт Docker client для указанного соединения."""

        connection = self._get_connection(connection_id)
        if connection is None:
            error_message = f"Connection {connection_id} not found"
            LOGGER.error("Docker client creation aborted: %s", error_message)
            raise DockerAPIError(error_message)

        timeout_enabled = bool(
            self._settings.get_value("connections", "connection_timeout_enabled", default=True)
        )
        timeout = int(self._settings.get_value("connections", "connection_timeout_sec", default=5))
        if not timeout_enabled or timeout <= 0:
            return DockerClientWrapper(connection)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(DockerClientWrapper, connection)
            try:
                return future.result(timeout=timeout)
            except TimeoutError as exc:
                future.cancel()
                LOGGER.error(
                    "Docker client creation timeout for connection %s (%s) after %s seconds",
                    connection.identifier,
                    connection.name,
                    timeout,
                )
                raise DockerAPIError(f"Connection timeout after {timeout} seconds") from exc

    # ------------------------------------------------------------------- fetches
    def fetch_containers(self, connection_id: str) -> List[Dict[str, Any]]:
        """Возвращает список контейнеров для соединения."""

        client = self._create_client(connection_id)
        return containers.list_containers(client)

    def fetch_images(self, connection_id: str) -> List[Dict[str, Any]]:
        """Возвращает список образов."""

        client = self._create_client(connection_id)
        return images.list_images(client)

    def fetch_volumes(self, connection_id: str) -> List[Dict[str, Any]]:
        """Возвращает список томов."""

        client = self._create_client(connection_id)
        return volumes.list_volumes(client)

    def fetch_builds(self, connection_id: str) -> List[Dict[str, Any]]:
        """Возвращает историю сборок."""

        client = self._create_client(connection_id)
        env = self.build_cli_env(connection_id)
        return builds.list_builds(client, env=env)

    # ---------------------------------------------------------------- operations
    def start_container(self, connection_id: str, container_id: str) -> bool:
        """Запускает контейнер и возвращает True в случае успеха."""

        client = self._create_client(connection_id)
        try:
            containers.start_container(client, container_id)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot start container %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return False

    def stop_container(self, connection_id: str, container_id: str) -> bool:
        """Останавливает контейнер."""

        client = self._create_client(connection_id)
        try:
            containers.stop_container(client, container_id)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot stop container %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return False

    def pause_container(self, connection_id: str, container_id: str) -> bool:
        """Ставит контейнер на паузу."""

        client = self._create_client(connection_id)
        try:
            containers.pause_container(client, container_id)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot pause container %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return False

    def restart_container(self, connection_id: str, container_id: str) -> bool:
        """Перезапускает контейнер."""

        client = self._create_client(connection_id)
        try:
            containers.restart_container(client, container_id)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot restart container %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return False

    def remove_container(
        self, connection_id: str, container_id: str, *, force: bool = False
    ) -> bool:
        """Удаляет контейнер."""

        client = self._create_client(connection_id)
        try:
            containers.remove_container(client, container_id, force=force)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot remove container %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return False

    def remove_image(self, connection_id: str, image_id: str, force: bool = False) -> bool:
        """Удаляет Docker-образ."""

        client = self._create_client(connection_id)
        try:
            images.remove_image(client, image_id, force=force)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot remove image %s on connection %s: %s",
                image_id,
                connection_id,
                exc,
            )
            return False

    def remove_volume(self, connection_id: str, volume_name: str, force: bool = False) -> bool:
        """Удаляет том."""

        client = self._create_client(connection_id)
        try:
            volumes.remove_volume(client, volume_name, force=force)
            return True
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot remove volume %s on connection %s: %s",
                volume_name,
                connection_id,
                exc,
            )
            return False

    def fetch_container_logs(self, connection_id: str, container_id: str, tail: int = 500) -> str:
        """Возвращает логи контейнера."""

        client = self._create_client(connection_id)
        try:
            return containers.fetch_logs(client, container_id, tail=tail)
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot fetch logs for %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return ""

    def inspect_container(self, connection_id: str, container_id: str) -> Dict[str, Any]:
        """Возвращает результат docker inspect."""

        client = self._create_client(connection_id)
        try:
            return containers.inspect_container(client, container_id)
        except DockerAPIError as exc:
            LOGGER.error(
                "Cannot inspect %s on connection %s: %s",
                container_id,
                connection_id,
                exc,
            )
            return {}

    # -------------------------------------------------------------- CLI helpers
    def build_cli_env(self, connection_id: str | None) -> Dict[str, str]:
        """Формирует окружение для docker CLI с учётом соединения."""

        env = os.environ.copy()
        if not connection_id:
            return env
        connection = self._get_connection(connection_id)
        if connection is None:
            return env
        host = self._resolve_docker_host(connection)
        if host:
            env["DOCKER_HOST"] = host
        if connection.type == "remote" and connection.ssh and connection.ssh.key_path:
            env["DOCKER_SSH_IDENTITY"] = connection.ssh.key_path
        return env

    def _resolve_docker_host(self, connection: Connection) -> str | None:
        """Возвращает строку для переменной DOCKER_HOST."""

        if connection.socket:
            return connection.socket
        if connection.type == "remote" and connection.ssh:
            user = connection.ssh.username or "root"
            host = connection.ssh.host
            port = connection.ssh.port or 22
            return f"ssh://{user}@{host}:{port}"
        return None
