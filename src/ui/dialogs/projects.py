"""Диалоги управления проектами и форм проведения операций."""

from __future__ import annotations

import datetime as dt
import re
from functools import partial
from typing import Dict, List, Optional

from PySide6 import QtCore, QtWidgets

from src.connections.manager import ConnectionManager
from src.connections.models import Connection
from src.projects.manager import ProjectManager
from src.projects.models import Project, ProjectRunHistory
from src.i18n.translator import translate

SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")


def _normalize_identifier(value: str) -> str:
    """Удаляет недопустимые символы из идентификатора и приводит к нижнему регистру."""

    slug = value.strip().lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _status_label(status: str) -> str:
    mapping = {
        "active": translate("projects.status.active"),
        "paused": translate("projects.status.paused"),
        "stopped": translate("projects.status.stopped"),
        "archived": translate("projects.status.archived"),
    }
    return mapping.get(status, status)


def _project_types() -> Dict[str, str]:
    return {
        "docker_command": translate("projects.form.type.command"),
        "dockerfile_path": translate("projects.form.type.dockerfile"),
        "compose_path": translate("projects.form.type.compose"),
        "bash_script": translate("projects.form.type.script"),
    }


class ProjectFormDialog(QtWidgets.QDialog):
    """Форма создания или редактирования проекта."""

    def __init__(
        self,
        *,
        connection_manager: ConnectionManager,
        project: Optional[Project] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._project = project
        self._connection_manager = connection_manager
        self._result: Optional[Project] = None
        self._current_type = project.type if project else "docker_command"
        self.setWindowTitle(translate("projects.form.title"))
        self.resize(950, 640)

        self._build_ui()
        if project:
            self._populate_form(project)

    # ----------------------------------------------------------------- ui
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.addWidget(self._build_general_group())
        content_layout.addWidget(self._build_type_group())
        content_layout.addWidget(self._build_run_group())
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("projects.form.general"))
        form = QtWidgets.QFormLayout(group)

        self._id_edit = QtWidgets.QLineEdit()
        self._id_edit.setPlaceholderText("my-project")
        slug_hint = QtWidgets.QLabel(translate("projects.form.slug_hint"))
        slug_hint.setWordWrap(True)
        id_layout = QtWidgets.QVBoxLayout()
        id_layout.addWidget(self._id_edit)
        id_layout.addWidget(slug_hint)
        form.addRow(translate("projects.fields.id"), id_layout)

        self._name_edit = QtWidgets.QLineEdit()
        form.addRow(translate("projects.fields.name"), self._name_edit)

        self._description_edit = QtWidgets.QPlainTextEdit()
        self._description_edit.setPlaceholderText(translate("projects.fields.description"))
        self._description_edit.setFixedHeight(80)
        form.addRow(translate("projects.fields.description"), self._description_edit)

        self._priority_spin = QtWidgets.QSpinBox()
        self._priority_spin.setRange(1, 5)
        self._priority_spin.setValue(3)
        form.addRow(translate("projects.fields.priority"), self._priority_spin)

        self._status_combo = QtWidgets.QComboBox()
        for status in ("active", "paused", "stopped", "archived"):
            self._status_combo.addItem(_status_label(status), status)
        form.addRow(translate("projects.fields.status"), self._status_combo)

        tags_layout = QtWidgets.QVBoxLayout()
        top_row = QtWidgets.QHBoxLayout()
        self._tags_input = QtWidgets.QLineEdit()
        self._tags_input.setPlaceholderText(translate("projects.form.tags.placeholder"))
        add_button = QtWidgets.QToolButton()
        add_button.setText("+")
        add_button.setToolTip(translate("projects.form.tags.add"))
        add_button.clicked.connect(self._add_tag_from_input)
        remove_button = QtWidgets.QToolButton()
        remove_button.setText("-")
        remove_button.setToolTip(translate("projects.form.tags.remove"))
        remove_button.clicked.connect(self._remove_selected_tag)
        top_row.addWidget(self._tags_input)
        top_row.addWidget(add_button)
        top_row.addWidget(remove_button)
        tags_layout.addLayout(top_row)
        hint = QtWidgets.QLabel(translate("projects.form.tags_hint"))
        hint.setWordWrap(True)
        tags_layout.addWidget(hint)
        self._tags_list = QtWidgets.QListWidget()
        self._tags_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        tags_layout.addWidget(self._tags_list)
        form.addRow(translate("projects.fields.tags"), tags_layout)

        return group

    def _build_type_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("projects.form.command_type"))
        layout = QtWidgets.QVBoxLayout(group)

        self._type_buttons = QtWidgets.QButtonGroup(self)
        types_row = QtWidgets.QHBoxLayout()
        types_row.setSpacing(16)
        for project_type, label in _project_types().items():
            button = QtWidgets.QRadioButton(label)
            button.setChecked(project_type == self._current_type)
            self._type_buttons.addButton(button)
            button.toggled.connect(partial(self._on_type_changed, project_type))
            types_row.addWidget(button)
        layout.addLayout(types_row)

        self._command_label = QtWidgets.QLabel()
        self._command_stack = QtWidgets.QStackedWidget()

        command_widget = QtWidgets.QWidget()
        command_layout = QtWidgets.QVBoxLayout(command_widget)
        self._command_edit = QtWidgets.QPlainTextEdit()
        self._command_edit.setPlaceholderText("docker run -it ...")
        self._command_edit.setFixedHeight(120)
        command_layout.addWidget(self._command_edit)
        self._command_stack.addWidget(command_widget)

        path_widget = QtWidgets.QWidget()
        path_layout = QtWidgets.QHBoxLayout(path_widget)
        self._path_edit = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton(translate("projects.form.browse"))
        browse_button.clicked.connect(self._choose_path)
        path_layout.addWidget(self._path_edit)
        path_layout.addWidget(browse_button)
        self._command_stack.addWidget(path_widget)

        layout.addWidget(self._command_label)
        layout.addWidget(self._command_stack)
        self._sync_command_inputs()
        return group

    def _build_run_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("projects.form.run_settings"))
        form = QtWidgets.QFormLayout(group)

        self._connection_combo = QtWidgets.QComboBox()
        for connection in self._connection_manager.list_connections():
            self._connection_combo.addItem(connection.name, connection.identifier)
        form.addRow(translate("projects.fields.connection"), self._connection_combo)

        self._detached_checkbox = QtWidgets.QCheckBox(translate("projects.form.detached"))
        form.addRow("", self._detached_checkbox)

        timeout_row = QtWidgets.QHBoxLayout()
        self._timeout_spin = QtWidgets.QSpinBox()
        self._timeout_spin.setRange(0, 3600)
        timeout_row.addWidget(self._timeout_spin)
        timeout_hint = QtWidgets.QLabel(translate("projects.form.timeout_hint"))
        timeout_hint.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        timeout_row.addWidget(timeout_hint)
        form.addRow(translate("projects.form.timeout"), timeout_row)

        self._save_logs_checkbox = QtWidgets.QCheckBox(translate("projects.form.save_logs"))
        self._save_logs_checkbox.setChecked(True)
        form.addRow("", self._save_logs_checkbox)

        self._max_logs_spin = QtWidgets.QSpinBox()
        self._max_logs_spin.setRange(100, 100000)
        self._max_logs_spin.setValue(1000)
        form.addRow(translate("projects.form.max_logs"), self._max_logs_spin)
        return group

    # -------------------------------------------------------------- handlers
    def _add_tag_from_input(self) -> None:
        raw = self._tags_input.text().strip()
        if not raw:
            return
        for tag in [part.strip() for part in raw.split(",") if part.strip()]:
            if not self._tag_exists(tag):
                self._tags_list.addItem(tag)
        self._tags_input.clear()

    def _remove_selected_tag(self) -> None:
        for item in self._tags_list.selectedItems():
            row = self._tags_list.row(item)
            self._tags_list.takeItem(row)

    def _tag_exists(self, tag: str) -> bool:
        for index in range(self._tags_list.count()):
            if self._tags_list.item(index).text() == tag:
                return True
        return False

    def _on_type_changed(self, project_type: str, checked: bool) -> None:
        if not checked:
            return
        self._current_type = project_type
        self._sync_command_inputs()

    def _sync_command_inputs(self) -> None:
        label_map = {
            "docker_command": translate("projects.form.command_label.docker"),
            "dockerfile_path": translate("projects.form.command_label.dockerfile"),
            "compose_path": translate("projects.form.command_label.compose"),
            "bash_script": translate("projects.form.command_label.script"),
        }
        self._command_label.setText(label_map.get(self._current_type, ""))
        self._command_stack.setCurrentIndex(0 if self._current_type == "docker_command" else 1)

    def _choose_path(self) -> None:
        filters = {
            "dockerfile_path": "Dockerfile (Dockerfile *Dockerfile);;All files (*.*)",
            "compose_path": "docker-compose (*.yml *.yaml);;All files (*.*)",
            "bash_script": "Scripts (*.sh);;All files (*.*)",
        }
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            translate("projects.form.browse"),
            "",
            filters.get(self._current_type, "All files (*.*)"),
        )
        if selected:
            self._path_edit.setText(selected)

    # --------------------------------------------------------------- populate
    def _populate_form(self, project: Project) -> None:
        self._id_edit.setText(project.identifier)
        self._id_edit.setEnabled(False)
        self._name_edit.setText(project.name)
        self._description_edit.setPlainText(project.description)
        self._priority_spin.setValue(project.priority)
        status_index = self._status_combo.findData(project.status)
        if status_index >= 0:
            self._status_combo.setCurrentIndex(status_index)
        for tag in project.tags:
            if not self._tag_exists(tag):
                self._tags_list.addItem(tag)
        if project.type == "docker_command":
            self._command_edit.setPlainText(project.command_or_path)
        else:
            self._path_edit.setText(project.command_or_path)
        connection_index = self._connection_combo.findData(project.connection_id)
        if connection_index >= 0:
            self._connection_combo.setCurrentIndex(connection_index)
        self._detached_checkbox.setChecked(project.detached_mode)
        self._timeout_spin.setValue(project.timeout_seconds)
        self._save_logs_checkbox.setChecked(project.save_logs)
        self._max_logs_spin.setValue(project.max_log_lines)

    # ----------------------------------------------------------------- accept
    def accept(self) -> None:
        identifier = _normalize_identifier(self._id_edit.text())
        self._id_edit.setText(identifier)
        name = self._name_edit.text().strip()
        connection_id = self._connection_combo.currentData()
        if not identifier or not name or not connection_id:
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                translate("messages.validation_project"),
            )
            return
        if not identifier or not SLUG_PATTERN.match(identifier):
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                translate("projects.form.slug_hint"),
            )
            return

        command_value = self._command_edit.toPlainText().strip()
        if self._current_type != "docker_command":
            command_value = self._path_edit.text().strip()
        if not command_value:
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                translate("projects.fields.command"),
            )
            return

        self._add_tag_from_input()
        tags = [self._tags_list.item(i).text() for i in range(self._tags_list.count())]
        base_kwargs = {
            "identifier": identifier,
            "name": name,
            "command_or_path": command_value,
            "connection_id": str(connection_id),
            "type": self._current_type,
            "description": self._description_edit.toPlainText().strip(),
            "tags": tags,
            "priority": int(self._priority_spin.value()),
            "status": self._status_combo.currentData(),
            "detached_mode": self._detached_checkbox.isChecked(),
            "timeout_seconds": int(self._timeout_spin.value()),
            "save_logs": self._save_logs_checkbox.isChecked(),
            "max_log_lines": int(self._max_logs_spin.value()),
        }
        if self._project:
            base_kwargs.update(
                created_at=self._project.created_at,
                updated_at=self._project.updated_at,
                author=self._project.author,
                run_history=list(self._project.run_history),
            )
        self._result = Project(**base_kwargs)
        super().accept()

    def get_project(self) -> Optional[Project]:
        """Возвращает собранный проект."""

        return self._result


