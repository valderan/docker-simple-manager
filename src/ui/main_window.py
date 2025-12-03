"""Главное окно DSM: объединяет менеджеры, таблицы и диалоги."""

from __future__ import annotations

import logging
import os
from datetime import datetime
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from src.connections.manager import ConnectionManager
from src.connections.models import Connection, ConnectionStatus
from src.docker_api.data_provider import DockerDataProvider
from src.docker_api.exceptions import DockerAPIError
from src.i18n.translator import translate
from src.projects.manager import ProjectManager
from src.settings.registry import SettingsRegistry
from src.ui.dialogs.connections import ConnectionsDialog
from src.ui.dialogs.container_console import ContainerConsoleDialog
from src.ui.dialogs.container_details import ContainerDetailsDialog
from src.ui.dialogs.logs import LogsDialog
from src.ui.dialogs.help import HelpDialog
from src.ui.dialogs.about import AboutDialog
from src.ui.dialogs.projects import ProjectsDialog
from src.ui.dialogs.settings import SettingsDialog
from src.ui.styles.theme_manager import apply_theme
from src.ui.widgets.footer import FooterWidget
from src.ui.widgets.tables import ColumnDefinition, ResourceTable, RowAction
from src.utils.system_metrics import read_system_metrics


class MainWindow(QtWidgets.QMainWindow):
    """Главное окно с вкладками Docker и вспомогательными диалогами."""

    def __init__(
        self,
        *,
        settings: SettingsRegistry,
        connection_manager: ConnectionManager,
        project_manager: ProjectManager,
        docker_data_provider: DockerDataProvider,
        workspace_dir: Path,
    ) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)  # Логгер главного окна
        self._settings = settings
        self._connection_manager = connection_manager
        self._project_manager = project_manager
        self._docker_data_provider = docker_data_provider
        self._workspace_dir = workspace_dir
        self._resources_dir = Path(__file__).resolve().parents[1]
        self._log_dir = workspace_dir / "logs"
        icon_path = self._resources_dir / "resources" / "icons" / "logo-dsm.png"
        self._app_icon = QtGui.QIcon()
        if icon_path.exists():
            base_pixmap = QtGui.QPixmap(str(icon_path))
            for size in (16, 24, 32, 48, 64, 96, 128, 256, 512):
                self._app_icon.addPixmap(
                    base_pixmap.scaled(
                        size,
                        size,
                        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                        QtCore.Qt.TransformationMode.SmoothTransformation,
                    )
                )
            self.setWindowIcon(self._app_icon)
        self._menu_actions: Dict[str, QtGui.QAction] = {}
        self._shortcuts: Dict[str, QtGui.QShortcut] = {}
        self._connection_selector = QtWidgets.QComboBox()
        self._connection_selector.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._refresh_button = QtWidgets.QPushButton(translate("actions.refresh"))
        self._refresh_button.setToolTip(translate("actions.refresh_all_tooltip"))
        self._dashboard_labels: List[QtWidgets.QLabel] = []
        self._status_label = QtWidgets.QLabel()
        self._tabs = QtWidgets.QTabWidget()
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._on_auto_refresh_timer)
        self._container_metrics_timer = QtCore.QTimer(self)
        self._container_metrics_timer.timeout.connect(self._refresh_container_metrics)
        self._system_metrics_timer = QtCore.QTimer(self)
        self._system_metrics_timer.timeout.connect(self._update_system_metrics)
        self._refresh_worker: QtCore.QThread | None = None
        self._refresh_manual_trigger: bool = False
        self._active_refresh_connection: str | None = None
        self._metrics_worker: QtCore.QThread | None = None
        self._current_connection_id: str | None = None
        self._last_refresh_at: datetime | None = None
        self._refresh_in_progress = False

        self._containers_table = self._create_containers_table()
        self._images_table = self._create_images_table()
        self._volumes_table = self._create_volumes_table()
        self._builds_table = self._create_builds_table()
        self._builds_instruction = self._create_builds_instruction()
        self._builds_stack = QtWidgets.QStackedWidget()
        self._buildx_available = False
        self._builds_instruction = self._create_builds_instruction()
        self._builds_tab_widget: QtWidgets.QWidget | None = None
        self._buildx_available = False
        self._footer = FooterWidget()
        self._init_table_state(self._containers_table, "containers")
        self._init_table_state(self._images_table, "images")
        self._init_table_state(self._volumes_table, "volumes")
        self._init_table_state(self._builds_table, "builds")

        self._setup_window()
        self._apply_initial_window_state()
        self._create_menu_bar()
        self._create_status_bar()
        self._apply_hotkeys()
        self._apply_startup_connection_policy()
        self._load_connections()
        self._load_projects_summary()
        self._restore_ui_state()
        self._refresh_data()
        self._start_auto_refresh()
        self._start_metrics_timers()

    # ------------------------------------------------------------------- setup
    def _setup_window(self) -> None:
        self.setWindowTitle(translate("app.title"))
        self.resize(1400, 900)

        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.addWidget(self._build_top_panel())
        root_layout.addWidget(self._build_dashboard())
        root_layout.addWidget(self._build_tabs())
        root_layout.addWidget(self._footer)
        self.setCentralWidget(central)

    def _apply_initial_window_state(self) -> None:
        if self._settings.get_value("app", "window_maximized", default=True):
            self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
            return
        width = int(self._settings.get_value("app", "window_width", default=1400))
        height = int(self._settings.get_value("app", "window_height", default=900))
        x_pos = int(self._settings.get_value("app", "window_x", default=0))
        y_pos = int(self._settings.get_value("app", "window_y", default=0))
        self.resize(width, height)
        self.move(x_pos, y_pos)

    def _build_top_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        layout.addWidget(QtWidgets.QLabel(translate("labels.active_connection")))
        self._connection_selector.currentIndexChanged.connect(self._on_connection_changed)
        layout.addWidget(self._connection_selector, stretch=4)
        self._refresh_button.clicked.connect(self._on_refresh_button_clicked)
        layout.addWidget(self._refresh_button)
        layout.addStretch()
        return panel

    def _build_dashboard(self) -> QtWidgets.QWidget:
        dashboard = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(dashboard)
        connections_label = QtWidgets.QLabel()
        projects_label = QtWidgets.QLabel()
        refresh_label = QtWidgets.QLabel()
        layout.addWidget(connections_label)
        layout.addWidget(projects_label)
        layout.addWidget(refresh_label)
        layout.addStretch()
        self._dashboard_labels = [connections_label, projects_label, refresh_label]
        return dashboard

    def _build_tabs(self) -> QtWidgets.QTabWidget:
        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(
            self._wrap_table_with_actions(self._containers_table, []),
            translate("tabs.containers"),
        )
        self._tabs.addTab(
            self._wrap_table_with_actions(self._images_table, self._images_actions()),
            translate("tabs.images"),
        )
        self._tabs.addTab(
            self._wrap_table_with_actions(self._volumes_table, self._volumes_actions()),
            translate("tabs.volumes"),
        )
        self._builds_table_container = self._wrap_table_with_actions(self._builds_table, [])
        self._builds_stack.addWidget(self._builds_table_container)
        self._builds_stack.addWidget(self._builds_instruction)
        self._tabs.addTab(self._builds_stack, translate("tabs.builds"))
        self._update_builds_tab()
        self._tabs.currentChanged.connect(self._on_tab_changed)
        return self._tabs

    def _wrap_table_with_actions(
        self,
        table: ResourceTable,
        actions: Sequence[tuple[str, Callable[[], None]]],
    ) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(table)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        if actions:
            buttons = QtWidgets.QHBoxLayout()
            for label, handler in actions:
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(handler)
                buttons.addWidget(button)
            buttons.addStretch()
            layout.addLayout(buttons)
        return container

    def _create_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        connections_menu = menu_bar.addMenu(translate("menu.connections"))
        manage_connections = connections_menu.addAction(translate("actions.manage_connections"))
        manage_connections.triggered.connect(self._open_connections_dialog)
        self._menu_actions["open_connections_manager"] = manage_connections
        self.addAction(manage_connections)
        test_action = connections_menu.addAction(translate("actions.test_connection"))
        test_action.triggered.connect(self._test_active_connection)
        self._menu_actions["test_connection"] = test_action
        self.addAction(test_action)

        projects_menu = menu_bar.addMenu(translate("menu.projects"))
        manage_projects = projects_menu.addAction(translate("actions.manage_projects"))
        manage_projects.triggered.connect(self._open_projects_dialog)
        self._menu_actions["open_projects_manager"] = manage_projects
        self.addAction(manage_projects)

        parameters_menu = menu_bar.addMenu(translate("menu.parameters"))
        settings_action = parameters_menu.addAction(translate("menu.settings"))
        settings_action.triggered.connect(self._open_settings_dialog)
        self._menu_actions["open_settings"] = settings_action
        self.addAction(settings_action)
        logs_action = parameters_menu.addAction(translate("menu.logs"))
        logs_action.triggered.connect(self._open_logs_dialog)
        self._menu_actions["open_logs"] = logs_action
        self.addAction(logs_action)

        help_action = parameters_menu.addAction(translate("menu.help"))
        help_action.triggered.connect(self._open_help_dialog)
        self._menu_actions["open_help"] = help_action
        self.addAction(help_action)

        about_action = parameters_menu.addAction(translate("menu.about"))
        about_action.triggered.connect(self._open_about_dialog)
        self._menu_actions["open_about"] = about_action
        self.addAction(about_action)

        exit_action = parameters_menu.addAction(translate("actions.exit"))
        exit_action.triggered.connect(self.close)
        self._menu_actions["exit_app"] = exit_action
        self.addAction(exit_action)

    def _create_status_bar(self) -> None:
        self.statusBar().showMessage(translate("footer.status"))
        self.statusBar().addPermanentWidget(self._status_label)

    def _apply_hotkeys(self) -> None:
        """Применяет текущие настройки горячих клавиш к действиям и шорткатам."""

        hotkeys_group = self._settings.get_group("hotkeys")
        for key, action in self._menu_actions.items():
            sequence = hotkeys_group.get(key)
            if sequence:
                action.setShortcut(QtGui.QKeySequence(sequence))
        for shortcut in self._shortcuts.values():
            shortcut.deleteLater()
        self._shortcuts.clear()

        def register_shortcut(setting_key: str, handler: Callable[[], None]) -> None:
            sequence = hotkeys_group.get(setting_key)
            if not sequence:
                return
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence), self)
            shortcut.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(handler)
            self._shortcuts[setting_key] = shortcut

        register_shortcut("refresh_data", lambda: self._on_refresh_button_clicked())

        def make_tab_handler(idx: int) -> Callable[[], None]:
            def handler() -> None:
                self._switch_to_tab_index(idx)

            return handler

        for index, setting_key in enumerate(
            ["switch_tab_1", "switch_tab_2", "switch_tab_3", "switch_tab_4"]
        ):
            register_shortcut(setting_key, make_tab_handler(index))
        register_shortcut("next_tab", self._switch_to_next_tab)
        register_shortcut("prev_tab", self._switch_to_previous_tab)

    def _apply_startup_connection_policy(self) -> None:
        """Применяет настройку автоактивации соединений при запуске приложения."""

        auto_activate = bool(
            self._settings.get_value(
                "connections",
                "auto_activate_connections",
                default=True,
            )
        )
        if auto_activate:
            return

        changed = False
        for connection in self._connection_manager.list_active_connections():
            self._connection_manager.deactivate_connection(connection.identifier)
            changed = True
        if not changed:
            return

        self._settings.set_value("connections", "default_connection", None)
        self._logger.info(
            "Auto activation disabled: all connections marked inactive on startup.",
        )

    # ---------------------------------------------------------------- dashboard
    def _load_connections(self) -> None:
        self._connection_selector.blockSignals(True)
        self._connection_selector.clear()
        all_connections = self._connection_manager.list_connections()
        active_connections = self._connection_manager.list_active_connections()
        for connection in active_connections:
            label = f"{connection.name} ({connection.type})"
            self._connection_selector.addItem(label, connection.identifier)
        self._connection_selector.blockSignals(False)

        default_connection = self._settings.get_value(
            "connections", "default_connection", default=None
        )
        if default_connection:
            if any(conn.identifier == default_connection for conn in active_connections):
                index = self._connection_selector.findData(default_connection)
                if index >= 0:
                    self._connection_selector.setCurrentIndex(index)
                    self._current_connection_id = default_connection
            else:
                self._settings.set_value("connections", "default_connection", None)

        if not active_connections:
            self._current_connection_id = None
            self._apply_no_active_state(len(all_connections))
            return

        if self._current_connection_id not in {conn.identifier for conn in active_connections}:
            self._select_first_local_connection(active_connections)

        self._apply_active_state()
        self._update_dashboard_counts(len(all_connections), None)
        self._update_footer_engine_status()

    def _load_projects_summary(self) -> None:
        projects_count = len(self._project_manager.list_projects())
        self._update_dashboard_counts(
            len(self._connection_manager.list_connections()), projects_count
        )

    def _select_first_local_connection(self, connections: List[Connection] | None = None) -> None:
        """Выбирает первое доступное локальное соединение."""

        connections = connections or self._connection_manager.list_connections()
        for connection in connections:
            if connection.type != "remote":
                index = self._connection_selector.findData(connection.identifier)
                if index >= 0:
                    self._connection_selector.setCurrentIndex(index)
                    self._current_connection_id = connection.identifier
                    return
        if connections:
            index = self._connection_selector.findData(connections[0].identifier)
            if index >= 0:
                self._connection_selector.setCurrentIndex(index)
                self._current_connection_id = connections[0].identifier
                return
        self._connection_selector.setCurrentIndex(-1)
        self._current_connection_id = None

    def _apply_no_active_state(self, total_connections: int) -> None:
        self._stop_background_fetchers()
        self._refresh_timer.stop()
        self._container_metrics_timer.stop()
        self._system_metrics_timer.stop()
        self._connection_selector.setEnabled(False)
        self._refresh_button.setEnabled(False)
        self._tabs.setEnabled(False)
        self._status_label.setText(translate("messages.create_connection"))
        self._update_dashboard_counts(total_connections, None)

    def _apply_active_state(self) -> None:
        self._connection_selector.setEnabled(True)
        self._refresh_button.setEnabled(True)
        self._tabs.setEnabled(True)
        self._status_label.setText(translate("status.loaded"))

    def _show_loading_state(self) -> None:
        for table in (
            self._containers_table,
            self._images_table,
            self._volumes_table,
            self._builds_table,
        ):
            table.show_placeholder(translate("status.loading_data"))
        self._status_label.setText(translate("status.loading_data"))

    def _stop_background_fetchers(self, *, block: bool = False) -> None:
        if self._refresh_worker is not None:
            self._refresh_worker.requestInterruption()
            if block:
                self._refresh_worker.wait()
            else:
                self._refresh_worker.wait(200)
            if not self._refresh_worker.isRunning():
                self._refresh_worker = None
            self._refresh_in_progress = False
            self._refresh_manual_trigger = False
            self._active_refresh_connection = None
        if self._metrics_worker is not None:
            self._metrics_worker.requestInterruption()
            if block:
                self._metrics_worker.wait()
            else:
                self._metrics_worker.wait(200)
            if not self._metrics_worker.isRunning():
                self._metrics_worker = None
        self._refresh_timer.stop()
        self._container_metrics_timer.stop()
        self._system_metrics_timer.stop()

    def _update_dashboard_counts(self, connections_count: int, projects_count: int | None) -> None:
        if not self._dashboard_labels:
            return
        active_count = len(self._connection_manager.list_active_connections())
        connections_text = (
            "[ "
            + translate("dashboard.connections_detailed").format(
                active=active_count, total=connections_count
            )
            + " ]"
        )
        self._dashboard_labels[0].setText(connections_text)
        if projects_count is not None:
            projects_text = (
                "[ " + translate("dashboard.projects").format(count=projects_count) + " ]"
            )
        else:
            current_text = self._dashboard_labels[1].text().strip()
            projects_text = (
                current_text
                if current_text
                else "[ " + translate("dashboard.projects").format(count=0) + " ]"
            )
        self._dashboard_labels[1].setText(projects_text)
        self._dashboard_labels[1].setText(projects_text)
        auto_refresh = bool(
            self._settings.get_value("connections", "auto_refresh_enabled", default=True)
        )
        if auto_refresh:
            interval = int(self._settings.get_value("connections", "refresh_rate_ms", default=5000))
            refresh_text = (
                "[ " + translate("dashboard.refresh_interval").format(interval=interval) + " ]"
            )
        else:
            refresh_text = "[ " + translate("dashboard.refresh_manual") + " ]"
        self._dashboard_labels[2].setText(refresh_text)

    # ---------------------------------------------------------------- tab state
    def _restore_ui_state(self) -> None:
        last_tab = int(self._settings.get_value("ui_state", "last_active_tab", default=0))
        last_tab = min(last_tab, self._tabs.count() - 1)
        self._tabs.setCurrentIndex(last_tab)

    def _on_tab_changed(self, index: int) -> None:
        self._settings.set_value("ui_state", "last_active_tab", index)

    def _on_connection_changed(self, index: int) -> None:
        connection_id = self._connection_selector.itemData(index)
        if not isinstance(connection_id, str):
            self._buildx_available = self._check_buildx_available(None)
            self._update_builds_tab()
            return
        self._stop_background_fetchers()
        self._show_loading_state()
        self._current_connection_id = connection_id
        try:
            connection = self._connection_manager.get_connection(connection_id)
        except KeyError:
            connection = None
        if connection and connection.type != "remote":
            self._settings.set_value("connections", "default_connection", connection_id)
        else:
            self._settings.set_value("connections", "default_connection", None)
        self._buildx_available = self._check_buildx_available(connection_id)
        self._update_builds_tab()
        self._refresh_data()
        self._update_footer_engine_status()
        self._start_container_metrics_timer()

    def _on_refresh_button_clicked(self) -> None:
        """Запускает ручное обновление всех вкладок через кнопку."""

        self._refresh_data(manual=True)

    # --------------------------------------------------------------- data fetch
    def _refresh_data(self, manual: bool = False) -> None:
        if self._refresh_in_progress or self._refresh_worker is not None:
            return
        connection_id = self._current_connection_id  # Активное соединение Docker
        if not connection_id:
            self._status_label.setText(translate("status.no_connection"))
            for table in (
                self._containers_table,
                self._images_table,
                self._volumes_table,
                self._builds_table,
            ):
                table.set_rows([])
            self._last_refresh_at = None
            self._container_metrics_timer.stop()
            return

        self._refresh_in_progress = True
        self._refresh_manual_trigger = manual
        self._active_refresh_connection = connection_id
        if manual:
            self._set_refresh_button_busy(True)
        self._status_label.setText(translate("status.loading"))
        if manual:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

        worker = DockerFetchThread(
            provider=self._docker_data_provider,
            connection_id=connection_id,
            include_builds=self._buildx_available,
            mode="full",
        )
        worker.data_ready.connect(self._on_refresh_worker_ready)
        worker.error.connect(self._on_refresh_worker_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, "_refresh_worker", None))
        self._refresh_worker = worker
        worker.start()

    def _on_refresh_worker_ready(self, payload: Dict[str, Any]) -> None:
        if payload.get("mode") != "full":
            return
        data = payload.get("data", {})
        containers = data.get("containers", [])
        images = data.get("images", [])
        volumes = data.get("volumes", [])
        builds_data = data.get("builds", [])
        self._containers_table.set_rows(self._format_containers(containers))
        self._images_table.set_rows(self._format_images(images))
        self._volumes_table.set_rows(self._format_volumes(volumes))
        self._builds_table.set_rows(self._format_builds(builds_data))

        if self._system_metrics_timer.isActive():
            self._update_system_metrics()
        else:
            self._footer.update_stats(ram="N/A", cpu="N/A")
        self._last_refresh_at = datetime.now()
        self._update_last_refresh_label()
        if self._refresh_manual_trigger:
            timestamp = self._last_refresh_at.strftime("%H:%M:%S %d/%m/%y")
            self._status_label.setText(translate("status.last_updated").format(timestamp=timestamp))
        else:
            self._status_label.setText(translate("status.loaded"))
        self._finish_refresh_task()

    def _on_refresh_worker_error(self, message: str) -> None:
        connection_id = self._active_refresh_connection or self._current_connection_id or ""
        if connection_id:
            self._handle_connection_error(connection_id, message)
        self._finish_refresh_task()

    def _finish_refresh_task(self) -> None:
        if self._refresh_manual_trigger:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._set_refresh_button_busy(False)
        self._refresh_in_progress = False
        self._refresh_manual_trigger = False
        self._active_refresh_connection = None

    # ------------------------------------------------------------- action bars
    def _images_actions(self) -> List[tuple[str, Callable[[], None]]]:
        return [
            (translate("actions.remove_image"), self._remove_selected_image),
        ]

    def _volumes_actions(self) -> List[tuple[str, Callable[[], None]]]:
        return [
            (translate("actions.remove_volume"), self._remove_selected_volume),
        ]

    # --------------------------------------------------------------- user actions
    def _remove_selected_image(self) -> None:
        row = self._images_table.current_row() or {}  # Активная строка таблицы образов
        image_id = row.get("id")  # Идентификатор выбранного образа
        if image_id and self._current_connection_id:
            image_name = row.get("name") or "-"  # Название образа для логирования
            image_tag = row.get("tag") or "-"  # Тег образа для логирования
            self._logger.info(
                "Image delete requested: connection=%s, image_id=%s, name=%s, tag=%s",
                self._current_connection_id,
                image_id,
                image_name,
                image_tag,
            )
            try:
                success = self._docker_data_provider.remove_image(
                    self._current_connection_id,
                    str(image_id),
                    force=False,
                )
                if success:
                    self._logger.info(
                        "Image delete succeeded: connection=%s, image_id=%s",
                        self._current_connection_id,
                        image_id,
                    )
                    self._refresh_data()
                else:
                    self._logger.error(
                        "Image delete reported failure: connection=%s, image_id=%s",
                        self._current_connection_id,
                        image_id,
                    )
                    self._show_error(
                        "Не удалось удалить выбранный образ. Подробности смотрите в логах."
                    )
            except DockerAPIError as exc:
                self._logger.error(
                    "Image delete raised error: connection=%s, image_id=%s, error=%s",
                    self._current_connection_id,
                    image_id,
                    exc,
                )
                self._show_error(str(exc))

    def _remove_selected_volume(self) -> None:
        row = self._volumes_table.current_row() or {}  # Активная строка таблицы томов
        volume_name = row.get("name")  # Имя удаляемого тома
        if volume_name and self._current_connection_id:
            self._logger.info(
                "Volume delete requested: connection=%s, volume=%s",
                self._current_connection_id,
                volume_name,
            )
            try:
                success = self._docker_data_provider.remove_volume(
                    self._current_connection_id,
                    str(volume_name),
                    force=False,
                )
                if success:
                    self._logger.info(
                        "Volume delete succeeded: connection=%s, volume=%s",
                        self._current_connection_id,
                        volume_name,
                    )
                    self._refresh_data()
                else:
                    self._logger.error(
                        "Volume delete reported failure: connection=%s, volume=%s",
                        self._current_connection_id,
                        volume_name,
                    )
                    self._show_error(
                        "Не удалось удалить выбранный том. Подробности смотрите в логах."
                    )
            except DockerAPIError as exc:
                self._logger.error(
                    "Volume delete raised error: connection=%s, volume=%s, error=%s",
                    self._current_connection_id,
                    volume_name,
                    exc,
                )
                self._show_error(str(exc))

    def _start_container_row(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id:
            return
        self._execute_container_action(
            self._docker_data_provider.start_container,
            str(container_id),
            action_name="start",
            container_name=str(row.get("name") or container_id),
        )

    def _pause_container_row(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id:
            return
        self._execute_container_action(
            self._docker_data_provider.pause_container,
            str(container_id),
            action_name="pause",
            container_name=str(row.get("name") or container_id),
        )

    def _stop_container_row(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id:
            return
        self._execute_container_action(
            self._docker_data_provider.stop_container,
            str(container_id),
            action_name="stop",
            container_name=str(row.get("name") or container_id),
        )

    def _restart_container_row(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id:
            return
        self._execute_container_action(
            self._docker_data_provider.restart_container,
            str(container_id),
            action_name="restart",
            container_name=str(row.get("name") or container_id),
        )

    def _delete_container_row(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id or not self._current_connection_id:
            return
        if (
            QtWidgets.QMessageBox.question(
                self,
                translate("actions.delete_container"),
                translate("messages.confirm_delete"),
            )
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self._execute_container_action(
                lambda conn_id, cont_id: self._docker_data_provider.remove_container(
                    conn_id, cont_id, force=True
                ),
                str(container_id),
                action_name="delete",
                container_name=str(row.get("name") or container_id),
            )

    def _view_container_details(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id or not self._current_connection_id:
            return
        try:
            logs = self._docker_data_provider.fetch_container_logs(
                self._current_connection_id, str(container_id)
            )
            inspect_data = self._docker_data_provider.inspect_container(
                self._current_connection_id, str(container_id)
            )
        except DockerAPIError as exc:
            self._show_error(str(exc))
            return
        dialog = ContainerDetailsDialog(
            container_name=row.get("name", str(container_id)),
            logs=logs,
            inspect_data=inspect_data,
            parent=self,
        )
        dialog.exec()

    # --------------------------------------------------------------- auto refresh
    def _start_auto_refresh(self) -> None:
        self._refresh_timer.stop()
        enabled = bool(
            self._settings.get_value("connections", "auto_refresh_enabled", default=True)
        )
        if not enabled:
            return
        refresh_rate = int(self._settings.get_value("connections", "refresh_rate_ms", default=5000))
        if refresh_rate <= 0:
            return
        self._refresh_timer.start(refresh_rate)
        self._start_container_metrics_timer()

    def _start_metrics_timers(self) -> None:
        """Перезапускает таймеры метрик согласно настройкам."""

        self._start_container_metrics_timer()
        self._start_system_metrics_timer()

    def _start_container_metrics_timer(self) -> None:
        """Настраивает таймер обновления метрик контейнеров."""

        self._container_metrics_timer.stop()
        connection_id = self._current_connection_id
        if not connection_id:
            return
        interval = int(
            self._settings.get_value("metrics", "container_stats_refresh_ms", default=5000)
        )
        if interval <= 0:
            return
        self._container_metrics_timer.start(interval)

    def _start_system_metrics_timer(self) -> None:
        """Настраивает таймер системных метрик."""

        self._system_metrics_timer.stop()
        metrics_group = self._settings.get_group("metrics")
        if not metrics_group.get("system_metrics_enabled"):
            self._footer.update_stats(ram="N/A", cpu="N/A")
            return
        interval = int(metrics_group.get("system_metrics_refresh_ms"))
        if interval <= 0:
            self._footer.update_stats(ram="N/A", cpu="N/A")
            return
        self._system_metrics_timer.start(interval)
        self._update_system_metrics()

    def _switch_to_tab_index(self, index: int) -> None:
        """Переключает вкладку по индексу, если он в пределах диапазона."""

        if index < 0 or index >= self._tabs.count():
            return
        self._tabs.setCurrentIndex(index)

    def _switch_to_next_tab(self) -> None:
        """Активирует следующую вкладку."""

        count = self._tabs.count()
        if count == 0:
            return
        self._tabs.setCurrentIndex((self._tabs.currentIndex() + 1) % count)

    def _switch_to_previous_tab(self) -> None:
        """Активирует предыдущую вкладку."""

        count = self._tabs.count()
        if count == 0:
            return
        self._tabs.setCurrentIndex((self._tabs.currentIndex() - 1) % count)

    # --------------------------------------------------------------- dialogs etc
    def _open_connections_dialog(self) -> None:
        dialog = ConnectionsDialog(self._connection_manager, parent=self)
        dialog.exec()
        if getattr(dialog, "has_changes", False):
            self._load_connections()
            self._refresh_data()

    def _open_projects_dialog(self) -> None:
        dialog = ProjectsDialog(
            project_manager=self._project_manager,
            connection_manager=self._connection_manager,
            parent=self,
        )
        if dialog.exec():
            self._load_projects_summary()

    def _test_active_connection(self) -> None:
        connection_id = self._current_connection_id
        if not connection_id:
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.no_connection_title"),
                translate("messages.no_connection_body"),
            )
            return
        status = self._connection_manager.test_connection(connection_id)
        QtWidgets.QMessageBox.information(
            self,
            translate("messages.test_result_title"),
            translate("messages.test_result_body").format(status=status.value),
        )
        self._refresh_data()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(
            settings=self._settings,
            connection_manager=self._connection_manager,
            parent=self,
        )
        if dialog.exec():
            app_instance = QtWidgets.QApplication.instance()
            if isinstance(app_instance, QtWidgets.QApplication):
                apply_theme(app_instance, self._settings)
            self._refresh_timer.stop()
            self._start_auto_refresh()
            self._load_connections()
            self._update_last_refresh_label()
            self._start_metrics_timers()
            self._update_builds_tab()
            self._apply_hotkeys()

    def _open_logs_dialog(self) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        dialog = LogsDialog(log_dir=self._log_dir, parent=self)
        dialog.exec()

    def _open_help_dialog(self) -> None:
        dialog = HelpDialog(
            language=self._settings.get_value("app", "language", default="ru"),
            resources_dir=self._resources_dir,
            parent=self,
        )
        dialog.exec()

    def _open_about_dialog(self) -> None:
        dialog = AboutDialog(
            icon=self._app_icon if hasattr(self, "_app_icon") else None, parent=self
        )
        dialog.exec()

    def _open_container_shell(self, row: Dict[str, Any]) -> None:
        container_id = row.get("id")
        if not container_id or not self._current_connection_id:
            return
        try:
            docker_host = self._connection_manager.get_connection(
                self._current_connection_id
            ).socket
        except KeyError:
            docker_host = None
        terminal_group = self._settings.get_group("terminal")
        use_system_console = terminal_group.get("use_system_console")
        if use_system_console:
            self._open_system_console(str(container_id), docker_host)
            return
        shell_value = terminal_group.get("container_shell") or "/bin/sh"
        dialog = ContainerConsoleDialog(
            container_id=str(container_id),
            container_name=row.get("name", str(container_id)),
            shell_command=shell_value,
            docker_host=docker_host,
            parent=self,
        )
        dialog.exec()

    def _open_system_console(self, container_id: str, docker_host: str | None) -> None:
        command = ["x-terminal-emulator", "-e", "docker", "exec", "-it", container_id, "/bin/bash"]
        env = os.environ.copy()
        if docker_host:
            env["DOCKER_HOST"] = docker_host
        else:
            env.pop("DOCKER_HOST", None)
        try:
            subprocess.Popen(command, env=env)
        except OSError:
            QtWidgets.QMessageBox.warning(
                self,
                translate("terminal.errors.title"),
                translate("terminal.errors.start_failed").format(
                    cmd=" ".join(["docker", "exec", "-it", container_id, "/bin/bash"])
                ),
            )

    # -------------------------------------------------------------- formatting
    def _format_containers(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        for row in rows:
            formatted.append(
                {
                    "stack": row.get("project") or row.get("name") or "Compose stack",
                    "name": row.get("name", ""),
                    "id": row.get("id", ""),
                    "image": (
                        ", ".join(row.get("image", []))
                        if isinstance(row.get("image"), list)
                        else row.get("image", "")
                    ),
                    "ports": ", ".join(row.get("ports", [])) if row.get("ports") else "-",
                    "cpu_percent": row.get("cpu_percent", "N/A"),
                    "memory_usage": row.get("memory_usage", "N/A"),
                    "memory_percent": row.get("memory_percent", "N/A"),
                    "disk_io": row.get("disk_io", "N/A"),
                    "network_io": row.get("network_io", "N/A"),
                    "pids": row.get("pids", "N/A"),
                    "status": row.get("status", ""),
                }
            )
        return formatted

    def _format_images(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        for row in rows:
            tags = row.get("tags") or []
            formatted.append(
                {
                    "name": tags[0] if tags else translate("tables.group_unknown"),
                    "tag": tags[0].split(":")[1] if tags and ":" in tags[0] else "-",
                    "id": row.get("id", ""),
                    "created": row.get("created", "N/A"),
                    "size": self._format_size(row.get("size")),
                }
            )
        return formatted

    def _format_volumes(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        for row in rows:
            formatted.append(
                {
                    "name": row.get("name", ""),
                    "driver": row.get("driver", ""),
                    "mountpoint": row.get("mountpoint", ""),
                    "created": row.get("created", "N/A"),
                    "size": self._format_size(row.get("size")),
                }
            )
        return formatted

    def _format_builds(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = []
        default_builder = translate("builds.builder_default")
        for row in rows:
            builder = row.get("builder") or default_builder
            formatted.append(
                {
                    "name": row.get("name", "build"),
                    "id": row.get("id", ""),
                    "builder": builder,
                    "duration": row.get("duration", "N/A"),
                    "created": row.get("created", "N/A"),
                    "author": row.get("author", "-"),
                    "is_mine": bool(row.get("is_mine")),
                }
            )
        return formatted

    def _format_size(self, size_bytes: Any) -> str:
        if not isinstance(size_bytes, (int, float)):
            return "N/A"
        size = float(size_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        index = 0
        while size >= 1024 and index < len(units) - 1:
            size /= 1024.0
            index += 1
        return f"{size:.1f} {units[index]}"

    def _parse_shell_command(self, value: str) -> tuple[str, List[str]] | None:
        try:
            parts = shlex.split(value)
        except ValueError:
            return None
        if not parts:
            return None
        return parts[0], parts[1:]

    def _execute_container_action(
        self,
        func: Callable[[str, str], bool],
        container_id: str,
        *,
        action_name: str,
        container_name: str,
    ) -> None:
        if not self._current_connection_id:
            return
        connection_id = self._current_connection_id
        self._logger.info(
            "Container action %s requested: connection=%s, container_id=%s, name=%s",
            action_name,
            connection_id,
            container_id,
            container_name,
        )
        try:
            success = func(connection_id, container_id)
            if success:
                self._logger.info(
                    "Container action %s succeeded: connection=%s, container_id=%s",
                    action_name,
                    connection_id,
                    container_id,
                )
                self._refresh_data()
            else:
                self._logger.error(
                    "Container action %s reported failure: connection=%s, container_id=%s",
                    action_name,
                    connection_id,
                    container_id,
                )
                self._show_error(
                    "Не удалось выполнить действие над контейнером. Подробности смотрите в логах."
                )
        except DockerAPIError as exc:
            self._logger.error(
                "Container action %s raised error: connection=%s, container_id=%s, error=%s",
                action_name,
                connection_id,
                container_id,
                exc,
            )
            self._show_error(str(exc))

    def _show_error(self, message: str) -> None:
        self._logger.error("UI error: %s", message)  # Логируем каждую ошибку интерфейса
        QtWidgets.QMessageBox.critical(
            self,
            translate("terminal.errors.title"),
            message,
        )

    # -------------------------------------------------------------- table factory
    def _create_containers_table(self) -> ResourceTable:
        columns = [
            ColumnDefinition("Name", "name"),
            ColumnDefinition("Container ID", "id"),
            ColumnDefinition("Image", "image"),
            ColumnDefinition("Port(s)", "ports"),
            ColumnDefinition("CPU (%)", "cpu_percent"),
            ColumnDefinition("Memory usage", "memory_usage"),
            ColumnDefinition("Memory (%)", "memory_percent"),
            ColumnDefinition("Disk", "disk_io"),
            ColumnDefinition("Network I/O", "network_io"),
            ColumnDefinition("PIDs", "pids"),
        ]
        row_actions = [
            RowAction("▶", translate("actions.start_container"), self._start_container_row),
            RowAction("⏸", translate("actions.pause_container"), self._pause_container_row),
            RowAction("■", translate("actions.stop_container"), self._stop_container_row),
            RowAction("↻", translate("actions.restart_container"), self._restart_container_row),
            RowAction("🗑", translate("actions.delete_container"), self._delete_container_row),
            RowAction("ℹ", translate("actions.view_details"), self._view_container_details),
            RowAction("⌨", translate("actions.open_cmd"), self._open_container_shell),
        ]

        def highlight_running(item: QtWidgets.QTreeWidgetItem, row: Dict[str, Any]) -> None:
            status = str(row.get("status", "")).lower()
            if status.startswith("up") or status.startswith("running"):
                item.setForeground(0, QtGui.QBrush(QtGui.QColor("#00c853")))
            elif "pause" in status:
                item.setForeground(0, QtGui.QBrush(QtGui.QColor("#fdd835")))
            else:
                item.setForeground(0, QtGui.QBrush())

        return ResourceTable(
            columns=columns,
            group_key="stack",
            toggle_label=translate("tables.only_running"),
            toggle_filter=lambda row: str(row.get("status", "")).lower().startswith("run"),
            row_actions=row_actions,
            row_post_processor=highlight_running,
        )

    def _create_images_table(self) -> ResourceTable:
        columns = [
            ColumnDefinition("Name", "name"),
            ColumnDefinition("Tag", "tag"),
            ColumnDefinition("Image ID", "id"),
            ColumnDefinition("Created", "created"),
            ColumnDefinition("Size", "size"),
        ]
        return ResourceTable(columns=columns)

    def _create_volumes_table(self) -> ResourceTable:
        columns = [
            ColumnDefinition("Name", "name"),
            ColumnDefinition("Driver", "driver"),
            ColumnDefinition("Mount point", "mountpoint"),
            ColumnDefinition("Created", "created"),
            ColumnDefinition("Size", "size"),
        ]
        table = ResourceTable(columns=columns)
        tree = table.tree
        tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._on_volume_context_menu)
        return table

    def _create_builds_table(self) -> ResourceTable:
        columns = [
            ColumnDefinition("Name", "name"),
            ColumnDefinition("ID", "id"),
            ColumnDefinition("Builder", "builder"),
            ColumnDefinition("Duration", "duration"),
            ColumnDefinition("Created", "created"),
            ColumnDefinition("Author", "author"),
        ]
        return ResourceTable(
            columns=columns,
            toggle_label=translate("tables.only_my_builds"),
            toggle_filter=lambda row: bool(row.get("is_mine")),
        )

    def _create_builds_instruction(self) -> QtWidgets.QTextBrowser:
        widget = QtWidgets.QTextBrowser()
        widget.setReadOnly(True)
        widget.setOpenExternalLinks(True)
        widget.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        widget.setObjectName("buildsInstruction")
        widget.setStyleSheet("QTextBrowser { padding: 16px; }")
        widget.setHtml(self._get_buildx_instruction_html())
        return widget

    def _refresh_container_metrics(self) -> None:
        """Обновляет метрики контейнеров без затрагивания остальных вкладок."""

        if self._refresh_in_progress or self._metrics_worker is not None:
            return
        connection_id = self._current_connection_id
        if not connection_id:
            self._container_metrics_timer.stop()
            return
        worker = DockerFetchThread(
            provider=self._docker_data_provider,
            connection_id=connection_id,
            include_builds=False,
            mode="containers",
        )
        worker.data_ready.connect(self._on_metrics_worker_ready)
        worker.error.connect(self._on_metrics_worker_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, "_metrics_worker", None))
        self._metrics_worker = worker
        worker.start()

    def _on_metrics_worker_ready(self, payload: Dict[str, Any]) -> None:
        if payload.get("mode") != "containers":
            return
        data = payload.get("data", {})
        containers = data.get("containers", [])
        self._containers_table.set_rows(self._format_containers(containers))

    def _on_metrics_worker_error(self, _: str) -> None:
        pass

    def _update_system_metrics(self) -> None:
        """Обновляет футер значениями системных метрик."""

        try:
            metrics = read_system_metrics()
        except Exception:
            self._footer.update_stats(ram="N/A", cpu="N/A")
            return
        self._footer.update_stats(ram=metrics.ram, cpu=metrics.cpu)

    def _check_buildx_available(self, connection_id: str | None) -> bool:
        """Проверяет наличие Docker Buildx для выбранного соединения."""

        env = self._docker_data_provider.build_cli_env(connection_id)
        try:
            subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def _get_buildx_instruction_html(self) -> str:
        """Возвращает HTML инструкции по установке Buildx."""

        title = translate("builds.instructions.title")
        if platform.system() == "Linux":
            body = translate("builds.instructions.body_linux")
        else:
            body = translate("builds.instructions.body_desktop")
        body_html = "<br>".join(body.splitlines())
        return f"<h3>{title}</h3><p>{body_html}</p>"

    def _update_builds_tab(self) -> None:
        """Переключает содержимое вкладки «Сборки»."""

        if not hasattr(self, "_builds_stack"):
            return
        self._builds_instruction.setHtml(self._get_buildx_instruction_html())
        if self._buildx_available:
            self._builds_stack.setCurrentWidget(self._builds_table_container)
        else:
            self._builds_stack.setCurrentWidget(self._builds_instruction)

    def _on_volume_context_menu(self, point: QtCore.QPoint) -> None:
        if not self._volumes_table:
            return
        tree = self._volumes_table.tree
        index = tree.indexAt(point)
        if index.column() != 2:
            return
        item = tree.itemAt(point)
        if item is None:
            return
        row = item.data(0, QtCore.Qt.ItemDataRole.UserRole) or {}
        mountpoint = row.get("mountpoint")
        if not mountpoint:
            return
        menu = QtWidgets.QMenu(self)
        action = menu.addAction(translate("volumes.actions.copy_mountpoint"))

        def copy_mount() -> None:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(str(mountpoint))
            self.statusBar().showMessage(
                translate("volumes.messages.mountpoint_copied"),
                3000,
            )

        action.triggered.connect(copy_mount)
        menu.exec(tree.viewport().mapToGlobal(point))

    # -------------------------------------------------------------- footer utils
    def _update_footer_engine_status(self) -> None:
        connection: ConnectionStatus | None = None
        if self._current_connection_id:
            try:
                connection = self._connection_manager.get_connection(
                    self._current_connection_id
                ).status
            except KeyError:
                connection = None
        status_text = translate("footer.engine_running")
        if connection:
            status_text = f"{translate('footer.engine_running')} ({connection.value})"
        self._footer.update_engine_status(status_text)

    # -------------------------------------------------------------- state helpers
    def _init_table_state(self, table: ResourceTable, table_id: str) -> None:
        header = table.tree.header()
        widths = self._get_saved_column_widths(table_id)
        if widths:
            for index, width in enumerate(widths):
                if index < header.count():
                    header.resizeSection(index, width)
        header.sectionResized.connect(
            lambda *_args, tbl=table, tid=table_id: self._save_table_column_widths(tbl, tid)
        )

    def _get_saved_column_widths(self, table_id: str) -> List[int]:
        state = self._settings.get_value("ui_state", "column_widths", default={})
        if isinstance(state, dict):
            raw_widths = state.get(table_id)
            if isinstance(raw_widths, list):
                try:
                    return [int(value) for value in raw_widths]
                except (TypeError, ValueError):
                    return []
        return []

    def _save_table_column_widths(self, table: ResourceTable, table_id: str) -> None:
        header = table.tree.header()
        widths = [header.sectionSize(i) for i in range(header.count())]
        state = dict(self._settings.get_value("ui_state", "column_widths", default={}))
        state[table_id] = widths
        self._settings.set_value("ui_state", "column_widths", state)

    def _handle_connection_error(self, connection_id: str, error_message: str) -> None:
        """Обрабатывает ошибки подключения, предлагая отключить соединение."""

        timeout = int(self._settings.get_value("connections", "connection_timeout_sec", default=5))
        try:
            connection = self._connection_manager.get_connection(connection_id)
        except KeyError:
            connection = None
        connection_name = (
            connection.name if connection else connection_id
        )  # Имя соединения для текста сообщения
        self._logger.error(
            "Connection error detected: connection=%s, name=%s, error=%s",
            connection_id,
            connection_name,
            error_message,
        )
        message = translate("messages.connection_timeout_body").format(
            name=connection_name,
            seconds=timeout,
            error=error_message,
        )
        result = QtWidgets.QMessageBox.question(
            self,
            translate("messages.connection_timeout_title"),
            message,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                self._connection_manager.deactivate_connection(connection_id)
            except KeyError:
                pass
            self._settings.set_value("connections", "default_connection", None)
            self._load_connections()
        self._status_label.setText(error_message)

    def _set_refresh_button_busy(self, busy: bool) -> None:
        """Отображает визуальный отклик кнопки обновления."""

        self._refresh_button.setDown(busy)
        self._refresh_button.setEnabled(not busy)
        QtWidgets.QApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )

    def _update_last_refresh_label(self) -> None:
        """Обновляет текст статуса с информацией о времени последнего обновления."""

        if not self._last_refresh_at:
            self._status_label.setText(translate("status.loaded"))
            return
        timestamp = self._last_refresh_at.strftime("%H:%M:%S %d/%m/%y")
        self._status_label.setText(translate("status.last_updated").format(timestamp=timestamp))

    def _on_auto_refresh_timer(self) -> None:
        """Обработчик таймера автообновления."""

        self._refresh_data()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._stop_background_fetchers(block=True)
        maximized = self.isMaximized()
        self._settings.set_value("app", "window_maximized", maximized)
        if not maximized:
            geometry = self.geometry()
            self._settings.set_value("app", "window_width", geometry.width())
            self._settings.set_value("app", "window_height", geometry.height())
            self._settings.set_value("app", "window_x", geometry.x())
            self._settings.set_value("app", "window_y", geometry.y())
        self._settings.save_to_disk()
        super().closeEvent(event)


def create_main_window(
    *,
    settings: SettingsRegistry,
    connection_manager: ConnectionManager,
    project_manager: ProjectManager,
    docker_data_provider: DockerDataProvider,
    workspace_dir: Path,
) -> MainWindow:
    """Фабрика главного окна."""

    return MainWindow(
        settings=settings,
        connection_manager=connection_manager,
        project_manager=project_manager,
        docker_data_provider=docker_data_provider,
        workspace_dir=workspace_dir,
    )


class DockerFetchThread(QtCore.QThread):
    """Фоновая задача запросов к Docker API для разгрузки UI."""

    data_ready = QtCore.Signal(dict)
    error = QtCore.Signal(str)

    def __init__(
        self,
        *,
        provider: DockerDataProvider,
        connection_id: str,
        include_builds: bool,
        mode: str,
    ) -> None:
        super().__init__()
        self._provider = provider
        self._connection_id = connection_id
        self._include_builds = include_builds
        self._mode = mode

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return
            if self._mode == "containers":
                containers = self._provider.fetch_containers(self._connection_id)
                self.data_ready.emit({"mode": self._mode, "data": {"containers": containers}})
                return

            if self.isInterruptionRequested():
                return
            containers = self._provider.fetch_containers(self._connection_id)
            if self.isInterruptionRequested():
                return
            images = self._provider.fetch_images(self._connection_id)
            if self.isInterruptionRequested():
                return
            volumes = self._provider.fetch_volumes(self._connection_id)
            builds_data: List[Dict[str, Any]] = []
            if self._include_builds:
                if self.isInterruptionRequested():
                    return
                builds_data = self._provider.fetch_builds(self._connection_id)
            self.data_ready.emit(
                {
                    "mode": self._mode,
                    "data": {
                        "containers": containers,
                        "images": images,
                        "volumes": volumes,
                        "builds": builds_data,
                    },
                }
            )
        except DockerAPIError as exc:
            self.error.emit(str(exc))
