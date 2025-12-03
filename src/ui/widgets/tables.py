"""Переиспользуемые виджеты для интерактивных таблиц DSM."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Sequence

from PySide6 import QtCore, QtWidgets

from src.i18n.translator import translate


RowData = Dict[str, Any]
ToggleFilter = Callable[[RowData], bool]


@dataclass(slots=True)
class ColumnDefinition:
    """Описание одной колонки таблицы."""

    header: str
    key: str
    formatter: Callable[[Any], str] | None = None

    def render(self, value: Any) -> str:
        """Возвращает строку для отображения."""

        if self.formatter:
            return self.formatter(value)
        if value is None:
            return "-"
        return str(value)


@dataclass(slots=True)
class RowAction:
    """Описание действия над строкой таблицы."""

    label: str
    tooltip: str
    callback: Callable[[RowData], None]


class ResourceTable(QtWidgets.QWidget):
    """Виджет с поиском, фильтрами и деревообразной таблицей."""

    def __init__(
        self,
        *,
        columns: Sequence[ColumnDefinition],
        group_key: str | None = None,
        toggle_label: str | None = None,
        toggle_filter: ToggleFilter | None = None,
        row_actions: Sequence[RowAction] | None = None,
        row_post_processor: Callable[[QtWidgets.QTreeWidgetItem, RowData], None] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self._group_key = group_key
        self._toggle_filter = toggle_filter
        self._row_actions = list(row_actions) if row_actions else []
        self._row_post_processor = row_post_processor
        self._rows: List[RowData] = []
        self._default_placeholder = translate("tables.no_data")
        self._placeholder_text = self._default_placeholder
        if self._row_actions:
            self._columns.append(ColumnDefinition(translate("tables.actions"), "__actions__"))
        self._setup_ui(toggle_label)

    # ------------------------------------------------------------------ setup
    def _setup_ui(self, toggle_label: str | None) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        controls = QtWidgets.QHBoxLayout()
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText(translate("tables.search_placeholder"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._refresh_view)
        controls.addWidget(self._search)

        controls.addStretch()

        self._toggle_checkbox: QtWidgets.QCheckBox | None = None
        if toggle_label:
            self._toggle_checkbox = QtWidgets.QCheckBox(toggle_label)
            self._toggle_checkbox.stateChanged.connect(self._refresh_view)
            controls.addWidget(self._toggle_checkbox)

        layout.addLayout(controls)

        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels([column.header for column in self._columns])
        header = self._tree.header()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self._tree.setRootIsDecorated(self._group_key is not None)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._tree)

    @property
    def tree(self) -> QtWidgets.QTreeWidget:
        """Доступ к внутреннему дереву."""

        return self._tree

    # ----------------------------------------------------------------- data api
    def set_rows(self, rows: Iterable[RowData]) -> None:
        """Сохраняет и отображает список строк."""

        self._placeholder_text = self._default_placeholder
        self._rows = list(rows)
        self._refresh_view()

    def show_placeholder(self, message: str) -> None:
        """Отображает сообщение вместо данных."""

        self._rows = []
        self._placeholder_text = message or self._default_placeholder
        self._refresh_view()

    def current_row(self) -> RowData | None:
        """Возвращает данные выбранной строки (только дочерние элементы)."""

        item = self._tree.currentItem()
        if item is None:
            return None
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return data
        return None

    def selected_value(self, key: str) -> str | None:
        """Возвращает значение конкретного поля выбранной строки."""

        row = self.current_row()
        if not row:
            return None
        value = row.get(key)
        if value is None:
            return None
        return str(value)

    # --------------------------------------------------------------- rendering
    def _refresh_view(self) -> None:
        self._tree.clear()
        rows = self._apply_filters()
        if not rows:
            placeholder = QtWidgets.QTreeWidgetItem(
                [self._placeholder_text] + [""] * (len(self._columns) - 1)
            )
            placeholder.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            font = placeholder.font(0)
            font.setItalic(True)
            placeholder.setFont(0, font)
            self._tree.addTopLevelItem(placeholder)
            return

        if self._group_key:
            groups: Dict[str, List[RowData]] = defaultdict(list)
            for row in rows:
                group_name = row.get(self._group_key) or translate("tables.group_unknown")
                groups[str(group_name)].append(row)
            for group_name, grouped_rows in groups.items():
                parent = QtWidgets.QTreeWidgetItem([group_name] + [""] * (len(self._columns) - 1))
                parent.setFlags(parent.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
                self._tree.addTopLevelItem(parent)
                for row in grouped_rows:
                    self._create_item(row, parent)
        else:
            for row in rows:
                self._create_item(row, None)
        self._tree.expandAll()

    def _create_item(
        self,
        row: RowData,
        parent: QtWidgets.QTreeWidgetItem | None,
    ) -> None:
        values = []
        for column in self._columns:
            if column.key == "__actions__":
                values.append("")
            else:
                values.append(column.render(row.get(column.key)))
        if parent is None:
            item = QtWidgets.QTreeWidgetItem(self._tree, values)
        else:
            item = QtWidgets.QTreeWidgetItem(parent, values)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, row)
        for index, value in enumerate(values):
            if self._columns[index].key != "__actions__":
                item.setToolTip(index, value)
        if self._row_actions:
            self._attach_row_actions(item, row)
        if self._row_post_processor:
            self._row_post_processor(item, row)

    def _attach_row_actions(self, item: QtWidgets.QTreeWidgetItem, row: RowData) -> None:
        """Добавляет кнопки действий в последнюю колонку."""

        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for action in self._row_actions:
            button = QtWidgets.QToolButton()
            button.setText(action.label)
            button.setToolTip(action.tooltip)
            button.clicked.connect(lambda _checked=False, cb=action.callback, r=row: cb(r))
            layout.addWidget(button)
        layout.addStretch()
        self._tree.setItemWidget(item, len(self._columns) - 1, container)

    # -------------------------------------------------------------- filtering
    def _apply_filters(self) -> List[RowData]:
        rows = list(self._rows)
        if self._toggle_checkbox and self._toggle_filter and self._toggle_checkbox.isChecked():
            rows = [row for row in rows if self._toggle_filter(row)]

        query = self._search.text().strip().lower()
        if not query:
            return rows

        filtered: List[RowData] = []
        for row in rows:
            if self._row_matches(row, query):
                filtered.append(row)
        return filtered

    def _row_matches(self, row: RowData, query: str) -> bool:
        for column in self._columns:
            if column.key == "__actions__":
                continue
            value = row.get(column.key)
            if value is None:
                continue
            if query in str(value).lower():
                return True
        if self._group_key:
            group_value = row.get(self._group_key)
            if group_value and query in str(group_value).lower():
                return True
        return False
