# Архитектура проекта Docker Simple Manager (Project Architecture)

## 1. Общая архитектура на высоком уровне

```
┌─────────────────────────────────────────────────────────────────────┐
│                     User Interface Layer (PySide6)                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ Main Window │ Dialogs │ Widgets │ Themes │ i18n             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                     Business Logic Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ Connections  │  │  Projects    │  │ Docker API   │                 │
│  │  Manager     │  │   Manager    │  │  Wrapper     │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                   Settings & Configuration Layer                       │
│  ┌─────────────────────────────────────────────────────────────┐      │
│  │ Settings Registry │ Groups │ Validators │ Observers         │      │
│  └─────────────────────────────────────────────────────────────┘      │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                        Core Services Layer                             │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐                │
│  │  Logging       │  │  Utils      │  │ Path Manager │                │
│  └────────────────┘  └─────────────┘  └──────────────┘                │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                      External Systems                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ Docker       │  │ SSH/Paramiko │  │ File System  │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Структура директорий и модулей

### 2.1 Полная структура проекта

```
docker-simple-manager/
│
├── docs/
│   ├── 01_technical_specification.md         # ТЗ проекта
│   ├── 02_settings_system_architecture.md    # Архитектура настроек
│   ├── 03_ui_ux_prototypes.md               # Прототипы интерфейсов
│   ├── 04_ai_agent_prompt.md                # Промпт для AI
│   ├── 05_development_checklist.md          # Чеклист разработки
│   ├── 06_project_architecture.md           # Этот файл
│   ├── API.md                               # API документация
│   └── CONTRIBUTING.md                      # Гайд для контрибьюторов
│
├── src/
│   ├── __init__.py                          # __version__, exports
│   ├── main.py                              # Entry point
│   ├── app.py                               # Главное окно приложения
│   │
│   ├── settings/                            # ФАЗА 1: Система настроек
│   │   ├── __init__.py                      # Экспорты (SettingsRegistry, etc)
│   │   ├── registry.py                      # SettingsRegistry (Singleton)
│   │   ├── groups.py                        # SettingsGroup и подклассы
│   │   ├── validators.py                    # Система валидации
│   │   ├── observers.py                     # Observer pattern
│   │   ├── migration.py                     # Миграция конфигураций
│   │   ├── exceptions.py                    # Пользовательские исключения
│   │   └── schemas.py                       # JSON schemas для валидации
│   │
│   ├── connections/                         # ФАЗА 2: Менеджер соединений
│   │   ├── __init__.py
│   │   ├── manager.py                       # ConnectionManager класс
│   │   ├── models.py                        # Connection, SSHConfig, etc
│   │   ├── docker_client.py                 # Docker API wrapper
│   │   ├── ssh_tunnel.py                    # SSH tunneling
│   │   └── exceptions.py                    # Connection-specific ошибки
│   │
│   ├── projects/                            # ФАЗА 2: Менеджер проектов
│   │   ├── __init__.py
│   │   ├── manager.py                       # ProjectManager класс
│   │   ├── models.py                        # Project, ProjectRunHistory
│   │   ├── executor.py                      # Выполнение команд/проектов
│   │   ├── parser.py                        # Парсинг Dockerfile, compose
│   │   └── exceptions.py                    # Project-specific ошибки
│   │
│   ├── docker_api/                          # ФАЗА 2-3: Docker API интеграция
│   │   ├── __init__.py
│   │   ├── client.py                        # Основной Docker client wrapper
│   │   ├── containers.py                    # Работа с контейнерами
│   │   ├── images.py                        # Работа с образами
│   │   ├── volumes.py                       # Работа с томами
│   │   ├── builds.py                        # Работа с сборками
│   │   ├── models.py                        # DTO для Docker объектов
│   │   └── exceptions.py                    # Docker-specific ошибки
│   │
│   ├── ui/                                  # ФАЗА 3: UI/UX компоненты
│   │   ├── __init__.py
│   │   ├── main_window.py                   # Главное окно (QMainWindow)
│   │   ├── base_widgets.py                  # Базовые переиспользуемые компоненты
│   │   │
│   │   ├── dialogs/                         # Диалоговые окна
│   │   │   ├── __init__.py
│   │   │   ├── connection_dialog.py         # Диалог создания/редактирования соединения
│   │   │   ├── project_dialog.py            # Диалог создания/редактирования проекта
│   │   │   ├── settings_dialog.py           # Диалог настроек (4 вкладки)
│   │   │   ├── help_dialog.py               # Справка
│   │   │   ├── about_dialog.py              # О программе
│   │   │   ├── confirm_dialog.py            # Подтверждение действий
│   │   │   └── base_dialog.py               # Базовый класс для диалогов
│   │   │
│   │   ├── widgets/                         # Переиспользуемые виджеты
│   │   │   ├── __init__.py
│   │   │   ├── tables.py                    # Tables для containers, images, volumes, builds
│   │   │   ├── buttons.py                   # Icon buttons, action buttons
│   │   │   ├── terminal.py                  # Terminal widget (footer)
│   │   │   ├── dashboard.py                 # Dashboard панель
│   │   │   ├── toolbar.py                   # Toolbar компоненты
│   │   │   ├── tabs.py                      # Таб-менеджер
│   │   │   └── statusbar.py                 # Статус бар
│   │   │
│   │   ├── tabs/                            # Табы для главного окна
│   │   │   ├── __init__.py
│   │   │   ├── connection_tab.py            # Таб с соединением Docker
│   │   │   ├── projects_tab.py              # Таб менеджера проектов
│   │   │   ├── connections_manager_tab.py   # Таб менеджера соединений
│   │   │   └── base_tab.py                  # Базовый класс табов
│   │   │
│   │   ├── styles/                          # Стили оформления
│   │   │   ├── __init__.py
│   │   │   ├── light_theme.qss              # Светлая тема (QSS)
│   │   │   ├── dark_theme.qss               # Темная тема (QSS)
│   │   │   ├── styles.py                    # Динамические стили (Python)
│   │   │   └── colors.py                    # Палитра цветов
│   │   │
│   │   └── resources/                       # Ресурсы UI
│   │       ├── __init__.py
│   │       ├── icons/                       # SVG/PNG иконки
│   │       ├── fonts/                       # Пользовательские шрифты
│   │       └── images/                      # Логотип и изображения
│   │
│   ├── utils/                               # Утилиты
│   │   ├── __init__.py
│   │   ├── logger.py                        # Конфигурация логирования
│   │   ├── paths.py                         # Управление путями (~/.dsmanager)
│   │   ├── validators.py                    # Общие валидаторы
│   │   ├── helpers.py                       # Вспомогательные функции
│   │   ├── ssh_utils.py                     # Утилиты для SSH
│   │   ├── docker_utils.py                  # Утилиты для Docker
│   │   └── exceptions.py                    # Общие исключения
│   │
│   └── i18n/                                # Интернационализация
│       ├── __init__.py                      # Функции для i18n
│       ├── translator.py                    # Класс транслятора
│       └── strings/
│           ├── ru.json                      # Русские переводы
│           └── en.json                      # Английские переводы
│
├── tests/                                   # Unit тесты
│   ├── __init__.py
│   ├── conftest.py                          # Pytest конфигурация и fixtures
│   │
│   ├── test_settings/
│   │   ├── __init__.py
│   │   ├── test_validators.py               # Тесты валидаторов
│   │   ├── test_registry.py                 # Тесты SettingsRegistry
│   │   ├── test_groups.py                   # Тесты SettingsGroup
│   │   ├── test_observers.py                # Тесты Observer pattern
│   │   └── test_migration.py                # Тесты миграций
│   │
│   ├── test_connections/
│   │   ├── __init__.py
│   │   ├── test_manager.py
│   │   ├── test_models.py
│   │   └── test_docker_client.py
│   │
│   ├── test_projects/
│   │   ├── __init__.py
│   │   ├── test_manager.py
│   │   ├── test_models.py
│   │   └── test_executor.py
│   │
│   ├── test_docker_api/
│   │   ├── __init__.py
│   │   ├── test_containers.py
│   │   ├── test_images.py
│   │   ├── test_volumes.py
│   │   └── test_builds.py
│   │
│   ├── test_ui/
│   │   ├── __init__.py
│   │   ├── test_main_window.py
│   │   ├── test_dialogs.py
│   │   └── test_widgets.py
│   │
│   └── test_utils/
│       ├── __init__.py
│       ├── test_logger.py
│       ├── test_paths.py
│       └── test_validators.py
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                           # CI/CD pipeline
│   │   └── cd.yml                           # CD pipeline (releases)
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── .gitignore                               # Git ignore rules
├── .pre-commit-config.yaml                  # Pre-commit hooks
├── pyproject.toml                           # Конфигурация проекта и зависимостей
├── pyinstaller.spec                         # PyInstaller конфигурация
├── setup_dev.sh                             # Скрипт для разработки
├── Makefile                                 # Команды для разработки
├── README.md                                # Главный README
├── LICENSE                                  # MIT лицензия
└── CHANGELOG.md                             # История изменений
```

---

## 3. Взаимодействие между модулями

### 3.1 Инициализация приложения

```
main.py
   ├─► setup_logging()
   │   └─► LoggingSettings из SettingsRegistry
   │
   ├─► initialize_settings()
   │   ├─► SettingsRegistry.load_from_disk()
   │   ├─► apply_migrations()
   │   └─► register_observers()
   │
   ├─► initialize_workdir()
   │   ├─► проверить ~/.dsmanager
   │   ├─► создать структуру
   │   ├─► ConnectionManager.load_from_disk()
   │   └─► ProjectManager.load_from_disk()
   │
   └─► MainWindow()
       ├─► setup UI
       ├─► load connections
       ├─► restore tabs
       └─► start event loop
