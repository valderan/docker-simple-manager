"""Тесты пользовательских исключений подсистемы настроек."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.settings.exceptions import (
    SettingsIOError,
    SettingsMigrationError,
    SettingsNotFoundError,
    SettingsValidationError,
)


class TestSettingsNotFoundError:
    """Проверяет формирование сообщений для отсутствующих ключей."""

    def test_error_message_and_logging(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("ERROR")
        error = SettingsNotFoundError("app", "language")
        assert str(error) == "Setting 'app.language' not found"
        assert "app.language" in caplog.text


class TestSettingsValidationError:
    """Проверяет валидационные ошибки."""

    def test_contains_reason_and_value(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("ERROR")
        error = SettingsValidationError("logging.level", "INVALID", "unknown level")
        assert error.key == "logging.level"
        assert error.value == "INVALID"
        assert error.reason == "unknown level"
        assert "unknown level" in str(error)
        assert "INVALID" in caplog.text


class TestSettingsMigrationError:
    """Проверяет сообщения миграционных ошибок."""

    def test_contains_versions(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("ERROR")
        error = SettingsMigrationError("1.0.0", "1.1.0", "test failure")
        assert "1.0.0" in str(error)
        assert "1.1.0" in str(error)
        assert "test failure" in caplog.text


class TestSettingsIOError:
    """Проверяет ошибки ввода-вывода."""

    def test_contains_path(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("ERROR")
        fake_path = tmp_path / "config.json"
        error = SettingsIOError(fake_path, "permission denied")
        assert str(fake_path) in str(error)
        assert "permission denied" in caplog.text
