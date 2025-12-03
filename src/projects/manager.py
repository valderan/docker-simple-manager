"""Менеджер проектов: загрузка, CRUD, запуск и история."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from src.connections.models import Connection
from src.projects.executor import enqueue_project_log, execute_project
from src.projects.models import Project, ProjectRunHistory


class ProjectManager:
    """Управляет сохранением проектов и историей их запусков."""

    def __init__(self, projects_dir: Path, logs_dir: Path | None = None) -> None:
        self._projects_dir = projects_dir
        self._logger = logging.getLogger(__name__)
        self._projects: Dict[str, Project] = {}
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir = logs_dir or (self._projects_dir / "logs")
        self._logs_dir.mkdir(exist_ok=True)
        self._log_file = self._logs_dir / "projects.log"
        self.load_projects()

    def load_projects(self) -> None:
        """Загружает все проекты из каталога."""

        loaded: Dict[str, Project] = {}
        for file in self._projects_dir.glob("*.json"):
            data = json.loads(file.read_text(encoding="utf-8"))
            project = Project.from_dict(data)
            loaded[project.identifier] = project
        self._projects = loaded

    def list_projects(self) -> List[Project]:
        return list(self._projects.values())

    def get_project(self, identifier: str) -> Project:
        try:
            return self._projects[identifier]
        except KeyError:
            raise KeyError(f"Project '{identifier}' not found") from None

    def add_project(self, project: Project) -> None:
        if project.identifier in self._projects:
            raise ValueError(f"Project '{project.identifier}' already exists")
        timestamp = self._timestamp()
        project.created_at = project.created_at or timestamp
        project.updated_at = timestamp
        self._projects[project.identifier] = project
        self._logger.info(
            "Project created: id=%s name=%s connection=%s",
            project.identifier,
            project.name,
            project.connection_id,
        )
        self._save_project(project)

    def update_project(self, project: Project) -> None:
        if project.identifier not in self._projects:
            raise KeyError(f"Project '{project.identifier}' not found")
        stored = self._projects[project.identifier]
        project.created_at = stored.created_at
        project.updated_at = self._timestamp()
        self._projects[project.identifier] = project
        self._logger.info(
            "Project updated: id=%s name=%s connection=%s",
            project.identifier,
            project.name,
            project.connection_id,
        )
        self._save_project(project)

    def delete_project(self, identifier: str) -> None:
        if identifier in self._projects:
            self._projects.pop(identifier)
            self._logger.info("Project deleted: id=%s", identifier)
            file = self._projects_dir / f"{identifier}.json"
            if file.exists():
                file.unlink()
            self._remove_logs(identifier)

    def run_project(self, identifier: str, connection: Connection) -> ProjectRunHistory:
        """Запускает проект и добавляет запись истории."""

        project = self.get_project(identifier)
        start = time.time()
        log_file: Optional[Path] = None
        if project.save_logs:
            log_file = self._log_file
            self._append_project_log(project, "проект запущен")

        self._logger.info(
            "Project run started: id=%s type=%s connection=%s detached=%s",
            project.identifier,
            project.type,
            connection.identifier,
            project.detached_mode,
        )
        try:
            result = execute_project(project, connection, log_file)
        except Exception as exc:
            if log_file:
                self._append_project_log(project, f"ошибка запуска: {exc}")
            self._logger.error("Project %s failed: %s", identifier, exc)
            raise

        duration_ms = int((time.time() - start) * 1000)
        run_entry = ProjectRunHistory(
            run_id=str(uuid.uuid4()),
            timestamp=self._timestamp(),
            status=result.status,
            duration_ms=duration_ms,
            log_file=str(result.log_file) if result.log_file else None,
            error_message=result.error_message,
        )
        project.run_history.append(run_entry)
        project.updated_at = self._timestamp()
        self._save_project(project)
        if log_file:
            self._append_project_log(
                project,
                f"проект завершён, статус: {run_entry.status}, длительность {run_entry.duration_ms} мс",
            )
        self._logger.info(
            "Project run finished: id=%s status=%s duration_ms=%s log_file=%s",
            project.identifier,
            run_entry.status,
            run_entry.duration_ms,
            run_entry.log_file,
        )
        return run_entry

    def _save_project(self, project: Project) -> None:
        file_path = self._projects_dir / f"{project.identifier}.json"
        file_path.write_text(
            json.dumps(project.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _remove_logs(self, identifier: str) -> None:
        return

    def _append_project_log(self, project: Project, message: str) -> None:
        enqueue_project_log(self._log_file, project.identifier, message)
