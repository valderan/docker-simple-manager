"""Тесты системы миграций настроек."""

from __future__ import annotations

from pathlib import Path

import json

import pytest

from src.settings.migration import SettingsMigration
from src.settings.registry import SettingsRegistry


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.json"


def test_migration_applied_when_version_outdated(config_path: Path) -> None:
    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    config = {
        "version": "0.9.0",
        "schema_version": 1,
        "app": {"language": "ru"},
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    registry = SettingsRegistry(config_path)
    registry.load_from_disk()

    migrated_value = registry.get_value("app", "language")
    assert migrated_value == "ru"
    metadata_notifications = registry._metadata.get("notifications")  # type: ignore[attr-defined]
    assert metadata_notifications is not None
    assert metadata_notifications["enabled"] is True


def test_migration_failure_restores_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.9.0",
        "schema_version": 1,
        "app": {"language": "ru"},
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    def failing_migration(data: dict) -> dict:
        raise RuntimeError("boom")

    SettingsMigration.register_migration((9, 9, 9), failing_migration)

    registry = SettingsRegistry(config_path)
    with pytest.raises(Exception):
        registry.load_from_disk()

    backup_path = config_path.with_suffix(".bak")
    assert backup_path.exists()
