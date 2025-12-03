"""Футер приложения с отображением статусов и кнопкой терминала."""

from __future__ import annotations

from PySide6 import QtWidgets

from src.i18n.translator import translate


class FooterWidget(QtWidgets.QWidget):
    """Нижняя панель с короткими статусами."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(24)

        self._engine_label = QtWidgets.QLabel(translate("footer.engine_running"))
        layout.addWidget(self._engine_label)

        self._stats_label = QtWidgets.QLabel(
            f"{translate('footer.stat_ram')}: N/A   " f"{translate('footer.stat_cpu')}: N/A"
        )
        layout.addWidget(self._stats_label)
        layout.addStretch()

    def update_engine_status(self, text: str) -> None:
        """Обновляет текст статуса docker engine."""

        self._engine_label.setText(text)

    def update_stats(self, *, ram: str, cpu: str) -> None:
        """Отображает основные метрики."""

        self._stats_label.setText(
            f"{translate('footer.stat_ram')}: {ram}   " f"{translate('footer.stat_cpu')}: {cpu}"
        )
