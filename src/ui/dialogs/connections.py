"""Диалоги управления соединениями Docker."""

from __future__ import annotations

import logging
import os
import platform
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.connections.docker_client import get_docker_version
from src.connections.manager import ConnectionManager
from src.connections.models import Connection, ConnectionStatus, SSHConfig
from src.i18n.translator import translate
from src.utils.helpers import normalize_socket_path

DEFAULT_LOCAL_SOCKET = "unix:///var/run/docker.sock"
DEFAULT_REMOTE_SOCKET = "/var/run/docker.sock"


class ConnectionFormDialog(QtWidgets.QDialog):
    """Форма создания/редактирования соединения с поддержкой прокрутки."""

    def __init__(
        self,
        *,
        connection: Optional[Connection] = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._result: Optional[Connection] = None
        self._test_thread: Optional[ConnectionProbeThread] = None
        self.setWindowTitle(translate("connections.form.title"))
        self.resize(640, 720)
        self._build_ui()
        if connection:
            self._populate_form(connection)

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.addWidget(self._build_general_group())
        content_layout.addWidget(self._build_ssh_group())
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._test_status_label = QtWidgets.QLabel()
        layout.addWidget(self._test_status_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("connections.form.section.general"))
        form = QtWidgets.QFormLayout(group)
        self._id_edit = QtWidgets.QLineEdit()
        self._name_edit = QtWidgets.QLineEdit()
        self._comment_edit = QtWidgets.QLineEdit()
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.addItems(["local", "remote"])
        self._type_combo.currentTextChanged.connect(self._update_ssh_visibility)

        socket_row = QtWidgets.QWidget()
        socket_layout = QtWidgets.QHBoxLayout(socket_row)
        socket_layout.setContentsMargins(0, 0, 0, 0)
        self._socket_edit = QtWidgets.QLineEdit(DEFAULT_LOCAL_SOCKET)
        self._socket_picker = QtWidgets.QToolButton()
        self._socket_picker.setText("…")
        self._socket_picker.setToolTip(translate("connections.form.detect_sockets"))
        self._socket_picker.clicked.connect(self._show_socket_picker)
        socket_layout.addWidget(self._socket_edit, stretch=1)
        socket_layout.addWidget(self._socket_picker)

        self._test_button = QtWidgets.QPushButton(translate("connections.form.test"))
        self._test_button.clicked.connect(self._test_connection)

        form.addRow(translate("connections.fields.id"), self._id_edit)
        form.addRow(translate("connections.fields.name"), self._name_edit)
        form.addRow(translate("connections.fields.comment"), self._comment_edit)
        form.addRow(translate("connections.fields.type"), self._type_combo)
        form.addRow(translate("connections.fields.socket"), socket_row)
        form.addRow("", self._test_button)
        return group

    def _build_ssh_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("connections.form.section.ssh"))
        form = QtWidgets.QFormLayout(group)
        self._ssh_host = QtWidgets.QLineEdit()
        self._ssh_port = QtWidgets.QSpinBox()
        self._ssh_port.setRange(1, 65535)
        self._ssh_port.setValue(22)
        self._ssh_user = QtWidgets.QLineEdit("root")
        self._ssh_password = QtWidgets.QLineEdit()
        self._ssh_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self._use_ssh_key = QtWidgets.QCheckBox(translate("connections.form.use_ssh_key"))
        self._use_ssh_key.toggled.connect(self._update_ssh_key_state)
        ssh_key_row = QtWidgets.QWidget()
        ssh_key_layout = QtWidgets.QHBoxLayout(ssh_key_row)
        ssh_key_layout.setContentsMargins(0, 0, 0, 0)
        self._ssh_key = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QToolButton()
        browse_button.setText("📁")
        browse_button.setToolTip(translate("connections.actions.choose_ssh_key"))
        browse_button.clicked.connect(self._browse_ssh_key)
        ssh_key_layout.addWidget(self._ssh_key)
        ssh_key_layout.addWidget(browse_button)

        self._remote_socket_edit = QtWidgets.QLineEdit(DEFAULT_REMOTE_SOCKET)

        form.addRow(translate("connections.fields.ssh_host"), self._ssh_host)
        form.addRow(translate("connections.fields.ssh_port"), self._ssh_port)
        form.addRow(translate("connections.fields.ssh_user"), self._ssh_user)
        form.addRow(translate("connections.fields.ssh_password"), self._ssh_password)
        form.addRow(self._use_ssh_key)
        form.addRow(translate("connections.fields.ssh_key"), ssh_key_row)
        form.addRow(translate("connections.fields.remote_socket"), self._remote_socket_edit)
        self._update_ssh_visibility(self._type_combo.currentText())
        return group

    def _update_ssh_visibility(self, connection_type: str) -> None:
        is_remote = connection_type == "remote"
        for widget in (
            self._ssh_host,
            self._ssh_port,
            self._ssh_user,
            self._ssh_password,
            self._use_ssh_key,
            self._ssh_key,
            self._remote_socket_edit,
        ):
            widget.setEnabled(is_remote)
        self._socket_picker.setEnabled(connection_type == "local")
        self._update_ssh_key_state(self._use_ssh_key.isChecked() and is_remote)

    def _update_ssh_key_state(self, checked: bool) -> None:
        self._ssh_key.setEnabled(checked)

    def _populate_form(self, connection: Connection) -> None:
        self._id_edit.setText(connection.identifier)
        self._id_edit.setEnabled(False)
        self._name_edit.setText(connection.name)
        self._comment_edit.setText(connection.comment)
        index = self._type_combo.findText(connection.type)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)
        if connection.type == "remote":
            self._socket_edit.setText(DEFAULT_LOCAL_SOCKET)
            self._remote_socket_edit.setText(connection.socket or DEFAULT_REMOTE_SOCKET)
        else:
            self._socket_edit.setText(normalize_socket_path(connection.socket))
            self._remote_socket_edit.setText(DEFAULT_REMOTE_SOCKET)
        if connection.ssh:
            self._ssh_host.setText(connection.ssh.host)
            self._ssh_port.setValue(connection.ssh.port)
            self._ssh_user.setText(connection.ssh.username)
            if connection.ssh.password:
                self._ssh_password.setText(connection.ssh.password)
            if connection.ssh.key_path:
                self._use_ssh_key.setChecked(True)
                self._ssh_key.setText(connection.ssh.key_path)

    def _show_socket_picker(self) -> None:
        sockets = discover_docker_sockets()
        if not sockets:
            QtWidgets.QMessageBox.information(
                self,
                translate("connections.form.detect_sockets"),
                translate("connections.messages.no_sockets_found"),
            )
            return
        selection, ok = QtWidgets.QInputDialog.getItem(
            self,
            translate("connections.form.select_socket"),
            translate("connections.messages.choose_socket"),
            sockets,
            editable=False,
        )
        if ok and selection:
            self._socket_edit.setText(normalize_socket_path(selection))

    def _browse_ssh_key(self) -> None:
        ssh_dir = Path.home() / ".ssh"
        start_dir = ssh_dir if ssh_dir.exists() else Path.home()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            translate("connections.actions.choose_ssh_key"),
            str(start_dir),
        )
        if file_path:
            self._ssh_key.setText(file_path)

    def _build_connection_model(self) -> Optional[Connection]:
        identifier = self._id_edit.text().strip()
        name = self._name_edit.text().strip()
        socket = self._socket_edit.text().strip()
        if not identifier or not name or not socket:
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                translate("messages.validation_connection"),
            )
            return None
        connection_type = self._type_combo.currentText()
        if connection_type != "remote":
            socket = normalize_socket_path(socket)
        ssh_config: Optional[SSHConfig] = None
        remote_socket = socket
        if connection_type == "remote":
            host = self._ssh_host.text().strip()
            if not host:
                QtWidgets.QMessageBox.warning(
                    self,
                    translate("messages.validation_error_title"),
                    translate("messages.validation_connection"),
                )
                return None
            remote_socket = self._remote_socket_edit.text().strip() or DEFAULT_REMOTE_SOCKET
            ssh_config = SSHConfig(
                host=host,
                port=int(self._ssh_port.value()),
                username=self._ssh_user.text().strip() or "root",
                password=self._ssh_password.text().strip() or None,
                key_path=(
                    self._ssh_key.text().strip() or None if self._use_ssh_key.isChecked() else None
                ),
            )
        return Connection(
            identifier=identifier,
            name=name,
            socket=remote_socket if connection_type == "remote" else socket,
            type=connection_type,
            comment=self._comment_edit.text().strip(),
            ssh=ssh_config,
        )

    def _test_connection(self) -> None:
        connection = self._build_connection_model()
        if connection is None:
            return
        self._test_button.setEnabled(False)
        self._test_status_label.setText(translate("connections.form.test"))
        thread = ConnectionProbeThread(connection)
        thread.success.connect(self._on_test_success)
        thread.error.connect(self._on_test_error)
        thread.finished.connect(lambda: self._test_button.setEnabled(True))
        thread.finished.connect(lambda: setattr(self, "_test_thread", None))
        thread.finished.connect(thread.deleteLater)
        self._test_thread = thread
        thread.start()

    def _on_test_success(self, message: str) -> None:
        self._test_status_label.setText(translate("connections.form.test_ok") + f" ({message})")

    def _on_test_error(self, message: str) -> None:
        self._test_status_label.setText(translate("connections.form.test_error") + f": {message}")

    def accept(self) -> None:
        model = self._build_connection_model()
        if model is None:
            return
        if self._connection:
            model.status = self._connection.status
            model.is_active = self._connection.is_active
            model.created_at = self._connection.created_at
        self._result = model
        super().accept()

    def get_connection(self) -> Optional[Connection]:
        return self._result

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._test_thread is not None:
            self._test_thread.requestInterruption()
            self._test_thread.wait(200)
            self._test_thread = None
        super().closeEvent(event)


