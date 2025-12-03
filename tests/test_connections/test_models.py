"""Тесты моделей данных для соединений."""

from __future__ import annotations

from src.connections.models import Connection, ConnectionStatus, SSHConfig


def test_connection_defaults() -> None:
    conn = Connection(identifier="1", name="Local", socket="unix:///var/run/docker.sock")
    assert conn.status == ConnectionStatus.UNKNOWN
    assert conn.is_active is False


def test_connection_with_ssh() -> None:
    ssh = SSHConfig(host="example.com", username="ubuntu", key_path="~/.ssh/id_rsa")
    conn = Connection(
        identifier="remote",
        name="Remote",
        socket="unix:///var/run/docker.sock",
        type="remote",
        ssh=ssh,
    )
    data = conn.to_dict()
    assert data["type"] == "remote"
    assert data["ssh"]["host"] == "example.com"


def test_connection_status_enum() -> None:
    assert ConnectionStatus.ONLINE.value == "online"
    assert str(ConnectionStatus.OFFLINE) == "ConnectionStatus.OFFLINE"
