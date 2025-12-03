# Чеклист разработки проекта Docker Simple Manager (Development Checklist)

## ФАЗА 1: СИСТЕМА НАСТРОЕК И ИНФРАСТРУКТУРА (Weeks 1)

### 1.1 Подготовка проекта и окружения

- [x] Создать репозиторий на GitHub
- [x] Настроить структуру директорий проекта
- [x] Создать `pyproject.toml` с зависимостями:
  - [x] pyside6 (UI фреймворк)
  - [x] docker (Docker API)
  - [x] paramiko (SSH)
  - [x] pydantic (валидация)
  - [x] pytest (тестирование)
  - [x] pytest-cov (покрытие тестами)
  - [x] black (форматирование)
  - [x] flake8 (линтер)
  - [x] mypy (type checking)
  - [x] python-dotenv (переменные окружения)
- [x] Настроить CI/CD (GitHub Actions):
  - [x] Линтирование (flake8, mypy)
  - [x] Тестирование (pytest)
  - [x] Проверка покрытия (80% минимум)
  - [x] Сборка на Linux и macOS
- [x] Создать README.md с инструкциями по установке
- [x] Создать setup_dev.sh для разработки

### 1.2 Система исключений и логирования

- [ ] Реализовать `src/settings/exceptions.py`:
  - [x] SettingsError (базовое исключение)
  - [x] SettingsNotFoundError
  - [x] SettingsValidationError
  - [x] SettingsMigrationError
  - [x] SettingsIOError
  - [x] Информативные сообщения ошибок
  - [x] Логирование при выбросе исключений

- [ ] Реализовать `src/utils/logger.py`:
  - [x] Конфигурация логирования
  - [x] Ротация логовых файлов
  - [x] Разные уровни логирования (DEBUG, INFO, WARNING, ERROR)
  - [x] Форматирование логов
  - [x] Сохранение логов в `~/.dsmanager/logs/`

- [ ] Написать unit тесты:
  - [x] Тесты всех исключений
  - [x] Тесты логирования
  - [ ] Минимум 50 тестов

### 1.3 Система валидации

- [ ] Реализовать `src/settings/validators.py`:
  - [x] Validator (абстрактный базовый класс)
  - [x] RangeValidator (диапазон значений)
  - [x] EnumValidator (перечисление)
  - [x] TypeValidator (проверка типа)
  - [x] RegexValidator (регулярное выражение)
  - [x] CompositeValidator (комбинирование валидаторов)

- [ ] Каждый валидатор:
  - [x] Метод validate() возвращающий (bool, str)
  - [x] Информативные сообщения об ошибках
  - [ ] Docstrings с примерами
  - [x] Минимум 3 unit теста на валидатор

- [ ] Написать unit тесты:
  - [ ] Минимум 40 тестов на валидацию
  - [x] Граничные случаи (edge cases)
  - [x] Комбинированные валидаторы

### 1.4 Базовые классы для групп настроек

- [ ] Реализовать `src/settings/groups.py`:
  - [x] SettingsGroup (абстрактный базовый класс):
    - [x] _initialize_defaults()
    - [x] _setup_validators()
    - [x] get(key) -> Any
    - [x] set(key, value) -> None
    - [x] validate(key, value) -> (bool, str)
    - [x] to_dict() -> Dict
    - [x] from_dict(data: Dict) -> None
    - [x] get_schema() -> Dict
    - [x] reset_to_defaults() -> None

- [ ] Реализовать конкретные группы:
  - [x] AppSettings:
    - [x] language (default: "ru")
    - [x] theme (default: "system")
    - [x] window_width, window_height, window_x, window_y
    - [x] window_maximized, save_window_state
    - [x] Валидаторы для каждого поля

  - [x] LoggingSettings:
    - [x] enabled
    - [x] level (DEBUG, INFO, WARNING, ERROR)
    - [x] max_file_size_mb (1-1000)
    - [x] max_archived_files (1-50)
    - [x] Валидаторы

  - [x] ThemeSettings:
    - [x] Цвета для светлой темы (primary, background, text и т.д.)
    - [x] Цвета для темной темы
    - [x] Валидация hex кодов

  - [x] HotkeysSettings:
    - [x] Все 8 горячих клавиш (из спеки)
    - [x] Валидация формата (Ctrl+Alt+X)
    - [ ] Проверка дублей

  - [x] ConnectionsSettings:
    - [x] auto_connect_on_startup
    - [x] default_connection
    - [x] refresh_rate_ms (1000-60000)

  - [x] ProjectsSettings:
    - [x] auto_load_projects
    - [x] default_project
    - [x] show_project_history

  - [x] UIStateSettings:
    - [x] open_tabs (список открытых табов)
    - [x] last_active_tab
    - [x] dashboard_visible, footer_visible

