"""Вспомогательные функции для запуска проектов и подготовки команд."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Dict, Optional, Tuple

from src.connections.models import Connection
from src.projects.models import Project

_LOG_QUEUE: "Queue[tuple[Path, str]]" = Queue()
_LOG_WRITER_STARTED = False


def _ensure_log_writer() -> None:
    global _LOG_WRITER_STARTED
    if _LOG_WRITER_STARTED:
        return
    thread = threading.Thread(target=_log_writer_loop, name="project-log-writer", daemon=True)
    thread.start()
    _LOG_WRITER_STARTED = True


def _log_writer_loop() -> None:
    logger = logging.getLogger(__name__)
    while True:
        log_file, line = _LOG_QUEUE.get()
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:  # pragma: no cover - файловая система
            logger.error("Failed to write project log %s: %s", log_file, exc)


def enqueue_project_log(log_file: Path, project_id: str, message: str) -> None:
    _ensure_log_writer()
    _LOG_QUEUE.put((log_file, f"[{project_id}] {message}\n"))


@dataclass(slots=True)
class ProjectExecutionResult:
    """Результат выполнения проекта."""

    status: str
    command: str
    log_file: Optional[Path]
    error_message: Optional[str] = None


def execute_project(
    project: Project,
    connection: Connection,
    log_file: Optional[Path],
) -> ProjectExecutionResult:
    """Запускает проект локально и собирает результат выполнения."""

    if connection.type != "local":
        raise RuntimeError("Запуск проектов через удалённые соединения будет реализован позднее.")

    command, working_dir = _build_command(project)
    env = _build_environment(connection)
    if project.detached_mode:
        _run_detached(
            project,
            command,
            working_dir,
            env,
            log_file if project.save_logs else None,
        )
        return ProjectExecutionResult(
            status="running",
            command=command,
            log_file=log_file if project.save_logs else None,
        )

    output, return_code = _run_blocking(command, working_dir, project.timeout_seconds, env)
    if project.save_logs and log_file:
        _write_limited_log(project, log_file, output, project.max_log_lines)
    status = "success" if return_code == 0 else "failed"
    error_message = None if return_code == 0 else f"Process exited with code {return_code}"
    return ProjectExecutionResult(
        status=status,
        command=command,
        log_file=log_file if project.save_logs else None,
        error_message=error_message,
    )


def _build_command(project: Project) -> Tuple[str, Optional[Path]]:
    """Создаёт команду и рабочую директорию на основе типа проекта."""

    value = project.command_or_path.strip()
    project_type = project.type or "docker_command"
    if project_type == "docker_command":
        if not value:
            raise ValueError("Команда Docker не может быть пустой")
        return value, None

    resolved_path = _resolve_path(value)
    if project_type == "dockerfile_path":
        if not resolved_path.is_file():
            raise FileNotFoundError(str(resolved_path))
        quoted = shlex.quote(resolved_path.name)
        command = f"docker build -f {quoted} ."
        return command, resolved_path.parent

    if project_type == "compose_path":
        if not resolved_path.is_file():
            raise FileNotFoundError(str(resolved_path))
        quoted = shlex.quote(resolved_path.name)
        base_command = f"docker compose -f {quoted} up"
        if project.detached_mode:
            base_command += " -d"
        return base_command, resolved_path.parent

    if project_type == "bash_script":
        if not resolved_path.is_file():
            raise FileNotFoundError(str(resolved_path))
        quoted = shlex.quote(resolved_path.name)
        return f"bash {quoted}", resolved_path.parent

    raise ValueError(f"Неизвестный тип проекта: {project_type}")


def _resolve_path(value: str) -> Path:
    """Преобразует значение пути в абсолютный Path."""

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _build_environment(connection: Connection) -> Dict[str, str]:
    """Формирует окружение для запуска docker-команд."""

    env = os.environ.copy()
    socket = (connection.socket or "").strip()
    if socket:
        env["DOCKER_HOST"] = socket
    else:
        env.pop("DOCKER_HOST", None)
    return env


def _run_blocking(
    command: str,
    working_dir: Optional[Path],
    timeout_seconds: int,
    env: Dict[str, str],
) -> Tuple[str, int]:
    """Выполняет команду синхронно и возвращает вывод и код возврата."""

    timeout = None if timeout_seconds <= 0 else timeout_seconds
    completed = subprocess.run(  # noqa: PLW1510 - нужно shell для сложных команд
        command,
        cwd=str(working_dir) if working_dir else None,
        shell=True,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=env,
    )
    return completed.stdout or "", completed.returncode


def _run_detached(
    project: Project,
    command: str,
    working_dir: Optional[Path],
    env: Dict[str, str],
    log_file: Optional[Path],
) -> None:
    """Запускает команду в фоне, при необходимости записывая вывод в projects.log."""

    if log_file is None:
        subprocess.Popen(  # noqa: P204
            command,
            cwd=str(working_dir) if working_dir else None,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        return

    process = subprocess.Popen(  # noqa: P204
        command,
        cwd=str(working_dir) if working_dir else None,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        start_new_session=True,
    )

    def _consume_output() -> None:
        assert process.stdout is not None
        with process.stdout:
            for line in process.stdout:
                enqueue_project_log(log_file, project.identifier, line.rstrip())

    threading.Thread(target=_consume_output, daemon=True).start()


def _write_limited_log(project: Project, log_file: Path, output: str, max_lines: int) -> None:
    """Сохраняет вывод команды в projects.log с префиксом идентификатора."""

    lines = output.splitlines()
    if max_lines > 0:
        lines = lines[-max_lines:]
    for line in lines:
        enqueue_project_log(log_file, project.identifier, line)
