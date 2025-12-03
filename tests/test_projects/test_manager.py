"""Тесты ProjectManager."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.connections.models import Connection
from src.projects.manager import ProjectManager
from src.projects.models import Project


def make_project() -> Project:
    return Project(
        identifier="proj",
        name="Demo",
        command_or_path="docker run hello",
        connection_id="local",
    )


def test_add_and_load_project(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path, tmp_path / "logs")
    manager.add_project(make_project())

    reloaded = ProjectManager(tmp_path, tmp_path / "logs")
    assert len(reloaded.list_projects()) == 1
    assert reloaded.get_project("proj").name == "Demo"


def test_update_and_delete_project(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path, tmp_path / "logs")
    project = make_project()
    manager.add_project(project)

    updated = Project(identifier="proj", name="New", command_or_path="run", connection_id="local")
    manager.update_project(updated)
    assert manager.get_project("proj").name == "New"

    manager.delete_project("proj")
    assert manager.list_projects() == []


def test_run_project_records_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ProjectManager(tmp_path, tmp_path / "logs")
    manager.add_project(make_project())

    monkeypatch.setattr(
        "src.projects.manager.execute_project",
        lambda project, connection, log_file: SimpleNamespace(
            status="success",
            log_file=log_file,
            error_message=None,
        ),
    )
    connection = Connection(identifier="local", name="Local", socket="unix:///var/run/docker.sock")
    entry = manager.run_project("proj", connection)
    assert entry.status == "success"
    project = manager.get_project("proj")
    assert len(project.run_history) == 1
