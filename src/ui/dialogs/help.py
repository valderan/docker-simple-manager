"""Полноценный диалог справки с Markdown и поиском."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from src.i18n.translator import translate


class HelpDialog(QtWidgets.QDialog):
    """Отображает контент из faq_{lang}.md и предоставляет поиск."""

    def __init__(
        self,
        *,
        language: str,
        resources_dir: Path,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._language = language.lower()
        self._resources_dir = resources_dir
        self._search_position = 0
        self._text_browser = QtWidgets.QTextBrowser()
        self._search_edit = QtWidgets.QLineEdit()
        self._search_button = QtWidgets.QPushButton(translate("help.search"))
        self._status_label = QtWidgets.QLabel()

        self.setWindowTitle(translate("help.dialog.title"))
        self.resize(800, 600)
        self._build_ui()
        self._load_markdown()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        search_row = QtWidgets.QHBoxLayout()
        self._search_edit.setPlaceholderText(translate("help.search.placeholder"))
        self._search_edit.returnPressed.connect(self._on_search_clicked)
        search_row.addWidget(self._search_edit)
        self._search_button.clicked.connect(self._on_search_clicked)
        search_row.addWidget(self._search_button)
        layout.addLayout(search_row)

        self._text_browser.setOpenExternalLinks(True)
        layout.addWidget(self._text_browser, stretch=1)
        layout.addWidget(self._status_label)

        close_button = QtWidgets.QPushButton(translate("actions.close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def _load_markdown(self) -> None:
        file_name = f"faq_{'ru' if self._language == 'ru' else 'en'}.md"
        file_path = self._resources_dir / file_name
        if not file_path.exists():
            fallback = self._resources_dir / "faq_en.md"
            file_path = fallback if fallback.exists() else file_path
        if not file_path.exists():
            self._text_browser.setPlainText(translate("help.errors.not_found"))
            self._status_label.setText(str(file_path))
            return
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - файловые ошибки
            self._text_browser.setPlainText(translate("help.errors.load_failed").format(error=exc))
            self._status_label.setText(str(file_path))
            return
        self._text_browser.setMarkdown(content)
        self._status_label.setText(str(file_path))
        self._text_browser.moveCursor(QtGui.QTextCursor.MoveOperation.Start)

    def _on_search_clicked(self) -> None:
        query = self._search_edit.text().strip()
        if not query:
            self._status_label.setText(translate("help.search.enter_query"))
            return
        document = self._text_browser.document()
        cursor = self._text_browser.textCursor()
        if cursor.isNull() or not cursor.hasSelection():
            cursor = QtGui.QTextCursor(document)
            cursor.setPosition(0)
        found = document.find(query, cursor)
        if not found:
            cursor = QtGui.QTextCursor(document)
            cursor.setPosition(0)
            found = document.find(query, cursor)
            if not found:
                self._status_label.setText(translate("help.search.not_found"))
                return
        self._text_browser.setTextCursor(found)
        self._status_label.setText("")