class ProjectsDialog(QtWidgets.QDialog):
    """Диалог управления перечнем проектов."""

    def __init__(
        self,
        *,
        project_manager: ProjectManager,
        connection_manager: ConnectionManager,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._manager = project_manager
        self._connection_manager = connection_manager
        self._projects: List[Project] = []
        self._filtered: List[Project] = []
        self._state_store = QtCore.QSettings("docker-simple-manager", "ProjectsDialog")
        self.setWindowTitle(translate("projects.dialog.title"))
        self.resize(1100, 620)
        self._run_workers: List[ProjectRunThread] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(self._build_toolbar())
        layout.addLayout(self._build_filters())
        layout.addWidget(self._build_table())

        close_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        close_button = close_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        close_button.setText(translate("actions.close"))
        close_box.accepted.connect(self.accept)
        layout.addWidget(close_box)

        self._restore_state()
        self._reload_projects()

    # ---------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton(translate("actions.add"))
        add_button.clicked.connect(self._add_project)
        layout.addWidget(add_button)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel(translate("projects.filter.search")))
        self._search_edit = QtWidgets.QLineEdit()
        self._search_edit.setPlaceholderText(translate("projects.filter.placeholder"))
        self._search_edit.textChanged.connect(self._apply_filters)
        layout.addWidget(self._search_edit)
        return layout

    def _build_filters(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(translate("projects.filter.tags")))
        self._tag_filter = QtWidgets.QComboBox()
        self._tag_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self._tag_filter)

        layout.addWidget(QtWidgets.QLabel(translate("projects.filter.status")))
        self._status_filter = QtWidgets.QComboBox()
        self._status_filter.addItem(translate("projects.filter.status_all"), None)
        for status in ("active", "paused", "stopped", "archived"):
            self._status_filter.addItem(_status_label(status), status)
        self._status_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self._status_filter)

        layout.addWidget(QtWidgets.QLabel(translate("projects.filter.sort")))
        self._sort_combo = QtWidgets.QComboBox()
        self._sort_combo.addItem(translate("projects.filter.sort_name"), "name")
        self._sort_combo.addItem(translate("projects.filter.sort_recent"), "recent")
        self._sort_combo.addItem(translate("projects.filter.sort_priority"), "priority")
        self._sort_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self._sort_combo)
        layout.addStretch()
        return layout

    def _build_table(self) -> QtWidgets.QTableWidget:
        self._table = QtWidgets.QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                translate("projects.columns.name"),
                translate("projects.columns.description"),
                translate("projects.columns.connection"),
                translate("projects.columns.status"),
                translate("projects.columns.created"),
                translate("projects.columns.actions"),
            ]
        )
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for index in range(self._table.columnCount()):
            header.setSectionResizeMode(index, QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(120)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._edit_selected_project)
        return self._table

    # --------------------------------------------------------------- data
    def _reload_projects(self) -> None:
        self._projects = self._manager.list_projects()
        self._rebuild_tag_filter()
        self._apply_filters()

    def _rebuild_tag_filter(self) -> None:
        tags = sorted({tag for project in self._projects for tag in project.tags})
        current = self._tag_filter.currentData() if hasattr(self, "_tag_filter") else None
        self._tag_filter.blockSignals(True)
        self._tag_filter.clear()
        self._tag_filter.addItem(translate("projects.filter.tags_all"), None)
        for tag in tags:
            self._tag_filter.addItem(tag, tag)
        if current is not None:
            index = self._tag_filter.findData(current)
            if index >= 0:
                self._tag_filter.setCurrentIndex(index)
        self._tag_filter.blockSignals(False)

    def _apply_filters(self) -> None:
        search = self._search_edit.text().strip().lower()
        tag = self._tag_filter.currentData()
        status = self._status_filter.currentData()
        sort_mode = self._sort_combo.currentData()

        filtered = []
        for project in self._projects:
            if tag and tag not in project.tags:
                continue
            if status and project.status != status:
                continue
            if (
                search
                and search not in project.name.lower()
                and search not in project.description.lower()
            ):
                tag_match = any(search in tag.lower() for tag in project.tags)
                if not tag_match:
                    continue
            filtered.append(project)

        if sort_mode == "name":
            filtered.sort(key=lambda proj: proj.name.lower())
        elif sort_mode == "recent":
            filtered.sort(key=lambda proj: self._parse_timestamp(proj.created_at), reverse=True)
        elif sort_mode == "priority":
            filtered.sort(key=lambda proj: proj.priority, reverse=True)

        self._filtered = filtered
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._filtered))
        for row, project in enumerate(self._filtered):
            self._set_text_item(row, 0, project.name, project.identifier)
            self._set_text_item(row, 1, project.description)
            connection_name = self._resolve_connection_name(project.connection_id)
            self._set_text_item(row, 2, connection_name)
            self._set_text_item(row, 3, _status_label(project.status))
            self._set_text_item(row, 4, self._format_created(project.created_at))
            self._table.setCellWidget(row, 5, self._make_actions_widget(project))

    def _set_text_item(
        self, row: int, column: int, text: str, identifier: Optional[str] = None
    ) -> None:
        item = QtWidgets.QTableWidgetItem(text or "—")
        if identifier is not None:
            item.setData(QtCore.Qt.ItemDataRole.UserRole, identifier)
        self._table.setItem(row, column, item)

    def _make_actions_widget(self, project: Project) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        actions = [
            ("▶", translate("projects.actions.run"), self._run_project),
            ("✎", translate("actions.edit"), self._edit_project),
            ("🗑", translate("actions.delete"), self._delete_project),
        ]
        for icon, tooltip, handler in actions:
            button = QtWidgets.QToolButton()
            button.setText(icon)
            button.setToolTip(tooltip)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(partial(handler, project.identifier))
            layout.addWidget(button)
        layout.addStretch()
        return widget

    # ----------------------------------------------------------- utilities
    def _resolve_connection_name(self, identifier: str) -> str:
        try:
            return self._connection_manager.get_connection(identifier).name
        except KeyError:
            return identifier

    def _format_created(self, value: Optional[str]) -> str:
        if not value:
            return "—"
        try:
            date = self._parse_timestamp(value)
            return date.strftime("%Y-%m-%d")
        except ValueError:
            return value

    def _parse_timestamp(self, value: Optional[str]) -> dt.datetime:
        if not value:
            return dt.datetime.min
        try:
            return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return dt.datetime.min

    def _current_project(self) -> Optional[Project]:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._filtered):
            return None
        return self._filtered[row]

    # --------------------------------------------------------------- actions
    def _add_project(self) -> None:
        dialog = ProjectFormDialog(connection_manager=self._connection_manager, parent=self)
        if dialog.exec():
            project = dialog.get_project()
            if project:
                try:
                    self._manager.add_project(project)
                except ValueError as exc:
                    self._show_error(str(exc))
                self._reload_projects()

    def _edit_project(self, identifier: Optional[str] = None) -> None:
        project = self._find_project(identifier) or self._current_project()
        if not project:
            self._show_info(translate("projects.messages.no_project_selected"))
            return
        dialog = ProjectFormDialog(
            connection_manager=self._connection_manager,
            project=project,
            parent=self,
        )
        if dialog.exec():
            updated = dialog.get_project()
            if updated:
                self._manager.update_project(updated)
                self._reload_projects()

    def _edit_selected_project(self) -> None:
        self._edit_project()

    def _delete_project(self, identifier: Optional[str] = None) -> None:
        project = self._find_project(identifier) or self._current_project()
        if not project:
            self._show_info(translate("projects.messages.no_project_selected"))
            return
        message = translate("projects.confirm.delete").format(name=project.name)
        result = QtWidgets.QMessageBox.question(self, translate("actions.delete"), message)
        if result != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._manager.delete_project(project.identifier)
        self._reload_projects()

    def _run_project(self, identifier: Optional[str] = None) -> None:
        project = self._find_project(identifier) or self._current_project()
        if not project:
            self._show_info(translate("projects.messages.no_project_selected"))
            return
        try:
            connection = self._connection_manager.get_connection(project.connection_id)
        except KeyError:
            self._show_error(translate("projects.messages.no_connection"))
            return
        confirm = translate("projects.confirm.run").format(name=project.name)
        reply = QtWidgets.QMessageBox.question(self, translate("projects.actions.run"), confirm)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        worker = ProjectRunThread(self._manager, project.identifier, connection)
        worker.result.connect(self._on_project_run_success)
        worker.error.connect(self._on_project_run_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda w=worker: self._cleanup_run_worker(w))
        self._run_workers.append(worker)
        worker.start()

    def _find_project(self, identifier: Optional[str]) -> Optional[Project]:
        if not identifier:
            return None
        for project in self._projects:
            if project.identifier == identifier:
                return project
        return None

    def _on_project_run_success(self, entry: ProjectRunHistory) -> None:
        if entry.status == "running":
            self._show_info(translate("projects.messages.run_started_detached"))
        elif entry.status == "success":
            self._show_info(translate("projects.messages.run_success"))
        else:
            error_text = entry.error_message or ""
            self._show_error(translate("projects.messages.run_failed").format(error=error_text))
        self._reload_projects()

    def _on_project_run_error(self, payload: Dict[str, str]) -> None:
        error_type = payload.get("type")
        message = payload.get("message", "")
        if error_type == "file":
            self._show_error(translate("projects.messages.file_not_found").format(path=message))
        else:
            self._show_error(message)

    def _cleanup_run_worker(self, worker: "ProjectRunThread") -> None:
        try:
            self._run_workers.remove(worker)
        except ValueError:
            pass

    # ------------------------------------------------------------- messaging
    def _show_info(self, text: str) -> None:
        QtWidgets.QMessageBox.information(self, self.windowTitle(), text)

    def _show_error(self, text: str) -> None:
        QtWidgets.QMessageBox.critical(self, self.windowTitle(), text)

    def accept(self) -> None:
        self._save_state()
        super().accept()

    def reject(self) -> None:  # pragma: no cover - всегда считаем работу успешной
        self.accept()

    def _save_state(self) -> None:
        self._state_store.setValue("geometry", self.saveGeometry())
        self._state_store.setValue("header_state", self._table.horizontalHeader().saveState())

    def _restore_state(self) -> None:
        geometry = self._state_store.value("geometry")
        if geometry is not None:
            if isinstance(geometry, QtCore.QByteArray):
                self.restoreGeometry(geometry)
            else:
                self.restoreGeometry(QtCore.QByteArray(geometry))
        header_state = self._state_store.value("header_state")
        if header_state is not None:
            if not isinstance(header_state, QtCore.QByteArray):
                header_state = QtCore.QByteArray(header_state)
            self._table.horizontalHeader().restoreState(header_state)


class ProjectRunThread(QtCore.QThread):
    """Фоновый запуск проекта, чтобы не блокировать UI."""

    result = QtCore.Signal(object)
    error = QtCore.Signal(dict)

    def __init__(
        self,
        manager: ProjectManager,
        project_id: str,
        connection: Connection,
    ) -> None:
        super().__init__()
        self._manager = manager
        self._project_id = project_id
        self._connection = connection

    def run(self) -> None:
        try:
            entry = self._manager.run_project(self._project_id, self._connection)
            self.result.emit(entry)
        except FileNotFoundError as exc:
            self.error.emit({"type": "file", "message": str(exc)})
        except Exception as exc:
            self.error.emit({"type": "generic", "message": str(exc)})
