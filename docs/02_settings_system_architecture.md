# Архитектура системы настроек (Settings System Architecture)

## 1. Обзор системы настроек

Система настроек является фундаментом приложения Docker Simple Manager. Она обеспечивает:
- Централизованное хранение всех конфигураций
- Предсказуемое поведение приложения
- Простоту добавления новых настроек
- Сохранение состояния между сеансами
- Возможность миграции конфигураций

---

## 2. Архитектурный подход

### 2.1 Паттерн: Registry + Factory + Observer

```
┌─────────────────────────────────────────────────────┐
│           Settings System Architecture              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │     SettingsRegistry (Singleton)             │  │
│  │  - Хранилище всех настроек                   │  │
│  │  - Валидация значений                        │  │
│  │  - Синхронизация с disk                      │  │
│  └──────────────────────────────────────────────┘  │
│                      ▲                             │
│                      │ управляет                   │
│  ┌──────────────────┴──────────────────────────┐  │
│  │    SettingsGroup (Base Class)               │  │
│  │  - AppSettings                              │  │
│  │  - LoggingSettings                          │  │
│  │  - ThemeSettings                            │  │
│  │  - HotkeysSettings                          │  │
│  │  - ConnectionsSettings                      │  │
│  │  - ProjectsSettings                         │  │
│  └──────────────────────────────────────────────┘  │
│                      ▲                             │
│                      │                             │
│  ┌──────────────────┴──────────────────────────┐  │
│  │    SettingsObserver (Event System)          │  │
│  │  - Оповещение об изменениях                 │  │
│  │  - Подписка на события                      │  │
│  │  - Синхронизация UI                         │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │    SettingsMigration (Version Control)       │  │
│  │  - Миграция между версиями                  │  │
│  │  - Обратная совместимость                   │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │    SettingsValidator (Type Safety)           │  │
│  │  - Валидация типов данных                   │  │
│  │  - Проверка диапазонов значений             │  │
│  │  - Пользовательские валидаторы              │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Структура классов

### 3.1 Иерархия классов

```python
# Базовые классы
SettingsRegistry (Singleton)
    ├── _settings: Dict[str, SettingsGroup]
    ├── _observers: List[SettingsObserver]
    ├── _dirty: bool
    ├── _file_path: Path
    └── methods:
        ├── get_group(group_name: str) -> SettingsGroup
        ├── set_value(group: str, key: str, value: Any)
        ├── get_value(group: str, key: str, default: Any)
        ├── register_observer(observer: SettingsObserver)
        ├── notify_observers(group: str, key: str, old_value, new_value)
        ├── save_to_disk()
        ├── load_from_disk()
        └── reset_to_defaults()

SettingsGroup (Abstract Base Class)
    ├── group_name: str
    ├── _defaults: Dict[str, Any]
    ├── _validators: Dict[str, Validator]
    ├── _values: Dict[str, Any]
    └── methods:
        ├── get(key: str) -> Any
        ├── set(key: str, value: Any)
        ├── validate(key: str, value: Any) -> bool
        ├── to_dict() -> Dict
        ├── from_dict(data: Dict)
        └── get_schema() -> Dict

# Конкретные группы настроек
AppSettings(SettingsGroup)
    ├── language: str (default: "ru" or "en")
    ├── theme: str (default: "system", values: ["light", "dark", "system"])
    ├── window_width: int (default: 1920)
    ├── window_height: int (default: 1080)
    ├── window_x: int (default: 0)
    ├── window_y: int (default: 0)
    ├── window_maximized: bool (default: true)
    └── save_window_state: bool (default: true)

