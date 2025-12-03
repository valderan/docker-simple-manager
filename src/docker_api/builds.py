"""Функции для работы со сборками Docker."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List

from docker.errors import DockerException

from src.docker_api.client import DockerClientWrapper


def list_builds(
    client: DockerClientWrapper, *, env: Dict[str, str] | None = None
) -> List[Dict[str, Any]]:
    """Возвращает историю сборок (id, builder, время, автор)."""

    legacy = _collect_legacy_history(client)
    if legacy:
        return legacy

    cli_env = env or os.environ.copy()
    cli_builds = _collect_buildx_history(cli_env)
    if cli_builds:
        return cli_builds
    return []


def _collect_buildx_history(env: Dict[str, str]) -> List[Dict[str, Any]]:
    builders = _list_builder_names(env)
    if not builders:
        builders = ["default"]
    result: List[Dict[str, Any]] = []
    for builder in builders:
        entries = _run_buildx_history_command(builder, env)
        if not entries:
            continue
        for entry in entries:
            result.append(_convert_buildx_entry(entry, builder or "buildx"))
    if result:
        return result

    du_entries = _run_buildx_du_command(env)
    return [_convert_buildx_entry(entry, "buildx") for entry in du_entries]


def _run_buildx_history_command(builder: str | None, env: Dict[str, str]) -> List[Dict[str, Any]]:
    command = ["docker", "buildx", "history", "ls", "--format", "json"]
    if builder:
        command.extend(["--builder", builder])
    return _run_buildx_command(command, env)


def _run_buildx_du_command(env: Dict[str, str]) -> List[Dict[str, Any]]:
    command = ["docker", "buildx", "du", "--verbose", "--format", "json"]
    return _run_buildx_command(command, env)


def _run_buildx_command(command: List[str], env: Dict[str, str]) -> List[Dict[str, Any]]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    return _parse_json_output(result.stdout)


def _list_builder_names(env: Dict[str, str]) -> List[str]:
    command = ["docker", "buildx", "ls", "--format", "json"]
    entries = _run_buildx_command(command, env)
    if entries:
        names = []
        for entry in entries:
            name = entry.get("name") or entry.get("Name")
            if name:
                names.append(str(name).strip("* "))
        return names

    # Fallback: текстовый вывод
    try:
        output = subprocess.run(
            ["docker", "buildx", "ls"],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    names = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("NAME"):
            continue
        names.append(line.split()[0].strip("*"))
    return names


def _convert_buildx_entry(entry: Dict[str, Any], builder: str) -> Dict[str, Any]:
    ref = entry.get("ref") or entry.get("digest") or entry.get("recordID") or entry.get("id") or ""
    short_id = ref.split("/")[-1][:12] if ref else entry.get("id", "unknown")[:12]
    name = entry.get("name") or entry.get("description") or ref or "build"

    created_ts = _parse_timestamp_value(
        entry.get("completedAt")
        or entry.get("completed_at")
        or entry.get("createdAt")
        or entry.get("created_at")
    )
    started_ts = _parse_timestamp_value(
        entry.get("startedAt")
        or entry.get("started_at")
        or entry.get("createdAt")
        or entry.get("created_at")
    )
    duration_seconds = _extract_duration_seconds(
        entry.get("duration") or entry.get("elapsed"), started_ts, created_ts
    )

    return {
        "name": str(name),
        "id": short_id,
        "builder": builder,
        "duration": _format_duration(duration_seconds),
        "created": _format_timestamp(
            entry.get("completedAt")
            or entry.get("completed_at")
            or entry.get("createdAt")
            or entry.get("created_at")
        ),
        "author": entry.get("author")
        or entry.get("initiator")
        or entry.get("creator")
        or entry.get("started_by")
        or "-",
        "is_mine": str(entry.get("status", "")).lower() == "completed",
    }


def _extract_duration_seconds(
    raw_value: Any, start: datetime | None, end: datetime | None
) -> float | None:
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str) and raw_value.endswith("s"):
        try:
            return float(raw_value.rstrip("s"))
        except ValueError:
            return None
    if start and end:
        return max((end - start).total_seconds(), 0)
    return None


def _collect_legacy_history(client: DockerClientWrapper) -> List[Dict[str, Any]]:
    raw = client.get_raw_client()
    history_method = getattr(raw.api, "build_history", None)
    if history_method is None:  # pragma: no cover
        return []
    try:
        history = history_method()  # pragma: no cover
    except DockerException:
        return []

    builds: List[Dict[str, Any]] = []
    for record in history:
        builds.append(
            {
                "name": ", ".join(record.get("tags", [])) or record.get("id") or "build",
                "id": record.get("id"),
                "builder": record.get("builder") or "docker",
                "duration": _format_duration(record.get("duration")),
                "created": _format_timestamp(record.get("created")),
                "author": record.get("author") or "-",
                "is_mine": True,
            }
        )
    return builds


def _parse_json_output(output: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(output)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    entries: List[Dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def _format_duration(value: Any) -> str:
    if value in (None, "", "N/A"):
        return "N/A"
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return str(value)
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = seconds / 60.0
    return f"{minutes:.1f} min"


def _format_timestamp(value: Any) -> str:
    timestamp = _parse_timestamp_value(value)
    if not timestamp:
        return "N/A"

    delta = datetime.now(timezone.utc) - timestamp
    days = delta.days
    if days < 1:
        hours = delta.seconds // 3600
        if hours:
            return f"{hours}h ago"
        minutes = (delta.seconds % 3600) // 60
        if minutes:
            return f"{minutes}m ago"
        return "just now"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    if months == 1:
        return "1 month ago"
    return f"{months} months ago"


def _parse_timestamp_value(value: Any) -> datetime | None:
    if value in (None, "", "N/A"):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None
