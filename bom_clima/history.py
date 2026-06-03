"""History management for Bom Clima."""

import json
from datetime import datetime

from .config import load_config
from .constants import HISTORY_FILE


def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            result: list[dict] = json.loads(HISTORY_FILE.read_text("utf-8"))
            return result
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_history(history: list[dict], limit: int = 50) -> None:
    history = history[-limit:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), "utf-8")


def add_history(city: str, lat: float, lon: float) -> None:
    cfg = load_config()
    history = load_history()
    entry = {
        "city": city,
        "lat": lat,
        "lon": lon,
        "when": datetime.now().isoformat(),
    }
    history.append(entry)
    save_history(history, cfg.get("history_limit", 50))