- [ ] Для каждой группы:
  - [ ] Минимум 10 unit тестов
  - [ ] Тесты get/set
  - [ ] Тесты валидации
  - [ ] Тесты export/import
  - [ ] Тесты reset

### 1.5 SettingsRegistry (Singleton)

- [ ] Реализовать `src/settings/registry.py`:
  - [x] Singleton паттерн:
    - [x] __new__() для гарантии одного экземпляра
    - [x] _instance класс переменная
    - [ ] Thread-safe доступ

  - [x] Методы:
    - [x] __init__() - инициализация групп
    - [x] _register_groups() - регистрация всех групп
    - [x] get_value(group, key, default=None) -> Any
    - [x] set_value(group, key, value) -> None
    - [x] get_group(group) -> SettingsGroup
    - [x] register_observer(observer) -> None
    - [x] notify_observers(group, key, old, new) -> None
    - [x] save_to_disk(path=None) -> None
    - [x] load_from_disk(path) -> None
    - [x] validate() -> bool
    - [x] reset_to_defaults() -> None
    - [x] export_to_json(path) -> None
    - [x] import_from_json(path) -> None

  - [x] Обработка ошибок:
    - [x] SettingsNotFoundError если группа/ключ не найден
    - [x] SettingsValidationError если значение невалидно
    - [x] SettingsIOError если ошибка файла
    - [x] Логирование всех ошибок

  - [x] Сохранение:
    - [x] JSON формат
    - [x] Версионирование (version поле)
    - [x] Schema версия (для миграций)
    - [ ] Автосохранение при изменениях
    - [ ] Дебоунсинг для частых изменений

- [ ] Unit тесты:
  - [x] 20+ тестов для SettingsRegistry
  - [x] Тест Singleton паттерна
  - [x] Тесты get/set value
  - [x] Тесты save/load
  - [ ] Тесты валидации
  - [x] Тесты наблюдателей
  - [ ] Тесты обработки ошибок

### 1.6 Observer Pattern для настроек

- [ ] Реализовать `src/settings/observers.py`:
  - [x] SettingsObserver (абстрактный класс):
    - [x] on_setting_changed(group, key, old, new) -> None

  - [x] Встроенные наблюдатели:
    - [x] LoggingSettingsObserver (логирует изменения)
    - [ ] Сохранение в файл при изменениях

  - [x] Система подписки:
    - [x] register_observer() в SettingsRegistry
    - [x] unregister_observer()
    - [x] notify_observers()
    - [x] Безопасное удаление наблюдателей

  - [x] Обработка ошибок:
    - [x] Исключения в наблюдателях не должны сломать систему
    - [x] Логирование ошибок в наблюдателях

- [ ] Unit тесты:
  - [x] 15+ тестов для Observer pattern
  - [x] Тесты регистрации/отписки
  - [x] Тесты уведомлений
  - [x] Тесты обработки ошибок

### 1.7 Система миграций конфигураций

- [ ] Реализовать `src/settings/migration.py`:
  - [x] SettingsMigration класс:
    - [x] register_migration() - регистрировать миграцию
    - [ ] migrate() - применить одну миграцию
    - [x] apply_migrations() - применить все нужные миграции
    - [ ] get_migrations_needed() - найти нужные миграции

  - [x] Миграция 1.0.0 -> 1.1.0 (пример):
    - [x] Добавить новые поля с дефолтами
    - [x] Преобразовать старые поля если нужно
    - [x] Логирование процесса

  - [x] Обработка ошибок:
    - [x] SettingsMigrationError при ошибке
    - [x] Откат в случае критической ошибки
    - [x] Backup старого конфига

- [ ] Unit тесты:
  - [ ] 10+ тестов для миграций
  - [x] Тест регистрации миграции
  - [x] Тест применения одной миграции
  - [ ] Тест цепочки миграций
  - [x] Тест обработки ошибок

### 1.8 Модуль инициализации приложения

