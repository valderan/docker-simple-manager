"""Интерактивная консоль контейнера на базе pexpect."""

from __future__ import annotations

import os
import shlex
from typing import Dict, List, Optional

import pexpect
from PySide6 import QtCore, QtGui, QtWidgets

from src.i18n.translator import translate


class ContainerConsoleDialog(QtWidgets.QDialog):
    """Диалог, отображающий интерактивный вывод docker exec."""

    def __init__(
        self,
        container_id: str,
        container_name: str,
        shell_command: str,
        docker_host: str | None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._container_id = container_id
        self._shell_command = shell_command
        self._docker_host = docker_host
        self._process: Optional[pexpect.spawn[str]] = None
        self._notifier: Optional[QtCore.QSocketNotifier] = None

        self.setWindowTitle(translate("containers.console.title").format(name=container_name))
        self.resize(900, 600)

        layout = QtWidgets.QVBoxLayout(self)
        self._output = QtWidgets.QPlainTextEdit()
        self._output.setFont(QtGui.QFont("Monospace", 11))
        self._output.setReadOnly(True)
        self._output.installEventFilter(self)
        layout.addWidget(self._output)

        self._status_label = QtWidgets.QLabel("")
        layout.addWidget(self._status_label)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._spawn_thread: Optional[ConsoleSpawnThread] = None
        self._start_process_async()

    def _start_process_async(self) -> None:
        self._status_label.setText(translate("terminal.messages.connecting"))
        self._progress.show()
        self._output.setDisabled(True)
        thread = ConsoleSpawnThread(
            container_id=self._container_id,
            shell_parts=self._build_docker_command(),
            docker_host=self._docker_host,
        )
        thread.success.connect(self._on_spawn_ready)
        thread.error.connect(self._on_spawn_error)
        thread.finished.connect(thread.deleteLater)
        self._spawn_thread = thread
        thread.start()

    def _on_spawn_ready(self, process: pexpect.spawn[str], command: str) -> None:
        self._spawn_thread = None
        self._progress.hide()
        self._output.setDisabled(False)
        self._process = process
        self._notifier = QtCore.QSocketNotifier(
            self._process.fileno(), QtCore.QSocketNotifier.Type.Read
        )
        self._notifier.activated.connect(self._read_output)
        self._status_label.setText(command)

    def _on_spawn_error(self, message: str) -> None:
        self._progress.hide()
        QtWidgets.QMessageBox.critical(self, translate("terminal.errors.title"), message)
        self.reject()

    def _build_docker_command(self) -> List[str]:
        parts = self._split_shell(self._shell_command) or ["/bin/sh"]
        return ["exec", "-it", self._container_id] + parts

    def _split_shell(self, value: str) -> List[str]:
        try:
            parts = shlex.split(value)
            return parts if parts else ["/bin/sh"]
        except ValueError:
            return ["/bin/sh"]

    # ----------------------------------------------------------------- IO logic
    def _read_output(self) -> None:
        if not self._process:
            return
        try:
            while True:
                chunk = self._process.read_nonblocking(size=4096, timeout=0)
                if not chunk:
                    break
                self._output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                self._output.insertPlainText(chunk)
                self._output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        except pexpect.exceptions.TIMEOUT:
            pass
        except pexpect.exceptions.EOF:
            self._append_message(translate("terminal.messages.finished").format(code=0))
            self._cleanup_process()

    def _append_message(self, message: str) -> None:
        self._output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self._output.insertPlainText("\n" + message + "\n")
        self._output.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    # ---------------------------------------------------------------- key input
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj is self._output and event.type() == QtCore.QEvent.Type.KeyPress:
            self._handle_key_event(event)  # type: ignore[arg-type]
            return True
        return super().eventFilter(obj, event)

    def _handle_key_event(self, event: QtGui.QKeyEvent) -> None:
        if not self._process or not self._process.isalive():
            return

        key = event.key()
        text = event.text()

        sequences: Dict[int, str] = {
            QtCore.Qt.Key.Key_Return: "\r",
            QtCore.Qt.Key.Key_Enter: "\r",
            QtCore.Qt.Key.Key_Backspace: "\x7f",
            QtCore.Qt.Key.Key_Escape: "\x1b",
            QtCore.Qt.Key.Key_Tab: "\t",
            QtCore.Qt.Key.Key_Left: "\x1b[D",
            QtCore.Qt.Key.Key_Right: "\x1b[C",
            QtCore.Qt.Key.Key_Up: "\x1b[A",
            QtCore.Qt.Key.Key_Down: "\x1b[B",
        }

        if key in sequences:
            self._process.write(sequences[key])
        elif text:
            self._process.write(text)

    # ---------------------------------------------------------------- lifecycle
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._cleanup_process()
        super().closeEvent(event)

    def _cleanup_process(self) -> None:
        if self._notifier is not None:
            self._notifier.setEnabled(False)
            self._notifier.deleteLater()
            self._notifier = None
        if self._process is not None:
            if self._process.isalive():
                self._process.terminate()
            self._process.close(force=True)
            self._process = None
        if self._spawn_thread is not None:
            self._spawn_thread.quit()
            self._spawn_thread.wait(1000)
            self._spawn_thread = None


class ConsoleSpawnThread(QtCore.QThread):
    success = QtCore.Signal(object, str)
    error = QtCore.Signal(str)

    def __init__(
        self, *, container_id: str, shell_parts: List[str], docker_host: str | None
    ) -> None:
        super().__init__()
        self._container_id = container_id
        self._shell_parts = shell_parts
        self._docker_host = docker_host
        self._process: Optional[pexpect.spawn[str]] = None

    def run(self) -> None:
        previous_host = os.environ.get("DOCKER_HOST")
        try:
            if self._docker_host:
                os.environ["DOCKER_HOST"] = self._docker_host
            else:
                os.environ.pop("DOCKER_HOST", None)
            process = pexpect.spawn(
                "docker",
                self._shell_parts,
                encoding="utf-8",
                echo=False,
                timeout=None,
            )
            self._process = process
            self.success.emit(process, "docker " + " ".join(self._shell_parts))
        except Exception as exc:  # pragma: no cover - зависит от окружения
            self.error.emit(str(exc))
        finally:
            if previous_host is not None:
                os.environ["DOCKER_HOST"] = previous_host
            else:
                os.environ.pop("DOCKER_HOST", None)
