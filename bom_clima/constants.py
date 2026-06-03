"""Constants for the Bom Clima application."""

import os
from pathlib import Path

BASE_URL_GEO = "https://geocoding-api.open-meteo.com/v1/search"
BASE_URL_WEATHER = "https://api.open-meteo.com/v1/forecast"
BASE_URL_AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
BASE_URL_ALERTS = "https://api.open-meteo.com/v1/warnings"
IP_API_URL = "https://ipapi.co/json/"
HEADERS = {"User-Agent": "BomClima/0.2.1"}
TIMEOUT = 10

WMO_CODES = {
    0: {"pt": ("Limpo", "☀️"), "en": ("Clear sky", "☀️"), "es": ("Despejado", "☀️")},
    1: {"pt": ("Principalmente limpo", "🌤️"), "en": ("Mainly clear", "🌤️"), "es": ("Principalmente despejado", "🌤️")},
    2: {"pt": ("Parcialmente nublado", "⛅"), "en": ("Partly cloudy", "⛅"), "es": ("Parcialmente nublado", "⛅")},
    3: {"pt": ("Nublado", "☁️"), "en": ("Overcast", "☁️"), "es": ("Nublado", "☁️")},
    45: {"pt": ("Nevoeiro", "🌫️"), "en": ("Fog", "🌫️"), "es": ("Niebla", "🌫️")},
    48: {"pt": ("Nevoeiro com geada", "🌫️"), "en": ("Rime fog", "🌫️"), "es": ("Niebla helada", "🌫️")},
    51: {"pt": ("Garoa leve", "🌦️"), "en": ("Light drizzle", "🌦️"), "es": ("Llovizna ligera", "🌦️")},
    53: {"pt": ("Garoa moderada", "🌦️"), "en": ("Moderate drizzle", "🌦️"), "es": ("Llovizna moderada", "🌦️")},
    55: {"pt": ("Garoa densa", "🌧️"), "en": ("Dense drizzle", "🌧️"), "es": ("Llovizna densa", "🌧️")},
    56: {"pt": ("Garoa congelante leve", "🌧️"), "en": ("Light freezing drizzle", "🌧️"), "es": ("Llovizna helada ligera", "🌧️")},
    57: {"pt": ("Garoa congelante densa", "🌧️"), "en": ("Dense freezing drizzle", "🌧️"), "es": ("Llovizna helada densa", "🌧️")},
    61: {"pt": ("Chuva leve", "🌧️"), "en": ("Light rain", "🌧️"), "es": ("Lluvia ligera", "🌧️")},
    63: {"pt": ("Chuva moderada", "🌧️"), "en": ("Moderate rain", "🌧️"), "es": ("Lluvia moderada", "🌧️")},
    65: {"pt": ("Chuva forte", "🌧️"), "en": ("Heavy rain", "🌧️"), "es": ("Lluvia fuerte", "🌧️")},
    66: {"pt": ("Chuva congelante leve", "🌧️"), "en": ("Light freezing rain", "🌧️"), "es": ("Lluvia helada ligera", "🌧️")},
    67: {"pt": ("Chuva congelante forte", "🌧️"), "en": ("Heavy freezing rain", "🌧️"), "es": ("Lluvia helada fuerte", "🌧️")},
    71: {"pt": ("Neve leve", "🌨️"), "en": ("Light snow", "🌨️"), "es": ("Nieve ligera", "🌨️")},
    73: {"pt": ("Neve moderada", "🌨️"), "en": ("Moderate snow", "🌨️"), "es": ("Nieve moderada", "🌨️")},
    75: {"pt": ("Neve forte", "🌨️"), "en": ("Heavy snow", "🌨️"), "es": ("Nieve fuerte", "🌨️")},
    77: {"pt": ("Grãos de neve", "🌨️"), "en": ("Snow grains", "🌨️"), "es": ("Granos de nieve", "🌨️")},
    80: {"pt": ("Pancadas leves", "🌦️"), "en": ("Light showers", "🌦️"), "es": ("Chubascos ligeros", "🌦️")},
    81: {"pt": ("Pancadas moderadas", "🌧️"), "en": ("Moderate showers", "🌧️"), "es": ("Chubascos moderados", "🌧️")},
    82: {"pt": ("Pancadas violentas", "⛈️"), "en": ("Violent showers", "⛈️"), "es": ("Chubascos violentos", "⛈️")},
    85: {"pt": ("Neve leve em pancadas", "🌨️"), "en": ("Light snow showers", "🌨️"), "es": ("Chubascos de nieve ligeros", "🌨️")},
    86: {"pt": ("Neve forte em pancadas", "🌨️"), "en": ("Heavy snow showers", "🌨️"), "es": ("Chubascos de nieve fuertes", "🌨️")},
    95: {"pt": ("Trovoada", "⛈️"), "en": ("Thunderstorm", "⛈️"), "es": ("Tormenta", "⛈️")},
    96: {"pt": ("Trovoada com granizo leve", "⛈️"), "en": ("Thunderstorm with light hail", "⛈️"), "es": ("Tormenta con granizo ligero", "⛈️")},
    99: {"pt": ("Trovoada com granizo forte", "⛈️"), "en": ("Thunderstorm with heavy hail", "⛈️"), "es": ("Tormenta con granizo fuerte", "⛈️")},
}

COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO",
]

WIND_ARROWS = {
    "N": "\u2191", "NNE": "\u2197", "NE": "\u2197", "ENE": "\u2192\u2197",
    "E": "\u2192", "ESE": "\u2198", "SE": "\u2198", "SSE": "\u2193\u2198",
    "S": "\u2193", "SSO": "\u2199", "SO": "\u2199", "OSO": "\u2190\u2199",
    "O": "\u2190", "ONO": "\u2196", "NO": "\u2196", "NNO": "\u2191\u2196",
}

AQI_LABELS = {
    "en": ["Good", "Fair", "Moderate", "Poor", "Very Poor"],
    "pt": ["Bom", "Regular", "Moderado", "Ruim", "Péssimo"],
    "es": ["Bueno", "Regular", "Moderado", "Malo", "Muy malo"],
}

WEEKDAYS = {
    "pt": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "es": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
}

VALID_CONFIG_KEYS = {
    "unit_system", "city_default", "forecast_days", "forecast_hours",
    "color", "history_limit", "lang",
}

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "bom-clima"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bom-clima"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "bom-clima"

CONFIG_FILE = CONFIG_DIR / "config.json"
LANG_FILE = CONFIG_DIR / "lang"
CACHE_FILE = CACHE_DIR / "cache.db"
HISTORY_FILE = DATA_DIR / "history.json"


def ensure_app_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


CACHE_TTL_GEO = 86400 * 7
CACHE_TTL_WEATHER = 1800

DEWPOINT_COMFORT = {
    "en": [(10, "dry", "Dry"), (16, "comfortable", "Comfortable"), (20, "muggy", "Muggy"), (999, "oppressive", "Oppressive")],
    "pt": [(10, "seco", "Seco"), (16, "confortável", "Confortável"), (20, "abafado", "Abafado"), (999, "opressivo", "Opressivo")],
    "es": [(10, "seco", "Seco"), (16, "cómodo", "Cómodo"), (20, "bochornoso", "Bochornoso"), (999, "opresivo", "Opresivo")],
}

EXTREME_RAIN_DAILY_MM = 30
EXTREME_WIND_KMH = 50
EXTREME_HEAT_C = 35
EXTREME_COLD_C = 0
EXTREME_UV = 8
EXTREME_CAPE = 1500

RAIN_WINDOW_HOURS = 24
RAIN_PROB_THRESHOLD = 30

DAY_SCORE_IDEAL_TEMP = 22
