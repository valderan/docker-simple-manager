# Промпт для AI Агента разработчика (Developer AI Agent Prompt)

## ФАЗА 1: СИСТЕМА НАСТРОЕК И ИНФРАСТРУКТУРА

### Общая инструкция

Ты — опытный Python разработчик высочайшего качества. Твоя задача разработать приложение **Docker Simple Manager** (DSM) на Python 3.13+ с использованием PySide6 и менеджера пакетов uv.

**Критические требования:**
- Код должен быть production-ready
- 100% type hints во всех функциях
- Соблюдение PEP-8 и best practices Python
- Минимум 80% unit test coverage
- Полная документация всех компонентов
- Логирование на английском языке
- Обработка всех возможных ошибок

**Структура проекта:**
```
docker-simple-manager/
├── docs/                          # Документация
│   ├── 01_technical_specification.md
│   ├── 02_settings_system_architecture.md
│   ├── 03_ui_ux_prototypes.md
│   ├── 04_ai_prompt.md
│   ├── 05_development_checklist.md
│   └── 06_project_architecture.md
├── src/
│   ├── __init__.py
│   ├── main.py                    # Точка входа приложения
│   ├── app.py                     # Главное окно приложения
│   ├── settings/                  # Система настроек (ФАЗА 1)
│   │   ├── __init__.py
│   │   ├── registry.py            # SettingsRegistry (Singleton)
│   │   ├── groups.py              # SettingsGroup и подклассы
│   │   ├── validators.py          # Система валидации
│   │   ├── observers.py           # Observer pattern
│   │   ├── migration.py           # Миграция конфигураций
│   │   └── exceptions.py          # Пользовательские исключения
│   ├── connections/               # Менеджер соединений (ФАЗА 2)
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── models.py
│   │   └── docker_client.py
│   ├── projects/                  # Менеджер проектов (ФАЗА 2)
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── models.py
│   │   └── executor.py
│   ├── docker_api/                # Интеграция с Docker API (ФАЗА 2-3)
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── containers.py
│   │   ├── images.py
│   │   ├── volumes.py
│   │   └── builds.py
│   ├── ui/                        # UI компоненты (ФАЗА 3)
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── dialogs/
│   │   │   ├── connections.py
│   │   │   ├── projects.py
│   │   │   ├── settings.py
│   │   │   ├── help.py
│   │   │   ├── about.py
│   │   │   └── confirm.py
│   │   ├── widgets/
│   │   │   ├── tables.py
│   │   │   ├── buttons.py
│   │   │   ├── terminal.py
│   │   │   └── dashboard.py
│   │   └── styles/
│   │       ├── light_theme.qss
│   │       └── dark_theme.qss
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── paths.py
│   │   ├── validators.py
│   │   └── helpers.py
│   └── i18n/                      # Интернационализация
│       ├── __init__.py
│       ├── translations.py
│       └── strings/
│           ├── ru.json
│           └── en.json
├── tests/                         # Unit тесты
│   ├── __init__.py
│   ├── test_settings/
│   ├── test_connections/
│   ├── test_projects/
│   ├── test_docker_api/
│   └── test_ui/
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml                 # Конфигурация uv и зависимостей
├── pyinstaller.spec              # Конфигурация PyInstaller
├── setup_dev.sh                  # Скрипт для настройки разработки
└── README.md
```

---

## ФАЗА 1: СИСТЕМА НАСТРОЕК (Settings System Implementation)

### Задача 1.1: Создать базовую архитектуру системы настроек

**Файл:** `src/settings/exceptions.py`

Создать пользовательские исключения:

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

class SettingsMigrationError(SettingsError):
    """Ошибка миграции конфигурации"""
    pass

class SettingsIOError(SettingsError):
    """Ошибка при чтении/записи файла конфигурации"""
    pass
```

**Требования:**
- Все исключения должны иметь информативные сообщения
- Логирование ошибок при выбросе исключений
- Поддержка стека ошибок

---

### Задача 1.2: Реализовать систему валидации

**Файл:** `src/settings/validators.py`

Создать валидаторы:

```python
from abc import ABC, abstractmethod
from typing import Any, Tuple

