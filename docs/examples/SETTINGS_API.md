# Руководство по системе настроек

## Общая структура

Все настройки сгруппированы по логическим секциям. Каждая группа предоставляет методы `get`, `set`, `to_dict`, `from_dict`, `reset_to_defaults`. Работа всегда ведётся через `SettingsRegistry`.

```python
from pathlib import Path
from src.settings.registry import SettingsRegistry

registry = SettingsRegistry(Path("~/.dsmanager/config.json"))
registry.load_from_disk()

language = registry.get_value("app", "language")
registry.set_value("logging", "level", "DEBUG")
registry.save_to_disk()
```

## Группы настроек

### AppSettings (`app`)

| Ключ | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `language` | `str` | `ru` | Локаль (ru/en) |
| `theme` | `str` | `system` | Тема (light/dark/system) |
| `window_width`, `window_height` | `int` | `1920`, `1080` | Размер окна |
| `window_x`, `window_y` | `int` | `0` | Позиция окна |
| `window_maximized`, `save_window_state` | `bool` | `True` | Поведение окна |

### LoggingSettings (`logging`)

| Ключ | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `enabled` | `bool` | `True` | Включить/выключить логирование |
| `level` | `str` | `INFO` | Уровень логов |
| `max_file_size_mb` | `int` | `10` | Размер файла логов |
| `max_archived_files` | `int` | `5` | Количество резервных копий |

### ThemeSettings (`theme`)

Содержит 11 HEX-цветов для светлой/тёмной темы (primary/background/text/border и accent-*). Все значения проходят проверку по шаблону `#RRGGBB`.

### HotkeysSettings (`hotkeys`)

Содержит сочетания клавиш для основных действий (`open_connections_manager`, `open_projects_manager`, `open_settings`, `open_logs`, `open_help`, `next_tab`, `prev_tab`, `run_last_project`). Формат проверяется регулярным выражением.

### ConnectionsSettings (`connections`)

| Ключ | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `auto_connect_on_startup` | `list[str]` | `[]` | Список ID соединений для автоподключения |
| `default_connection` | `Optional[str]` | `None` | Соединение по умолчанию |
| `refresh_rate_ms` | `int` | `5000` | Интервал обновления табов (мс) |

### ProjectsSettings (`projects`)

| Ключ | Тип | По умолчанию |
|------|-----|--------------|
| `auto_load_projects` | `bool` | `True` |
| `default_project` | `Optional[str]` | `None` |
| `show_project_history` | `bool` | `True` |

### UIStateSettings (`ui_state`)

| Ключ | Тип | По умолчанию | Описание |
|------|-----|--------------|----------|
| `open_tabs` | `list[dict]` | `[]` | Сохранённые вкладки |
| `last_active_tab` | `int` | `0` | Индекс активной вкладки |
| `dashboard_visible`, `footer_visible` | `bool` | `True` | Отображение панелей |

## Работа с наблюдателями

```python
from src.settings.observers import SettingsObserver

class UiObserver(SettingsObserver):
    def on_setting_changed(self, group, key, old_value, new_value):
        print(f"{group}.{key}: {old_value} -> {new_value}")

registry.register_observer(UiObserver())
registry.set_value("app", "language", "en")
```

## Экспорт и импорт

```python
registry.export_to_json(Path("backup.json"))
registry.import_from_json(Path("backup.json"))
```

Реестр автоматически применяет миграции и валидирует значения.
