"""Диалог настройки параметров приложения DSM."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Dict, List

from PySide6 import QtCore, QtGui, QtWidgets

from src.connections.manager import ConnectionManager
from src.i18n.translator import translate
from src.settings.exceptions import SettingsValidationError
from src.settings.registry import SettingsRegistry
from src.ui.dialogs.help import HelpDialog

THEME_COLOR_BASES = [
    ("primary_color", "settings.appearance.colors.primary"),
    ("background", "settings.appearance.colors.background"),
    ("text", "settings.appearance.colors.text"),
    ("border_color", "settings.appearance.colors.border"),
    ("table_background", "settings.appearance.colors.table_background"),
    ("table_alternate_background", "settings.appearance.colors.table_alternate"),
    ("table_selection_background", "settings.appearance.colors.table_selection_bg"),
    ("table_selection_text", "settings.appearance.colors.table_selection_text"),
]

ACCENT_COLOR_FIELDS = [
    ("accent_success", "settings.appearance.accents_success"),
    ("accent_error", "settings.appearance.accents_error"),
    ("accent_warning", "settings.appearance.accents_warning"),
    ("accent_info", "settings.appearance.accents_info"),
]

VARIANT_LABEL_KEYS = {
    "light": "settings.appearance.light",
    "dark": "settings.appearance.dark",
}

HOTKEY_ACTIONS: List[tuple[str, str]] = [
    ("open_connections_manager", "settings.hotkeys.actions.open_connections_manager"),
    ("test_connection", "settings.hotkeys.actions.test_connection"),
    ("open_projects_manager", "settings.hotkeys.actions.open_projects_manager"),
    ("open_settings", "settings.hotkeys.actions.open_settings"),
    ("open_logs", "settings.hotkeys.actions.open_logs"),
    ("open_help", "settings.hotkeys.actions.open_help"),
    ("open_about", "settings.hotkeys.actions.open_about"),
    ("exit_app", "settings.hotkeys.actions.exit_app"),
    ("refresh_data", "settings.hotkeys.actions.refresh_data"),
    ("switch_tab_1", "settings.hotkeys.actions.switch_tab_1"),
    ("switch_tab_2", "settings.hotkeys.actions.switch_tab_2"),
    ("switch_tab_3", "settings.hotkeys.actions.switch_tab_3"),
    ("switch_tab_4", "settings.hotkeys.actions.switch_tab_4"),
    ("next_tab", "settings.hotkeys.actions.next_tab"),
    ("prev_tab", "settings.hotkeys.actions.prev_tab"),
    ("run_last_project", "settings.hotkeys.actions.run_last_project"),
]


class SettingsDialog(QtWidgets.QDialog):
    """Позволяет редактировать основные и логирующие параметры приложения."""

    def __init__(
        self,
        *,
        settings: SettingsRegistry,
        connection_manager: ConnectionManager | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._connection_manager = connection_manager
        self.setWindowTitle(translate("settings.dialog.title"))
        self.resize(600, 420)
        self._color_buttons: Dict[str, QtWidgets.QPushButton] = {}
        self._font_combo: QtWidgets.QFontComboBox | None = None
        self._font_size_spin: QtWidgets.QSpinBox | None = None
        self._refresh_spin: QtWidgets.QSpinBox
        self._timeout_spin: QtWidgets.QSpinBox
        self._hotkeys_state: Dict[str, str] = {}
        self._hotkey_labels: Dict[str, QtWidgets.QLabel] = {}
        self._create_widgets()
        self._load_values()

    def _create_widgets(self) -> None:
        """Создаёт вкладки и контролы для ввода значений."""

        layout = QtWidgets.QVBoxLayout(self)
        self._tabs = QtWidgets.QTabWidget()
        layout.addWidget(self._tabs)

        self._general_tab = self._build_general_tab()
        self._logging_tab = self._build_logging_tab()
        self._appearance_tab = self._build_appearance_tab()
        self._hotkeys_tab = self._build_hotkeys_tab()
        self._tabs.addTab(self._general_tab, translate("settings.tabs.general"))
        self._tabs.addTab(self._logging_tab, translate("settings.tabs.logging"))
        self._tabs.addTab(self._appearance_tab, translate("settings.tabs.appearance"))
        self._tabs.addTab(self._hotkeys_tab, translate("settings.tabs.hotkeys"))

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> QtWidgets.QWidget:
        """Создаёт вкладку с базовыми настройками."""

        widget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(widget)

        self._language_combo = QtWidgets.QComboBox()
        self._language_combo.addItems(["ru", "en"])
        form.addRow(translate("settings.fields.language"), self._language_combo)

        self._theme_combo = QtWidgets.QComboBox()
        self._theme_combo.addItems(["light", "dark", "system"])
        form.addRow(translate("settings.fields.theme"), self._theme_combo)

        self._save_window_state = QtWidgets.QCheckBox(translate("settings.fields.save_window"))
        form.addRow(self._save_window_state)

        self._refresh_enabled_check = QtWidgets.QCheckBox(
            translate("settings.fields.refresh_enabled")
        )
        self._refresh_enabled_check.stateChanged.connect(
            lambda state: self._refresh_spin.setEnabled(state == QtCore.Qt.CheckState.Checked)
        )
        form.addRow(self._refresh_enabled_check)

        self._refresh_spin = QtWidgets.QSpinBox()
        self._refresh_spin.setRange(1000, 60000)
        self._refresh_spin.setSingleStep(500)
        form.addRow(translate("settings.fields.refresh_rate"), self._refresh_spin)

        self._container_stats_spin = QtWidgets.QSpinBox()
        self._container_stats_spin.setRange(500, 60000)
        self._container_stats_spin.setSingleStep(500)
        form.addRow(
            translate("settings.fields.container_metrics_refresh"), self._container_stats_spin
        )

        self._timeout_spin = QtWidgets.QSpinBox()
        self._timeout_spin.setRange(1, 120)
        self._timeout_spin.setSuffix(" s")
        form.addRow(translate("settings.fields.connection_timeout"), self._timeout_spin)
        self._timeout_enabled_check = QtWidgets.QCheckBox(
            translate("settings.fields.timeout_enabled")
        )
        self._timeout_enabled_check.toggled.connect(self._timeout_spin.setEnabled)
        form.addRow(self._timeout_enabled_check)

        self._auto_load_projects = QtWidgets.QCheckBox(
            translate("settings.fields.auto_load_projects")
        )
        form.addRow(self._auto_load_projects)
        self._auto_activate_connections = QtWidgets.QCheckBox(
            translate("settings.fields.auto_activate_connections")
        )
        form.addRow(self._auto_activate_connections)

        self._system_metrics_spin = QtWidgets.QSpinBox()
        self._system_metrics_spin.setRange(500, 60000)
        self._system_metrics_spin.setSingleStep(500)

        self._system_metrics_checkbox = QtWidgets.QCheckBox(
            translate("settings.fields.system_metrics_enabled")
        )
        self._system_metrics_checkbox.stateChanged.connect(
            lambda state: self._system_metrics_spin.setEnabled(
                state == QtCore.Qt.CheckState.Checked
            )
        )
        form.addRow(self._system_metrics_checkbox)
        form.addRow(translate("settings.fields.system_metrics_refresh"), self._system_metrics_spin)

        self._default_connection_combo = QtWidgets.QComboBox()
        self._default_connection_combo.addItem(translate("settings.fields.no_default"), None)
        if self._connection_manager:
            for connection in self._connection_manager.list_connections():
                self._default_connection_combo.addItem(connection.name, connection.identifier)
        form.addRow(translate("settings.fields.default_connection"), self._default_connection_combo)

        self._use_system_console = QtWidgets.QCheckBox(
            translate("settings.fields.use_system_console")
        )
        form.addRow(self._use_system_console)

        self._container_shell_edit = QtWidgets.QLineEdit()
        form.addRow(translate("settings.fields.container_shell"), self._container_shell_edit)

        self._help_button = QtWidgets.QPushButton(translate("settings.general.help"))
        self._help_button.clicked.connect(self._open_help_dialog)
        form.addRow(self._help_button)

        return widget

    def _build_logging_tab(self) -> QtWidgets.QWidget:
        """Создаёт вкладку с параметрами логирования."""

        widget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(widget)

        self._logging_enabled = QtWidgets.QCheckBox(translate("settings.fields.logging_enabled"))
        form.addRow(self._logging_enabled)

        self._log_level_combo = QtWidgets.QComboBox()
        self._log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow(translate("settings.fields.logging_level"), self._log_level_combo)

        self._max_file_size_spin = QtWidgets.QSpinBox()
        self._max_file_size_spin.setRange(1, 1000)
        self._max_file_size_spin.setSuffix(" MB")
        form.addRow(translate("settings.fields.logging_size"), self._max_file_size_spin)

        self._max_files_spin = QtWidgets.QSpinBox()
        self._max_files_spin.setRange(1, 50)
        form.addRow(translate("settings.fields.logging_files"), self._max_files_spin)

        return widget

    def _build_appearance_tab(self) -> QtWidgets.QWidget:
        """Создаёт вкладку управления внешним видом.

        Используем ScrollArea, чтобы вкладка не растягивала диалог за границы
        экрана даже при добавлении новых элементов.
        """

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        self._light_colors_group = self._create_theme_colors_group("light")
        self._dark_colors_group = self._create_theme_colors_group("dark")
        self._accent_group = self._create_accent_group()
        self._font_group = self._create_font_group()

        layout.addWidget(self._light_colors_group)
        layout.addWidget(self._dark_colors_group)
        layout.addWidget(self._accent_group)
        layout.addWidget(self._font_group)
        layout.addStretch()

        scroll_area.setWidget(container)
        return scroll_area

    def _build_hotkeys_tab(self) -> QtWidgets.QWidget:
        """Создаёт вкладку управления глобальными горячими клавишами."""

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        instructions = QtWidgets.QLabel(translate("settings.hotkeys.instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(1, 1)
        for row_index, (setting_key, translation_key) in enumerate(HOTKEY_ACTIONS):
            action_label = QtWidgets.QLabel(translate(translation_key))
            action_label.setWordWrap(True)
            grid.addWidget(action_label, row_index, 0)

            value_label = QtWidgets.QLabel("-")
            self._hotkey_labels[setting_key] = value_label
            grid.addWidget(value_label, row_index, 1)

            change_button = QtWidgets.QPushButton(translate("settings.hotkeys.change"))
            change_button.clicked.connect(partial(self._change_hotkey, setting_key))
            grid.addWidget(change_button, row_index, 2)

        layout.addLayout(grid)

        reset_button = QtWidgets.QPushButton(translate("settings.hotkeys.reset"))
        reset_button.clicked.connect(self._reset_hotkeys_to_defaults)
        layout.addWidget(reset_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area

    def _create_theme_colors_group(self, variant: str) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate(VARIANT_LABEL_KEYS[variant]))
        grid = QtWidgets.QGridLayout(group)
        for row, (base_key, label_key) in enumerate(THEME_COLOR_BASES):
            key = f"{base_key}_{variant}"
            label = translate(label_key)
            self._add_color_picker_row(grid, row, label, key)

        reset_button = QtWidgets.QPushButton(
            translate(
                "settings.appearance.reset_light"
                if variant == "light"
                else "settings.appearance.reset_dark"
            )
        )
        reset_button.clicked.connect(partial(self._reset_theme_colors, variant))
        grid.addWidget(reset_button, len(THEME_COLOR_BASES), 0, 1, 2)
        return group

    def _create_accent_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("settings.appearance.accents"))
        grid = QtWidgets.QGridLayout(group)
        for row, (key, label_key) in enumerate(ACCENT_COLOR_FIELDS):
            self._add_color_picker_row(grid, row, translate(label_key), key)
        return group

    def _create_font_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(translate("settings.appearance.font_section"))
        layout = QtWidgets.QFormLayout(group)
        self._font_combo = QtWidgets.QFontComboBox()
        layout.addRow(translate("settings.appearance.font_family"), self._font_combo)
        self._font_size_spin = QtWidgets.QSpinBox()
        self._font_size_spin.setRange(6, 48)
        layout.addRow(translate("settings.appearance.font_size"), self._font_size_spin)
        reset_button = QtWidgets.QPushButton(translate("settings.appearance.reset_font"))
        reset_button.clicked.connect(self._reset_font_settings)
        layout.addRow(reset_button)
        return group

    def _add_color_picker_row(
        self,
        layout: QtWidgets.QGridLayout,
        row: int,
        label: str,
        key: str,
    ) -> None:
        layout.addWidget(QtWidgets.QLabel(label), row, 0)
        button = QtWidgets.QPushButton()
        button.setMinimumWidth(140)
        button.clicked.connect(partial(self._choose_color, key, label))
        layout.addWidget(button, row, 1)
        self._color_buttons[key] = button

    def _load_values(self) -> None:
        """Заполняет контролы текущими значениями из SettingsRegistry."""

        self._language_combo.setCurrentText(
            self._settings.get_value("app", "language", default="ru")
        )
        self._theme_combo.setCurrentText(self._settings.get_value("app", "theme", default="system"))
        self._save_window_state.setChecked(
            self._settings.get_value("app", "save_window_state", default=True)
        )
        refresh_enabled = bool(
            self._settings.get_value("connections", "auto_refresh_enabled", default=True)
        )
        self._refresh_enabled_check.setChecked(refresh_enabled)
        self._refresh_spin.setEnabled(refresh_enabled)
        self._refresh_spin.setValue(
            self._settings.get_value("connections", "refresh_rate_ms", default=5000)
        )
        metrics_group = self._settings.get_group("metrics")
        self._container_stats_spin.setValue(metrics_group.get("container_stats_refresh_ms"))
        timeout_enabled = bool(
            self._settings.get_value("connections", "connection_timeout_enabled", default=True)
        )
        self._timeout_enabled_check.setChecked(timeout_enabled)
        self._timeout_spin.setEnabled(timeout_enabled)
        self._timeout_spin.setValue(
            self._settings.get_value("connections", "connection_timeout_sec", default=5)
        )
        self._system_metrics_checkbox.setChecked(metrics_group.get("system_metrics_enabled"))
        self._system_metrics_spin.setEnabled(self._system_metrics_checkbox.isChecked())
        self._system_metrics_spin.setValue(metrics_group.get("system_metrics_refresh_ms"))
        self._auto_load_projects.setChecked(
            self._settings.get_value("projects", "auto_load_projects", default=True)
        )
        self._auto_activate_connections.setChecked(
            self._settings.get_value("connections", "auto_activate_connections", default=True)
        )

        default_connection = self._settings.get_value(
            "connections", "default_connection", default=None
        )
        if default_connection:
            index = self._default_connection_combo.findData(default_connection)
            if index >= 0:
                self._default_connection_combo.setCurrentIndex(index)

        terminal_group = self._settings.get_group("terminal")
        self._use_system_console.setChecked(terminal_group.get("use_system_console"))
        self._container_shell_edit.setText(terminal_group.get("container_shell"))

        logging_group = self._settings.get_group("logging")
        self._logging_enabled.setChecked(bool(logging_group.get("enabled")))
        self._log_level_combo.setCurrentText(logging_group.get("level"))
        self._max_file_size_spin.setValue(int(logging_group.get("max_file_size_mb")))
        self._max_files_spin.setValue(int(logging_group.get("max_archived_files")))
        self._load_appearance_values()
        self._load_hotkeys_values()

    def accept(self) -> None:
        """Сохраняет изменения и закрывает диалог."""

        try:
            self._apply_general_settings()
            self._apply_logging_settings()
            self._apply_appearance_settings()
            self._apply_hotkeys_settings()
            self._settings.save_to_disk()
        except SettingsValidationError as exc:
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                str(exc),
            )
            return
        super().accept()

    def _apply_general_settings(self) -> None:
        """Применяет настройки вкладки `Основные`."""

        self._settings.set_value("app", "language", self._language_combo.currentText())
        self._settings.set_value("app", "theme", self._theme_combo.currentText())
        self._settings.set_value("app", "save_window_state", self._save_window_state.isChecked())
        self._settings.set_value(
            "connections", "auto_refresh_enabled", self._refresh_enabled_check.isChecked()
        )
        self._settings.set_value("connections", "refresh_rate_ms", int(self._refresh_spin.value()))
        self._settings.set_value(
            "metrics",
            "container_stats_refresh_ms",
            int(self._container_stats_spin.value()),
        )
        self._settings.set_value(
            "connections",
            "connection_timeout_enabled",
            self._timeout_enabled_check.isChecked(),
        )
        self._settings.set_value(
            "connections", "connection_timeout_sec", int(self._timeout_spin.value())
        )
        self._settings.set_value(
            "projects", "auto_load_projects", self._auto_load_projects.isChecked()
        )
        self._settings.set_value(
            "connections", "auto_activate_connections", self._auto_activate_connections.isChecked()
        )
        self._settings.set_value(
            "metrics",
            "system_metrics_enabled",
            self._system_metrics_checkbox.isChecked(),
        )
        self._settings.set_value(
            "metrics",
            "system_metrics_refresh_ms",
            int(self._system_metrics_spin.value()),
        )

        default_connection = self._default_connection_combo.currentData()
        if default_connection is None:
            self._settings.set_value("connections", "default_connection", None)
        else:
            self._settings.set_value("connections", "default_connection", str(default_connection))

        self._settings.set_value(
            "terminal",
            "use_system_console",
            self._use_system_console.isChecked(),
        )
        self._settings.set_value(
            "terminal",
            "container_shell",
            self._container_shell_edit.text().strip() or "/bin/sh",
        )

    def _apply_logging_settings(self) -> None:
        """Применяет параметры логирования."""

        self._settings.set_value("logging", "enabled", self._logging_enabled.isChecked())
        self._settings.set_value("logging", "level", self._log_level_combo.currentText())
        self._settings.set_value(
            "logging", "max_file_size_mb", int(self._max_file_size_spin.value())
        )
        self._settings.set_value("logging", "max_archived_files", int(self._max_files_spin.value()))

    def _load_appearance_values(self) -> None:
        theme_group = self._settings.get_group("theme")
        for key, button in self._color_buttons.items():
            self._set_color_button_value(key, theme_group.get(key))
        if self._font_combo:
            font_value = theme_group.get("font_family")
            if font_value:
                self._font_combo.setCurrentFont(QtGui.QFont(font_value))
            else:
                self._font_combo.setCurrentFont(self.font())
        if self._font_size_spin:
            self._font_size_spin.setValue(int(theme_group.get("font_size")))

    def _set_color_button_value(self, key: str, value: str) -> None:
        button = self._color_buttons.get(key)
        if not button:
            return
        normalized = value.lower()
        qt_color = QtGui.QColor(normalized)
        text_color = "#000000" if qt_color.lightness() > 128 else "#ffffff"
        button.setProperty("color_value", normalized)
        button.setText(normalized.upper())
        button.setStyleSheet(
            f"background-color: {normalized}; border: 1px solid #7f7f7f; color: {text_color};"
        )

    def _choose_color(self, key: str, label: str) -> None:
        button = self._color_buttons[key]
        current_value = button.property("color_value") or "#000000"
        title = translate("settings.appearance.color_picker_title").format(name=label)
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current_value), self, title)
        if color.isValid():
            self._set_color_button_value(key, color.name())

    def _reset_theme_colors(self, variant: str) -> None:
        theme_group = self._settings.get_group("theme")
        for base_key, _label in THEME_COLOR_BASES:
            key = f"{base_key}_{variant}"
            default_value = theme_group.get_default(key)
            self._set_color_button_value(key, default_value)

    def _reset_font_settings(self) -> None:
        theme_group = self._settings.get_group("theme")
        if self._font_combo:
            default_family = theme_group.get_default("font_family") or self.font().family()
            self._font_combo.setCurrentFont(QtGui.QFont(default_family or self.font().family()))
        if self._font_size_spin:
            self._font_size_spin.setValue(int(theme_group.get_default("font_size")))

    def _apply_appearance_settings(self) -> None:
        for key, button in self._color_buttons.items():
            value = button.property("color_value")
            if not value:
                continue
            self._settings.set_value("theme", key, str(value))
        if self._font_combo:
            self._settings.set_value(
                "theme",
                "font_family",
                self._font_combo.currentFont().family(),
            )
        if self._font_size_spin:
            self._settings.set_value("theme", "font_size", int(self._font_size_spin.value()))

    def _load_hotkeys_values(self) -> None:
        """Загружает текущие значения горячих клавиш."""

        hotkeys_group = self._settings.get_group("hotkeys")
        self._hotkeys_state = hotkeys_group.to_dict()
        self._update_hotkeys_display()

    def _update_hotkeys_display(self) -> None:
        """Отображает актуальные комбинации в таблице."""

        hotkeys_group = self._settings.get_group("hotkeys")
        for key, label in self._hotkey_labels.items():
            value = self._hotkeys_state.get(key) or hotkeys_group.get(key)
            label.setText(value or "-")

    def _change_hotkey(self, key: str) -> None:
        """Открывает диалог выбора комбинации и обновляет состояние."""

        current_value = self._hotkeys_state.get(key) or ""
        dialog = HotkeyCaptureDialog(current_value=current_value, parent=self)
        if not dialog.exec():
            return
        new_value = dialog.sequence.strip()
        if not new_value:
            return
        duplicate_key = next(
            (
                other_key
                for other_key, other_value in self._hotkeys_state.items()
                if other_key != key and other_value == new_value
            ),
            None,
        )
        if duplicate_key:
            labels_map = dict(HOTKEY_ACTIONS)
            QtWidgets.QMessageBox.warning(
                self,
                translate("messages.validation_error_title"),
                translate("settings.hotkeys.dialog.duplicate").format(
                    action=translate(labels_map.get(duplicate_key, duplicate_key))
                ),
            )
            return
        self._hotkeys_state[key] = new_value
        self._update_hotkeys_display()

    def _reset_hotkeys_to_defaults(self) -> None:
        """Возвращает горячие клавиши к значениям по умолчанию."""

        hotkeys_group = self._settings.get_group("hotkeys")
        for key, _ in HOTKEY_ACTIONS:
            try:
                self._hotkeys_state[key] = hotkeys_group.get_default(key)
            except Exception:  # pragma: no cover - защитный код
                self._hotkeys_state[key] = hotkeys_group.get(key)
        self._update_hotkeys_display()

    def _apply_hotkeys_settings(self) -> None:
        """Сохраняет все комбинации в SettingsRegistry."""

        for key, value in self._hotkeys_state.items():
            if value:
                self._settings.set_value("hotkeys", key, value)

    def _open_help_dialog(self) -> None:
        """Открывает справку из настроек."""

        dialog = HelpDialog(
            language=self._settings.get_value("app", "language", default="ru"),
            resources_dir=Path(__file__).resolve().parents[2],
            parent=self,
        )
        dialog.exec()


class HotkeyCaptureDialog(QtWidgets.QDialog):
    """Диалог записи новой горячей клавиши."""

    def __init__(self, *, current_value: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.sequence: str = current_value
        self._sequence_edit = QtWidgets.QKeySequenceEdit()
        self._sequence_edit.setMaximumSequenceLength(1)
        if current_value and current_value != "-":
            self._sequence_edit.setKeySequence(QtGui.QKeySequence(current_value))
        self._current_label = QtWidgets.QLabel(
            translate("settings.hotkeys.dialog.current").format(value=current_value or "-")
        )

        self.setWindowTitle(translate("settings.hotkeys.dialog.title"))
        self.resize(420, 180)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        instructions = QtWidgets.QLabel(translate("settings.hotkeys.dialog.hint"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self._sequence_edit.keySequenceChanged.connect(self._on_sequence_changed)
        layout.addWidget(self._sequence_edit)
        layout.addWidget(self._current_label)

        buttons = QtWidgets.QHBoxLayout()
        clear_button = QtWidgets.QPushButton(translate("settings.hotkeys.dialog.clear"))
        clear_button.clicked.connect(self._on_clear_clicked)
        buttons.addWidget(clear_button)
        buttons.addStretch()

        done_button = QtWidgets.QPushButton(translate("settings.hotkeys.dialog.done"))
        done_button.clicked.connect(self._on_done_clicked)
        cancel_button = QtWidgets.QPushButton(translate("actions.close"))
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(done_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _on_sequence_changed(self, sequence: QtGui.QKeySequence) -> None:
        self.sequence = sequence.toString(QtGui.QKeySequence.SequenceFormat.NativeText)
        self._current_label.setText(
            translate("settings.hotkeys.dialog.current").format(value=self.sequence or "-")
        )

    def _on_clear_clicked(self) -> None:
        self._sequence_edit.clear()
        self._on_sequence_changed(QtGui.QKeySequence())

    def _on_done_clicked(self) -> None:
        self.accept()
