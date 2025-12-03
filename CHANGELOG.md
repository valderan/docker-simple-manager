# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-12-03

### Added
- PySide6-based main window with containers/images/volumes/builds tabs and dashboard.
- Connection Manager dialog with activation/deactivation, async status checks, socket picker, SSH key picker, and logging of actions.
- Project Manager dialog that mirrors the specification (table view, scrollable form, confirmations, logging to `projects.log`).
- Asynchronous Docker data provider, background refresh workers, queue-based logging for projects.
- Settings dialog (language/theme, refresh timers, connection timeouts, logging, hotkeys) with persistence via SettingsRegistry.
- PyInstaller spec and Makefile targets for Linux/macOS builds (`make build-linux`, `make build-macos`).
- Comprehensive documentation in `docs/` and bilingual READMEs (`README.md`, `README_en.md`).

### Fixed
- Enforced policy for auto-activating connections on startup based on user settings.
- Corrected dashboard labels, status placeholders, and timers when switching connections.
- Resolved mypy/flake8 warnings related to UI dialogs and executor threads.

### Known Issues
- Qt plugin warning about missing `libtiff.so.5` may appear during PyInstaller builds on Linux (requires system package installation).

[0.1.0]: https://github.com/dsmanager/docker-simple-manager/releases/tag/v0.1.0
