"""Тесты групп настроек и базового класса."""

from __future__ import annotations

import pytest

from src.settings.exceptions import SettingsNotFoundError, SettingsValidationError
from src.settings.groups import (
    AppSettings,
    ConnectionsSettings,
    HotkeysSettings,
    LoggingSettings,
    ProjectsSettings,
    ThemeSettings,
    UIStateSettings,
)


def test_app_settings_defaults_and_set() -> None:
    settings = AppSettings()
    assert settings.get("language") == "ru"
    settings.set("language", "en")
    assert settings.get("language") == "en"


def test_app_settings_invalid_value_raises() -> None:
    settings = AppSettings()
    with pytest.raises(SettingsValidationError):
        settings.set("theme", "blue")


def test_logging_settings_ranges() -> None:
    settings = LoggingSettings()
    settings.set("max_file_size_mb", 100)
    with pytest.raises(SettingsValidationError):
        settings.set("max_archived_files", 0)


def test_theme_settings_regex() -> None:
    settings = ThemeSettings()
    settings.set("primary_color_light", "#123456")
    with pytest.raises(SettingsValidationError):
        settings.set("background_dark", "not-a-color")


def test_hotkeys_settings_pattern() -> None:
    settings = HotkeysSettings()
    settings.set("open_help", "Ctrl+H")
    with pytest.raises(SettingsValidationError):
        settings.set("open_help", "🚀invalid")


def test_connections_settings_types() -> None:
    settings = ConnectionsSettings()
    settings.set("refresh_rate_ms", 2000)
    with pytest.raises(SettingsValidationError):
        settings.set("refresh_rate_ms", 100)


def test_projects_settings_defaults() -> None:
    settings = ProjectsSettings()
    assert settings.get("auto_load_projects") is True
    settings.set("auto_load_projects", False)
    assert settings.get("auto_load_projects") is False


def test_ui_state_from_dict_and_reset() -> None:
    settings = UIStateSettings()
    payload = {
        "open_tabs": [{"type": "connection", "connection_id": "local"}],
        "last_active_tab": 2,
        "dashboard_visible": False,
        "footer_visible": False,
    }
    settings.from_dict(payload)
    assert settings.get("open_tabs") == payload["open_tabs"]
    settings.reset_to_defaults()
    assert settings.get("open_tabs") == []


def test_unknown_key_raises_not_found() -> None:
    settings = AppSettings()
    with pytest.raises(SettingsNotFoundError):
        settings.get("unknown")
