"""Функции для работы с контейнерами через Docker client."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from src.docker_api.client import DockerClientWrapper, DockerException
from src.docker_api.exceptions import DockerAPIError


def list_containers(client: DockerClientWrapper) -> List[Dict[str, Any]]:
    """Возвращает список контейнеров с базовыми метриками."""

    raw = client.get_raw_client()
    containers = []
    for container in raw.containers.list(all=True):  # pragma: no cover - docker отсутствует
        stats = {}
        status = getattr(container, "status", "") or ""
        status_normalized = status.lower()
        if status_normalized.startswith(("up", "running")):
            stats = _collect_stats(container)

        def stat_value(key: str, default: str = "N/A") -> str:
            value = stats.get(key)
            return value if value is not None else default

        containers.append(
            {
                "id": getattr(container, "short_id", container.id),
                "name": container.name,
                "status": status,
                "image": getattr(container.image, "tags", []),
                "ports": _format_ports(container.attrs.get("NetworkSettings", {})),
                "cpu_percent": stat_value("cpu_percent"),
                "memory_usage": stat_value("memory_usage"),
                "memory_percent": stat_value("memory_percent"),
                "disk_io": stat_value("disk_io"),
                "network_io": stat_value("network_io"),
                "pids": stat_value("pids"),
                "project": (
                    container.labels.get("com.docker.compose.project")
                    if hasattr(container, "labels")
                    else None
                ),
            }
        )
    return containers


def start_container(client: DockerClientWrapper, container_id: str) -> None:
    """Запускает контейнер."""

    raw = client.get_raw_client()
    container = raw.containers.get(container_id)
    try:
        container.start()  # pragma: no cover
    except DockerException as exc:  # pragma: no cover - зависит от окружения
        if "paused" in str(exc).lower():
            try:
                container.unpause()
                return
            except DockerException as unpause_exc:
                raise DockerAPIError(str(unpause_exc)) from unpause_exc
        raise DockerAPIError(str(exc)) from exc


def stop_container(client: DockerClientWrapper, container_id: str) -> None:
    """Останавливает контейнер."""

    raw = client.get_raw_client()
    try:
        raw.containers.get(container_id).stop()  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc


def pause_container(client: DockerClientWrapper, container_id: str) -> None:
    """Ставит контейнер на паузу."""

    raw = client.get_raw_client()
    try:
        raw.containers.get(container_id).pause()  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc


def restart_container(client: DockerClientWrapper, container_id: str) -> None:
    """Перезапускает контейнер."""

    raw = client.get_raw_client()
    try:
        raw.containers.get(container_id).restart()  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc


def remove_container(client: DockerClientWrapper, container_id: str, force: bool = False) -> None:
    """Удаляет контейнер."""

    raw = client.get_raw_client()
    try:
        raw.containers.get(container_id).remove(force=force)  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc


def fetch_logs(client: DockerClientWrapper, container_id: str, *, tail: int = 500) -> str:
    """Возвращает строку логов контейнера."""

    raw = client.get_raw_client()
    try:
        data = raw.containers.get(container_id).logs(tail=tail)  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="ignore")
    return str(data)


def inspect_container(client: DockerClientWrapper, container_id: str) -> Dict[str, Any]:
    """Возвращает словарь атрибутов контейнера."""

    raw = client.get_raw_client()
    try:
        container = raw.containers.get(container_id)  # pragma: no cover
    except DockerException as exc:
        raise DockerAPIError(str(exc)) from exc
    return getattr(container, "attrs", {})


def _collect_stats(container: Any) -> Dict[str, Any]:
    """Считывает статистику контейнера через docker stats."""

    try:
        raw_stats = container.stats(stream=False, decode=False)
        if isinstance(raw_stats, (bytes, str)):
            raw_stats = json.loads(raw_stats)
    except (DockerException, ValueError, TypeError):  # pragma: no cover - зависит от окружения
        return {}

    cpu_percent = _calculate_cpu_percent(raw_stats)
    memory_usage, memory_percent = _calculate_memory(raw_stats)
    network_io = _calculate_network_io(raw_stats)
    disk_io = _calculate_disk_io(raw_stats)
    pids = _safe_int(raw_stats.get("pids_stats", {}).get("current"))

    return {
        "cpu_percent": cpu_percent,
        "memory_usage": memory_usage,
        "memory_percent": memory_percent,
        "disk_io": disk_io,
        "network_io": network_io,
        "pids": pids,
    }


def _calculate_cpu_percent(stats: Dict[str, Any]) -> str:
    cpu_stats = stats.get("cpu_stats") or {}
    precpu = stats.get("precpu_stats") or {}
    cpu_delta = (cpu_stats.get("cpu_usage", {}).get("total_usage", 0)) - (
        precpu.get("cpu_usage", {}).get("total_usage", 0)
    )
    system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
    online_cpus = (
        cpu_stats.get("online_cpus")
        or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", []))
        or 1
    )
    if cpu_delta > 0 and system_delta > 0:
        percent = (cpu_delta / system_delta) * online_cpus * 100.0
        return f"{percent:.1f}%"
    return "N/A"


def _calculate_memory(stats: Dict[str, Any]) -> tuple[str, str]:
    memory_stats = stats.get("memory_stats") or {}
    usage = memory_stats.get("usage")
    limit = memory_stats.get("limit") or 0
    if usage is None:
        return "N/A", "N/A"
    percent = (usage / limit * 100) if limit else 0
    return _format_bytes(usage), f"{percent:.1f}%"


def _calculate_network_io(stats: Dict[str, Any]) -> str:
    networks = stats.get("networks") or {}
    rx = sum(interface.get("rx_bytes", 0) for interface in networks.values())
    tx = sum(interface.get("tx_bytes", 0) for interface in networks.values())
    if rx == 0 and tx == 0:
        return "N/A"
    return f"{_format_bytes(rx)} / {_format_bytes(tx)}"


def _calculate_disk_io(stats: Dict[str, Any]) -> str:
    blkio = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
    read = 0
    write = 0
    for entry in blkio:
        op = entry.get("op")
        if op == "Read":
            read += entry.get("value", 0)
        elif op == "Write":
            write += entry.get("value", 0)
    if read == 0 and write == 0:
        return "N/A"
    return f"{_format_bytes(read)} / {_format_bytes(write)}"


def _format_ports(network_settings: Dict[str, Any]) -> List[str]:
    ports = network_settings.get("Ports", {}) or {}
    result = []
    for container_port, mappings in ports.items():
        if not mappings:
            continue
        for mapping in mappings:
            result.append(f"{mapping.get('HostIp')}:{mapping.get('HostPort')} -> {container_port}")
    return result


def _format_bytes(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while numeric >= 1024 and index < len(units) - 1:
        numeric /= 1024.0
        index += 1
    return f"{numeric:.1f} {units[index]}"


def _safe_int(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "N/A"
