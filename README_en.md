# Docker Simple Manager

<p align="center">
  <img src="logo-dsm.png" alt="SVS Logo" width="160" height=auto/>
</p>

[Русская версия](README.md)

## Table of Contents

- [Project Overview](#project-overview)
- [Key Objectives](#key-objectives)
- [Interface Features](#interface-features)
- [Architecture & Components](#architecture--components)
- [Environment Setup](#environment-setup)
- [Run & Tests](#run--tests)
- [Binary Builds](#binary-builds)
- [Release Checklist](#release-checklist)
- [Documentation](#documentation)
- [License](#license)

## Project Overview

Docker Simple Manager is a cross-platform desktop application (Python 3.13+, PySide6) that simplifies day-to-day Docker operations. It manages multiple connections (local sockets, Docker Desktop, SSH hosts), allows creating runnable “projects”, and exposes all common Docker entities (containers, images, volumes, builds) via a responsive GUI.

## Key Objectives

- Manage multiple Docker connections: create/edit/delete, test status, activate/deactivate, log every action.
- Provide reusable project definitions (Docker commands, docker-compose files, Dockerfiles, shell scripts) with unified logging and launch history.
- Monitor and operate containers/images/volumes/builds from the main window tabs with automatic or manual refresh.
- Persist UI state (window geometry, table layouts, dialog sizes) and keep all blocking operations in worker threads.
- Offer centralized logging (`app.log`, `projects.log`) and quick access to settings, logs, help and about dialogs.

## Interface Features

- **Main window:** dashboard with counts, tabbed views (`Containers`, `Images`, `Volumes`, `Builds`), footer with status/terminal, placeholder texts while loading.
- **Connection Manager:** table with icon buttons (activate/deactivate, edit, test, delete), async status checks, SSH key picker, auto-state restoration.
- **Project Manager:** search/filterable table, icon actions (edit/run/logs/delete), scrollable form for create/edit, confirmations for destructive actions.
- **Settings dialog:** language/theme, refresh timers, connection timeout, project auto-load, logging levels, UI state options, hotkeys.
- **Auxiliary dialogs:** logs viewer, container console (pexpect), help/about.

## Architecture & Components

- `src/settings`: registry, groups, validators, observers, migrations.
- `src/connections`: manager, models, docker client helpers.
- `src/projects`: project manager, executor with queue-based logging.
- `src/docker_api`: high-level data provider for Docker resources.
- `src/ui`: main window, dialogs, widgets, resources, styles.
- `src/utils`, `src/i18n`: logging helpers, filesystem paths, translations.

See `docs/06_project_architecture.md` for the directory map and `docs/03_ui_ux_prototypes.md` for UI wireframes.

## Environment Setup

```bash
git clone https://github.com/dsmanager/docker-simple-manager.git
cd docker-simple-manager
uv pip install -e ".[dev]"
```

Set `DSM_HOME` if you need a custom workspace (default `~/.dsmanager`). Docker Engine or Docker Desktop should be reachable from the configured socket/SSH endpoint.

## Run & Tests

```bash
# run the GUI (inside the uv-managed venv)
uv run docker-simple-manager

# quality gates
make lint
make typecheck
make test
```

## Binary Builds

```
# Linux: produces dist/dsm-linux/dsm
make build-linux

# macOS builds universal2 by default; set DSM_MAC_ARCH=arm64|x86_64 if needed
make build-macos

# direct PyInstaller invocation with custom output names
DSM_BINARY_NAME=dsm DSM_DIST_NAME=dsm-linux \
  uv run --extra dev pyinstaller --clean -y pyinstaller.spec

# Build .deb package (Linux)
make package-deb
# Artifact: dist/docker-simple-manager_<version>_amd64.deb
```

All translations, styles and UI assets are bundled via `collect_data_files` inside `pyinstaller.spec`. Use `make dist-clean` to wipe `build/` and `dist/`.

## Release Checklist

1. Run `make lint`, `make typecheck`, `make test`.
2. Smoke-test GUI against local and remote Docker connections.
3. Build binaries for target platforms (`make build-linux`, `make build-macos`) and verify they start.
4. Update docs/changelog/version in `pyproject.toml`, archive artifacts if needed.
5. Execute `make dist-clean` before packaging the source tree.

## Documentation

- `docs/00_documentation_summary.md` — quick index of all docs.
- `docs/01_technical_specification.md` — functional specification.
- `docs/02_settings_system_architecture.md` — settings subsystem.
- `docs/03_ui_ux_prototypes.md` — ASCII UI prototypes.
- `docs/04_ai_agent_prompt.md` — AI developer guide.
- `docs/05_development_checklist.md` — task checklist.
- `docs/06_project_architecture.md` — architecture reference.
- `docs/07_implementation_overview.md` — current implementation summary.

## License

MIT License (to be finalized before release).***
