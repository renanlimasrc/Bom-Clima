"""API client for Open-Meteo and IP location."""

import json
from typing import Any

import requests

from .cache import cache_get_geo, cache_get_weather, cache_set_geo, cache_set_weather
from .constants import (
    BASE_URL_AIR,
    BASE_URL_GEO,
    BASE_URL_WEATHER,
    HEADERS,
    IP_API_URL,
    TIMEOUT,
)
from .i18n import t

MAX_FORECAST_DAYS = 16


def detect_location() -> dict | None:
    try:
        res = requests.get(IP_API_URL, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        data = res.json()
        if "latitude" in data and "longitude" in data:
            return {
                "lat": data["latitude"],
                "lon": data["longitude"],
                # ipapi.co sends an explicit null for VPN, proxy and carrier
                # ranges. .get(k, "") does not catch that, and the caller
                # concatenates these values into a string.
                "city": data.get("city") or "",
                "country": data.get("country_name") or data.get("country") or "",
            }
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return None


def search_city(nome: str, no_cache: bool = False) -> dict:
    from .i18n import _current_lang

    city_name = nome.strip() if nome else ""
    if not city_name:
        raise ValueError(t("empty_city"))
    lang = _current_lang()
    # The geocoding API localises place names, so the language belongs in the
    # cache key. Without it, running `bom-clima berlin` under a pt locale pins
    # "Berlim, Alemanha" for the full 7-day TTL, --lang en notwithstanding.
    cache_key = f"{lang}:{city_name.casefold()}"
    if not no_cache:
        cached = cache_get_geo(cache_key)
        if cached:
            return cached
    params: dict[str, str | int] = {"name": city_name, "count": 1, "language": lang, "format": "json"}
    try:
        res = requests.get(BASE_URL_GEO, params=params, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        data = res.json()
        result: dict = data["results"][0]
        if not no_cache:
            cache_set_geo(cache_key, result)
        return result
    except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
        # TypeError: the API answers {"results": null} rather than [] when it
        # finds nothing for some queries.
        raise ValueError(t("city_not_found").format(name=city_name)) from exc


def fetch_weather_data(
    lat: float,
    lon: float,
    unit_system: str = "metric",
    include_aqi: bool = False,
    forecast_days: int = 5,
    past_days: int = 0,
    no_cache: bool = False,
    verbose: bool = False,
) -> dict:
    # Clamp here as well as in the CLI: this is a public entry point and
    # forecast_days=0 comes back as HTTP 200 with an empty "daily" array.
    forecast_days = max(1, min(int(forecast_days), MAX_FORECAST_DAYS))
    past_days = max(0, int(past_days))
    cache_key = f"{lat:.4f}_{lon:.4f}_{unit_system}_{include_aqi}_{past_days}_{forecast_days}"
    if not no_cache:
        cached = cache_get_weather(cache_key)
        if cached:
            if verbose:
                print(f"[debug] cache hit for {cache_key}")
            return cached

    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,rain,wind_speed_10m,wind_direction_10m,"
            "wind_gusts_10m,weather_code,uv_index,"
            "pressure_msl,visibility,dew_point_2m,cloud_cover"
        ),
        "daily": (
            "temperature_2m_max,temperature_2m_min,sunrise,sunset,"
            "daylight_duration,precipitation_probability_max,"
            "precipitation_sum,precipitation_hours,weather_code,wind_speed_10m_max,"
            "wind_direction_10m_dominant,sunshine_duration,uv_index_max"
        ),
        "hourly": (
            "temperature_2m,apparent_temperature,rain,relative_humidity_2m,"
            "precipitation_probability,wind_speed_10m,cloud_cover,"
            "weather_code,uv_index,is_day,cape"
        ),
        "timezone": "auto",
        "forecast_days": forecast_days,
        "past_days": past_days,
    }
    if unit_system == "imperial":
        params["temperature_unit"] = "fahrenheit"
        params["wind_speed_unit"] = "mph"
        params["precipitation_unit"] = "inch"

    try:
        if verbose:
            print(f"[debug] fetching weather for {lat},{lon}")
        res = requests.get(BASE_URL_WEATHER, params=params, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        result: dict = res.json()
    except requests.RequestException as exc:
        raise ValueError(t("weather_error")) from exc

    # Open-Meteo answers HTTP 200 with {"error": true, "reason": ...} for bad
    # coordinates, and an intercepting proxy can do the same. Caching that would
    # keep every later run failing for the whole TTL, and display has no
    # "current" key to read. The isinstance guard matters: `"current" not in`
    # a null/list payload raises TypeError, which the callers' `except
    # ValueError` would not catch.
    if not isinstance(result, dict) or "current" not in result or "daily" not in result:
        raise ValueError(t("weather_error"))

    complete = True
    if include_aqi:
        try:
            air_params: dict[str, str | float] = {
                "latitude": lat,
                "longitude": lon,
                "current": "us_aqi,pm10,pm2_5,nitrogen_dioxide",
                "timezone": "auto",
            }
            air_res = requests.get(BASE_URL_AIR, params=air_params, headers=HEADERS, timeout=TIMEOUT)
            air_res.raise_for_status()
            result["air_quality"] = air_res.json().get("current", {})
        except requests.RequestException as exc:
            if verbose:
                print(f"[debug] AQI fetch failed: {exc}")
            result["air_quality"] = {}
            complete = False

    if not no_cache:
        # A response missing the optional air-quality block is a transient
        # outage, not a result. Storing it would make --aqi report "N/A" for
        # the next 30 minutes even once the network recovered.
        if complete:
            cache_set_weather(cache_key, result)
        elif verbose:
            print(f"[debug] not caching {cache_key}: incomplete response")
    return result
