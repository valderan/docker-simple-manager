"""Определения дефолтной схемы конфигурации, используемой до Фазы 1."""

from __future__ import annotations

from typing import Any, Dict

# DEFAULT_CONFIG служит шаблоном для начального config.json
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0.0",
    "schema_version": 1,
    "app": {
        "language": "ru",
        "theme": "system",
        "window": {
            "width": 1280,
            "height": 720,
            "x": 0,
            "y": 0,
            "maximized": True,
        },
        "save_window_state": True,
    },
    "logging": {
        "enabled": True,
        "level": "INFO",
        "max_file_size_mb": 10,
        "max_archived_files": 5,
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    "metrics": {
        "container_stats_refresh_ms": 5000,
        "system_metrics_enabled": True,
        "system_metrics_refresh_ms": 3000,
    },
}
