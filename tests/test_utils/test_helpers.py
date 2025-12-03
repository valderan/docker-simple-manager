"""Тесты вспомогательных утилит."""

from __future__ import annotations

from src.utils.helpers import normalize_socket_path


def test_normalize_socket_path_adds_unix_prefix() -> None:
    assert normalize_socket_path("/var/run/docker.sock") == "unix:///var/run/docker.sock"


def test_normalize_socket_path_keeps_existing_scheme() -> None:
    assert normalize_socket_path("unix:///var/run/docker.sock") == "unix:///var/run/docker.sock"
    assert normalize_socket_path("tcp://127.0.0.1:2375") == "tcp://127.0.0.1:2375"


def test_normalize_socket_path_keeps_relative_values() -> None:
    assert normalize_socket_path("custom-socket") == "custom-socket"
