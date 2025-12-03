"""Проверки механизма наблюдателей за настройками."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.settings.registry import SettingsRegistry
from src.settings.observers import LoggingSettingsObserver


class DummyObserver:
    def __init__(self) -> None:
        self.triggered = False
        self.payload = None

    def on_setting_changed(
        self, group: str, key: str, old_value: object, new_value: object
    ) -> None:
        self.triggered = True
        self.payload = (group, key, old_value, new_value)


class FailingObserver:
    def __init__(self) -> None:
        self.counter = 0

    def on_setting_changed(
        self, group: str, key: str, old_value: object, new_value: object
    ) -> None:
        self.counter += 1
        raise RuntimeError("observer failed")


@pytest.fixture
def registry(tmp_path: Path) -> SettingsRegistry:
    SettingsRegistry._instance = None  # type: ignore[attr-defined]
    config_path = tmp_path / "config.json"
    reg = SettingsRegistry(config_path)
    reg.reset_to_defaults()
    yield reg
    SettingsRegistry._instance = None  # type: ignore[attr-defined]


def test_observer_receives_event(registry: SettingsRegistry) -> None:
    observer = DummyObserver()
    registry.register_observer(observer)
    registry.set_value("app", "language", "en")
    assert observer.triggered
    assert observer.payload == ("app", "language", "ru", "en")


def test_unregister_observer(registry: SettingsRegistry) -> None:
    observer = DummyObserver()
    registry.register_observer(observer)
    registry.unregister_observer(observer)
    registry.set_value("app", "language", "en")
    assert observer.triggered is False


def test_failing_observer_does_not_block_others(registry: SettingsRegistry) -> None:
    failing = FailingObserver()
    observer = DummyObserver()
    registry.register_observer(failing)
    registry.register_observer(observer)
    registry.set_value("app", "language", "en")
    assert observer.triggered is True
    assert failing.counter == 1


def test_logging_observer_does_not_raise(
    registry: SettingsRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO")
    observer = LoggingSettingsObserver()
    registry.register_observer(observer)
    registry.set_value("app", "language", "en")
    assert any("Setting changed" in record.message for record in caplog.records)
