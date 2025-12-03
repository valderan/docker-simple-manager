"""Диалог просмотра и управления логами приложения."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from PySide6 import QtCore, QtWidgets

from src.i18n.translator import translate


LOG_PATTERNS = [
    re.compile(r"\[(?P<timestamp>[^\]]+)\]\s+(?P<level>[A-Z]+)\s+[-:]\s+(?P<message>.+)"),
    re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
        r"\s*\|\s*(?P<level>[A-Z]+)\s*\|\s*(?P<message>.+)"
    ),
]
SUPPORTED_LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass(slots=True)
class LogEntry:
    """Структура одной записи лога."""

    line_no: int
    raw: str
    timestamp: datetime | None
    level: str
    message: str

    @property
    def timestamp_text(self) -> str:
        if self.timestamp:
            return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return "-"


class LogsDialog(QtWidgets.QDialog):
    """Показывает список лог-файлов с фильтрами, поиском и действиями."""

    def __init__(self, *, log_dir: Path, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._log_dir = log_dir
        self._current_file: Path | None = None
        self._entries: List[LogEntry] = []
        self._filtered_entries: List[LogEntry] = []
        self._state_store = QtCore.QSettings("docker-simple-manager", "LogsDialog")

        self._file_combo = QtWidgets.QComboBox()
        self._level_combo = QtWidgets.QComboBox()
        self._search_edit = QtWidgets.QLineEdit()
        self._date_from = QtWidgets.QDateEdit()
        self._date_to = QtWidgets.QDateEdit()
        self._table = QtWidgets.QTableWidget()
        self._stats_label = QtWidgets.QLabel()

        self.setWindowTitle(translate("logs.dialog.title"))
        self.resize(960, 580)
        self._setup_dates(-7)
        self._build_ui()
        self._restore_state()
        self._populate_file_combo()

    # ------------------------------------------------------------------ UI setup
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(self._build_filters_row())
        layout.addWidget(self._table)
        layout.addWidget(self._stats_label)
        layout.addLayout(self._build_actions_row())
        self._configure_table()
        self._update_stats()

    def _build_filters_row(self) -> QtWidgets.QVBoxLayout:
        top_row = QtWidgets.QHBoxLayout()

        self._file_combo.currentIndexChanged.connect(self._on_file_changed)
        top_row.addWidget(QtWidgets.QLabel(translate("logs.filter.file")))
        top_row.addWidget(self._file_combo, stretch=2)

        self._level_combo.addItem(translate("logs.level.all"), "ALL")
        for level in SUPPORTED_LEVELS[1:]:
            self._level_combo.addItem(level.title(), level)
        self._level_combo.currentIndexChanged.connect(self._apply_filters)
        top_row.addWidget(QtWidgets.QLabel(translate("logs.filter.level")))
        top_row.addWidget(self._level_combo)

        self._search_edit.setPlaceholderText(translate("logs.filter.search"))
        self._search_edit.textChanged.connect(self._apply_filters)
        top_row.addWidget(self._search_edit, stretch=2)

        date_row = QtWidgets.QHBoxLayout()
        date_row.addWidget(QtWidgets.QLabel(translate("logs.filter.date_from")))
        self._date_from.setDisplayFormat("dd.MM.yyyy")
        self._date_to.setDisplayFormat("dd.MM.yyyy")
        self._date_from.setMaximumWidth(130)
        self._date_to.setMaximumWidth(130)
        date_row.addWidget(self._date_from)
        date_row.addWidget(QtWidgets.QLabel(translate("logs.filter.date_to")))
        date_row.addWidget(self._date_to)

        for label, days in (
            (translate("logs.filter.today"), 0),
            (translate("logs.filter.week"), -7),
            (translate("logs.filter.month"), -30),
        ):
            button = QtWidgets.QPushButton(label)
            button.setAutoDefault(False)
            button.clicked.connect(lambda _=None, delta=days: self._apply_quick_range(delta))
            date_row.addWidget(button)

        date_row.addStretch()

        wrapper = QtWidgets.QVBoxLayout()
        wrapper.addLayout(top_row)
        wrapper.addLayout(date_row)
        return wrapper

    def _setup_dates(self, days_range: int = -7) -> None:
        today = QtCore.QDate.currentDate()
        self._date_from.setCalendarPopup(True)
        self._date_to.setCalendarPopup(True)
        self._date_from.setDate(today.addDays(days_range))
        self._date_to.setDate(today)
        self._date_from.dateChanged.connect(self._apply_filters)
        self._date_to.dateChanged.connect(self._apply_filters)

    def _configure_table(self) -> None:
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(
            [
                translate("logs.column.timestamp"),
                translate("logs.column.level"),
                translate("logs.column.message"),
            ]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.itemDoubleClicked.connect(self._on_entry_double_clicked)

    def _build_actions_row(self) -> QtWidgets.QHBoxLayout:
        actions = QtWidgets.QHBoxLayout()
        export_button = QtWidgets.QPushButton(translate("logs.actions.export"))
        delete_button = QtWidgets.QPushButton(translate("logs.actions.delete"))
        clear_button = QtWidgets.QPushButton(translate("logs.actions.clear_all"))
        close_button = QtWidgets.QPushButton(translate("actions.close"))

        export_button.clicked.connect(self._export_filtered)
        delete_button.clicked.connect(self._delete_selected_entries)
        clear_button.clicked.connect(self._clear_current_file)
        close_button.clicked.connect(self.accept)

        actions.addWidget(export_button)
        actions.addWidget(delete_button)
        actions.addWidget(clear_button)
        actions.addStretch()
        actions.addWidget(close_button)
        return actions

    def accept(self) -> None:
        self._save_state()
        super().accept()

    def reject(self) -> None:  # pragma: no cover - форма закрывается через accept
        self.accept()

    def _save_state(self) -> None:
        self._state_store.setValue("geometry", self.saveGeometry())
        self._state_store.setValue("selected_file", self._file_combo.currentText())

    def _restore_state(self) -> None:
        geometry = self._state_store.value("geometry")
        if geometry is not None:
            if not isinstance(geometry, QtCore.QByteArray):
                geometry = QtCore.QByteArray(geometry)
            self.restoreGeometry(geometry)

    # ---------------------------------------------------------------- file ops
    def _populate_file_combo(self) -> None:
        self._file_combo.clear()
        files: List[Path] = sorted(self._log_dir.glob("*.log"))
        for file_path in files:
            self._file_combo.addItem(file_path.name, file_path)
        if not files:
            return
        preferred = self._state_store.value("selected_file")
        if isinstance(preferred, str):
            index = self._file_combo.findText(preferred)
            if index >= 0:
                self._file_combo.setCurrentIndex(index)
                return
        self._file_combo.setCurrentIndex(0)

    def _on_file_changed(self, index: int) -> None:
        data = self._file_combo.itemData(index)
        if isinstance(data, Path):
            self._current_file = data
            self._load_entries_from_file()
        else:
            self._current_file = None
            self._entries = []
            self._apply_filters()

    def _load_entries_from_file(self) -> None:
        if not self._current_file or not self._current_file.exists():
            self._entries = []
            self._apply_filters()
            return

        entries: List[LogEntry] = []
        for line_no, raw_line in enumerate(
            self._current_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        ):
            entry = self._parse_log_line(raw_line, line_no)
            entries.append(entry)
        self._entries = entries
        self._apply_filters()

    def _parse_log_line(self, line: str, line_no: int) -> LogEntry:
        match = None
        for pattern in LOG_PATTERNS:
            match = pattern.match(line)
            if match:
                break
        if not match:
            return LogEntry(line_no=line_no, raw=line, timestamp=None, level="INFO", message=line)

        timestamp_text = match.group("timestamp")
        timestamp = self._parse_timestamp(timestamp_text)
        level = match.group("level").upper()
        message = match.group("message").strip()
        return LogEntry(
            line_no=line_no, raw=line, timestamp=timestamp, level=level, message=message
        )

    def _parse_timestamp(self, value: str) -> datetime | None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S,%f"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    # ---------------------------------------------------------------- filters
    def _apply_quick_range(self, days_delta: int) -> None:
        today = QtCore.QDate.currentDate()
        self._date_from.blockSignals(True)
        self._date_to.blockSignals(True)
        if days_delta == 0:
            self._date_from.setDate(today)
        else:
            self._date_from.setDate(today.addDays(days_delta))
        self._date_to.setDate(today)
        self._date_from.blockSignals(False)
        self._date_to.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self) -> None:
        selected_level = (self._level_combo.currentData() or "ALL").upper()
        search_text = self._search_edit.text().strip().lower()
        start_date = self._date_from.date()
        end_date = self._date_to.date()
        start_dt = datetime(start_date.year(), start_date.month(), start_date.day(), 0, 0, 0)
        end_dt = datetime(end_date.year(), end_date.month(), end_date.day(), 23, 59, 59)

        filtered: List[LogEntry] = []
        for entry in self._entries:
            if selected_level and selected_level != "ALL":
                if entry.level.upper() != selected_level:
                    continue
            if search_text and search_text not in entry.message.lower():
                continue
            if entry.timestamp:
                if entry.timestamp < start_dt or entry.timestamp > end_dt:
                    continue
            filtered.append(entry)

        self._filtered_entries = filtered
        self._render_table()
        self._update_stats()

    def _render_table(self) -> None:
        self._table.setRowCount(len(self._filtered_entries))
        for row_index, entry in enumerate(self._filtered_entries):
            items = [
                QtWidgets.QTableWidgetItem(entry.timestamp_text),
                QtWidgets.QTableWidgetItem(entry.level),
                QtWidgets.QTableWidgetItem(entry.message),
            ]
            for col, item in enumerate(items):
                item.setData(QtCore.Qt.ItemDataRole.UserRole, entry.line_no)
                self._table.setItem(row_index, col, item)

    def _on_entry_double_clicked(self, item: QtWidgets.QTableWidgetItem) -> None:
        """Открывает отдельное окно с детальной информацией выбранной записи."""

        row_index = item.row()  # Индекс строки, по которой выполнен двойной клик
        if row_index < 0 or row_index >= len(self._filtered_entries):
            return
        entry = self._filtered_entries[row_index]  # Выбранная запись лога
        dialog = _LogEntryDetailsDialog(entry, parent=self)
        dialog.exec()

    def _update_stats(self) -> None:
        self._stats_label.setText(
            translate("logs.stats.count").format(count=len(self._filtered_entries))
        )

    # --------------------------------------------------------------- actions
    def _export_filtered(self) -> None:
        if not self._filtered_entries:
            return
        target_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, translate("logs.actions.export"), "", "Text files (*.txt);;All files (*.*)"
        )
        if not target_path:
            return
        lines = [entry.raw for entry in self._filtered_entries]
        Path(target_path).write_text("\n".join(lines), encoding="utf-8")

    def _delete_selected_entries(self) -> None:
        if not self._current_file:
            return
        selected_rows = {index.row() for index in self._table.selectionModel().selectedRows()}
        if not selected_rows:
            return
        line_numbers = {self._filtered_entries[row].line_no for row in selected_rows}
        lines = self._current_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        remaining = [line for idx, line in enumerate(lines) if idx not in line_numbers]
        self._current_file.write_text(
            "\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8"
        )
        self._load_entries_from_file()

    def _clear_current_file(self) -> None:
        if not self._current_file:
            return
        self._current_file.write_text("", encoding="utf-8")
        self._load_entries_from_file()


class _LogEntryDetailsDialog(QtWidgets.QDialog):
    """Простое окно, показывающее полный текст выбранной записи лога."""

    def __init__(self, entry: LogEntry, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry = entry  # Сохраняем ссылку на запись
        self._text_edit = QtWidgets.QPlainTextEdit()  # Поле с полным текстом
        self._copy_button = QtWidgets.QPushButton(translate("logs.entry_dialog.copy"))
        self._close_button = QtWidgets.QPushButton(translate("actions.close"))

        self.setWindowTitle(translate("logs.entry_dialog.title"))
        self.resize(720, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        meta_label = QtWidgets.QLabel(
            translate("logs.entry_dialog.meta").format(
                timestamp=self._entry.timestamp_text,
                level=self._entry.level,
            )
        )
        layout.addWidget(meta_label)

        self._text_edit.setPlainText(self._entry.raw)
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)

        buttons = QtWidgets.QHBoxLayout()
        self._copy_button.clicked.connect(self._copy_text_to_clipboard)
        self._close_button.clicked.connect(self.accept)
        buttons.addWidget(self._copy_button)
        buttons.addStretch()
        buttons.addWidget(self._close_button)
        layout.addLayout(buttons)

    def _copy_text_to_clipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()  # Получаем общий буфер обмена
        clipboard.setText(self._text_edit.toPlainText())
