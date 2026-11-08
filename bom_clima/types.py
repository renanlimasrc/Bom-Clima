"""TypedDicts for the Open-Meteo payload boundary.

The API can answer HTTP 200 with a body that is missing, null or shaped like
an error; these types document the good path and let mypy check the boundary.
Internal blocks (`current`/`daily`/`hourly`) stay `dict[str, Any]`: typing every
cell would be brittle against API changes, and the display layer already
degrades them gracefully.
"""

from typing import Any, TypedDict


class CityCandidate(TypedDict, total=False):
    """One geocoding-API result, as returned by search_cities()."""

    id: int
    name: str
    latitude: float
    longitude: float
    country: str
    country_code: str
    admin1: str
    admin2: str
    population: int


class DetectedLocation(TypedDict, total=False):
    """IP-geolocation result from --detect."""

    lat: float
    lon: float
    city: str
    country: str


class WeatherResponse(TypedDict, total=False):
    """Success body of the forecast API, with the optional AQI block merged in.

    Open-Meteo also answers HTTP 200 with {"error": true, "reason": ...} for
    bad coordinates; those are rejected before they reach the display layer,
    but consumers still see the keys documented here as absent rather than
    guaranteed present.
    """

    current: dict[str, Any]
    daily: dict[str, Any]
    hourly: dict[str, Any]
    air_quality: dict[str, Any]


class HistoryEntry(TypedDict, total=False):
    """One line in history.json; entries are user-editable, so all keys optional."""

    city: str
    lat: float
    lon: float
    when: str
