# Docker Simple Manager — FAQ & Help

This document describes the application features in thematic sections. Use the search field in the help dialog to jump directly to the required topic.

## 1. Overview

- **Purpose**: manage local or remote Docker engines, containers, images, volumes, and build history from one GUI.
- **Supported OS**: Linux and macOS.
- **Workspace**: `~/.dsmanager` stores settings, projects, and logs.
- **Languages**: Russian or English (switch in Settings).
- **Themes**: Light, Dark, and System.

## 2. Main Window

- **Connection bar**: choose the active connection and refresh data (`F5` by default).
- **Dashboard**: number of connections and projects.
- **Tabs**:
  - `Containers` – control running containers.
  - `Images` – inspect and remove images.
  - `Volumes` – manage Docker volumes.
  - `Builds` – show buildx history (when buildx plugin available).
- **Footer**: engine status, system metrics, and embedded terminal area.
- **Tab shortcuts**: digits `1`–`4` switch between tabs (customizable).

## 3. Connection Manager

- Create local or remote (SSH) connections with socket, credentials, notes.
- Test connections, view status, set default connection or auto-connect list.
- Quickly open the dialog from the menu or a global shortcut.

## 4. Project Manager

- Define projects bound to connections with command/path, tags, priority, status, and history.
- Track run history, export/import project definitions.
- Launch the last project via a dedicated shortcut.

## 5. Managing Docker Resources

- **Containers**: start, pause, restart, delete, inspect logs, open shell sessions.
- **Images**: view list with tags, delete selected images.
- **Volumes**: list volumes, delete or copy their mount points.
- **Builds**: show build history when Docker Buildx is detected.

## 6. Container Console

- Run commands via embedded console or system terminal (configured in Settings).
- Default shell is `/bin/sh`, but any executable path may be set.

## 7. Application Logs

- Accessible from the Parameters → Logs menu.
- Filter by file, level, date range, or text query.
- Double-click any row to open a separate dialog with full log text and copy button.
- Export filtered lines, delete selected ones, or clear the entire file.

## 8. Help Center

- Open from the Parameters menu, Settings dialog button, or `F1`.
- Loads the localized markdown document (this file) with formatting and search support.

## 9. Settings Dialog

- **General**: language, theme, remembering window state, refresh intervals, connection timeouts, system metrics, terminal options.
- **Logging**: enable/disable logging, log level, file size, number of backups.
- **Appearance**: tweak light/dark palettes, accent colors, fonts; reset to defaults at any time.
- **Hotkeys**:
  - Shows every global shortcut (menus, tabs, refresh, help, etc.).
  - Use the capture dialog to press the desired combination; confirm with “Done”.
  - Reset all shortcuts to default values if needed.

## 10. Default Hotkeys

| Action | Shortcut |
|--------|----------|
| Open Connections Manager | `Ctrl+Alt+C` |
| Test Connection | `Ctrl+Alt+T` |
| Open Projects Manager | `Ctrl+Alt+P` |
| Open Settings | `Ctrl+Alt+S` |
| Open Logs | `Ctrl+Alt+L` |
| Open Help | `F1` |
| Refresh Data | `F5` |
| Switch to tab 1–4 | `1`, `2`, `3`, `4` |
| Exit Application | `Ctrl+Q` |
| Next tab | `Ctrl+Tab` |
| Previous tab | `Ctrl+Shift+Tab` |
| Run last project | `Ctrl+Alt+R` |

Every shortcut can be reassigned in the “Hotkeys” tab.

## 11. Frequently Asked Questions

1. **No builds are shown** — install Docker Buildx (see instructions inside the Builds tab) and restart the application.
2. **Cannot connect to remote Docker** — check SSH connectivity, key path, and increase the connection timeout if necessary.
3. **Containers list is empty** — make sure an active connection is selected and press `F5`.
4. **Terminal does not open** — enable “Use system console” or configure a valid shell path.
5. **Shortcuts stop working** — rebind them in Settings and ensure there are no conflicts between actions.

## 12. Tips

- Customize theme colors for better contrast in your environment.
- Keep exported projects under `~/.dsmanager/projects` for quick backup.
- Review application logs regularly to detect connection or Docker errors early.

