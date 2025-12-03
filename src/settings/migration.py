"""Система миграций настроек между версиями."""

from __future__ import annotations

import logging
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from src.settings.exceptions import SettingsMigrationError

MigrationFunc = Callable[[Dict[str, Any]], Dict[str, Any]]
VersionTuple = Tuple[int, int, int]


class SettingsMigration:
    """Регистратор и исполнитель миграций с поддержкой логирования и откатов."""

    _migrations: "OrderedDict[VersionTuple, MigrationFunc]" = OrderedDict()
    _logger = logging.getLogger(__name__)

    @classmethod
    def register_migration(cls, to_version: VersionTuple, func: MigrationFunc) -> None:
        cls._migrations[to_version] = func

    @classmethod
    def apply_migrations(
        cls,
        config: Dict[str, Any],
        current_version: VersionTuple,
        *,
        config_path: Path,
    ) -> Dict[str, Any]:
        backup_path = cls._create_backup(config_path)
        ordered_versions = sorted(cls._migrations.keys())
        for target_version in ordered_versions:
            if target_version > current_version:
                try:
                    config = cls._migrations[target_version](config)
                    cls._logger.info("Migration to %s applied.", target_version)
                except Exception as exc:
                    cls._logger.error("Migration to %s failed: %s", target_version, exc)
                    cls._restore_backup(config_path, backup_path)
                    raise SettingsMigrationError(
                        from_version=".".join(map(str, current_version)),
                        to_version=".".join(map(str, target_version)),
                        reason=str(exc),
                    ) from exc
        return config

    @staticmethod
    def _create_backup(config_path: Path) -> Path:
        if not config_path.exists():
            return config_path
        backup_path = config_path.with_suffix(".bak")
        shutil.copy2(config_path, backup_path)
        return backup_path

    @staticmethod
    def _restore_backup(config_path: Path, backup_path: Path) -> None:
        if backup_path.exists():
            shutil.copy2(backup_path, config_path)


def migrate_to_1_1_0(config: Dict[str, Any]) -> Dict[str, Any]:
    """Пример миграции, добавляющий раздел notifications."""

    config.setdefault(
        "notifications",
        {
            "enabled": True,
            "show_container_updates": True,
            "show_build_notifications": True,
        },
    )
    config["version"] = "1.1.0"
    config["schema_version"] = 2
    return config


SettingsMigration.register_migration((1, 1, 0), migrate_to_1_1_0)
