"""Высокоуровневые утилиты для создания и запуска GUI приложения DSM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PySide6 import QtCore, QtGui, QtWidgets

from src.connections.manager import ConnectionManager
from src.docker_api.data_provider import DockerDataProvider
from src.i18n.translator import set_language
from src.projects.manager import ProjectManager
from src.settings.registry import SettingsRegistry
from src.ui.main_window import create_main_window
from src.ui.styles.theme_manager import apply_theme


class RunnableApp(Protocol):
    """Интерфейс приложения, которое можно запустить и получить код возврата."""

    def run(self) -> int:  # pragma: no cover - протокол
        """Запускает цикл приложения и возвращает код завершения."""


@dataclass
class GUIApp:
    """Реализация приложения PySide6 с передачей всех менеджеров в UI."""

    settings: SettingsRegistry
    connection_manager: ConnectionManager
    project_manager: ProjectManager
    docker_data_provider: DockerDataProvider
    workspace_dir: Path

    def __post_init__(self) -> None:
        """Создаёт экземпляр QApplication и главное окно."""

        self._qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app_instance = QtWidgets.QApplication.instance()
        if isinstance(app_instance, QtWidgets.QApplication):
            apply_theme(app_instance, self.settings)
            icon_path = (
                Path(__file__).resolve().parent / "ui" / "resources" / "icons" / "logo-dsm.png"
            )
            if icon_path.exists():
                icon = QtGui.QIcon()
                pixmap = QtGui.QPixmap(str(icon_path))
                for size in (16, 24, 32, 48, 64, 128, 256, 512):
                    icon.addPixmap(
                        pixmap.scaled(
                            size,
                            size,
                            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                            QtCore.Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                app_instance.setWindowIcon(icon)
        set_language(self.settings.get_value("app", "language", default="en"))
        self._window = create_main_window(
            settings=self.settings,
            connection_manager=self.connection_manager,
            project_manager=self.project_manager,
            docker_data_provider=self.docker_data_provider,
            workspace_dir=self.workspace_dir,
        )

    def run(self) -> int:
        """Запускает основной цикл приложения."""

        self._window.show()
        return self._qt_app.exec()


def create_application(
    settings: SettingsRegistry,
    connection_manager: ConnectionManager,
    project_manager: ProjectManager,
    docker_data_provider: DockerDataProvider,
    workspace_dir: Path,
) -> RunnableApp:
    """Фабрика GUI приложения."""

    return GUIApp(
        settings=settings,
        connection_manager=connection_manager,
        project_manager=project_manager,
        docker_data_provider=docker_data_provider,
        workspace_dir=workspace_dir,
    )
