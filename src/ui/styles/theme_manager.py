"""Менеджер тем: загрузка QSS и применение к приложению."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, cast

from PySide6 import QtGui, QtWidgets

from src.settings.registry import SettingsRegistry
from src.settings.groups import ThemeSettings


def apply_theme(app: QtWidgets.QApplication, settings: SettingsRegistry) -> None:
    """Применяет визуальные настройки (цвета и шрифты)."""

    style_dir = Path(__file__).parent
    theme_choice = settings.get_value("app", "theme", default="system")
    theme_variant = "dark" if theme_choice == "dark" else "light"
    template_path = style_dir / f"{theme_variant}_theme.qss"
    template = template_path.read_text(encoding="utf-8")

    theme_group = cast(ThemeSettings, settings.get_group("theme"))
    palette = _build_palette(theme_group, theme_variant)
    qss = template.format(**palette)
    app.setStyleSheet(qss)
    _apply_font(app, theme_group)


def _build_palette(theme_group: ThemeSettings, variant: str) -> Dict[str, str]:
    suffix = "dark" if variant == "dark" else "light"
    palette = {
        "background": theme_group.get(f"background_{suffix}"),
        "text": theme_group.get(f"text_{suffix}"),
        "primary": theme_group.get(f"primary_color_{suffix}"),
        "border": theme_group.get(f"border_color_{suffix}"),
        "table_background": theme_group.get(f"table_background_{suffix}"),
        "table_alternate": theme_group.get(f"table_alternate_background_{suffix}"),
        "table_selection_bg": theme_group.get(f"table_selection_background_{suffix}"),
        "table_selection_text": theme_group.get(f"table_selection_text_{suffix}"),
    }
    if variant == "dark":
        palette["text_on_primary"] = theme_group.get("text_light")
    else:
        palette["text_on_primary"] = "#ffffff"
    return palette


def _apply_font(app: QtWidgets.QApplication, theme_group: ThemeSettings) -> None:
    """Применяет выбранные пользователем настройки шрифта."""

    current_font = app.font()
    family = theme_group.get("font_family")
    if not family:
        family = current_font.family()
    point_size = int(theme_group.get("font_size") or current_font.pointSize())
    font = QtGui.QFont(family, point_size)
    app.setFont(font)
