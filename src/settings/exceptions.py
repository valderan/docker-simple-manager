"""Пользовательские исключения подсистемы настроек."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)


class SettingsError(Exception):
    """Базовое исключение для любых ошибок настроек с поддержкой контекста."""

    def __init__(self, message: str, *, context: Optional[Dict[str, Any]] = None) -> None:
        """Сохраняет сообщение и контекст, логируя ошибку."""

        self.message = message
        self.context = context or {}
        super().__init__(message)
        LOGGER.error("%s | context=%s", message, self.context)


class SettingsNotFoundError(SettingsError):
    """Возникает, когда нужный ключ/группа отсутствуют."""

    def __init__(self, group: str, key: Optional[str] = None) -> None:
        suffix = f".{key}" if key else ""
        super().__init__(
            f"Setting '{group}{suffix}' not found",
            context={"group": group, "key": key},
        )


class SettingsValidationError(SettingsError):
    """Сигнализирует о некорректных входных данных при валидации."""

    def __init__(self, key: str, value: Any, reason: str) -> None:
        self.key = key
        self.value = value
        self.reason = reason
        super().__init__(
            f"Validation error for '{key}': {reason} (value={value!r})",
            context={"key": key, "value": value, "reason": reason},
        )


class SettingsMigrationError(SettingsError):
    """Используется при сбоях в миграции конфигурации."""

    def __init__(self, from_version: str, to_version: str, reason: str) -> None:
        super().__init__(
            f"Failed to migrate config {from_version} -> {to_version}: {reason}",
            context={
                "from_version": from_version,
                "to_version": to_version,
                "reason": reason,
            },
        )


class SettingsIOError(SettingsError):
    """Поднимается при ошибках чтения/записи config.json."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(
            f"I/O error with settings file '{path}': {reason}",
            context={"path": str(path), "reason": reason},
        )
