"""Централизованное описание путей приложения."""

from __future__ import annotations

from pathlib import Path


# CONFIG_DIR — базовая директория, где сохраняются настройки и логи
CONFIG_DIR = Path.home() / ".dsmanager"