class ConnectionsDialog(QtWidgets.QDialog):
    """Менеджер соединений с управлением активацией и тестированием."""

    def __init__(self, manager: ConnectionManager, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._logger = logging.getLogger(__name__)
        self._state_store = QtCore.QSettings("docker-simple-manager", "ConnectionsDialog")
        self._table = QtWidgets.QTableWidget(0, 5)
        self._connections: List[Connection] = []
        self._test_thread: Optional[ConnectionTestThread] = None
        self._has_changes = False
        self.setWindowTitle(translate("connections.dialog.title"))
        self.resize(950, 520)
        self._build_ui()
        self._restore_state()
        self._reload_connections()
        self._run_status_check(initial=True)

    @property
    def has_changes(self) -> bool:
        return self._has_changes

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(self._build_toolbar())
        layout.addWidget(self._build_table())
        layout.addLayout(self._build_status_row())

    def _build_toolbar(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton(translate("actions.add"))
        add_button.clicked.connect(self._add_connection)
        check_button = QtWidgets.QPushButton(translate("connections.actions.check_all"))
        check_button.clicked.connect(self._run_status_check)
        self._only_active_check = QtWidgets.QCheckBox(translate("connections.filter.only_active"))
        self._only_active_check.toggled.connect(self._refresh_table)
        layout.addWidget(add_button)
        layout.addWidget(check_button)
        layout.addStretch()
        layout.addWidget(self._only_active_check)
        return layout

    def _build_table(self) -> QtWidgets.QTableWidget:
        headers = [
            translate("connections.columns.name"),
            translate("connections.columns.type"),
            translate("connections.columns.status"),
            translate("connections.columns.last_used"),
            translate("connections.columns.actions"),
        ]
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        return self._table

    def _reload_connections(self) -> None:
        self._connections = self._manager.list_connections()
        self._refresh_table()

    def _refresh_table(self) -> None:
        connections = (
            [conn for conn in self._connections if conn.is_active]
            if self._only_active_check.isChecked()
            else list(self._connections)
        )
        self._table.setRowCount(len(connections))
        for row, connection in enumerate(connections):
            self._table.setItem(row, 0, QtWidgets.QTableWidgetItem(connection.name))
            self._table.setItem(row, 1, QtWidgets.QTableWidgetItem(connection.type.title()))
            status_item = QtWidgets.QTableWidgetItem(self._format_status(connection))
            self._table.setItem(row, 2, status_item)
            last_used = connection.last_used or "—"
            self._table.setItem(row, 3, QtWidgets.QTableWidgetItem(last_used))
            self._table.setCellWidget(row, 4, self._build_actions_widget(connection))

    def _format_status(self, connection: Connection) -> str:
        symbol = {
            ConnectionStatus.ONLINE: "✓",
            ConnectionStatus.OFFLINE: "✗",
            ConnectionStatus.UNKNOWN: "?",
        }.get(connection.status, "?")
        text_key = {
            ConnectionStatus.ONLINE: "connections.status.online",
            ConnectionStatus.OFFLINE: "connections.status.offline",
            ConnectionStatus.UNKNOWN: "connections.status.unknown",
        }[connection.status]
        return f"{symbol} {translate(text_key)}"

    def _build_actions_widget(self, connection: Connection) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        toggle_button = QtWidgets.QToolButton()
        toggle_button.setText("■" if connection.is_active else "▶")
        toggle_button.setToolTip(
            translate(
                "connections.actions.deactivate"
                if connection.is_active
                else "connections.actions.activate"
            )
        )
        toggle_button.clicked.connect(
            lambda _checked=False, conn=connection: self._toggle_connection(conn)
        )
        layout.addWidget(toggle_button)

        edit_button = QtWidgets.QToolButton()
        edit_button.setText("✎")
        edit_button.setToolTip(translate("actions.edit"))
        edit_button.clicked.connect(lambda _=False, conn=connection: self._edit_connection(conn))
        layout.addWidget(edit_button)

        test_button = QtWidgets.QToolButton()
        test_button.setText("✓")
        test_button.setToolTip(translate("actions.test_connection"))
        test_button.clicked.connect(
            lambda _checked=False, conn=connection: self._run_status_check([conn.identifier])
        )
        layout.addWidget(test_button)

        delete_button = QtWidgets.QToolButton()
        delete_button.setText("🗑")
        delete_button.setToolTip(translate("actions.delete"))
        delete_button.clicked.connect(
            lambda _checked=False, conn=connection: self._delete_connection(conn)
        )
        layout.addWidget(delete_button)

        return widget

    def _add_connection(self) -> None:
        dialog = ConnectionFormDialog(parent=self)
        if dialog.exec():
            connection = dialog.get_connection()
            if connection:
                try:
                    self._manager.add_connection(connection)
                    self._logger.info("Connection added: %s", connection.identifier)
                    self._has_changes = True
                    self._reload_connections()
                except ValueError as exc:
                    QtWidgets.QMessageBox.warning(self, self.windowTitle(), str(exc))

    def _edit_connection(self, connection: Connection) -> None:
        dialog = ConnectionFormDialog(connection=connection, parent=self)
        if dialog.exec():
            updated = dialog.get_connection()
            if updated:
                updated.is_active = connection.is_active
                updated.status = connection.status
                updated.created_at = connection.created_at
                self._manager.update_connection(updated)
                self._logger.info("Connection updated: %s", updated.identifier)
                self._has_changes = True
                self._reload_connections()

    def _delete_connection(self, connection: Connection) -> None:
        if (
            QtWidgets.QMessageBox.question(
                self,
                translate("actions.delete"),
                translate("messages.confirm_delete"),
            )
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        self._manager.delete_connection(connection.identifier)
        self._logger.info("Connection deleted: %s", connection.identifier)
        self._has_changes = True
        self._reload_connections()

    def _toggle_connection(self, connection: Connection) -> None:
        if connection.is_active:
            self._manager.deactivate_connection(connection.identifier)
            self._logger.info("Connection deactivated: %s", connection.identifier)
        else:
            self._manager.activate_connection(connection.identifier)
            self._logger.info("Connection activated: %s", connection.identifier)
        self._has_changes = True
        self._reload_connections()

    def _run_status_check(
        self, identifiers: Optional[List[str]] = None, *, initial: bool = False
    ) -> None:
        if self._test_thread is not None:
            self._test_thread.requestInterruption()
            self._test_thread.wait(100)
        ids = identifiers or [conn.identifier for conn in self._connections]
        if not ids:
            return
        self._status_label.setText(
            translate("connections.actions.check_all")
            if not initial
            else translate("connections.messages.checking")
        )
        thread = ConnectionTestThread(manager=self._manager, identifiers=ids)
        thread.status_updated.connect(self._on_status_updated)
        thread.finished.connect(lambda: self._status_label.setText(""))
        thread.finished.connect(lambda: setattr(self, "_test_thread", None))
        thread.finished.connect(thread.deleteLater)
        self._test_thread = thread
        thread.start()

    def _on_status_updated(self, identifier: str, status: ConnectionStatus) -> None:
        for connection in self._connections:
            if connection.identifier == identifier:
                connection.status = status
                if status == ConnectionStatus.ONLINE:
                    connection.last_used = datetime.utcnow().isoformat()
                break
        self._refresh_table()

    def _build_status_row(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        self._status_label = QtWidgets.QLabel()
        close_button = QtWidgets.QPushButton(translate("actions.close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(self._status_label)
        layout.addStretch()
        layout.addWidget(close_button)
        return layout

    def accept(self) -> None:
        self._save_state()
        super().accept()

    def reject(self) -> None:
        self._save_state()
        super().reject()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._test_thread is not None:
            self._test_thread.requestInterruption()
            self._test_thread.wait(200)
            self._test_thread = None
        super().closeEvent(event)

    def _save_state(self) -> None:
        self._state_store.setValue("geometry", self.saveGeometry())
        self._state_store.setValue("header_state", self._table.horizontalHeader().saveState())

    def _restore_state(self) -> None:
        geometry = self._state_store.value("geometry")
        if isinstance(geometry, QtCore.QByteArray):
            self.restoreGeometry(geometry)
        elif geometry:
            self.restoreGeometry(QtCore.QByteArray(geometry))
        header_state = self._state_store.value("header_state")
        if isinstance(header_state, QtCore.QByteArray):
            self._table.horizontalHeader().restoreState(header_state)
        elif header_state:
            self._table.horizontalHeader().restoreState(QtCore.QByteArray(header_state))


class ConnectionTestThread(QtCore.QThread):
    """Проверяет одно или несколько соединений в отдельном потоке."""

    status_updated = QtCore.Signal(str, ConnectionStatus)

    def __init__(
        self,
        *,
        manager: ConnectionManager,
        identifiers: List[str],
    ) -> None:
        super().__init__()
        self._manager = manager
        self._identifiers = identifiers

    def run(self) -> None:
        for identifier in self._identifiers:
            if self.isInterruptionRequested():
                return
            status = self._manager.test_connection(identifier)
            self.status_updated.emit(identifier, status)


class ConnectionProbeThread(QtCore.QThread):
    """Проверка соединения из формы без его сохранения."""

    success = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, connection: Connection) -> None:
        super().__init__()
        self._connection = connection

    def run(self) -> None:
        try:
            version = get_docker_version(self._connection)
            self.success.emit(version)
        except Exception as exc:  # pragma: no cover
            self.error.emit(str(exc))


def discover_docker_sockets() -> List[str]:
    """Возвращает список доступных сокетов Docker на локальной машине."""

    sockets: List[str] = []
    candidates = [Path("/var/run/docker.sock")]
    docker_host = os.environ.get("DOCKER_HOST")
    if docker_host and docker_host.startswith("unix://"):
        candidates.append(Path(docker_host[len("unix://") :]))
    if platform.system() == "Linux":
        candidates.extend(Path("/tmp").glob("docker-*.sock"))
        uid = os.getuid()
        candidates.append(Path(f"/run/user/{uid}/docker.sock"))
        candidates.append(Path(f"/run/user/{uid}/docker-desktop/docker.sock"))
        candidates.append(Path.home() / ".docker" / "desktop" / "docker.sock")
    if platform.system() == "Darwin":
        candidates.append(Path.home() / ".docker" / "run" / "docker.sock")
        candidates.append(Path.home() / ".docker" / "desktop" / "docker.sock")
    for path in candidates:
        socket_path = Path(path).expanduser()
        if _is_socket(socket_path):
            sockets.append(normalize_socket_path(str(socket_path)))
    return sorted(set(sockets))


def _is_socket(path: Path) -> bool:
    try:
        return path.exists() and stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False
