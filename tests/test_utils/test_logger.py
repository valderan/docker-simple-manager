"""Проверки подсистемы логирования."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from src.utils.logger import configure_logging, get_logger, resolve_log_level


def test_configure_logging_creates_file(tmp_path: Path) -> None:
    """После конфигурации должны появиться файлы логов и запись в них."""

    log_dir = tmp_path / "logs"
    configure_logging(log_dir, level_name="INFO", max_bytes=1024, backup_count=1)

    logger = get_logger("dsl.test")
    logger.info("log entry")
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = log_dir / "app.log"
    assert log_file.exists()
    assert "log entry" in log_file.read_text(encoding="utf-8")


def test_resolve_log_level_invalid() -> None:
    """Неизвестный уровень логирования приводит к ValueError."""

    with pytest.raises(ValueError):
        resolve_log_level("INVALID")
