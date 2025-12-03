"""Модели данных для проектов и истории запусков."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ProjectRunHistory:
    """Запись об одном запуске проекта."""

    run_id: str
    timestamp: str
    status: str
    duration_ms: int
    log_file: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "log_file": self.log_file,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectRunHistory":
        return cls(
            run_id=data.get("run_id", ""),
            timestamp=data.get("timestamp", ""),
            status=data.get("status", "unknown"),
            duration_ms=int(data.get("duration_ms", 0)),
            log_file=data.get("log_file"),
            error_message=data.get("error_message"),
        )


@dataclass(slots=True)
class Project:
    """Описание проекта, запускаемого через Docker или вспомогательные скрипты."""

    identifier: str
    name: str
    command_or_path: str
    connection_id: str
    type: str = "docker_command"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    priority: int = 0
    status: str = "active"
    version: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    author: Optional[str] = None
    detached_mode: bool = False
    timeout_seconds: int = 30
    save_logs: bool = True
    max_log_lines: int = 1000
    run_history: List[ProjectRunHistory] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.identifier,
            "name": self.name,
            "command_or_path": self.command_or_path,
            "connection_id": self.connection_id,
            "type": self.type,
            "description": self.description,
            "tags": self.tags,
            "priority": self.priority,
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "author": self.author,
            "detached_mode": self.detached_mode,
            "timeout_seconds": self.timeout_seconds,
            "save_logs": self.save_logs,
            "max_log_lines": self.max_log_lines,
            "run_history": [entry.to_dict() for entry in self.run_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        history = [
            ProjectRunHistory.from_dict(entry)
            for entry in data.get("run_history", [])
            if isinstance(entry, dict)
        ]
        identifier = data.get("id") or data.get("identifier")
        if not isinstance(identifier, str):
            raise ValueError("Project id is required")
        return cls(
            identifier=identifier,
            name=data.get("name", ""),
            command_or_path=data.get("command_or_path", ""),
            connection_id=data.get("connection_id", ""),
            type=data.get("type", "docker_command"),
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
            priority=int(data.get("priority", 0)),
            status=data.get("status", "active"),
            version=int(data.get("version", 1)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            author=data.get("author"),
            detached_mode=bool(data.get("detached_mode", False)),
            timeout_seconds=int(data.get("timeout_seconds", 30)),
            save_logs=bool(data.get("save_logs", True)),
            max_log_lines=int(data.get("max_log_lines", 1000)),
            run_history=history,
        )
