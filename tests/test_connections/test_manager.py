"""Тесты класса ConnectionManager."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.connections.manager import ConnectionManager
from src.connections.models import Connection, ConnectionStatus


def make_connection(identifier: str = "local") -> Connection:
    return Connection(identifier=identifier, name="Local", socket="unix:///var/run/docker.sock")


def test_add_and_load_connection(tmp_path: Path) -> None:
    file_path = tmp_path / "connections.json"
    manager = ConnectionManager(file_path)
    assert manager.list_connections() == []

    connection = make_connection()
    manager.add_connection(connection)

    loaded = ConnectionManager(file_path)
    assert len(loaded.list_connections()) == 1
    assert loaded.get_connection("local").name == "Local"


def test_update_and_delete(tmp_path: Path) -> None:
    manager = ConnectionManager(tmp_path / "connections.json")
    connection = make_connection()
    manager.add_connection(connection)

    updated = Connection(identifier="local", name="New name", socket="unix:///var/run/docker.sock")
    manager.update_connection(updated)
    assert manager.get_connection("local").name == "New name"

    manager.delete_connection("local")
    assert manager.list_connections() == []


def test_set_status_and_test_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ConnectionManager(tmp_path / "connections.json")
    connection = make_connection()
    manager.add_connection(connection)

    manager.set_status("local", ConnectionStatus.OFFLINE)
    assert manager.get_connection("local").status == ConnectionStatus.OFFLINE

    monkeypatch.setattr(
        "src.connections.manager.get_docker_version",
        lambda conn: "24.0",
    )
    status = manager.test_connection("local")
    assert status == ConnectionStatus.ONLINE


def test_add_duplicate_raises(tmp_path: Path) -> None:
    manager = ConnectionManager(tmp_path / "connections.json")
    manager.add_connection(make_connection())
    with pytest.raises(ValueError):
        manager.add_connection(make_connection())
