"""Полноценный реестр настроек приложения (Singleton)."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.settings.exceptions import SettingsIOError, SettingsNotFoundError, SettingsValidationError
from src.settings.groups import (
    AppSettings,
    ConnectionsSettings,
    HotkeysSettings,
    LoggingSettings,
    MetricsSettings,
    ProjectsSettings,
    SettingsGroup,
    TerminalSettings,
    ThemeSettings,
    UIStateSettings,
)
from src.settings.migration import SettingsMigration
from src.settings.observers import SettingsObserver
from src.settings.schemas import DEFAULT_CONFIG


class SettingsRegistry:
    """Singleton-реестр, управляющий всеми группами настроек."""

    _instance: Optional["SettingsRegistry"] = None

    def __new__(cls, config_path: Optional[Path] = None) -> "SettingsRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if getattr(self, "_initialized", False):
            if config_path is not None:
                self._file_path = config_path
            return

        self._logger = logging.getLogger(__name__)
        self._file_path = config_path or Path.home() / ".dsmanager" / "config.json"
        self._settings: Dict[str, SettingsGroup] = {}
        self._observers: List[SettingsObserver] = []
        self._metadata: Dict[str, Any] = {}
        self._dirty = False
        self._current_version = self._parse_version(DEFAULT_CONFIG.get("version", "1.0.0"))

        self._register_groups()
        self._extract_metadata(DEFAULT_CONFIG)
        self._initialized = True

    @property
    def config_path(self) -> Path:
        """Путь к текущему файлу конфигурации."""

        return self._file_path

    # --------------------------------------------------------------------- API
    def get_value(self, group: str, key: str, default: Any = None) -> Any:
        settings_group = self._settings.get(group)
        if not settings_group:
            if default is not None:
                return default
            raise SettingsNotFoundError(group, key)
        try:
            return settings_group.get(key)
        except SettingsNotFoundError:
            if default is not None:
                return default
            raise

    def set_value(self, group: str, key: str, value: Any) -> None:
        settings_group = self._require_group(group)
        old_value = settings_group.get(key)
        settings_group.set(key, value)
        self._dirty = True
        self.notify_observers(group, key, old_value, value)

    def get_group(self, group: str) -> SettingsGroup:
        return self._require_group(group)

    def register_observer(self, observer: SettingsObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister_observer(self, observer: SettingsObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, group: str, key: str, old_value: Any, new_value: Any) -> None:
        for observer in list(self._observers):
            try:
                observer.on_setting_changed(group, key, old_value, new_value)
            except Exception as exc:  # pragma: no cover
                self._logger.error("Observer %s failed: %s", observer, exc, exc_info=True)

    def save_to_disk(self, path: Optional[Path] = None) -> None:
        target = path or self._file_path
        payload = dict(self._metadata)
        for name, group in self._settings.items():
            payload[name] = group.to_dict()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            raise SettingsIOError(target, str(exc)) from exc
        self._dirty = False

    def load_from_disk(self, path: Optional[Path] = None) -> None:
        target = path or self._file_path
        if not target.exists():
            self._logger.info("Config file %s not found, writing defaults.", target)
            self.save_to_disk(target)
            return
        try:
            content = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SettingsIOError(target, str(exc)) from exc

        merged = self._merge_with_defaults(content)
        migrated = self._apply_migrations_if_needed(merged)
        self._extract_metadata(migrated)
        for name, group in self._settings.items():
            group_data = migrated.get(name, {})
            if isinstance(group_data, dict):
                group.from_dict(group_data)
        self.validate()
        self._dirty = False

    def validate(self) -> bool:
        for name, group in self._settings.items():
            for key in group.keys():
                value = group.get(key)
                is_valid, error = group.validate(key, value)
                if not is_valid:
                    raise SettingsValidationError(
                        key=f"{name}.{key}",
                        value=value,
                        reason=error,
                    )
        return True

    def reset_to_defaults(self) -> None:
        for group in self._settings.values():
            group.reset_to_defaults()
        self._dirty = True

    def export_to_json(self, path: Path) -> None:
        self.save_to_disk(path)

    def import_from_json(self, path: Path) -> None:
        self.load_from_disk(path)
        self._dirty = True
        self.save_to_disk(self._file_path)

    # ----------------------------------------------------------------- helpers
    def _register_groups(self) -> None:
        self._settings = {
            "app": AppSettings(),
            "logging": LoggingSettings(),
            "theme": ThemeSettings(),
            "hotkeys": HotkeysSettings(),
            "connections": ConnectionsSettings(),
            "projects": ProjectsSettings(),
            "terminal": TerminalSettings(),
            "metrics": MetricsSettings(),
            "ui_state": UIStateSettings(),
        }

    def _require_group(self, group: str) -> SettingsGroup:
        try:
            return self._settings[group]
        except KeyError:
            raise SettingsNotFoundError(group, None) from None

    def _merge_with_defaults(self, incoming: Dict[str, Any]) -> Dict[str, Any]:
        base = copy.deepcopy(DEFAULT_CONFIG)
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key].update(value)
            else:
                base[key] = value
        return base

    def _extract_metadata(self, data: Dict[str, Any]) -> None:
        self._metadata = {key: value for key, value in data.items() if key not in self._settings}

    def _apply_migrations_if_needed(self, config: Dict[str, Any]) -> Dict[str, Any]:
        version_str = config.get("version", DEFAULT_CONFIG.get("version", "1.0.0"))
        version_tuple = self._parse_version(version_str)
        if version_tuple < self._current_version:
            config = SettingsMigration.apply_migrations(
                config,
                version_tuple,
                config_path=self._file_path,
            )
        config["version"] = DEFAULT_CONFIG.get("version", "1.0.0")
        return config

    @staticmethod
    def _parse_version(version: str) -> Tuple[int, int, int]:
        parts = version.split(".")
        while len(parts) < 3:
            parts.append("0")
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2])
        return major, minor, patch