```

### 3.2 Открытие соединения с Docker

```
User clicks "Connect to Docker Local"
   ├─► MainWindow.open_connection(connection_id)
   │
   ├─► ConnectionManager.get_connection(connection_id)
   │
   ├─► DockerClient(connection).connect()
   │   ├─► если SSH → SSHTunnel.connect()
   │   └─► docker.APIClient(socket)
   │
   ├─► ConnectionTab.load_containers()
   │   ├─► DockerClient.list_containers()
   │   ├─► ContainersTable.populate(data)
   │   └─► кэш результатов с refresh_rate
   │
   └─► UI обновлена
```

### 3.3 Запуск проекта

```
User clicks "Run Project"
   ├─► ProjectManager.get_project(project_id)
   │
   ├─► ProjectExecutor.execute(project, connection)
   │   ├─► parse command or file path
   │   ├─► подключиться к Docker (connection)
   │   ├─► выполнить команду
   │   ├─► сохранить логи
   │   └─► обновить ProjectRunHistory
   │
   ├─► обновить UI
   │   ├─► показать результат
   │   ├─► показать логи
   │   └─► обновить статус
   │
   └─► ProjectManager.save_to_disk()
```

### 3.4 Изменение настроек

```
User changes setting in Settings Dialog
   ├─► SettingsGroup.set(key, value)
   │   ├─► validate(key, value)
   │   ├─► _values[key] = value
   │   └─► mark_dirty()
   │
   ├─► SettingsRegistry.notify_observers()
   │   ├─► LoggingSettingsObserver.on_setting_changed()
   │   ├─► UIObserver.on_setting_changed() → update UI
   │   ├─► ThemeObserver.on_setting_changed() → switch theme
   │   └─► LanguageObserver.on_setting_changed() → retranslate
   │
   └─► SettingsRegistry.save_to_disk()
       └─► config.json обновлен
