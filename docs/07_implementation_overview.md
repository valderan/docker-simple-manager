# Обзор текущей реализации (Implementation Overview)

Этот документ описывает реализацию проекта Docker Simple Manager на текущем этапе (после Фазы 3). Используйте его, чтобы быстро понять структуру и ключевые файлы без повторного анализа всего репозитория.

## Фаза 1 — Система настроек
- `src/settings/registry.py`: Singleton реестр групп настроек, поддерживает загрузку/сохранение, миграции, наблюдателей, экспорт/импорт.
- `src/settings/groups.py`: реализация `SettingsGroup` и конкретных групп (`AppSettings`, `LoggingSettings`, `ThemeSettings`, `HotkeysSettings`, `ConnectionsSettings`, `ProjectsSettings`, `UIStateSettings`).
- `src/settings/validators.py`: валидаторы (type/range/enum/regex/composite).
- `src/settings/migration.py`: класс `SettingsMigration`, пример миграции 1.0 -> 1.1.
- `src/settings/observers.py`: интерфейс observer’ов + logging observer.
- `src/main.py`: инициализация реестра, работа с `DSM_HOME`, подготовка рабочей директории, запуск приложения.

## Фаза 2 — Менеджеры и Docker API
- `src/connections/models.py`: `Connection`, `SSHConfig`, `ConnectionStatus`.
- `src/connections/manager.py`: CRUD соединений, загрузка/сохранение `connections.json`, проверка статуса.
- `src/docker_api/client.py`: `DockerClientWrapper` (создание docker-py клиента, ping, ошибки).
- `src/docker_api/containers|images|volumes|builds.py`: функции работы с соответствующими сущностями (пока базовые операции).
- `src/projects/models.py`: `Project`, `ProjectRunHistory`.
- `src/projects/manager.py`: CRUD проектов, запуск `run_project`, запись истории.

## Фаза 3 — UI и интеграция
- `src/ui/main_window.py`: QMainWindow с меню, дашбордом, вкладками и footer. Текст берётся через i18n `translate()`.
- `src/app.py`: создаёт `QApplication`, применяет тему (`src/ui/styles/theme_manager.py`), устанавливает язык (`src/i18n/translator.py`) и запускает окно.
- `src/ui/dialogs/*`: заглушки диалогов (Connections, Projects, Settings, Help) для будущей интеграции.
- `src/ui/widgets/tables.py`: базовые таблицы для Containers/Images/Volumes/Builds.
- `src/ui/widgets/terminal.py`: Read-only терминал для footer.
- `src/i18n/translator.py` и `strings/en.json`, `strings/ru.json`: простой переводчик, загружающий JSON строки.
- `src/ui/styles/light_theme.qss`, `dark_theme.qss`: темы оформления.

## Тесты
Пока автоматизированы только части без GUI: `tests/test_connections/*`, `tests/test_projects/test_manager.py`. GUI тесты планируется внедрить после настройки окружения (см. ч.к.)

## Следующие шаги (Phase 3.5, 3.6)
См. расширенный чеклист в `docs/05_development_checklist.md` для задач интеграции данных в UI и финализации GUI.
