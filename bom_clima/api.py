"""API client for Open-Meteo and IP location."""

import json
from typing import Any

import requests

from .cache import cache_get_geo, cache_get_weather, cache_set_geo, cache_set_weather
from .constants import (
    BASE_URL_AIR,
    BASE_URL_ALERTS,
    BASE_URL_GEO,
    BASE_URL_WEATHER,
    HEADERS,
    IP_API_URL,
    TIMEOUT,
)
from .i18n import t


def detect_location() -> dict | None:
    try:
        res = requests.get(IP_API_URL, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        data = res.json()
        if "latitude" in data and "longitude" in data:
            return {
                "lat": data["latitude"],
                "lon": data["longitude"],
                "city": data.get("city", ""),
                "country": data.get("country_name", data.get("country", "")),
            }
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return None


def search_city(nome: str, no_cache: bool = False) -> dict:
    from .i18n import _current_lang

    city_name = nome.strip() if nome else ""
    if not city_name:
        raise ValueError(t("empty_city"))
    if not no_cache:
        cached = cache_get_geo(city_name)
        if cached:
            return cached
    params: dict[str, str | int] = {"name": city_name, "count": 1, "language": _current_lang(), "format": "json"}
    try:
        res = requests.get(BASE_URL_GEO, params=params, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        data = res.json()
        result: dict = data["results"][0]
        if not no_cache:
            cache_set_geo(city_name, result)
        return result
    except (requests.RequestException, KeyError, IndexError) as exc:
        raise ValueError(t("city_not_found").format(name=city_name)) from exc


def fetch_weather_data(
    lat: float,
    lon: float,
    unit_system: str = "metric",
    include_alerts: bool = False,
    include_aqi: bool = False,
    forecast_days: int = 5,
    past_days: int = 0,
    no_cache: bool = False,
    verbose: bool = False,
) -> dict:
    cache_key = f"{lat:.4f}_{lon:.4f}_{unit_system}_{include_aqi}_{forecast_days}"
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

    if include_alerts:
        try:
            alert_params: dict[str, str | float] = {"latitude": lat, "longitude": lon, "format": "json"}
            alert_res = requests.get(
                BASE_URL_ALERTS,
                params=alert_params,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            alert_res.raise_for_status()
            result["alerts"] = alert_res.json().get("alerts", [])
        except requests.RequestException as exc:
            if verbose:
                print(f"[debug] Alerts fetch failed: {exc}")
            result["alerts"] = []

    cache_set_weather(cache_key, result)
    return result
