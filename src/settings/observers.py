"""Интерфейсы и базовые реализации наблюдателей за настройками."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable


@runtime_checkable
class SettingsObserver(Protocol):
    """Базовый контракт наблюдателя."""

    def on_setting_changed(
        self,
        group: str,
        key: str,
        old_value: object,
        new_value: object,
    ) -> None:
        """Обрабатывает событие изменения конкретного ключа."""


class LoggingSettingsObserver:
    """Наблюдатель, который отправляет события в журнал."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def on_setting_changed(
        self,
        group: str,
        key: str,
        old_value: object,
        new_value: object,
    ) -> None:
        self._logger.info(
            "Setting changed: %s.%s (%r -> %r)",
            group,
            key,
            old_value,
            new_value,
        )
