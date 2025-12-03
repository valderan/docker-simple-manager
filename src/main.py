"""Точка входа в приложение Docker Simple Manager."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from src import __version__
from src.app import create_application
from src.connections.manager import ConnectionManager
from src.docker_api.data_provider import DockerDataProvider
from src.projects.manager import ProjectManager
from src.settings.registry import SettingsRegistry
from src.utils.logger import configure_logging

LOGGER = logging.getLogger(__name__)


def initialize_settings(config_path: Path) -> SettingsRegistry:
    """Получает singleton реестр настроек и загружает config.json."""

    registry = SettingsRegistry(config_path=config_path)
    registry.load_from_disk()
    return registry


def setup_logging_from_settings(base_dir: Path, settings: SettingsRegistry) -> None:
    """Настраивает логирование в соответствии с LoggingSettings."""

    logging_settings = settings.get_group("logging")
    if not logging_settings.get("enabled"):
        logging.disable(logging.CRITICAL)
        return

    logging.disable(logging.NOTSET)
    configure_logging(
        log_dir=base_dir / "logs",
        level_name=logging_settings.get("level", "INFO"),
        max_bytes=logging_settings.get("max_file_size_mb", 10) * 1024 * 1024,
        backup_count=logging_settings.get("max_archived_files", 5),
    )


def initialize_workdir(base_dir: Path) -> bool:
    """Создаёт рабочую структуру (~/.dsmanager/projects, logs, connections.json)."""

    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "projects").mkdir(exist_ok=True)
        (base_dir / "logs").mkdir(exist_ok=True)
        connections_file = base_dir / "connections.json"
        if not connections_file.exists():
            connections_file.write_text(json.dumps({"connections": []}, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        LOGGER.error("Не удалось инициализировать рабочую директорию: %s", exc)
        return False


def main() -> int:
    """Основная точка входа: готовит окружение и запускает приложение."""

    home_dir = Path(os.environ.get("DSM_HOME", Path.home()))
    base_dir = home_dir / ".dsmanager"
    configure_logging(base_dir / "logs")

    settings = initialize_settings(base_dir / "config.json")
    setup_logging_from_settings(base_dir, settings)

    if not initialize_workdir(base_dir):
        return 1

    connection_manager = ConnectionManager(base_dir / "connections.json")
    project_manager = ProjectManager(base_dir / "projects", base_dir / "logs")
    docker_data_provider = DockerDataProvider(connection_manager, settings)

    LOGGER.info("Запуск Docker Simple Manager версии %s", __version__)
    app = create_application(
        settings=settings,
        connection_manager=connection_manager,
        project_manager=project_manager,
        docker_data_provider=docker_data_provider,
        workspace_dir=base_dir,
    )
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
