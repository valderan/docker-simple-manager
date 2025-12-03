"""Вспомогательные функции для продвинутой настройки логирования."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final, cast

LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def resolve_log_level(level_name: str) -> int:
    """Преобразует строковый уровень логирования в числовой."""

    try:
        return cast(int, getattr(logging, level_name.upper()))
    except AttributeError as exc:  # pragma: no cover - защитный код
        raise ValueError(f"Unknown log level: {level_name}") from exc


def configure_logging(
    log_dir: Path,
    *,
    log_file_name: str = "app.log",
    level_name: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Создаёт конфигурацию логирования с ротацией файлов и выводом в консоль."""

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file_name
    log_level = resolve_log_level(level_name)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, stream_handler],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Удобная обёртка над logging.getLogger."""

    return logging.getLogger(name)
