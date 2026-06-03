"""Configuration management for Bom Clima."""

import json
from typing import Any

from .constants import CONFIG_FILE

DEFAULT_CONFIG: dict[str, Any] = {
    "unit_system": "metric",
    "city_default": None,
    "forecast_days": 5,
    "forecast_hours": 6,
    "color": True,
    "history_limit": 50,
    "lang": None,
}


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
            cfg.update(data)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