class Validator(ABC):
    """Базовый класс для валидаторов"""
    
    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Валидировать значение. Возвращает (is_valid, error_message)"""
        pass

class RangeValidator(Validator):
    """Валидатор диапазона значений"""
    def __init__(self, min_value: Any = None, max_value: Any = None):
        self.min_value = min_value
        self.max_value = max_value

class EnumValidator(Validator):
    """Валидатор перечисления"""
    def __init__(self, allowed_values: List[Any]):
        self.allowed_values = allowed_values

class TypeValidator(Validator):
    """Валидатор типа данных"""
    def __init__(self, expected_type: type):
        self.expected_type = expected_type

class RegexValidator(Validator):
    """Валидатор по регулярному выражению"""
    def __init__(self, pattern: str):
        self.pattern = pattern

# Каждый валидатор должен:
# - Реализовать validate() метод
# - Возвращать информативное сообщение об ошибке
# - Быть переиспользуемым
# - Иметь unit тесты
```

**Требования:**
- Все валидаторы должны быть composable (можно комбинировать)
- Поддержка кастомных валидаторов
- Полное покрытие тестами

---

### Задача 1.3: Реализовать базовый класс SettingsGroup

**Файл:** `src/settings/groups.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class SettingsGroup(ABC):
    """Базовый класс для группы настроек"""
    
    def __init__(self):
        self.group_name: str = ""
        self._defaults: Dict[str, Any] = {}
        self._validators: Dict[str, Validator] = {}
        self._values: Dict[str, Any] = {}
        self._initialize_defaults()
    
    @abstractmethod
    def _initialize_defaults(self) -> None:
        """Инициализировать дефолтные значения"""
        pass
    
    @abstractmethod
    def _setup_validators(self) -> None:
        """Настроить валидаторы"""
        pass
    
    def get(self, key: str) -> Any:
        """Получить значение"""
        pass
    
    def set(self, key: str, value: Any) -> None:
        """Установить значение с валидацией"""
        pass
    
    def validate(self, key: str, value: Any) -> Tuple[bool, str]:
        """Валидировать значение"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        pass
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Загрузить из словаря"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Получить JSON schema группы"""
        pass
    
    def reset_to_defaults(self) -> None:
        """Сбросить на дефолты"""
        pass
```

Создать конкретные группы:

```python
class AppSettings(SettingsGroup):
    """Основные настройки приложения"""
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
            "save_window_state": True
        }
        self._values = self._defaults.copy()

class LoggingSettings(SettingsGroup):
    """Настройки логирования"""
    group_name = "logging"
    
    def _initialize_defaults(self) -> None:
        self._defaults = {
            "enabled": True,
            "level": "INFO",
            "max_file_size_mb": 10,
            "max_archived_files": 5
        }
        self._values = self._defaults.copy()

# Аналогично для:
# - ThemeSettings
# - HotkeysSettings
# - ConnectionsSettings
# - ProjectsSettings
# - UIStateSettings
```

**Требования:**
- Каждая группа должна иметь default значения
- Валидация при установке значений
- Возможность экспорта/импорта
- Полное покрытие тестами

---

### Задача 1.4: Реализовать SettingsRegistry (Singleton)

**Файл:** `src/settings/registry.py`

```python
from typing import Dict, Optional, List, Any
from pathlib import Path
import json
import logging

