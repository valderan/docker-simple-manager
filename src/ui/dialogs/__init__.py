"""Пакет диалоговых окон."""

from .connections import ConnectionsDialog
from .projects import ProjectsDialog
from .settings import SettingsDialog
from .help import HelpDialog

__all__ = [
    "ConnectionsDialog",
    "ProjectsDialog",
    "SettingsDialog",
    "HelpDialog",
]
