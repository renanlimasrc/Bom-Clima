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
            # Editors on Windows write a BOM, and users type regional codes.
            raw = LANG_FILE.read_text("utf-8").lstrip("﻿").strip()
            if raw[:2] in _SUPPORTED_LANGS:
                _current_lang_cache = raw[:2]
                return _current_lang_cache
        except (OSError, UnicodeDecodeError):
            pass
    # POSIX precedence is LC_ALL > LC_MESSAGES > LANG. Reading only $LANG
    # ignored a user's explicit LC_ALL, and LC_ALL=C with LANG=pt_BR is common.
    env = (
        os.environ.get("LC_ALL")
        or os.environ.get("LC_MESSAGES")
        or os.environ.get("LANGUAGE")
        or os.environ.get("LANG")
        or ""
    )
    if env:
        code = env.split(".")[0].split("_")[0][:2]
        if code in _SUPPORTED_LANGS:
            _current_lang_cache = code
            return code
    try:
        # Read-only: locale.setlocale() here mutated LC_MESSAGES for the whole
        # process as a side effect of the first t() call.
        loc = locale.getlocale(locale.LC_MESSAGES)
        code = (loc[0] or "").split("_")[0][:2]
        if code in _SUPPORTED_LANGS:
            _current_lang_cache = code
            return code
    except (locale.Error, ValueError, TypeError):
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


def set_lang(lang: str, persist: bool = False) -> None:
    """Apply a language for this run.

    persist=False by default: `--lang` used to write ~/.config/bom-clima/lang on
    every call, so a one-off `bom-clima sp --lang en` silently overrode the
    desktop locale for every later run. Only an explicit `--config-set lang=`
    should reach that far, which is what the one caller below passes.
    """
    global _current_lang_cache
    if lang not in _SUPPORTED_LANGS:
        return
    _current_lang_cache = lang
    if not persist:
        return
    try:
        LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LANG_FILE.write_text(lang, "utf-8")
    except OSError:
        # The choice still applies to this run; only persistence failed, and a
        # read-only $HOME must not abort the command.
        pass


def reset_lang_cache() -> None:
    global _current_lang_cache
    _current_lang_cache = None