LoggingSettings(SettingsGroup)
    ├── enabled: bool (default: true)
    ├── level: str (default: "INFO", values: ["DEBUG", "INFO", "WARNING", "ERROR"])
    ├── max_file_size_mb: int (default: 10, range: 1-1000)
    ├── max_archived_files: int (default: 5, range: 1-50)
    └── log_format: str (default: "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

ThemeSettings(SettingsGroup)
    ├── primary_color_light: str (hex, default: "#218094")
    ├── primary_color_dark: str (hex, default: "#32b8c6")
    ├── background_light: str (hex, default: "#fcfcf9")
    ├── background_dark: str (hex, default: "#1f2121")
    ├── text_light: str (hex, default: "#134252")
    ├── text_dark: str (hex, default: "#f5f5f5")
    ├── border_color_light: str (hex)
    ├── border_color_dark: str (hex)
    ├── accent_success: str (hex)
    ├── accent_error: str (hex)
    ├── accent_warning: str (hex)
    └── accent_info: str (hex)

HotkeysSettings(SettingsGroup)
    ├── open_connections_manager: str (default: "Ctrl+Alt+C")
    ├── open_projects_manager: str (default: "Ctrl+Alt+P")
    ├── open_settings: str (default: "Ctrl+Alt+S")
    ├── open_logs: str (default: "Ctrl+Alt+L")
    ├── open_help: str (default: "Ctrl+Alt+H")
    ├── next_tab: str (default: "Ctrl+Tab")
    ├── prev_tab: str (default: "Ctrl+Shift+Tab")
    └── run_last_project: str (default: "Ctrl+Alt+R")

ConnectionsSettings(SettingsGroup)
    ├── auto_connect_on_startup: List[str] (connection IDs, default: [])
    ├── default_connection: str (default: null)
    └── refresh_rate_ms: int (default: 5000, range: 1000-60000)

ProjectsSettings(SettingsGroup)
    ├── auto_load_projects: bool (default: true)
    ├── default_project: str (default: null)
    └── show_project_history: bool (default: true)

SettingsObserver (Abstract Base Class)
    └── methods:
        └── on_setting_changed(group: str, key: str, old_value: Any, new_value: Any)

SettingsValidator (Base Class)
    └── methods:
        ├── validate(value: Any) -> Tuple[bool, str]
        ├── get_error_message() -> str

# Специфичные валидаторы
RangeValidator(SettingsValidator)
    ├── min_value: Any
    ├── max_value: Any
    └── methods:
        └── validate(value: Any) -> Tuple[bool, str]

EnumValidator(SettingsValidator)
    ├── allowed_values: List[Any]
    └── methods:
        └── validate(value: Any) -> Tuple[bool, str]

TypeValidator(SettingsValidator)
    ├── expected_type: type
    └── methods:
        └── validate(value: Any) -> Tuple[bool, str]

RegexValidator(SettingsValidator)
    ├── pattern: str
    └── methods:
        └── validate(value: Any) -> Tuple[bool, str]

SettingsMigration
    ├── _migrations: Dict[int, Callable]
    └── methods:
        ├── register_migration(from_version: int, to_version: int, func: Callable)
        ├── migrate(old_config: Dict, from_version: int, to_version: int) -> Dict
        └── apply_migrations(config: Dict) -> Dict
```

---

## 4. Схема данных и валидация

### 4.1 Полная структура config.json

```json
{
  "version": "1.0.0",
  "schema_version": 1,
  "app": {
    "language": "ru",
    "theme": "system",
    "window": {
      "width": 1920,
      "height": 1080,
      "x": 0,
      "y": 0,
      "maximized": true
    },
    "save_window_state": true
  },
  "logging": {
    "enabled": true,
    "level": "INFO",
    "max_file_size_mb": 10,
    "max_archived_files": 5,
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "theme": {
    "colors": {
      "light": {
        "primary": "#218094",
        "background": "#fcfcf9",
        "text": "#134252",
        "border": "#5e5240",
        "accent_success": "#208094",
        "accent_error": "#c01547",
        "accent_warning": "#a84b2f",
        "accent_info": "#626c71"
      },
      "dark": {
        "primary": "#32b8c6",
        "background": "#1f2121",
        "text": "#f5f5f5",
        "border": "#777c7c",
        "accent_success": "#32b8c6",
        "accent_error": "#ff5459",
        "accent_warning": "#e68161",
        "accent_info": "#a7a9a9"
      }
    }
  },
  "hotkeys": {
    "open_connections_manager": "Ctrl+Alt+C",
    "open_projects_manager": "Ctrl+Alt+P",
    "open_settings": "Ctrl+Alt+S",
    "open_logs": "Ctrl+Alt+L",
    "open_help": "Ctrl+Alt+H",
    "next_tab": "Ctrl+Tab",
    "prev_tab": "Ctrl+Shift+Tab",
    "run_last_project": "Ctrl+Alt+R"
  },
  "connections": {
    "auto_connect_on_startup": [],
    "default_connection": null,
    "refresh_rate_ms": 5000
  },
  "projects": {
    "auto_load_projects": true,
    "default_project": null,
    "show_project_history": true
  },
  "ui_state": {
    "open_tabs": [
      {
        "type": "connection",
        "connection_id": "local-docker",
        "view": "containers"
      }
    ],
    "last_active_tab": 0,
    "dashboard_visible": true,
    "footer_visible": true
  }
}
```

### 4.2 Правила валидации

```python
VALIDATION_RULES = {
    "app": {
        "language": EnumValidator(["ru", "en"]),
        "theme": EnumValidator(["light", "dark", "system"]),
        "window": {
            "width": RangeValidator(800, 10000),
            "height": RangeValidator(600, 10000),
            "x": RangeValidator(-10000, 10000),
            "y": RangeValidator(-10000, 10000),
            "maximized": TypeValidator(bool)
        },
        "save_window_state": TypeValidator(bool)
    },
    "logging": {
        "enabled": TypeValidator(bool),
        "level": EnumValidator(["DEBUG", "INFO", "WARNING", "ERROR"]),
        "max_file_size_mb": RangeValidator(1, 1000),
        "max_archived_files": RangeValidator(1, 50)
    },
    "hotkeys": {
        "open_connections_manager": RegexValidator(r"^[\w\+\-]+$"),
        # ... все остальные hotkeys
    },
    "connections": {
        "refresh_rate_ms": RangeValidator(1000, 60000)
    }
}
```

---

## 5. Примеры использования

### 5.1 Получение значения настройки

```python
from src.settings import SettingsRegistry

# Получить реестр (singleton)
settings = SettingsRegistry()

# Получить значение
language = settings.get_value("app", "language")
theme = settings.get_value("app", "theme", default="system")
refresh_rate = settings.get_value("connections", "refresh_rate_ms")

# Получить всю группу
app_settings = settings.get_group("app")
language = app_settings.get("language")
```

### 5.2 Установка значения настройки

```python
# Установить одно значение
settings.set_value("app", "language", "en")
settings.set_value("app", "theme", "dark")
settings.set_value("connections", "refresh_rate_ms", 3000)

# Все изменения автоматически:
# - валидируются
# - сохраняются на диск
# - уведомляют наблюдателей
```

### 5.3 Подписка на изменения настроек

```python
from src.settings.observers import SettingsObserver

class MyUIObserver(SettingsObserver):
    def on_setting_changed(self, group: str, key: str, old_value, new_value):
        if group == "app" and key == "theme":
            print(f"Тема изменилась с {old_value} на {new_value}")
            self.apply_new_theme(new_value)
        elif group == "app" and key == "language":
            print(f"Язык изменился на {new_value}")
            self.retranslate_ui()

# Зарегистрировать наблюдателя
observer = MyUIObserver()
settings.register_observer(observer)

# Теперь при изменении будет вызван callback
settings.set_value("app", "theme", "dark")  # -> on_setting_changed будет вызван
```

### 5.4 Работа с группами настроек

```python
# Получить группу
app_settings = settings.get_group("app")

# Получить из группы
language = app_settings.get("language")

# Установить в группу
app_settings.set("language", "en")

# Получить все значения группы
all_app_settings = app_settings.to_dict()

# Загрузить в группу
app_settings.from_dict({
    "language": "ru",
    "theme": "dark"
})
```

### 5.5 Валидация при установке

```python
# Если значение невалидно - будет выброшена ошибка SettingsValidationError
try:
    settings.set_value("logging", "level", "INVALID")  # -> SettingsValidationError
except SettingsValidationError as e:
    print(f"Ошибка валидации: {e}")

# Вручную валидировать значение
validator = RangeValidator(1, 1000)
is_valid, error_msg = validator.validate(500)  # -> (True, "")
is_valid, error_msg = validator.validate(5000)  # -> (False, "Value must be between 1 and 1000")
```

---

## 6. Процесс инициализации

### 6.1 Этапы инициализации при запуске

```
┌─────────────────────────────────────────────┐
│   Запуск приложения (main.py)               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ SettingsRegistry     │
        │ инициализирует себя   │
        └──────────┬───────────┘
                   │
                   ▼
    ┌───────────────────────────────┐
    │ Проверить наличие config.json │
    └──────────┬────────┬───────────┘
               │        │
         ДА   │        │   НЕТ
              ▼        ▼
        ┌──────┐  ┌──────────────────┐
        │Загр. │  │Создать дефолты   │
        │файл  │  │Сохранить на диск │
        └──┬───┘  └────────┬─────────┘
           │               │
           └───────┬───────┘
                   ▼
        ┌──────────────────────┐
        │ Валидировать схему   │
        │ (версия, структура)  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Применить миграции   │
        │ если нужно           │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Загрузить значения в │
        │ SettingsGroups       │
        └──────────┬───────────┘
                   │
                   ▼
    ┌───────────────────────────────┐
    │ Установить язык и тему        │
    │ на основе настроек            │
    └───────────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │ Восстановить состояние окна   │
    │ (размер, позиция, вкладки)    │
    └───────────┬───────────────────┘
                │
                ▼
        ┌──────────────────────┐
        │ Приложение готово    │
        │ к работе             │
        └──────────────────────┘
```

### 6.2 Псевдокод инициализации

```python
def initialize_settings():
    """Инициализировать систему настроек при запуске приложения"""
    
    settings = SettingsRegistry()
    
    # Шаг 1: Определить путь к конфигу
    config_path = Path.home() / ".dsmanager" / "config.json"
    
    # Шаг 2: Проверить наличие файла
    if not config_path.exists():
        logger.info("config.json не найден. Создаю дефолты...")
        settings.create_defaults()
        settings.save_to_disk(config_path)
    else:
        logger.info("Загружаю config.json...")
        settings.load_from_disk(config_path)
    
    # Шаг 3: Валидировать
    try:
        settings.validate()
    except SettingsValidationError as e:
        logger.error(f"Ошибка валидации конфига: {e}")
        settings.create_defaults()
    
    # Шаг 4: Применить миграции
    current_version = settings.get_value("version")
    if current_version != CURRENT_VERSION:
        logger.info(f"Применяю миграции {current_version} -> {CURRENT_VERSION}")
        settings.migrate(current_version, CURRENT_VERSION)
    
    # Шаг 5: Установить язык
    language = settings.get_value("app", "language")
    set_application_language(language)
    
    # Шаг 6: Установить тему
    theme = settings.get_value("app", "theme")
    set_application_theme(theme)
    
    logger.info("Settings initialized successfully")
    return settings
```

---

## 7. Система миграции конфигураций

### 7.1 Пример миграции (v1.0.0 -> v1.1.0)

```python
def migrate_1_0_to_1_1(config: dict) -> dict:
    """
    Миграция конфигурации от версии 1.0 к версии 1.1
    Добавляет новый раздел 'notifications'
    """
    if "notifications" not in config:
        config["notifications"] = {
            "enabled": True,
            "show_container_updates": True,
            "show_build_notifications": True
        }
    
    # Обновить версию
    config["version"] = "1.1.0"
    config["schema_version"] = 2
    
    return config

# Зарегистрировать миграцию
SettingsMigration.register_migration(
    from_version=(1, 0, 0),
    to_version=(1, 1, 0),
    func=migrate_1_0_to_1_1
)
```

---

## 8. Обработка ошибок

### 8.1 Пользовательские исключения

```python
class SettingsError(Exception):
    """Базовое исключение для ошибок настроек"""
    pass

class SettingsNotFoundError(SettingsError):
    """Настройка не найдена"""
    pass

class SettingsValidationError(SettingsError):
    """Ошибка валидации значения"""
    def __init__(self, key: str, value: Any, reason: str):
        self.key = key
        self.value = value
        self.reason = reason
        super().__init__(
            f"Validation error for setting '{key}': {reason} (value: {value})"
        )

class SettingsMigrationError(SettingsError):
    """Ошибка миграции конфигурации"""
    pass

class SettingsIOError(SettingsError):
    """Ошибка при чтении/записи файла конфигурации"""
    pass
```

### 8.2 Обработка в коде

```python
try:
    settings.set_value("logging", "max_file_size_mb", 5000)
except SettingsValidationError as e:
    logger.error(f"Invalid value: {e.reason}")
    show_user_error(f"Неверное значение: {e.reason}")
except SettingsNotFoundError as e:
    logger.error(f"Setting not found: {e}")
except SettingsIOError as e:
    logger.error(f"IO error: {e}")
```

---

## 9. Тестирование системы настроек

### 9.1 Unit тесты

```python
def test_settings_get_value():
    """Тест получения значения"""
    settings = SettingsRegistry()
    value = settings.get_value("app", "language")
    assert isinstance(value, str)
    assert value in ["ru", "en"]

def test_settings_set_value():
    """Тест установки значения"""
    settings = SettingsRegistry()
    settings.set_value("app", "language", "en")
    assert settings.get_value("app", "language") == "en"

def test_settings_validation():
    """Тест валидации"""
    settings = SettingsRegistry()
    with pytest.raises(SettingsValidationError):
        settings.set_value("app", "language", "invalid")

def test_settings_persistence():
    """Тест сохранения и загрузки"""
    settings = SettingsRegistry()
    settings.set_value("app", "language", "en")
    settings.save_to_disk()
    
    settings2 = SettingsRegistry()
    settings2.load_from_disk()
    assert settings2.get_value("app", "language") == "en"

def test_settings_migration():
    """Тест миграции"""
    old_config = {"version": "1.0.0", "app": {"language": "ru"}}
    migration = SettingsMigration()
    new_config = migration.apply_migrations(old_config)
    assert new_config["version"] == CURRENT_VERSION
```

---

## 10. Документация API

### 10.1 Публичный API

```python
# SettingsRegistry
settings = SettingsRegistry()
settings.get_value(group: str, key: str, default: Any = None) -> Any
settings.set_value(group: str, key: str, value: Any) -> None
settings.get_group(group: str) -> SettingsGroup
settings.register_observer(observer: SettingsObserver) -> None
settings.save_to_disk(path: Path = None) -> None
settings.load_from_disk(path: Path = None) -> None
settings.reset_to_defaults() -> None
settings.validate() -> bool
settings.migrate(from_version: str, to_version: str) -> None
settings.export_to_json(path: Path) -> None
settings.import_from_json(path: Path) -> None

# SettingsGroup
group.get(key: str) -> Any
group.set(key: str, value: Any) -> None
group.to_dict() -> Dict[str, Any]
group.from_dict(data: Dict[str, Any]) -> None
group.get_schema() -> Dict[str, Any]

# SettingsObserver
observer.on_setting_changed(group: str, key: str, old_value: Any, new_value: Any) -> None
```

---

## 11. Чеклист реализации системы настроек

- [ ] Создать базовый класс SettingsGroup
- [ ] Создать SettingsRegistry (Singleton)
- [ ] Реализовать систему валидации (Validators)
- [ ] Создать конкретные группы настроек (AppSettings, LoggingSettings и т.д.)
- [ ] Реализовать систему наблюдателей (Observer pattern)
- [ ] Реализовать сохранение/загрузку JSON
- [ ] Реализовать систему миграций
- [ ] Создать обработчик ошибок
- [ ] Написать unit тесты (мин. 80% покрытие)
- [ ] Создать документацию API
- [ ] Реализовать интеграцию с UI (диалоги настроек)
- [ ] Протестировать на Linux и macOS

