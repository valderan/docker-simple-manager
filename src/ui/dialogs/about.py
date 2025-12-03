"""Диалог «О программе» с локализацией."""

from __future__ import annotations

import platform
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from src import __version__
from src.i18n.translator import translate


class AboutDialog(QtWidgets.QDialog):
    """Отображает сведения о приложении, версии и ссылках."""

    def __init__(
        self,
        *,
        icon: QtGui.QIcon | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon = icon
        self.setWindowTitle(translate("about.dialog.title"))
        self.resize(480, 320)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        icon_path = Path(__file__).resolve().parents[1] / "resources" / "icons" / "logo-dsm.png"
        pixmap = None
        if self._icon and not self._icon.isNull():
            pixmap = self._icon.pixmap(128, 128)
        elif icon_path.exists():
            pixmap = QtGui.QPixmap(str(icon_path)).scaled(
                128,
                128,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        if pixmap:
            icon_label = QtWidgets.QLabel()
            icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)

        title = QtWidgets.QLabel(translate("about.app.name"))
        font = title.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version_label = QtWidgets.QLabel(translate("about.version").format(version=__version__))
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        build_label = QtWidgets.QLabel(
            translate("about.build").format(python=platform.python_version())
        )
        build_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(build_label)

        description = QtWidgets.QLabel(translate("about.description"))
        description.setWordWrap(True)
        description.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        copyright_label = QtWidgets.QLabel(translate("about.copyright"))
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        github_link = QtWidgets.QLabel(
            f"<a href='https://github.com/dsmanager/docker-simple-manager'>{translate('about.links.github')}</a>"
        )
        github_link.setTextFormat(QtCore.Qt.TextFormat.RichText)
        github_link.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        github_link.setOpenExternalLinks(True)
        github_link.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(github_link)

        close_button = QtWidgets.QPushButton(translate("actions.close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

    def _open_url(self, url: str) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
