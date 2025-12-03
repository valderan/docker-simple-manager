"""Тесты высокоуровневого поставщика Docker-данных."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from src.connections.models import Connection
from src.docker_api import containers
from src.docker_api.data_provider import DockerDataProvider
from src.docker_api.exceptions import DockerAPIError


class DummySettings:
    """Минимальные настройки для тестов."""

    def get_value(self, group: str, key: str, default: Any = None) -> Any:
        if group == "connections" and key == "connection_timeout_sec":
            return 1
        return default


class DummyConnectionManager:
    """Минимальный менеджер соединений для тестов."""

    def __init__(self, connection: Connection | None = None) -> None:
        self._connection = connection

    def get_connection(self, identifier: str) -> Connection:
        if self._connection and self._connection.identifier == identifier:
            return self._connection
        raise KeyError(identifier)


def _make_connection() -> Connection:
    """Создаёт базовое соединение."""

    return Connection(identifier="local", name="Local", socket="unix:///var/run/docker.sock")


def test_fetch_containers_returns_empty_when_connection_missing() -> None:
    """Метод должен бросать исключение, если соединение не найдено."""

    provider = DockerDataProvider(DummyConnectionManager(connection=None), DummySettings())
    with pytest.raises(DockerAPIError):
        provider.fetch_containers("unknown")


def test_fetch_containers_uses_api(monkeypatch) -> None:
    """Метод должен проксировать вызов к docker_api.containers."""

    provider = DockerDataProvider(DummyConnectionManager(_make_connection()), DummySettings())

    def fake_create_client(self, connection_id: str) -> object:  # type: ignore[override]
        assert connection_id == "local"
        return object()

    def fake_list(client: object) -> List[Dict[str, Any]]:
        assert client is not None
        return [{"id": "abc"}]

    monkeypatch.setattr(DockerDataProvider, "_create_client", fake_create_client)
    monkeypatch.setattr(containers, "list_containers", fake_list)

    rows = provider.fetch_containers("local")
    assert rows[0]["id"] == "abc"


def test_start_container_propagates_action(monkeypatch) -> None:
    """Метод start_container возвращает True при успешной операции."""

    provider = DockerDataProvider(DummyConnectionManager(_make_connection()), DummySettings())
    fake_called: Dict[str, Any] = {}

    def fake_create_client(self, connection_id: str) -> object:  # type: ignore[override]
        return object()

    def fake_start(client: object, container_id: str) -> None:
        fake_called["container_id"] = container_id

    monkeypatch.setattr(DockerDataProvider, "_create_client", fake_create_client)
    monkeypatch.setattr(containers, "start_container", fake_start)

    assert provider.start_container("local", "demo")
    assert fake_called["container_id"] == "demo"