class SettingsRegistry:
    """Singleton реестр всех настроек приложения"""
    
    _instance: Optional['SettingsRegistry'] = None
    
    def __new__(cls) -> 'SettingsRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._settings: Dict[str, SettingsGroup] = {}
        self._observers: List[SettingsObserver] = []
        self._dirty: bool = False
        self._file_path: Optional[Path] = None
        self._logger = logging.getLogger(__name__)
        
        self._register_groups()
        self._initialized = True
    
    def _register_groups(self) -> None:
        """Зарегистрировать все группы настроек"""
        self._settings["app"] = AppSettings()
        self._settings["logging"] = LoggingSettings()
        self._settings["theme"] = ThemeSettings()
        self._settings["hotkeys"] = HotkeysSettings()
        self._settings["connections"] = ConnectionsSettings()
        self._settings["projects"] = ProjectsSettings()
        self._settings["ui_state"] = UIStateSettings()
    
    def get_value(
        self,
        group: str,
        key: str,
        default: Optional[Any] = None
    ) -> Any:
        """Получить значение из группы"""
        pass
    
    def set_value(self, group: str, key: str, value: Any) -> None:
        """Установить значение в группу"""
        pass
    
    def get_group(self, group: str) -> SettingsGroup:
        """Получить группу целиком"""
        pass
    
    def register_observer(self, observer: 'SettingsObserver') -> None:
        """Зарегистрировать наблюдателя"""
        pass
    
    def notify_observers(
        self,
        group: str,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Уведомить всех наблюдателей об изменении"""
        pass
    
    def save_to_disk(self, path: Optional[Path] = None) -> None:
        """Сохранить конфиг на диск"""
        pass
    
    def load_from_disk(self, path: Path) -> None:
        """Загрузить конфиг с диска"""
        pass
    
    def validate(self) -> bool:
        """Валидировать всю конфигурацию"""
        pass
    
    def reset_to_defaults(self) -> None:
        """Сбросить все на дефолты"""
        pass
    
    def export_to_json(self, path: Path) -> None:
        """Экспортировать в JSON"""
        pass
    
    def import_from_json(self, path: Path) -> None:
        """Импортировать из JSON"""
        pass
```

**Требования:**
- Singleton паттерн (только один экземпляр)
- Thread-safe операции
- Автоматическое сохранение при изменениях
- Версионирование конфигурации
- Логирование всех операций
- Обработка ошибок файловой системы

---

### Задача 1.5: Реализовать Observer Pattern для настроек

**Файл:** `src/settings/observers.py`

```python
from abc import ABC, abstractmethod
from typing import Any

class SettingsObserver(ABC):
    """Базовый класс для наблюдателя за изменениями настроек"""
    
    @abstractmethod
    def on_setting_changed(
        self,
        group: str,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Вызывается когда изменилась настройка"""
        pass

class LoggingSettingsObserver(SettingsObserver):
    """Наблюдатель который логирует все изменения"""
    
    def on_setting_changed(
        self,
        group: str,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        logger.info(
            f"Setting changed: {group}.{key} = {old_value} -> {new_value}"
        )

# Аналогично для других наблюдателей:
# - UISettingsObserver (обновляет UI при изменениях)
# - ThemeObserver (переключает тему)
# - LanguageObserver (переключает язык)
```

**Требования:**
- Поддержка множественных наблюдателей
- Асинхронные уведомления где необходимо
- Обработка исключений в наблюдателях
- Возможность отписки от событий

---

### Задача 1.6: Реализовать систему миграций конфигураций

**Файл:** `src/settings/migration.py`

```python
from typing import Dict, Callable, Tuple
import logging

class SettingsMigration:
    """Менеджер миграций конфигураций между версиями"""
    
    _migrations: Dict[Tuple[int, int, int], Callable] = {}
    
    @classmethod
    def register_migration(
        cls,
        from_version: Tuple[int, int, int],
        to_version: Tuple[int, int, int],
        func: Callable[[Dict], Dict]
    ) -> None:
        """Зарегистрировать миграцию"""
        pass
    
    @classmethod
    def migrate(
        cls,
        old_config: Dict,
        from_version: str,
        to_version: str
    ) -> Dict:
        """Применить миграцию"""
        pass
    
    @classmethod
    def apply_migrations(cls, config: Dict) -> Dict:
        """Применить все необходимые миграции"""
        pass

# Пример миграции
def migrate_1_0_to_1_1(config: Dict) -> Dict:
    """Миграция от 1.0.0 к 1.1.0"""
    if "notifications" not in config:
        config["notifications"] = {
            "enabled": True,
            "show_container_updates": True
        }
    return config
```

**Требования:**
- Поддержка цепочки миграций
- Откат в случае ошибки
- Логирование процесса миграции
- Версионирование сбережений

---

### Задача 1.7: Настроить инициализацию приложения

**Файл:** `src/main.py`

```python
import sys
import logging
from pathlib import Path
from src.settings import SettingsRegistry
from src.app import MainWindow
from src.i18n import set_language

def setup_logging(settings: SettingsRegistry) -> None:
    """Настроить логирование на основе настроек"""
    pass

def initialize_workdir(settings: SettingsRegistry) -> bool:
    """Инициализировать рабочую директорию"""
    pass

def initialize_settings() -> SettingsRegistry:
    """Инициализировать систему настроек"""
    settings = SettingsRegistry()
    config_path = Path.home() / ".dsmanager" / "config.json"
    
    if not config_path.exists():
        # Создать дефолты и сохранить
        settings.save_to_disk(config_path)
    else:
        # Загрузить существующий конфиг
        settings.load_from_disk(config_path)
    
    return settings

def main() -> None:
    """Точка входа приложения"""
    try:
        settings = initialize_settings()
        setup_logging(settings)
        
        # Установить язык
        language = settings.get_value("app", "language")
        set_language(language)
        
        # Проверить рабочую директорию
        if not initialize_workdir(settings):
            sys.exit(1)
        
        # Запустить приложение
        app = MainWindow()
        sys.exit(app.run())
    
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Требования:**
- Обработка всех ошибок при инициализации
- Graceful shutdown
- Логирование всех действий

---

### Задача 1.8: Написать unit тесты для системы настроек

**Файл:** `tests/test_settings/test_registry.py`

```python
import pytest
from pathlib import Path
from src.settings import SettingsRegistry, SettingsValidationError

class TestSettingsRegistry:
    
    @pytest.fixture
    def settings(self):
        """Создать новый реестр для каждого теста"""
        return SettingsRegistry()
    
    def test_singleton_pattern(self):
        """Тест Singleton паттерна"""
        settings1 = SettingsRegistry()
        settings2 = SettingsRegistry()
        assert settings1 is settings2
    
    def test_get_value(self, settings):
        """Тест получения значения"""
        language = settings.get_value("app", "language")
        assert language in ["ru", "en"]
    
    def test_set_value(self, settings):
        """Тест установки значения"""
        settings.set_value("app", "language", "en")
        assert settings.get_value("app", "language") == "en"
    
    def test_validation_error(self, settings):
        """Тест ошибки валидации"""
        with pytest.raises(SettingsValidationError):
            settings.set_value("app", "language", "invalid")
    
    def test_save_and_load(self, settings, tmp_path):
        """Тест сохранения и загрузки"""
        config_file = tmp_path / "config.json"
        settings.set_value("app", "language", "en")
        settings.save_to_disk(config_file)
        
        new_settings = SettingsRegistry()
        new_settings.load_from_disk(config_file)
        assert new_settings.get_value("app", "language") == "en"
    
    def test_observer_notification(self, settings):
        """Тест уведомления наблюдателей"""
        # Создать mock наблюдателя
        # Зарегистрировать его
        # Изменить значение
        # Проверить что наблюдатель был уведомлен
        pass
    
    # Дополнительные тесты...
```

**Требования:**
- Минимум 30 unit тестов
- 100% покрытие критических путей
- Тесты для всех методов
- Тесты для обработки ошибок
- Моки для внешних зависимостей

---

## ИТОГИ ФАЗЫ 1

По завершении Фазы 1 должно быть:

✅ Полная система управления настройками (Settings System)
✅ Все настройки организованы в группы (SettingsGroup)
✅ Валидация всех входных данных
✅ Observer pattern для реактивных обновлений
✅ Сохранение/загрузка конфигураций
✅ Миграция между версиями
✅ Unit тесты с 100% покрытием
✅ Логирование всех операций
✅ Обработка всех ошибок
✅ Документация API
✅ Готовность к интеграции с UI

---

## СЛЕДУЮЩИЕ ФАЗЫ

После успешного завершения Фазы 1:

**ФАЗА 2:** Менеджер соединений и основной Docker функционал
- Реализация Connection Manager
- Docker API интеграция
- Project Manager
- Работа с контейнерами, образами, томами, сборками

**ФАЗА 3:** UI/UX и интеграция
- Создание главного окна приложения
- Диалоги и виджеты
- Таблицы для отображения данных
- Темы оформления

**ФАЗА 4:** Сборка и оптимизация
- PyInstaller конфигурация
- Тестирование на целевых ОС
- Оптимизация производительности
- Подготовка к релизу

---

## СТАНДАРТЫ КАЧЕСТВА КОДА

Все созданные компоненты ДОЛЖНЫ соответствовать:

```python
# Пример идеального компонента

from typing import Any, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class MyComponent:
    """
    Краткое описание компонента.
    
    Детальное описание того что делает компонент,
    как его использовать, примеры.
    
    Attributes:
        param1: Описание параметра
        param2: Описание параметра
    """
    
    def __init__(self, param1: str, param2: int) -> None:
        """
        Инициализировать компонент.
        
        Args:
            param1: Первый параметр
            param2: Второй параметр
        
        Raises:
            ValueError: Если param2 < 0
        """
        if param2 < 0:
            raise ValueError("param2 must be >= 0")
        
        self.param1: str = param1
        self.param2: int = param2
        logger.debug(f"MyComponent initialized with param1={param1}, param2={param2}")
    
    def do_something(self, data: str) -> Optional[str]:
        """
        Сделать что-то с данными.
        
        Args:
            data: Входные данные
        
        Returns:
            Обработанные данные или None если ошибка
        
        Raises:
            TypeError: Если data не строка
        """
        if not isinstance(data, str):
            raise TypeError(f"Expected str, got {type(data)}")
        
        try:
            result = data.upper()
            logger.debug(f"do_something: {data} -> {result}")
            return result
        except Exception as e:
            logger.error(f"Error in do_something: {e}", exc_info=True)
            return None
```

**Требования по коду:**
- ✅ Полная типизация (type hints)
- ✅ Docstrings в формате Google Style
- ✅ Логирование всех операций
- ✅ Обработка ошибок
- ✅ Unit тесты для каждого метода
- ✅ Примеры использования в docstrings
- ✅ Соблюдение PEP-8
- ✅ Максимум 120 символов в строке
- ✅ Асинхронные операции где нужно
- ✅ Memory эффективность

