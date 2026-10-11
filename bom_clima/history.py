"""History management for Bom Clima."""

import contextlib
import json
import os
from datetime import datetime

from .config import load_config
from .constants import HISTORY_FILE


def _quarantine() -> None:
    """Move a damaged history file aside instead of silently discarding it.

    load_history() returns [] on error and the next add_history() writes a fresh
    file, so without this the user loses every record with no warning at all.
    A read-only or missing directory must not stop the app from running.
    """
    with contextlib.suppress(OSError):
        os.replace(HISTORY_FILE, HISTORY_FILE.with_name(HISTORY_FILE.name + ".corrupt"))


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        raw = HISTORY_FILE.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        _quarantine()
        return []
    # json.loads accepts a bare number or string too, and callers expect a list
    # of dicts they can .append() to.
    if not isinstance(result, list):
        _quarantine()
        return []
    return [entry for entry in result if isinstance(entry, dict)]


def save_history(history: list[dict], limit: int = 50) -> None:
    # limit comes straight from config.json, which the user can hand-edit, so it
    # may arrive as a float, a string or None and break the slice below.
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    history = [] if limit <= 0 else history[-limit:]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file and rename: write_text() truncates first, so an
    # interrupted write would leave invalid JSON behind.
    tmp = HISTORY_FILE.with_name(HISTORY_FILE.name + ".tmp")
    tmp.write_text(json.dumps(history, indent=2, ensure_ascii=False), "utf-8")
    os.replace(tmp, HISTORY_FILE)


def add_history(city: str, lat: float, lon: float) -> None:
    cfg = load_config()
    history = load_history()
    entry = {
        "city": city,
        "lat": lat,
        "lon": lon,
        "when": datetime.now().astimezone().isoformat(),
    }
    history.append(entry)
    save_history(history, cfg.get("history_limit", 50))
