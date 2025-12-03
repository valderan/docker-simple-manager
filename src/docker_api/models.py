"""Упрощённые структуры данных для описания объектов Docker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContainerSummary:
    """Минимальное представление контейнера."""

    identifier: str  # идентификатор контейнера из docker ps
