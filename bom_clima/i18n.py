"""Internationalization module for Bom Clima."""

import json
import locale
import os
from pathlib import Path

from .constants import LANG_FILE

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_SUPPORTED_LANGS = ("en", "pt", "es")
_LOCALES_DIR = Path(__file__).parent / "locales"


def _load_translations() -> dict[str, dict[str, str]]:
    translations: dict[str, dict[str, str]] = {}
    for lang in _SUPPORTED_LANGS:
        path = _LOCALES_DIR / f"{lang}.json"
        if path.exists():
            try:
                translations[lang] = json.loads(path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                translations[lang] = {}
    return translations


def _ensure_translations() -> None:
    global _TRANSLATIONS
    if not _TRANSLATIONS:
        _TRANSLATIONS = _load_translations()


def t(key: str) -> str:
    _ensure_translations()
    lang = _current_lang()
    return _TRANSLATIONS.get(lang, _TRANSLATIONS.get("en", {})).get(
        key, _TRANSLATIONS.get("en", {}).get(key, key)
    )


_current_lang_cache: str | None = None


def _current_lang() -> str:
    global _current_lang_cache
    if _current_lang_cache is not None:
        return _current_lang_cache
    if LANG_FILE.exists():
        try:
            lang = LANG_FILE.read_text().strip()
            if lang in _SUPPORTED_LANGS:
                _current_lang_cache = lang
                return lang
        except OSError:
            pass
    env = os.environ.get("LANG", "")
    if env:
        code = env.split(".")[0][:2]
        if code in _SUPPORTED_LANGS:
            _current_lang_cache = code
            return code
    try:
        loc = locale.setlocale(locale.LC_MESSAGES, "")
        code = loc.split(".")[0][:2]
        if code in _SUPPORTED_LANGS:
            _current_lang_cache = code
            return code
    except (locale.Error, ValueError):
        pass
    if os.name == "nt":
        try:
            import ctypes
            windll = ctypes.windll.kernel32  # type: ignore[attr-defined]
            lang_id = windll.GetUserDefaultUILanguage()
            mapping = {
                0x0016: "pt", 0x0416: "pt", 0x0816: "pt", 0x000a: "es",
                0x040a: "es", 0x080a: "es", 0x0c0a: "es", 0x100a: "es",
                0x140a: "es", 0x180a: "es", 0x1c0a: "es", 0x200a: "es",
                0x240a: "es", 0x280a: "es", 0x2c0a: "es", 0x300a: "es",
                0x340a: "es", 0x380a: "es", 0x3c0a: "es", 0x400a: "es",
                0x0009: "en", 0x0409: "en", 0x0809: "en", 0x0c09: "en",
                0x1009: "en", 0x1409: "en", 0x1809: "en", 0x1c09: "en",
                0x2009: "en", 0x2409: "en", 0x2809: "en", 0x2c09: "en",
                0x3009: "en", 0x3409: "en", 0x3809: "en", 0x3c09: "en",
                0x4009: "en",
            }
            if lang_id in mapping:
                _current_lang_cache = mapping[lang_id]
                return mapping[lang_id]
        except (ImportError, AttributeError, OSError):
            pass
    _current_lang_cache = "en"
    return "en"


def set_lang(lang: str) -> None:
    global _current_lang_cache
    if lang in _SUPPORTED_LANGS:
        LANG_FILE.write_text(lang)
        _current_lang_cache = lang


def reset_lang_cache() -> None:
    global _current_lang_cache
    _current_lang_cache = None
