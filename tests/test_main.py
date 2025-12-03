"""Тесты вспомогательных функций модуля main."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.main import initialize_workdir, setup_logging_from_settings
from src.settings.groups import LoggingSettings


class DummySettings:
    def __init__(self, enabled: bool = True, level: str = "INFO") -> None:
        self.logging = LoggingSettings()
        self.logging.set("enabled", enabled)
        self.logging.set("level", level)

    def get_group(self, name: str):  # type: ignore[override]
        if name == "logging":
            return self.logging
        raise KeyError(name)


def test_initialize_workdir_creates_structure(tmp_path: Path) -> None:
    assert initialize_workdir(tmp_path)
    assert (tmp_path / "projects").exists()
    connections = json.loads((tmp_path / "connections.json").read_text(encoding="utf-8"))
    assert connections == {"connections": []}


def test_setup_logging_enabled_creates_log(tmp_path: Path) -> None:
    logging.disable(logging.NOTSET)
    settings = DummySettings(enabled=True, level="INFO")
    setup_logging_from_settings(tmp_path, settings)
    logger = logging.getLogger("test")
    logger.info("log entry")
    for handler in logging.getLogger().handlers:
        handler.flush()
    log_file = tmp_path / "logs" / "app.log"
    assert log_file.exists()
    assert "log entry" in log_file.read_text(encoding="utf-8")


def test_setup_logging_disabled(tmp_path: Path) -> None:
    logging.disable(logging.NOTSET)
    settings = DummySettings(enabled=False)
    setup_logging_from_settings(tmp_path, settings)
    assert logging.root.manager.disable >= logging.CRITICAL
    logging.disable(logging.NOTSET)
