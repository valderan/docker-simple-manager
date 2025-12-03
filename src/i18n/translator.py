"""Простой переводчик строк интерфейса."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_current_locale = "en"
_translations: Dict[str, str] = {}


def _load_default() -> None:
    try:
        set_language("en")
    except FileNotFoundError:
        _translations.clear()
        _translations["app.title"] = "Docker Simple Manager"


def set_language(language: str) -> None:
    """Загружает JSON переводы (en/ru)."""

    global _current_locale, _translations
    available = {"en", "ru"}
    if language not in available:
        language = "en"
    _current_locale = language
    strings_dir = Path(__file__).parent / "strings"
    file_path = strings_dir / f"{language}.json"
    _translations = json.loads(file_path.read_text(encoding="utf-8"))


def translate(key: str) -> str:
    """Возвращает перевод ключа."""

    return _translations.get(key, key)


_load_default()