- [ ] Реализовать `src/main.py`:
  - [x] Функция setup_logging(settings) -> None
    - [x] Настроить логирование на основе LoggingSettings
    - [x] Создать директорию логов если ее нет
    - [x] Ротация логовых файлов

  - [ ] Функция initialize_workdir(settings) -> bool
    - [x] Проверить наличие ~/.dsmanager
    - [ ] Создать если не существует (с подтверждением)
    - [x] Создать подпапки (projects, logs)
    - [x] Создать connections.json если не существует
    - [ ] Вернуть False если пользователь отказал создание

  - [x] Функция initialize_settings() -> SettingsRegistry
    - [x] Получить Singleton SettingsRegistry
    - [x] Проверить наличие config.json
    - [x] Если не существует - создать с дефолтами
    - [x] Если существует - загрузить
    - [x] Применить миграции если нужно

  - [ ] Функция main() -> None
    - [x] Инициализировать настройки
    - [x] Настроить логирование
    - [ ] Установить язык
    - [x] Инициализировать рабочую директорию
    - [x] Запустить главное окно приложения
    - [ ] Graceful shutdown при ошибке

  - [ ] Entry point:
    - [ ] if __name__ == "__main__": main()

- [ ] Unit тесты:
  - [x] Тесты инициализации
  - [ ] Тесты обработки ошибок
  - [ ] Моки для файловой системы

### 1.9 Конфигурация проекта

- [x] Создать `pyproject.toml`:
  - [x] Название проекта: docker-simple-manager
  - [x] Версия: 0.1.0
  - [x] Описание проекта
  - [x] Авторы
  - [x] Лицензия: MIT
  - [x] Python >= 3.13
  - [x] Зависимости (dependencies)
  - [x] Dev зависимости (dev-dependencies)
  - [x] Build system: setuptools

- [x] Создать `.env.example`:
  - [x] DEBUG=False
  - [x] LOG_LEVEL=INFO
  - [x] Другие переменные если нужны

- [x] Создать `setup_dev.sh`:
  - [x] Установка зависимостей через uv
  - [x] Установка pre-commit hooks
  - [x] Инструкции по использованию

- [x] Создать `.github/workflows/ci.yml`:
  - [x] Линтирование (black, flake8, mypy)
  - [x] Тестирование (pytest)
  - [x] Проверка покрытия (80% минимум)
  - [x] Сборка на Linux и macOS
  - [x] Отправка отчета о покрытии

### 1.10 Документация

- [x] Написать comprehensive docstrings для всех классов/функций
- [x] Создать `docs/SETTINGS_API.md`:
  - [x] Описание всех групп настроек
  - [x] Примеры использования
  - [x] API документация

- [x] Создать `docs/TESTING.md`:
  - [x] Как запустить тесты
  - [x] Как писать новые тесты
  - [x] Требования к покрытию

- [x] Обновить `README.md`:
  - [x] Описание проекта
  - [x] Требования к установке
  - [x] Инструкции по развертыванию
  - [x] Инструкции по разработке
  - [x] Инструкции по тестированию

### 1.11 Финальная проверка Фазы 1

- [x] Все 7 групп настроек реализованы:
  - [x] AppSettings ✓
  - [x] LoggingSettings ✓
  - [x] ThemeSettings ✓
  - [x] HotkeysSettings ✓
  - [x] ConnectionsSettings ✓
  - [x] ProjectsSettings ✓
  - [x] UIStateSettings ✓

- [ ] Общие требования:
  - [x] 100% type hints во всем коде
  - [x] Все исключения обработаны
  - [x] Логирование на английском языке
  - [x] Все методы имеют docstrings
  - [x] Соблюдается PEP-8

- [ ] Тестирование:
  - [ ] Минимум 150 unit тестов
  - [x] Минимум 80% code coverage
  - [x] Все тесты проходят
  - [ ] CI/CD зеленый

- [x] Документация:
  - [x] README.md полный и актуальный
  - [x] API документация полная
  - [x] Примеры использования есть

- [x] Готовность к Фазе 2:
  - [x] Система настроек стабильна
  - [x] Нет известных багов
  - [x] Код готов к review
  - [x] Можно интегрировать с UI

---

## ФАЗА 2: МЕНЕДЖЕР СОЕДИНЕНИЙ И DOCKER (Weeks 2-4)

### 2.1 Модели данных для соединений

- [x] Реализовать Connection, SSHConfig, ConnectionStatus моделей
- [x] Пример JSON структуры connections.json
- [x] Unit тесты для моделей

### 2.2 Менеджер соединений

- [x] Реализовать ConnectionManager класс
- [x] CRUD операции для соединений
- [x] Проверка соединений
- [x] Сохранение/загрузка из JSON

### 2.3 Docker API интеграция

- [x] Создать DockerClient обертку
- [x] Реализовать работу с контейнерами
- [x] Реализовать работу с образами
- [x] Реализовать работу с томами
- [x] Реализовать работу с сборками

### 2.4 Менеджер проектов