```

---

## 4. Паттерны проектирования

### 4.1 Singleton (Settings Registry)

```python
class SettingsRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Использование:** Единственный источник истины для всех настроек приложения

---

### 4.2 Observer (Settings Changes)

```python
class SettingsRegistry:
    def register_observer(self, observer):
        self._observers.append(observer)
    
    def notify_observers(self, group, key, old, new):
        for observer in self._observers:
            observer.on_setting_changed(group, key, old, new)
```

**Использование:** Реактивные обновления UI при изменении настроек

---

### 4.3 Factory (SettingsGroup creation)

```python
def _register_groups(self):
    self._settings["app"] = AppSettings()
    self._settings["logging"] = LoggingSettings()
    # ...
```

**Использование:** Создание и управление всеми типами групп настроек

---

### 4.4 Strategy (Validator)

```python
class Validator(ABC):
    @abstractmethod
    def validate(self, value):
        pass

class RangeValidator(Validator):
    def validate(self, value):
        # Проверить диапазон

class EnumValidator(Validator):
    def validate(self, value):
        # Проверить перечисление
```

**Использование:** Различные стратегии валидации для разных полей

---

### 4.5 Template Method (BaseDialog, BaseTab)

```python
class BaseDialog(QDialog):
    def exec_(self):
        self.setup_ui()
        self.connect_signals()
        self.load_data()
        return super().exec_()
```

