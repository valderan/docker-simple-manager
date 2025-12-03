"""Тесты полноценного SettingsRegistry."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pytest

from src.settings.exceptions import SettingsNotFoundError, SettingsValidationError
from src.settings.registry import SettingsRegistry


class DummyObserver:
    """Простой наблюдатель для проверки уведомлений."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, str, object, object]] = []

    def on_setting_changed(
        self, group: str, key: str, old_value: object, new_value: object
    ) -> None:
        self.events.append((group, key, old_value, new_value))


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.json"


@pytest.fixture
def registry(config_path: Path) -> SettingsRegistry:
    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    registry = SettingsRegistry(config_path)
    registry.reset_to_defaults()
    yield registry
    SettingsRegistry._instance = None  # type: ignore[attr-defined]


def test_singleton_instance(registry: SettingsRegistry) -> None:
    another = SettingsRegistry()
    assert registry is another


def test_get_and_set_value(registry: SettingsRegistry) -> None:
    registry.set_value("app", "language", "en")
    assert registry.get_value("app", "language") == "en"


def test_get_value_with_default(registry: SettingsRegistry) -> None:
    assert registry.get_value("app", "unknown", default="fallback") == "fallback"


def test_set_value_invalid_raises(registry: SettingsRegistry) -> None:
    with pytest.raises(SettingsValidationError):
        registry.set_value("app", "language", "de")


def test_unknown_group_raises(registry: SettingsRegistry) -> None:
    with pytest.raises(SettingsNotFoundError):
        registry.get_value("unknown", "key")


def test_save_and_load_persists_data(config_path: Path, registry: SettingsRegistry) -> None:
    registry.set_value("app", "language", "en")
    registry.save_to_disk()

    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    loaded = SettingsRegistry(config_path)
    loaded.load_from_disk()
    assert loaded.get_value("app", "language") == "en"


def test_load_creates_defaults_if_missing(tmp_path: Path) -> None:
    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    config_path = tmp_path / "missing.json"
    registry = SettingsRegistry(config_path)
    registry.load_from_disk()
    assert config_path.exists()


def test_observer_notification(registry: SettingsRegistry) -> None:
    observer = DummyObserver()
    registry.register_observer(observer)
    registry.set_value("app", "language", "en")
    assert observer.events[-1] == ("app", "language", "ru", "en")


def test_export_import_roundtrip(tmp_path: Path, registry: SettingsRegistry) -> None:
    export_path = tmp_path / "export.json"
    registry.set_value("logging", "level", "DEBUG")
    registry.export_to_json(export_path)

    registry.set_value("logging", "level", "INFO")
    registry.import_from_json(export_path)
    assert registry.get_value("logging", "level") == "DEBUG"
