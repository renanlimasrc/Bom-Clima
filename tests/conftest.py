#
# conftest.py - Tests for Bom Clima
# Copyright (C) 2026  ninrod
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.


import os
from unittest.mock import patch

import pytest

from bom_clima.i18n import reset_lang_cache


@pytest.fixture(autouse=True)
def mock_lang_for_tests():
    reset_lang_cache()
    with patch("bom_clima.i18n.LANG_FILE") as mock_file:
        mock_file.exists.return_value = False
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}):
            yield
    reset_lang_cache()


@pytest.fixture(autouse=True)
def isolate_app_state(tmp_path):
    """Keep tests off the real ~/.cache and undo display globals mutated by main().

    Without this, display._COLORS_ENABLED and console.no_color leak between tests
    (main() mutates them and nothing restores them), which makes the suite
    order-dependent, and the SQLite cache writes into the user's real cache.db.
    """
    from bom_clima import display

    old_enabled = display._COLORS_ENABLED
    old_no_color = getattr(display.console, "no_color", None)
    with patch("bom_clima.cache.CACHE_FILE", tmp_path / "cache.db"):
        yield
    display._COLORS_ENABLED = old_enabled
    if display.console is not None:
        display.console.no_color = old_no_color


@pytest.fixture
def mock_geo_response():
    return {
        "results": [{
            "name": "Sao Paulo",
            "latitude": -23.55,
            "longitude": -46.63,
            "admin1": "Sao Paulo",
            "country": "Brazil",
        }]
    }


@pytest.fixture
def mock_weather_response():
    return {
        "current": {
            "time": "2026-04-29T14:00",
            "temperature_2m": 25.5,
            "apparent_temperature": 27.0,
            "relative_humidity_2m": 65,
            "wind_speed_10m": 15,
            "wind_direction_10m": 180,
            "weather_code": 1,
            "rain": 0,
            "uv_index": 5.2,
        },
        "daily": {
            "time": ["2026-04-29", "2026-04-30", "2026-05-01"],
            "temperature_2m_max": [28.0, 27.0, 26.0],
            "temperature_2m_min": [18.0, 17.0, 16.0],
            "sunrise": ["2026-04-29T06:30", "2026-04-30T06:31", "2026-05-01T06:32"],
            "sunset": ["2026-04-29T18:00", "2026-04-30T17:59", "2026-05-01T17:58"],
            "daylight_duration": [41400, 41300, 41200],
            "precipitation_probability_max": [10, 20, 30],
            "precipitation_sum": [0, 1.2, 5.0],
            "precipitation_hours": [0, 2, 4],
            "weather_code": [1, 3, 61],
            "wind_speed_10m_max": [20, 25, 30],
            "wind_direction_10m_dominant": [180, 190, 200],
        },
        "hourly": {
            "time": ["2026-04-29T15:00", "2026-04-29T16:00", "2026-04-29T17:00"],
            "temperature_2m": [26.0, 25.5, 24.0],
            "apparent_temperature": [27.5, 26.0, 25.0],
            "rain": [0, 0, 0.5],
            "precipitation_probability": [5, 10, 40],
            "wind_speed_10m": [14, 13, 12],
            "weather_code": [1, 2, 61],
        },
    }


@pytest.fixture
def mock_weather_with_aqi():
    return {
        "current": {
            "time": "2026-04-29T14:00",
            "temperature_2m": 25.5,
            "apparent_temperature": 27.0,
            "relative_humidity_2m": 65,
            "wind_speed_10m": 15,
            "wind_direction_10m": 180,
            "weather_code": 1,
            "rain": 0,
            "uv_index": 5.2,
        },
        "daily": {
            "time": ["2026-04-29", "2026-04-30", "2026-05-01"],
            "temperature_2m_max": [28.0, 27.0, 26.0],
            "temperature_2m_min": [18.0, 17.0, 16.0],
            "sunrise": ["2026-04-29T06:30", "2026-04-30T06:31", "2026-05-01T06:32"],
            "sunset": ["2026-04-29T18:00", "2026-04-30T17:59", "2026-05-01T17:58"],
            "daylight_duration": [41400, 41300, 41200],
            "precipitation_probability_max": [10, 20, 30],
            "precipitation_sum": [0, 1.2, 5.0],
            "precipitation_hours": [0, 2, 4],
            "weather_code": [1, 3, 61],
            "wind_speed_10m_max": [20, 25, 30],
            "wind_direction_10m_dominant": [180, 190, 200],
        },
        "hourly": {
            "time": ["2026-04-29T15:00", "2026-04-29T16:00"],
            "temperature_2m": [26.0, 25.5],
            "apparent_temperature": [27.5, 26.0],
            "precipitation_probability": [5, 10],
            "wind_speed_10m": [14, 13],
            "weather_code": [1, 2],
        },
        "air_quality": {
            "us_aqi": 45,
            "pm2_5": 10.2,
            "time": "2026-04-29T14:00",
        },
    }