**Использование:** Общая логика для всех диалогов и табов

---

## 5. Поток данных в приложении

### 5.1 Входящие данные (User Input)

```
User Input
    ├─► UI Event (button click, text changed, etc)
    ├─► Validation in SettingsGroup/Validator
    ├─► Business Logic (Manager class)
    ├─► External System (Docker, SSH, File System)
    └─► Result → UI Update
```

### 5.2 Исходящие данные (State Management)

```
Application State
    ├─► SettingsRegistry (все настройки)
    ├─► ConnectionManager (все соединения)
    ├─► ProjectManager (все проекты)
    ├─► Observers (реактивные обновления)
    └─► MainWindow UI (отображение состояния)
```

### 5.3 Сохранение состояния

```
Shutdown Application
    ├─► MainWindow.closeEvent()
    ├─► SettingsRegistry.save_to_disk()
    ├─► ConnectionManager.save_to_disk()
    ├─► ProjectManager.save_to_disk()
    └─► Save window state (size, tabs, etc)

Startup Application
    ├─► Load settings from disk
    ├─► Load connections from disk
    ├─► Load projects from disk
    ├─► Restore window state
    └─► Resume operations
```

---

## 6. Обработка ошибок

### 6.1 Иерархия исключений

```
Exception
├── SettingsError
│   ├── SettingsNotFoundError
│   ├── SettingsValidationError
│   ├── SettingsMigrationError
│   └── SettingsIOError
├── ConnectionError (из connections/)
│   ├── ConnectionNotFoundError
│   ├── ConnectionTestFailedError
│   └── SSHConnectionError
├── ProjectError (из projects/)
│   ├── ProjectNotFoundError
│   ├── ProjectExecutionError
│   └── ProjectParseError
└── DockerError (из docker_api/)
    ├── DockerNotInstalled
    ├── DockerConnectionError
    └── DockerAPIError
```

### 6.2 Обработка в разных слоях

```
UI Layer (Dialog/Widget)
    ├─► Try: call Business Logic
    ├─► Catch: specific exceptions
    └─► Display: user-friendly error message

Business Logic Layer (Manager)
    ├─► Try: call external system
    ├─► Catch: external exceptions
    └─► Raise: domain-specific exceptions with logging

External System Layer (Docker, SSH)
    └─► Raise: low-level exceptions

Each exception:
    ├─► Logged (en)
    ├─► User message (i18n)
    └─► Handled gracefully
```

---

## 7. Конфигурация и развертывание

### 7.1 Файлы конфигурации

```
~/.dsmanager/
├── config.json          # Все настройки приложения
├── connections.json     # Список соединений Docker
├── projects/            # Каждый проект в отдельном JSON файле
│   ├── project-1.json
│   ├── project-2.json
│   └── ...
└── logs/                # Логовые файлы
    ├── app.log
    ├── connections.log
    ├── projects.log
    └── ...
```

### 7.2 Environment переменные

```
DEBUG=True/False        # Verbose logging
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
DSM_CONFIG_DIR=...      # Override config directory
DSM_DOCKER_SOCKET=...   # Override default socket
```

### 7.3 PyInstaller конфигурация

```spec
# pyinstaller.spec
analysis = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/i18n/strings', 'i18n/strings'),
        ('src/ui/styles', 'ui/styles'),
        ('src/ui/resources', 'ui/resources'),
    ],
    # ...
)
```

---

## 8. Testing стратегия

### 8.1 Unit тесты (80%+ coverage)

```
tests/
├── test_settings/           # 60 тестов
├── test_connections/        # 40 тестов
├── test_projects/           # 35 тестов
├── test_docker_api/         # 50 тестов
├── test_ui/                 # 30 тестов (limited, mostly manual)
└── test_utils/              # 25 тестов

Total: 240+ unit тестов
```

### 8.2 Integration тесты

```
Тесты взаимодействия между модулями:
├── Settings → UI update
├── Connection → Docker API
├── Project → Connection → Docker API
└── Full workflow testing
```