- [x] Модели Project, ProjectRunHistory
- [x] ProjectManager класс
- [x] CRUD операции для проектов
- [x] Запуск проектов с отслеживанием логов
- [x] История запусков

### 2.5 Остальное для Фазы 2...

- [ ] ... (детальные под-задачи для каждой части)

---

## ФАЗА 3: UI/UX И ИНТЕГРАЦИЯ (Weeks 5-6)

### 3.1 Главное окно приложения

- [x] MainWindow класс с QMainWindow
- [x] Система вкладок (QTabWidget)
- [x] Меню (QMenuBar)
- [x] Дашборд панель
- [x] Footer панель

### 3.2 Основные компоненты UI

- [x] Таблицы (Containers, Images, Volumes, Builds)
- [x] Диалоги (Connection, Project, Settings)
- [x] Утилиты (кнопки, иконки, tooltips)
- [x] Терминал в footer

### 3.3 Темы оформления

- [x] Светлая тема (light_theme.qss)
- [x] Темная тема (dark_theme.qss)
- [x] Переключение между темами

### 3.4 Интернационализация (i18n)

- [x] Русский перевод (ru.json)
- [x] Английский перевод (en.json)
- [x] Переключение языка

### 3.5 Интеграция данных в UI

- [x] Подключить `ConnectionManager` к UI:
  - [x] Вывод списка соединений в таблице
  - [x] Обновление статуса/проверка через UI
  - [x] Управление диалогом добавления/редактирования
- [x] Подключить `ProjectManager`:
  - [x] Вывод списка проектов
  - [x] Кнопки CRUD из UI
  - [x] Запуск проекта с отображением статуса
- [x] Привязать вкладки Containers/Images/Volumes/Builds к `docker_api` функциям:
  - [x] Отображение данных
  - [x] Обновление по таймеру
  - [x] Базовые действия (start/stop/remove)
- [x] Синхронизация состояния UI с Settings (сохранение выбранных вкладок, размеров таблиц и т.д.)

### 3.6 Взаимодействие и финализация GUI

- [x] Реализовать действия меню (Connections/Projects/Settings/Logs) и открыть соответствующие диалоги
- [x] Подключить терминал в footer к реальному выводу команд
- [x] Реализовать переключение темы/языка из UI (моментальное применение)
- [x] Добавить реакции на горячие клавиши из настроек
- [x] Завершить переводы для всех элементов интерфейса
- [x] Smoke-тесты (ручные) основного сценария: загрузка, подключение, просмотр данных, запуск проекта

---

## ФАЗА 4: СБОРКА И РЕЛИЗ (Week 7)

### 4.1 PyInstaller конфигурация

- [x] Создать pyinstaller.spec
- [x] Оптимизация размера бинарника
- [x] Тестирование на Linux
- [x] Тестирование на macOS

### 4.2 Финальное тестирование

- [x] QA тестирование на Linux
- [x] QA тестирование на macOS
- [x] Тестирование производительности
- [x] Тестирование стабильности

### 4.3 Подготовка релиза

- [x] Обновить версию везде
- [x] Написать Release Notes
- [x] Создать GitHub Release
- [x] Загрузить бинарники

---

## МЕТРИКИ УСПЕХА

### Конец Фазы 1:
- ✅ Система настроек 100% функциональна
- ✅ 150+ unit тестов, 80%+ coverage
- ✅ Ноль критических ошибок
- ✅ Документация полная
- ✅ Готово к интеграции с UI

### Конец Фазы 2:
- ✅ Все менеджеры работают
- ✅ Docker API интеграция завершена
- ✅ Проекты могут запускаться
- ✅ 300+ unit тестов, 80%+ coverage

### Конец Фазы 3:
- ✅ Весь UI реализован
- ✅ Обе темы работают
- ✅ Оба языка работают
- ✅ Все диалоги функциональны
- ✅ 400+ unit тестов, 75%+ coverage

### Конец Фазы 4:
- ✅ Приложение собирается на Linux и macOS
- ✅ Бинарники протестированы
- ✅ Нет критических ошибок
- ✅ Первый релиз готов (v1.0.0)

---

## ЕЖЕДНЕВНЫЙ WORKFLOW

**Утро:**
- Проверить CI/CD статус
- Обновить branch from main если нужно
- Читать созданные PR review comments

**День:**
- Реализовать назначенные задачи
- Писать unit тесты параллельно
- Запускать тесты локально перед push

**Вечер:**
- Push изменений на branch
- Создать PR в main
- Обновить соответствующий чеклист

**Weekly:**
- Встреча по прогрессу
- Обновление плана если нужно
- Планирование следующей недели
