"""Менеджер соединений Docker: загрузка, CRUD и проверка."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.connections.docker_client import get_docker_version
from src.connections.models import Connection, ConnectionStatus, SSHConfig
from src.utils.helpers import normalize_socket_path


class ConnectionManager:
    """Работает со списком соединений (загрузка/сохранение, CRUD, статус)."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._logger = logging.getLogger(__name__)
        self._connections: Dict[str, Connection] = {}
        self.load_from_disk()

    # ------------------------------------------------------------------ CRUD --
    def list_connections(self) -> List[Connection]:
        """Возвращает список всех соединений."""

        return list(self._connections.values())

    def list_active_connections(self) -> List[Connection]:
        """Возвращает только активные соединения."""

        return [connection for connection in self._connections.values() if connection.is_active]

    def get_connection(self, identifier: str) -> Connection:
        """Ищет соединение по идентификатору."""

        try:
            return self._connections[identifier]
        except KeyError:
            raise KeyError(f"Connection '{identifier}' not found") from None

    def add_connection(self, connection: Connection) -> None:
        """Добавляет новое соединение."""

        if connection.identifier in self._connections:
            raise ValueError(f"Connection '{connection.identifier}' already exists")
        self._connections[connection.identifier] = connection
        self.save_to_disk()

    def update_connection(self, connection: Connection) -> None:
        """Обновляет существующее соединение."""

        if connection.identifier not in self._connections:
            raise KeyError(f"Connection '{connection.identifier}' not found")
        self._connections[connection.identifier] = connection
        self.save_to_disk()

    def delete_connection(self, identifier: str) -> None:
        """Удаляет соединение, если оно существует."""

        if identifier in self._connections:
            self._connections.pop(identifier)
            self.save_to_disk()

    def activate_connection(self, identifier: str) -> None:
        """Отмечает соединение как активное."""

        connection = self.get_connection(identifier)
        if connection.is_active:
            return
        connection.is_active = True
        connection.last_used = datetime.now(UTC).isoformat()
        self.save_to_disk()

    def deactivate_connection(self, identifier: str) -> None:
        """Деактивирует соединение и сбрасывает статус."""

        connection = self.get_connection(identifier)
        if not connection.is_active:
            return
        connection.is_active = False
        connection.status = ConnectionStatus.OFFLINE
        self.save_to_disk()

    # ------------------------------------------------------------- persistence --
    def load_from_disk(self) -> None:
        """Загружает connections.json, создаёт файл при отсутствии."""

        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(json.dumps({"connections": []}, indent=2), encoding="utf-8")
            self._connections.clear()
            return

        content: Dict[str, Any] = json.loads(self._file_path.read_text(encoding="utf-8"))
        loaded: Dict[str, Connection] = {}
        for entry in content.get("connections", []):
            connection = self._connection_from_dict(entry)
            loaded[connection.identifier] = connection
        self._connections = loaded

    def save_to_disk(self) -> None:
        """Сериализует текущие соединения в JSON."""

        payload = {
            "connections": [connection.to_dict() for connection in self._connections.values()],
        }
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -------------------------------------------------------------- operations --
    def set_status(self, identifier: str, status: ConnectionStatus) -> None:
        """Проставляет статус соединения."""

        connection = self.get_connection(identifier)
        connection.status = status
        self.save_to_disk()

    def test_connection(self, identifier: str) -> ConnectionStatus:
        """Пытается выполнить тест соединения через docker client."""

        connection = self.get_connection(identifier)
        try:
            _ = get_docker_version(connection)
            connection.status = ConnectionStatus.ONLINE
            connection.last_used = datetime.now(UTC).isoformat()
        except Exception as exc:  # pragma: no cover - реального подключения пока нет
            self._logger.error(
                "Connection %s (%s) test failed: %s",
                identifier,
                connection.name,
                exc,
            )
            connection.status = ConnectionStatus.OFFLINE
        self.save_to_disk()
        return connection.status

    # ----------------------------------------------------------------- helpers --
    def _connection_from_dict(self, data: Dict[str, Any]) -> Connection:
        ssh_data = data.get("ssh")
        ssh: Optional[SSHConfig] = None
        if isinstance(ssh_data, dict):
            ssh = SSHConfig(
                host=ssh_data.get("host", ""),
                port=ssh_data.get("port", 22),
                username=ssh_data.get("username", "root"),
                password=ssh_data.get("password"),
                key_path=ssh_data.get("key_path"),
            )
        conn_type = data.get("type", "local")
        socket_value = data.get("socket", "")
        if conn_type != "remote":
            socket_value = normalize_socket_path(socket_value)
        status_str = data.get("status", ConnectionStatus.UNKNOWN.value)
        status = (
            ConnectionStatus(status_str)
            if status_str in ConnectionStatus._value2member_map_
            else ConnectionStatus.UNKNOWN
        )
        identifier = data.get("id") or data.get("identifier")
        if not identifier:
            raise ValueError("Connection id is required")
        return Connection(
            identifier=identifier,
            name=data.get("name", ""),
            socket=socket_value,
            type=conn_type,
            ssh=ssh,
            comment=data.get("comment", ""),
            status=status,
            version=data.get("version", 1),
            is_active=data.get("is_active", False),
            created_at=data.get("created_at"),
            last_used=data.get("last_used"),
        )
