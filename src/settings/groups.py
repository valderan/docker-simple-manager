"""Классы групп настроек с полной поддержкой валидации."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from src.settings.exceptions import SettingsNotFoundError, SettingsValidationError
from src.settings.validators import (
    CompositeValidator,
    EnumValidator,
    RangeValidator,
    RegexValidator,
    TypeValidator,
    Validator,
)

HEX_PATTERN = r"^#[0-9a-fA-F]{6}$"
HOTKEY_PATTERN = r"^[A-Za-z0-9\+\-\s]+$"


class SettingsGroup(ABC):
    """Абстрактная база для конкретных групп настроек."""

    group_name: str = ""

    def __init__(self) -> None:
        self._defaults: Dict[str, Any] = {}
        self._validators: Dict[str, Validator] = {}
        self._values: Dict[str, Any] = {}
        self._initialize_defaults()
        self._setup_validators()
        self.reset_to_defaults()

    @abstractmethod
    def _initialize_defaults(self) -> None:
        """Задаёт значения по умолчанию для группы."""

    @abstractmethod
    def _setup_validators(self) -> None:
        """Привязывает валидаторы к ключам группы."""

    def keys(self) -> Tuple[str, ...]:
        """Возвращает доступные ключи группы."""

        return tuple(self._defaults.keys())

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки."""

        if key not in self._defaults:
            raise SettingsNotFoundError(self.group_name, key)
        return self._values.get(key, default)

    def validate(self, key: str, value: Any) -> Tuple[bool, str]:
        """Применяет соответствующий валидатор и возвращает результат."""

        validator = self._validators.get(key)
        if not validator:
            return True, ""
        return validator.validate(value)

    def set(self, key: str, value: Any) -> None:
        """Сохраняет значение, выбрасывая ошибку при невалидных данных."""

        if key not in self._defaults:
            raise SettingsNotFoundError(self.group_name, key)
        is_valid, error = self.validate(key, value)
        if not is_valid:
            raise SettingsValidationError(
                key=f"{self.group_name}.{key}",
                value=value,
                reason=error,
            )
        self._values[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Возвращает копию всех значений."""

        return dict(self._values)

    def get_default(self, key: str) -> Any:
        """Возвращает значение по умолчанию для конкретного ключа."""

        if key not in self._defaults:
            raise SettingsNotFoundError(self.group_name, key)
        return self._defaults[key]

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Заполняет значениями из словаря (использует set для валидации)."""

        for key, value in data.items():
            if key in self._defaults:
                self.set(key, value)

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает простую схему с типом и дефолтом."""

        schema: Dict[str, Dict[str, Any]] = {}
        for key, default in self._defaults.items():
            schema[key] = {
                "type": type(default).__name__,
                "default": default,
            }
        return schema

    def reset_to_defaults(self) -> None:
        """Сбрасывает значения группы к дефолтным."""

        self._values = dict(self._defaults)


class AppSettings(SettingsGroup):
    """Группа базовых настроек приложения."""

    group_name = "app"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "language": "ru",
            "theme": "system",
            "window_width": 1920,
            "window_height": 1080,
            "window_x": 0,
            "window_y": 0,
            "window_maximized": True,
            "save_window_state": True,
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "language": EnumValidator(["ru", "en"]),
            "theme": EnumValidator(["light", "dark", "system"]),
            "window_width": RangeValidator(800, 10000),
            "window_height": RangeValidator(600, 10000),
            "window_x": RangeValidator(-10000, 10000),
            "window_y": RangeValidator(-10000, 10000),
            "window_maximized": TypeValidator(bool),
            "save_window_state": TypeValidator(bool),
        }


class LoggingSettings(SettingsGroup):
    """Настройки логирования приложения."""

    group_name = "logging"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "enabled": True,
            "level": "INFO",
            "max_file_size_mb": 10,
            "max_archived_files": 5,
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "enabled": TypeValidator(bool),
            "level": EnumValidator(["DEBUG", "INFO", "WARNING", "ERROR"]),
            "max_file_size_mb": RangeValidator(1, 1000),
            "max_archived_files": RangeValidator(1, 50),
        }


class ThemeSettings(SettingsGroup):
    """Настройки цветовых схем."""

    group_name = "theme"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "primary_color_light": "#218094",
            "primary_color_dark": "#32b8c6",
            "background_light": "#fcfcf9",
            "background_dark": "#1f2121",
            "text_light": "#134252",
            "text_dark": "#f5f5f5",
            "border_color_light": "#5e5240",
            "border_color_dark": "#777c7c",
            "table_background_light": "#ffffff",
            "table_background_dark": "#2b2d30",
            "table_alternate_background_light": "#f5f1ea",
            "table_alternate_background_dark": "#25272a",
            "table_selection_background_light": "#d2edf4",
            "table_selection_background_dark": "#3a505a",
            "table_selection_text_light": "#134252",
            "table_selection_text_dark": "#f5f5f5",
            "accent_success": "#208094",
            "accent_error": "#c01547",
            "accent_warning": "#a84b2f",
            "accent_info": "#626c71",
            "font_family": "",
            "font_size": 11,
        }

    def _setup_validators(self) -> None:
        validator = RegexValidator(HEX_PATTERN)
        color_keys = [
            key for key in self._defaults.keys() if key not in {"font_family", "font_size"}
        ]
        self._validators = {key: validator for key in color_keys}
        self._validators["font_family"] = TypeValidator(str)
        self._validators["font_size"] = RangeValidator(6, 48)


class HotkeysSettings(SettingsGroup):
    """Глобальные горячие клавиши приложения."""

    group_name = "hotkeys"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "open_connections_manager": "Ctrl+Alt+C",
            "test_connection": "Ctrl+Alt+T",
            "open_projects_manager": "Ctrl+Alt+P",
            "open_settings": "Ctrl+Alt+S",
            "open_logs": "Ctrl+Alt+L",
            "open_help": "F1",
            "open_about": "Ctrl+Alt+I",
            "exit_app": "Ctrl+Q",
            "next_tab": "Ctrl+Tab",
            "prev_tab": "Ctrl+Shift+Tab",
            "run_last_project": "Ctrl+Alt+R",
            "refresh_data": "F5",
            "switch_tab_1": "1",
            "switch_tab_2": "2",
            "switch_tab_3": "3",
            "switch_tab_4": "4",
        }

    def _setup_validators(self) -> None:
        composite = CompositeValidator([TypeValidator(str), RegexValidator(HOTKEY_PATTERN)])
        self._validators = {key: composite for key in self._defaults.keys()}


class ConnectionsSettings(SettingsGroup):
    """Параметры, связанные с менеджером соединений."""

    group_name = "connections"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "auto_connect_on_startup": [],
            "default_connection": None,
            "refresh_rate_ms": 5000,
            "connection_timeout_sec": 5,
            "auto_refresh_enabled": True,
            "connection_timeout_enabled": True,
            "auto_activate_connections": True,
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "auto_connect_on_startup": TypeValidator(list),
            "default_connection": TypeValidator((str, type(None))),
            "refresh_rate_ms": RangeValidator(1000, 60000),
            "connection_timeout_sec": RangeValidator(1, 120),
            "auto_refresh_enabled": TypeValidator(bool),
            "connection_timeout_enabled": TypeValidator(bool),
            "auto_activate_connections": TypeValidator(bool),
        }


class ProjectsSettings(SettingsGroup):
    """Настройки поведения менеджера проектов."""

    group_name = "projects"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "auto_load_projects": True,
            "default_project": None,
            "show_project_history": True,
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "auto_load_projects": TypeValidator(bool),
            "default_project": TypeValidator((str, type(None))),
            "show_project_history": TypeValidator(bool),
        }


class TerminalSettings(SettingsGroup):
    """Настройки терминалов."""

    group_name = "terminal"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "use_system_console": False,
            "container_shell": "/bin/sh",
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "use_system_console": TypeValidator(bool),
            "container_shell": TypeValidator(str),
        }


class UIStateSettings(SettingsGroup):
    """Настройки состояния пользовательского интерфейса."""

    group_name = "ui_state"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "open_tabs": [],
            "last_active_tab": 0,
            "dashboard_visible": True,
            "footer_visible": True,
            "column_widths": {},
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "open_tabs": TypeValidator(list),
            "last_active_tab": RangeValidator(0, 1000),
            "dashboard_visible": TypeValidator(bool),
            "footer_visible": TypeValidator(bool),
            "column_widths": TypeValidator(dict),
        }


class MetricsSettings(SettingsGroup):
    """Настройки частоты обновления метрик."""

    group_name = "metrics"

    def _initialize_defaults(self) -> None:
        self._defaults = {
            "container_stats_refresh_ms": 5000,
            "system_metrics_enabled": True,
            "system_metrics_refresh_ms": 3000,
        }

    def _setup_validators(self) -> None:
        self._validators = {
            "container_stats_refresh_ms": RangeValidator(500, 60000),
            "system_metrics_enabled": TypeValidator(bool),
            "system_metrics_refresh_ms": RangeValidator(500, 60000),
        }
