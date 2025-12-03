"""Исключения, относящиеся к взаимодействию с Docker API."""

from __future__ import annotations


class DockerAPIError(Exception):
    """Базовое исключение для ошибок Docker."""
