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

_INT_KEYS = ("forecast_days", "forecast_hours", "history_limit")


def _sanitize(cfg: dict[str, Any]) -> dict[str, Any]:
    """Replace values of the wrong type or out of range with the default.

    config.json is a plain text file the user can hand-edit, and every key is
    consumed later as a number. A string where an int is expected would
    otherwise surface as a TypeError deep inside display, with a traceback that
    points nowhere near the real cause, so validation happens here at the
    boundary.
    """
    for key in _INT_KEYS:
        if key not in cfg:
            cfg[key] = DEFAULT_CONFIG[key]
            continue
        value = cfg[key]
        if isinstance(value, bool) or not isinstance(value, int):
            cfg[key] = DEFAULT_CONFIG[key]
    if not 1 <= cfg["forecast_days"] <= 15:
        cfg["forecast_days"] = DEFAULT_CONFIG["forecast_days"]
    if cfg["forecast_hours"] < 1:
        cfg["forecast_hours"] = DEFAULT_CONFIG["forecast_hours"]
    if cfg["history_limit"] < 0:
        cfg["history_limit"] = DEFAULT_CONFIG["history_limit"]
    if "color" not in cfg or (cfg["color"] is not True and cfg["color"] is not False):
        cfg["color"] = DEFAULT_CONFIG["color"]
    if cfg.get("unit_system") not in ("metric", "imperial"):
        cfg["unit_system"] = DEFAULT_CONFIG["unit_system"]
    return cfg


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            data = None
        # cfg.update() with a non-dict payload raises TypeError, which the
        # JSON/OSError handler above does not catch.
        if isinstance(data, dict):
            cfg.update(data)
    return _sanitize(cfg)


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
