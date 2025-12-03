"""Диалог просмотра логов и инспекции контейнера."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from src.i18n.translator import translate


LOG_PREFIX_RE = re.compile(
    r"^\s*(\[[^\]]+\]|\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)(\s*\|\s*|\s+[-:]\s+)"
)


class ContainerDetailsDialog(QtWidgets.QDialog):
    """Отображает вкладки с логами, inspect и bind mounts."""

    def __init__(
        self,
        *,
        container_name: str,
        logs: str,
        inspect_data: Dict[str, Any],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(translate("containers.details.title").format(name=container_name))
        self.resize(950, 620)

        self._raw_logs = logs.splitlines() if logs else []
        self._inspect_data = inspect_data or {}
        self._settings = QtCore.QSettings("docker-simple-manager", "ContainerDetailsDialog")

        layout = QtWidgets.QVBoxLayout(self)
        self._tabs = QtWidgets.QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._create_logs_tab(), translate("containers.details.logs"))
        self._tabs.addTab(self._create_inspect_tab(), translate("containers.details.inspect"))
        self._tabs.addTab(self._create_mounts_tab(), translate("containers.details.binds"))

        self._restore_state()

        close_button = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        close_button.accepted.connect(self.accept)
        close_button.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText(
            translate("actions.close")
        )
        layout.addWidget(close_button)

    # ---------------------------------------------------------------- logs tab
    def _create_logs_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        controls = QtWidgets.QHBoxLayout()
        self._log_search = QtWidgets.QLineEdit()
        self._log_search.setPlaceholderText(translate("containers.logs.search"))
        self._log_search.textChanged.connect(self._refresh_logs_view)
        controls.addWidget(self._log_search, stretch=2)

        self._hide_timestamp = QtWidgets.QCheckBox(translate("containers.logs.hide_timestamp"))
        self._hide_timestamp.stateChanged.connect(self._refresh_logs_view)
        controls.addWidget(self._hide_timestamp)

        copy_button = QtWidgets.QPushButton(translate("containers.logs.copy"))
        copy_button.clicked.connect(self._copy_logs_to_clipboard)
        controls.addWidget(copy_button)
        controls.addStretch()
        layout.addLayout(controls)

        self._logs_view = QtWidgets.QPlainTextEdit()
        self._logs_view.setReadOnly(True)
        layout.addWidget(self._logs_view)
        self._refresh_logs_view()
        return widget

    def _refresh_logs_view(self) -> None:
        if not self._raw_logs:
            self._logs_view.setPlainText(translate("containers.details.no_logs"))
            return
        search = self._log_search.text().lower()
        filtered: Iterable[str]
        if search:
            filtered = [line for line in self._raw_logs if search in line.lower()]
        else:
            filtered = self._raw_logs

        def format_line(line: str) -> str:
            if self._hide_timestamp.isChecked():
                line = LOG_PREFIX_RE.sub("", line)
            return line

        text = "\n".join(format_line(line) for line in filtered)
        self._logs_view.setPlainText(text or translate("containers.details.no_logs"))

    def _copy_logs_to_clipboard(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self._logs_view.toPlainText())

    # -------------------------------------------------------------- inspect tab
    def _create_inspect_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        top_row = QtWidgets.QHBoxLayout()
        self._inspect_raw_checkbox = QtWidgets.QCheckBox(translate("containers.inspect.raw"))
        self._inspect_raw_checkbox.stateChanged.connect(self._toggle_inspect_view)
        top_row.addWidget(self._inspect_raw_checkbox)

        top_row.addWidget(QtWidgets.QLabel(translate("containers.inspect.section")))
        self._inspect_section_combo = QtWidgets.QComboBox()
        self._inspect_section_combo.currentIndexChanged.connect(self._jump_to_section)
        self._inspect_section_combo.setMinimumWidth(200)
        top_row.addWidget(self._inspect_section_combo, stretch=1)
        top_row.addStretch()
        layout.addLayout(top_row)

        self._inspect_stack = QtWidgets.QStackedWidget()
        layout.addWidget(self._inspect_stack)

        # Tree view
        self._inspect_tree = QtWidgets.QTreeWidget()
        self._inspect_tree.setColumnCount(2)
        self._inspect_tree.setHeaderLabels(["Key", "Value"])
        self._populate_tree(self._inspect_tree.invisibleRootItem(), self._inspect_data)
        self._inspect_tree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self._inspect_tree.header().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self._inspect_stack.addWidget(self._inspect_tree)

        # Raw view
        pretty = json.dumps(self._inspect_data, indent=2, ensure_ascii=False)
        self._inspect_text = QtWidgets.QPlainTextEdit()
        self._inspect_text.setReadOnly(True)
        self._inspect_text.setPlainText(pretty or "{}")
        self._inspect_stack.addWidget(self._inspect_text)

        self._inspect_raw_checkbox.setChecked(False)
        self._populate_section_combo()
        return widget

    def _populate_tree(
        self, parent: QtWidgets.QTreeWidgetItem, value: Any, key: str | None = None
    ) -> None:
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                item = QtWidgets.QTreeWidgetItem(parent, [str(sub_key), ""])
                self._populate_tree(item, sub_value, sub_key)
        elif isinstance(value, list):
            for index, sub_value in enumerate(value):
                item = QtWidgets.QTreeWidgetItem(parent, [f"[{index}]", ""])
                self._populate_tree(item, sub_value, f"[{index}]")
        else:
            text = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
            QtWidgets.QTreeWidgetItem(parent, [key or "", text])

    def _populate_section_combo(self) -> None:
        self._inspect_section_combo.blockSignals(True)
        self._inspect_section_combo.clear()
        if isinstance(self._inspect_data, dict):
            for key in self._inspect_data.keys():
                self._inspect_section_combo.addItem(str(key))
        self._inspect_section_combo.blockSignals(False)

    def _toggle_inspect_view(self) -> None:
        is_raw = self._inspect_raw_checkbox.isChecked()
        self._inspect_stack.setCurrentWidget(self._inspect_text if is_raw else self._inspect_tree)

    def _jump_to_section(self, index: int) -> None:
        if not self._inspect_raw_checkbox.isChecked():
            return
        key = self._inspect_section_combo.itemText(index)
        if not key:
            return
        pattern = f'"{key}"'
        cursor = self._inspect_text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
        self._inspect_text.setTextCursor(cursor)
        if not self._inspect_text.find(pattern):
            self._inspect_text.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
            if not self._inspect_text.find(pattern):
                return
        self._inspect_text.centerCursor()

    # -------------------------------------------------------------- mounts tab
    def _create_mounts_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        mounts = self._inspect_data.get("Mounts") or []
        if not isinstance(mounts, list) or not mounts:
            layout.addWidget(QtWidgets.QLabel(translate("containers.inspect.no_mounts")))
            return widget

        table = QtWidgets.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(
            [
                translate("containers.binds.source"),
                translate("containers.binds.destination"),
                translate("containers.binds.type"),
            ]
        )
        table.setRowCount(len(mounts))
        for row_index, mount in enumerate(mounts):
            source = mount.get("Source") or mount.get("HostPath") or "-"
            destination = mount.get("Destination") or mount.get("Target") or "-"
            mount_type = mount.get("Type") or "-"
            table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(str(source)))
            table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(str(destination)))
            table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(str(mount_type)))
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table)
        return widget

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._save_state()
        super().closeEvent(event)

    def _save_state(self) -> None:
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("tab_index", self._tabs.currentIndex())
        self._settings.setValue("inspect_raw", self._inspect_raw_checkbox.isChecked())

    def _restore_state(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        raw_index = self._settings.value("tab_index", 0)
        if isinstance(raw_index, int):
            tab_index = raw_index
        elif isinstance(raw_index, str) and raw_index.isdigit():
            tab_index = int(raw_index)
        else:
            tab_index = 0
        if 0 <= tab_index < self._tabs.count():
            self._tabs.setCurrentIndex(tab_index)
        raw = self._settings.value("inspect_raw", False)
        self._inspect_raw_checkbox.setChecked(bool(raw))
