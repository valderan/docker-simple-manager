"""Модели данных для описания соединений Docker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ConnectionStatus(str, Enum):
    """Статусы доступности соединения."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class SSHConfig:
    """Параметры SSH подключения."""

    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует конфигурацию в словарь."""

        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "key_path": self.key_path,
        }


@dataclass(slots=True)
class Connection:
    """Полное описание одного подключения к Docker."""

    identifier: str
    name: str
    socket: str
    type: str = "local"  # local или remote
    ssh: Optional[SSHConfig] = None
    comment: str = ""
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    version: int = 1
    is_active: bool = False
    created_at: Optional[str] = None
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует модель в dict."""

        return {
            "id": self.identifier,
            "name": self.name,
            "type": self.type,
            "socket": self.socket,
            "ssh": self.ssh.to_dict() if self.ssh else None,
            "comment": self.comment,
            "status": self.status.value,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_used": self.last_used,
        }