### 8.3 Manual тесты

```
- UI тесты (очень сложно автоматизировать с PySide6)
- Docker integration тесты (требуют Docker daemon)
- SSH тесты (требуют SSH сервер)
- Performance тесты (с реальными данными)
```

---

## 9. Performance оптимизация

### 9.1 Кэширование

```python
# Кэш Docker объектов с TTL
class DockerClient:
    def __init__(self, connection):
        self._cache = {}
        self._cache_ttl = 5  # seconds
    
    def list_containers(self, force_refresh=False):
        if not force_refresh and self._is_cache_valid():
            return self._cache['containers']
        # Fetch from Docker API
```

### 9.2 Асинхронные операции

```python
# Долгие операции в отдельном потоке
class ProjectExecutor:
    def execute_async(self, project, connection):
        worker = ExecutorWorker(project, connection)
        worker.finished.connect(self.on_execution_finished)
        self.thread_pool.start(worker)
```

### 9.3 Ленивая загрузка

```python
# Табы загружаются при открытии, не при инициализации
class MainWindow:
    def on_tab_activated(self, index):
        tab = self.tabs.widget(index)
        if not tab.is_loaded:
            tab.load_data()
```

---

## 10. Безопасность

### 10.1 Шифрование чувствительных данных

```python
# SSH пароли и ключи зашифрованы
class SSHConfig:
    def __init__(self, password: str):
        self.password_encrypted = encrypt_password(password)
    
    def get_password(self):
        return decrypt_password(self.password_encrypted)
```

### 10.2 Валидация входных данных

```python
# Все входные данные валидируются
class SettingsGroup:
    def set(self, key, value):
        validator = self._validators.get(key)
        if not validator.validate(value):
            raise SettingsValidationError(...)
```

### 10.3 Логирование действий

```python
# Все действия логируются с потенциалом аудита
logger.info(f"User created connection: {connection.name} on {connection.host}")
logger.info(f"User ran project: {project.name} on connection: {connection.name}")
```

---

## 11. Миграция и версионирование

### 11.1 Версионирование конфигурации

```json
{
  "version": "1.0.0",
  "schema_version": 1,
  "app": { ... },
  "logging": { ... }
}
```

### 11.2 Миграция при обновлении

```python
# Если app версия 1.1.0 но config версия 1.0.0
# автоматически применяются миграции
config = load_config()
if config['version'] != CURRENT_VERSION:
    config = migration_manager.apply_migrations(config)
```

---

## 12. Масштабируемость и расширяемость

### 12.1 Добавление новой сет группы

```python
# 1. Создать класс в groups.py
class NewSettings(SettingsGroup):
    def _initialize_defaults(self):
        self._defaults = { ... }

# 2. Зарегистрировать в registry
def _register_groups(self):
    self._settings["new"] = NewSettings()

# 3. Готово! Автоматически работает везде
```

### 12.2 Добавление новой UI диалога

```python
# 1. Наследовать от BaseDialog
class MyDialog(BaseDialog):
    def setup_ui(self):
        # UI setup
    
    def connect_signals(self):
        # Signal connections
    
    def load_data(self):
        # Load data from managers

# 2. Открыть из главного окна
self.dialog = MyDialog()
if self.dialog.exec_():
    self.refresh_ui()
```

### 12.3 Добавление новой команды Docker

```python
# 1. Добавить метод в DockerClient
class DockerClient:
    def my_new_command(self):
        return self.client.api.my_new_command()

# 2. Добавить в UI через новый таб/вкладку
# 3. Готово! Полностью интегрировано
```

---

## ЗАКЛЮЧЕНИЕ

Эта архитектура предусматривает:

✅ **Модульность** - Каждый компонент независим и тестируем
✅ **Масштабируемость** - Легко добавлять новые функции
✅ **Надежность** - Обработка ошибок, логирование, тестирование
✅ **Производительность** - Кэширование, асинхронные операции
✅ **Безопасность** - Валидация, шифрование, аудит
✅ **Поддерживаемость** - Чистый код, хорошая документация
✅ **Пользовательский опыт** - Интуитивный UI, быстрый отклик

Архитектура позволяет легко:
- Добавлять новые функции
- Исправлять баги
- Оптимизировать производительность
- Расширять функционал
- Улучшать UI/UX

