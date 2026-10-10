#
# test_bom_clima.py - Tests for Bom Clima
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

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bom_clima.api import detect_location, search_city
from bom_clima.cache import (
    cache_cleanup,
    cache_get_geo,
    cache_get_weather,
    cache_set_geo,
    cache_set_weather,
)
from bom_clima.cli import _validate_positive, apply_config_overrides, build_parser
from bom_clima.config import DEFAULT_CONFIG, load_config, save_config
from bom_clima.constants import VALID_CONFIG_KEYS, WMO_CODES
from bom_clima.display import format_weather_block
from bom_clima.formatters import (
    _get_documents_dir,
    _to_xml,
    display_width,
    export_data,
    format_duration,
    format_timestamp,
    get_moon_phase,
    get_wmo,
    is_day_icon,
    moon_phase_name,
    wind_direction,
)
from bom_clima.i18n import _current_lang, reset_lang_cache, set_lang, t


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


class TestWindDirection:
    @pytest.mark.parametrize("deg,expected", [
        (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
        (180, "S"), (225, "SO"), (270, "O"), (315, "NO"),
        (360, "N"), (11.25, "NNE"),
    ])
    def test_wind_direction(self, deg, expected):
        assert wind_direction(deg) == expected


class TestWmoCodes:
    def test_clear_sky(self):
        assert get_wmo(0, "pt") == ("Limpo", "\u2600\ufe0f")

    def test_rain(self):
        assert get_wmo(61, "pt") == ("Chuva leve", "\U0001f327\ufe0f")

    def test_unknown(self):
        assert get_wmo(999, "pt") == ("Desconhecido", "\u2753")

    def test_wmo_english(self):
        desc, _icon = get_wmo(0, "en")
        assert desc == "Clear sky"

    def test_wmo_spanish(self):
        desc, _icon = get_wmo(3, "es")
        assert desc == "Nublado"

    def test_snow_codes_present(self):
        assert 71 in WMO_CODES
        assert 73 in WMO_CODES
        assert 75 in WMO_CODES
        assert 77 in WMO_CODES

    def test_freezing_rain_codes(self):
        assert 56 in WMO_CODES
        assert 57 in WMO_CODES
        assert 66 in WMO_CODES
        assert 67 in WMO_CODES

    def test_snow_shower_codes(self):
        assert 85 in WMO_CODES
        assert 86 in WMO_CODES

    def test_heavy_hail_thunderstorm(self):
        assert 99 in WMO_CODES


class TestFormatting:
    def test_duracao(self):
        assert format_duration(3661) == "1h 01min"

    def test_duracao_zero(self):
        assert format_duration(0) == "0h 00min"

    def test_horario_no_seconds(self):
        assert format_timestamp("2026-04-29T14:30") == "14:30"

    def test_horario_with_seconds(self):
        assert format_timestamp("2026-04-29T14:30:00") == "14:30"

    def test_horario_fallback(self):
        assert format_timestamp("14:30") == "14:30"

    def test_is_day_icon(self):
        assert is_day_icon("2026-04-29T14:00:00") == "\u2600\ufe0f"
        assert is_day_icon("2026-04-29T22:00:00") == "\U0001f319"


class TestApiCalls:
    @patch("bom_clima.api.requests.get")
    def test_search_city_success(self, mock_get, mock_geo_response):
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_geo_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = search_city("Sao Paulo")
        assert result["name"] == "Sao Paulo"
        assert result["latitude"] == -23.55

    @patch("bom_clima.api.requests.get")
    def test_search_city_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="not found"):
            search_city("XyzNonexistent")

    @patch("bom_clima.api.requests.get")
    def test_detect_location_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"latitude": -23.55, "longitude": -46.63, "city": "Sao Paulo", "country_name": "Brazil"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = detect_location()
        assert result["city"] == "Sao Paulo"
        assert result["lat"] == -23.55

    @patch("bom_clima.api.requests.get")
    def test_detect_location_failure(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        result = detect_location()
        assert result is None


class TestExport:
    def test_export_json(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "json")
        data = json.loads(content)
        assert data["city"] == "Sao Paulo"
        assert "data" in data

    def test_export_csv(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "csv")
        assert "city" in content
        assert "temp_current" in content
        assert "Sao Paulo" in content

    def test_export_invalid_format(self, mock_weather_response):
        with pytest.raises(ValueError, match="Invalid format"):
            export_data(mock_weather_response, "Sao Paulo", "pdf")

    def test_export_to_file(self, mock_weather_response):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_data(mock_weather_response, "Sao Paulo", "json", f.name)
            assert os.path.exists(f.name)
            with open(f.name) as fh:
                file_content = json.loads(fh.read())
            assert file_content["city"] == "Sao Paulo"
            os.unlink(f.name)

    def test_export_yaml(self, mock_weather_response):
        yaml = pytest.importorskip("yaml")
        content = export_data(mock_weather_response, "Sao Paulo", "yaml")
        parsed = yaml.safe_load(content)
        assert parsed["city"] == "Sao Paulo"
        assert parsed["data"]["current"]

    def test_export_yaml_quotes_values_that_yaml_would_retype(self):
        """Unquoted scalars are re-read as bool/int/None, corrupting the data."""
        yaml = pytest.importorskip("yaml")
        dados = {
            "current": {"temperature_2m": 20.0, "rain": None, "note": "yes", "mode": "0755"},
            "daily": {},
        }
        parsed = yaml.safe_load(export_data(dados, "X", "yaml"))["data"]["current"]
        assert parsed["temperature_2m"] == 20.0 and isinstance(parsed["temperature_2m"], float)
        assert parsed["rain"] is None
        assert parsed["note"] == "yes"
        assert parsed["mode"] == "0755"

    def test_export_yaml_survives_apostrophes_in_city(self):
        yaml = pytest.importorskip("yaml")
        for city in ("O'Fallon", "Coeur d'Alene", "L'Haÿ-les-Roses"):
            out = export_data({"current": {}, "daily": {}}, city, "yaml")
            assert yaml.safe_load(out)["city"] == city

    def test_export_csv_uses_today_index(self):
        dados = {
            "current": {"time": "2026-08-12T16:00", "temperature_2m": 25,
                        "apparent_temperature": 27, "relative_humidity_2m": 65,
                        "wind_speed_10m": 15, "weather_code": 1, "rain": 0, "uv_index": 5},
            "daily": {"time": ["2026-08-11", "2026-08-12"],
                      "temperature_2m_max": [30, 28], "temperature_2m_min": [19, 18],
                      "precipitation_probability_max": [5, 10], "precipitation_sum": [0, 1],
                      "sunrise": ["2026-08-11T06:29", "2026-08-12T06:30"],
                      "sunset": ["2026-08-11T18:01", "2026-08-12T18:00"]},
        }
        content = export_data(dados, "X", "csv")
        assert "28" in content
        assert "06:30" in content
        assert "06:29" not in content

    def test_export_yaml_serializes_lists(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "yaml")
        assert "'['" not in content

    def test_export_xml(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "xml")
        assert '<?xml version="1.0"' in content
        assert 'city="Sao Paulo"' in content
        assert "<current>" in content

    def test_xml_escapes_special_chars(self):
        data = {"current": {"city": "Sao<Paulo&Co"}, "daily": {}}
        content = _to_xml("Sao<Paulo&Co", data)
        assert "Sao&lt;Paulo&amp;Co" in content


class TestConfig:
    def test_load_default_config(self):
        with patch("bom_clima.config.CONFIG_FILE") as mock_file:
            mock_file.exists.return_value = False
            cfg = load_config()
            assert cfg["unit_system"] == "metric"
            assert cfg["forecast_days"] == 5

    def test_apply_config_overrides_imperial(self):
        cfg = {"unit_system": "metric"}
        args = type("Args", (), {
            "imperial": True, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["unit_system"] == "imperial"

    def test_config_set_inf_does_not_crash(self):
        cfg = {"forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": ["forecast_days=inf"], "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch("bom_clima.cli.save_config"):
            result = apply_config_overrides(cfg, args)
        assert result["forecast_days"] == 5

    def test_apply_config_overrides_hours_days(self):
        cfg = {"forecast_hours": 12, "forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": 24, "days": 7,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["forecast_hours"] == 24
        assert result["forecast_days"] == 7

    def test_apply_config_overrides_days_capped_at_15(self):
        cfg = {"forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": 20,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["forecast_days"] == 15

    def test_apply_config_set_validates_keys(self):
        cfg = {"unit_system": "metric"}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": ["invalid_key=test"],
            "config_show": False, "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch("bom_clima.cli.save_config"):
            result = apply_config_overrides(cfg, args)
        assert "invalid_key" not in result

    def test_valid_config_keys(self):
        assert "unit_system" in VALID_CONFIG_KEYS
        assert "city_default" in VALID_CONFIG_KEYS
        assert "forecast_days" in VALID_CONFIG_KEYS

    def test_config_show_renders_panel(self):
        from bom_clima import cli as cli_mod
        cfg = {"unit_system": "metric", "color": True}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": True,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch.object(cli_mod, "r_panel") as mock_panel, \
             pytest.raises(SystemExit):
            cli_mod.apply_config_overrides(cfg, args)
        mock_panel.assert_called_once()
        content, kwargs = mock_panel.call_args.args[0], mock_panel.call_args.kwargs
        assert "unit_system:" in content
        assert "metric" in content
        assert "color:" in content
        assert "True" in content
        assert kwargs["title"] == "Configuration"

    def test_config_show_syncs_colors(self):
        from bom_clima import cli as cli_mod
        cfg = {"unit_system": "metric", "color": True}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": True,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch.object(cli_mod, "_set_colors_enabled") as mock_set, \
             patch.object(cli_mod, "r_panel"), \
             pytest.raises(SystemExit):
            cli_mod.apply_config_overrides(cfg, args)
        mock_set.assert_called_once_with(True)


class TestMoonPhase:
    def test_moon_phase_returns_valid_index(self):
        phase = get_moon_phase()
        assert phase in (0, 1, 2, 3)

    def test_moon_phase_name_pt(self):
        assert moon_phase_name(0, "pt") == "\U0001f311 Nova"

    def test_moon_phase_name_en(self):
        assert moon_phase_name(2, "en") == "\U0001f315 Full Moon"

    def test_moon_phase_name_es(self):
        assert moon_phase_name(3, "es") == "\U0001f318 Menguante"

    def test_moon_phase_name_default(self):
        assert moon_phase_name(1, "fr") == "\U0001f312 Waxing"


class TestCache:
    def test_cache_roundtrip_geo(self, tmp_path):
        with patch("bom_clima.cache.CACHE_FILE", tmp_path / "test_cache.db"):
            cache_set_geo("test_city", {"name": "TestCity", "lat": 1.0})
            result = cache_get_geo("test_city")
            assert result is not None
            assert result["name"] == "TestCity"

    def test_cache_miss_geo(self, tmp_path):
        with patch("bom_clima.cache.CACHE_FILE", tmp_path / "test_cache.db"):
            result = cache_get_geo("nonexistent")
            assert result is None

    def test_cache_roundtrip_weather(self, tmp_path):
        with patch("bom_clima.cache.CACHE_FILE", tmp_path / "test_cache.db"):
            cache_set_weather("key1", {"temp": 25})
            result = cache_get_weather("key1")
            assert result is not None
            assert result["temp"] == 25

    def test_cache_cleanup(self, tmp_path):
        with patch("bom_clima.cache.CACHE_FILE", tmp_path / "test_cache.db"):
            cache_set_geo("old", {"name": "Old"})
            removed = cache_cleanup()
            assert removed >= 0


class TestFormatWeatherBlock:
    def test_basic_block(self, mock_weather_response):
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", mock_weather_response, cfg)
        assert "Sao Paulo" in block
        assert "Temperature" in block
        assert "25.5" in block

    def test_block_with_aqi(self, mock_weather_with_aqi):
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", mock_weather_with_aqi, cfg)
        assert "Air Quality Index" in block
        assert "45" in block

    def test_uses_today_index_with_past_days(self):
        dados = {
            "current": {
                "time": "2026-04-29T14:00", "temperature_2m": 25.5,
                "apparent_temperature": 27.0, "relative_humidity_2m": 65,
                "wind_speed_10m": 15, "wind_direction_10m": 180,
                "weather_code": 1, "rain": 0, "uv_index": 5.2,
            },
            "daily": {
                "time": ["2026-04-28", "2026-04-29", "2026-04-30"],
                "temperature_2m_max": [30.0, 28.0, 27.0],
                "temperature_2m_min": [19.0, 18.0, 17.0],
                "sunrise": ["2026-04-28T06:29", "2026-04-29T06:30", "2026-04-30T06:31"],
                "sunset": ["2026-04-28T18:01", "2026-04-29T18:00", "2026-04-30T17:59"],
                "daylight_duration": [41500, 41400, 41300],
                "precipitation_probability_max": [5, 10, 20],
                "precipitation_sum": [0, 0, 1.2],
                "precipitation_hours": [0, 0, 2],
            },
        }
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", dados, cfg)
        assert "28.0°C" in block
        assert "30.0°C" not in block


class TestTempColor:
    @staticmethod
    def _temp_color(val, unit_sym):
        from bom_clima.display import HAS_RICH, _temp_color
        if not HAS_RICH:
            pytest.skip("rich not installed")
        return _temp_color(val, unit_sym)

    def test_metric_red_at_36(self):
        assert "[red]" in self._temp_color(36, "°C")

    def test_metric_green_mid(self):
        assert "[green]" in self._temp_color(25.5, "°C")

    def test_imperial_red_only_at_95(self):
        assert "[red]" in self._temp_color(95.0, "°F")

    def test_imperial_not_red_below_95(self):
        out = self._temp_color(94.9, "°F")
        assert "[red]" not in out
        assert "[yellow]" in out

    def test_imperial_low_temp_not_red(self):
        out = self._temp_color(56.9, "°F")
        assert "[red]" not in out
        assert "[cyan]" in out

    def test_imperial_yellow_range(self):
        assert "[yellow]" in self._temp_color(90.0, "°F")

    def test_imperial_green_range(self):
        assert "[green]" in self._temp_color(68.0, "°F")

    def test_imperial_cyan_range(self):
        assert "[cyan]" in self._temp_color(54.0, "°F")

    def test_imperial_blue_range(self):
        assert "[blue]" in self._temp_color(45.0, "°F")


class TestNoColorMarkup:
    @staticmethod
    def _set_colors(enabled):
        import bom_clima.display as d
        if not d.HAS_RICH:
            pytest.skip("rich not installed")
        old = d._COLORS_ENABLED
        d._COLORS_ENABLED = enabled
        return d, old

    def test_no_markup_when_colors_disabled(self):
        d, old = self._set_colors(False)
        try:
            assert d._temp_color(36, "°C") == "36°C"
            assert d._rain_color(70) == "70%"
        finally:
            d._COLORS_ENABLED = old

    def test_markup_when_colors_enabled(self):
        d, old = self._set_colors(True)
        try:
            assert d._temp_color(36, "°C") == "[red]36°C[/red]"
            assert d._rain_color(70) == "[red]70%[/red]"
        finally:
            d._COLORS_ENABLED = old

    def test_use_rich_kept_when_colors_disabled(self):
        d, old = self._set_colors(False)
        try:
            assert d._use_rich() is True
        finally:
            d._COLORS_ENABLED = old

    def test_set_colors_toggles_no_color(self):
        d, old = self._set_colors(True)
        try:
            d._set_colors_enabled(False)
            assert d.console is not None
            assert d.console.no_color is True
            d._set_colors_enabled(True)
            assert d.console.no_color is None
        finally:
            d._COLORS_ENABLED = old
            if d.console is not None:
                d.console.no_color = None


class TestI18n:
    def test_set_lang(self):
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("en")
            # The encoding is explicit: without it the file is written in the
            # process's preferred encoding, which is not utf-8 on Windows.
            mock_file.write_text.assert_called_once_with("en", "utf-8")

    def test_set_lang_invalid(self):
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("fr")
            mock_file.write_text.assert_not_called()

    def test_current_lang_from_env(self):
        reset_lang_cache()
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=False), \
             patch("bom_clima.i18n.LANG_FILE") as mock_file:
            mock_file.exists.return_value = False
            assert _current_lang() == "en"
        reset_lang_cache()

    def test_t_returns_translated_key(self):
        reset_lang_cache()
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}), \
             patch("bom_clima.i18n.LANG_FILE") as mock_file:
            mock_file.exists.return_value = False
            result = t("temperature")
            assert result == "Temperature"


class TestCityParsing:
    def test_comma_separated_cities(self):
        raw = "s\u00e3o paulo, guarulhos, campinas"
        cities = [c.strip() for c in raw.split(",") if c.strip()]
        assert cities == ["s\u00e3o paulo", "guarulhos", "campinas"]

    def test_comma_with_spaces(self):
        raw = "tokyo,london , paris"
        cities = [c.strip() for c in raw.split(",") if c.strip()]
        assert cities == ["tokyo", "london", "paris"]

    def test_single_city(self):
        raw = "new york"
        cities = [c.strip() for c in raw.split(",") if c.strip()]
        assert cities == ["new york"]


class TestCLIArguments:
    @patch("bom_clima.i18n.LANG_FILE")
    @patch("bom_clima.cli.save_config")
    def test_version(self, mock_save, mock_lang):
        mock_lang.exists.return_value = False
        parser = build_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True

    @patch("bom_clima.i18n.LANG_FILE")
    @patch("bom_clima.cli.save_config")
    def test_no_cache_flag(self, mock_save, mock_lang):
        mock_lang.exists.return_value = False
        parser = build_parser()
        args = parser.parse_args(["--no-cache", "London"])
        assert args.no_cache is True

    @patch("bom_clima.i18n.LANG_FILE")
    @patch("bom_clima.cli.save_config")
    def test_verbose_flag(self, mock_save, mock_lang):
        mock_lang.exists.return_value = False
        parser = build_parser()
        args = parser.parse_args(["--verbose", "London"])
        assert args.verbose is True

    @patch("bom_clima.i18n.LANG_FILE")
    @patch("bom_clima.cli.save_config")
    def test_lang_flag(self, mock_save, mock_lang):
        mock_lang.exists.return_value = False
        parser = build_parser()
        args = parser.parse_args(["--lang", "es"])
        assert args.lang == "es"


class TestDisplayWidth:
    def test_ascii(self):
        assert display_width("hello") == 5

    def test_empty(self):
        assert display_width("") == 0


class TestDocumentsDir:
    def test_fallback_documents_dir(self):
        result = _get_documents_dir()
        assert isinstance(result, Path)


class TestValidatePositive:
    def test_valid_value(self):
        _validate_positive(5, "--days")

    def test_zero_value(self):
        with pytest.raises(SystemExit):
            _validate_positive(0, "--days")

    def test_negative_value(self):
        with pytest.raises(SystemExit):
            _validate_positive(-1, "--days")

    def test_none_value(self):
        _validate_positive(None, "--days")


class TestGetAqiLabel:
    def test_good(self):
        from bom_clima.formatters import get_aqi_label
        assert get_aqi_label(25, "en") == "Good"

    def test_fair(self):
        from bom_clima.formatters import get_aqi_label
        assert get_aqi_label(75, "en") == "Fair"

    def test_moderate(self):
        from bom_clima.formatters import get_aqi_label
        assert get_aqi_label(125, "en") == "Moderate"

    def test_poor(self):
        from bom_clima.formatters import get_aqi_label
        assert get_aqi_label(175, "en") == "Poor"

    def test_very_poor(self):
        from bom_clima.formatters import get_aqi_label
        assert get_aqi_label(250, "en") == "Very Poor"


class TestGetWeekdayName:
    def test_weekday_en(self):
        from datetime import datetime

        from bom_clima.formatters import get_weekday_name
        dt = datetime(2026, 4, 29)
        assert get_weekday_name(dt, "en") == "Wed"

    def test_weekday_pt(self):
        from datetime import datetime

        from bom_clima.formatters import get_weekday_name
        dt = datetime(2026, 4, 29)
        assert get_weekday_name(dt, "pt") == "Qua"


class TestFormatTimeRemaining:
    def test_future_time(self):
        from datetime import datetime, timedelta

        from bom_clima.formatters import format_time_remaining
        future = (datetime.now() + timedelta(hours=2)).isoformat()
        result = format_time_remaining(future)
        assert "+1h" in result or "+2h" in result

    def test_past_time(self):
        from datetime import datetime, timedelta

        from bom_clima.formatters import format_time_remaining
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        result = format_time_remaining(past)
        assert "-1h" in result

    def test_uses_provided_now(self):
        from datetime import datetime

        from bom_clima.formatters import format_time_remaining
        now = datetime(2026, 4, 29, 6, 0)
        result = format_time_remaining("2026-04-29T08:30", now=now)
        assert "+2h" in result


class TestAddHistory:
    def test_add_history(self, tmp_path):
        with (
            patch("bom_clima.history.HISTORY_FILE", tmp_path / "history.json"),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "config.json"),
        ):
            from bom_clima.history import add_history, load_history
            add_history("TestCity", 1.0, 2.0)
            history = load_history()
            assert len(history) == 1
            assert history[0]["city"] == "TestCity"

    def test_history_limit_zero_empties(self, tmp_path):
        from bom_clima.history import load_history, save_history
        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "history.json"):
            save_history([{"city": "a"}, {"city": "b"}], 0)
            assert load_history() == []


class TestExportAllFormats:
    def test_export_json(self, mock_weather_response, tmp_path):
        from bom_clima.formatters import export_all_formats
        with patch("bom_clima.formatters._get_documents_dir", return_value=tmp_path):
            export_all_formats(mock_weather_response, "Sao Paulo", "json", None)
            assert (tmp_path / "Sao_Paulo.json").exists()

    def test_export_multiple_formats(self, mock_weather_response, tmp_path):
        from bom_clima.formatters import export_all_formats
        with patch("bom_clima.formatters._get_documents_dir", return_value=tmp_path):
            export_all_formats(mock_weather_response, "Sao Paulo", "json,csv", None)
            assert (tmp_path / "Sao_Paulo.json").exists()
            assert (tmp_path / "Sao_Paulo.csv").exists()


class TestDisplayWeather:
    def test_display_weather(self, mock_weather_response, capsys):
        from bom_clima.display import display_weather
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        display_weather("Sao Paulo", mock_weather_response, cfg, show_forecast=False, show_hourly=False)
        captured = capsys.readouterr()
        assert "Sao Paulo" in captured.out


class TestDisplayComparison:
    def test_display_comparison(self, mock_weather_response, capsys):
        from bom_clima.display import display_comparison
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        resultados = [("Sao Paulo", mock_weather_response, cfg, None)]
        display_comparison(resultados)
        captured = capsys.readouterr()
        assert "Sao Paulo" in captured.out


class TestDewpointComfort:
    def test_dry(self):
        from bom_clima.formatters import dewpoint_comfort
        assert dewpoint_comfort(5, "en") == "Dry"

    def test_comfortable(self):
        from bom_clima.formatters import dewpoint_comfort
        assert dewpoint_comfort(12, "en") == "Comfortable"

    def test_muggy(self):
        from bom_clima.formatters import dewpoint_comfort
        assert dewpoint_comfort(18, "en") == "Muggy"

    def test_oppressive(self):
        from bom_clima.formatters import dewpoint_comfort
        assert dewpoint_comfort(22, "en") == "Oppressive"

    def test_imperial_uses_celsius_thresholds(self):
        from bom_clima.formatters import dewpoint_comfort
        assert dewpoint_comfort(60, "en", unit_system="imperial") == "Comfortable"
        assert dewpoint_comfort(41, "en", unit_system="imperial") == "Dry"


class TestGenerateRecommendations:
    def test_umbrella(self):
        from bom_clima.formatters import generate_recommendations
        dados = {
            "current": {"temperature_2m": 20, "uv_index": 3},
            "daily": {"precipitation_probability_max": [70]}
        }
        recs = generate_recommendations(dados, {})
        assert any("umbrella" in r.lower() for r in recs)

    def test_sunscreen(self):
        from bom_clima.formatters import generate_recommendations
        dados = {
            "current": {"temperature_2m": 25, "uv_index": 8},
            "daily": {"precipitation_probability_max": [10]}
        }
        recs = generate_recommendations(dados, {})
        assert any("sunscreen" in r.lower() for r in recs)

    def test_good_run(self):
        from bom_clima.formatters import generate_recommendations
        dados = {
            "current": {"temperature_2m": 22, "uv_index": 4, "wind_speed_10m": 10, "visibility": 10000},
            "daily": {"precipitation_probability_max": [10]}
        }
        recs = generate_recommendations(dados, {})
        assert any("run" in r.lower() or "exercise" in r.lower() for r in recs)

    def test_imperial_jacket_threshold(self):
        from bom_clima.formatters import generate_recommendations
        dados = {
            "current": {"temperature_2m": 50, "uv_index": 2, "wind_speed_10m": 5, "visibility": 10000},
            "daily": {"precipitation_probability_max": [10]},
        }
        recs = generate_recommendations(dados, {"unit_system": "imperial"})
        assert any("jacket" in r.lower() or "casaco" in r.lower() for r in recs)


class TestDetectExtremes:
    def test_heat_wave(self):
        from bom_clima.formatters import detect_extremes
        dados = {
            "current": {"temperature_2m": 36, "uv_index": 5},
            "daily": {
                "temperature_2m_max": [38],
                "temperature_2m_min": [22],
                "precipitation_sum": [0],
            },
            "hourly": {"cape": [0]}
        }
        extremes = detect_extremes(dados)
        assert any("heat" in e.lower() or "calor" in e.lower() for e in extremes)

    def test_no_extremes(self):
        from bom_clima.formatters import detect_extremes
        dados = {
            "current": {"temperature_2m": 22, "uv_index": 3},
            "daily": {
                "temperature_2m_max": [25],
                "temperature_2m_min": [15],
                "precipitation_sum": [0],
            },
            "hourly": {"cape": [0]}
        }
        extremes = detect_extremes(dados)
        assert len(extremes) == 0

    def test_ignores_past_cape(self):
        from bom_clima.formatters import detect_extremes
        dados = {
            "current": {"time": "2026-08-12T16:00", "temperature_2m": 22, "uv_index": 3},
            "daily": {
                "temperature_2m_max": [25],
                "temperature_2m_min": [15],
                "precipitation_sum": [0],
            },
            "hourly": {
                "time": ["2026-08-12T10:00", "2026-08-12T18:00"],
                "cape": [2000, 100],
            },
        }
        extremes = detect_extremes(dados)
        assert len(extremes) == 0

    def test_imperial_no_false_heat(self):
        from bom_clima.formatters import detect_extremes
        dados = {
            "current": {"temperature_2m": 80, "uv_index": 3, "wind_speed_10m": 10},
            "daily": {
                "temperature_2m_max": [85],
                "temperature_2m_min": [60],
                "precipitation_sum": [0],
            },
            "hourly": {"cape": [0]},
        }
        extremes = detect_extremes(dados, unit_system="imperial")
        assert len(extremes) == 0

    def test_imperial_heat_at_100f(self):
        from bom_clima.formatters import detect_extremes
        dados = {
            "current": {"temperature_2m": 90, "uv_index": 3, "wind_speed_10m": 10},
            "daily": {
                "temperature_2m_max": [100],
                "temperature_2m_min": [70],
                "precipitation_sum": [0],
            },
            "hourly": {"cape": [0]},
        }
        extremes = detect_extremes(dados, unit_system="imperial")
        assert any("heat" in e.lower() or "calor" in e.lower() for e in extremes)


class TestRainWindowSummary:
    def test_detects_rain_window(self, mock_weather_response):
        from bom_clima.formatters import rain_window_summary
        result = rain_window_summary(mock_weather_response)
        assert len(result) == 1
        assert "17:00" in result[0]

    def test_no_rain_windows(self):
        from bom_clima.formatters import rain_window_summary
        dados = {
            "current": {"time": "2026-04-29T14:00"},
            "hourly": {
                "time": ["2026-04-29T15:00", "2026-04-29T16:00"],
                "precipitation_probability": [5, 10],
            },
        }
        assert rain_window_summary(dados) == []


class TestScoreDays:
    def test_score_returns_list(self, mock_weather_response):
        from bom_clima.formatters import score_days
        scores = score_days(mock_weather_response)
        assert isinstance(scores, list)
        assert len(scores) > 0
        assert len(scores[0]) == 2

    def test_score_higher_for_ideal_day(self):
        from bom_clima.formatters import score_days
        good = {
            "daily": {
                "time": ["2026-04-29"],
                "temperature_2m_max": [22],
                "temperature_2m_min": [18],
                "precipitation_probability_max": [5],
                "wind_speed_10m_max": [10],
                "sunshine_duration": [43200],
            }
        }
        bad = {
            "daily": {
                "time": ["2026-04-29"],
                "temperature_2m_max": [35],
                "temperature_2m_min": [30],
                "precipitation_probability_max": [80],
                "wind_speed_10m_max": [40],
                "sunshine_duration": [0],
            }
        }
        good_score = score_days(good)[0][1]
        bad_score = score_days(bad)[0][1]
        assert good_score > bad_score


# ---------------------------------------------------------------------------
# Argument Combination Tests
# ---------------------------------------------------------------------------

import argparse
import itertools

ALL_BOOLEAN_FLAGS = [
    "--detect", "--compare", "--aqi", "--imperial",
    "--no-color", "--history", "--no-cache", "--verbose",
    "--best-day", "--vs-yesterday", "--config-show", "--help", "--version",
]

ALL_VALUE_ARGS = [
    ("--days", "5"),
    ("--hours", "12"),
    ("--export", "json"),
    ("--output", "/tmp/test_output.json"),
    ("--lang", "en"),
    ("--config-set", "color=false"),
]


def _build_all_pairs():
    all_args = []
    for flag in ALL_BOOLEAN_FLAGS:
        all_args.append((flag,))
    for flag, val in ALL_VALUE_ARGS:
        all_args.append((flag, val))
    pairs = []
    for i in range(len(all_args)):
        for j in range(i + 1, len(all_args)):
            combo = list(all_args[i]) + list(all_args[j])
            pairs.append(combo)
    return pairs




def _build_n_way_combos(n):
    all_args = [(flag,) for flag in ALL_BOOLEAN_FLAGS]
    all_args += [(flag, val) for flag, val in ALL_VALUE_ARGS]
    combos = []
    for combo in itertools.combinations(all_args, n):
        flat = []
        for item in combo:
            flat.extend(item)
        combos.append(flat)
    return combos


TRIPLE_COMBOS = _build_n_way_combos(3)

EDGE_VALUE_COMBOS = [
    ["--days", "0"],
    ["--days", "-1"],
    ["--days", "15"],
    ["--days", "16"],
    ["--hours", "0"],
    ["--hours", "24"],
    ["--export", "json,csv,yaml,xml"],
    ["--export", "bogus"],
    ["--config-set", "forecast_days=7"],
    ["--config-set", "forecast_days=100"],
    ["--config-set", "lang=pt"],
    ["--lang", "es"],
    ["--lang", "pt"],
]


_FAKE_WEATHER = {
    "current": {
        "time": "2026-04-29T14:00", "temperature_2m": 25.5,
        "apparent_temperature": 27.0, "relative_humidity_2m": 65,
        "wind_speed_10m": 15, "wind_direction_10m": 180,
        "wind_gusts_10m": 25, "weather_code": 1, "rain": 0,
        "uv_index": 5.2, "pressure_msl": 1013, "visibility": 10000,
        "dew_point_2m": 18, "cloud_cover": 40,
    },
    "daily": {
        "time": ["2026-04-28", "2026-04-29", "2026-04-30", "2026-05-01"],
        "temperature_2m_max": [24.0, 28.0, 27.0, 26.0],
        "temperature_2m_min": [14.0, 18.0, 17.0, 16.0],
        "sunrise": ["2026-04-28T06:29", "2026-04-29T06:30", "2026-04-30T06:31", "2026-05-01T06:32"],
        "sunset": ["2026-04-28T18:01", "2026-04-29T18:00", "2026-04-30T17:59", "2026-05-01T17:58"],
        "daylight_duration": [41500, 41400, 41300, 41200],
        "precipitation_probability_max": [5, 10, 20, 30],
        "precipitation_sum": [0, 0, 1.2, 5.0],
        "precipitation_hours": [0, 0, 2, 4],
        "weather_code": [0, 1, 3, 61],
        "wind_speed_10m_max": [15, 20, 25, 30],
        "wind_direction_10m_dominant": [170, 180, 190, 200],
        "sunshine_duration": [32000, 30000, 28000, 25000],
        "uv_index_max": [6, 7, 6, 5],
    },
    "hourly": {
        "time": ["2026-04-29T15:00", "2026-04-29T16:00", "2026-04-29T17:00"],
        "temperature_2m": [26.0, 25.5, 24.0],
        "apparent_temperature": [27.5, 26.0, 25.0],
        "rain": [0, 0, 0.5],
        "relative_humidity_2m": [60, 62, 65],
        "precipitation_probability": [5, 10, 40],
        "wind_speed_10m": [14, 13, 12],
        "cloud_cover": [30, 40, 50],
        "weather_code": [1, 2, 61],
        "uv_index": [5, 4, 3],
        "is_day": [1, 1, 1],
        "cape": [100, 150, 200],
    },
}

_FAKE_GEO = {
    "name": "Sao Paulo", "latitude": -23.55, "longitude": -46.63,
    "admin1": "Sao Paulo", "country": "Brazil",
}

_FAKE_DETECT = {
    "lat": -23.55, "lon": -46.63,
    "city": "Sao Paulo", "country": "Brazil",
}

_FAKE_AQI = {
    "current": {"us_aqi": 45, "pm2_5": 10.2, "pm10": 15.0, "nitrogen_dioxide": 8.0},
}

class TestArgumentParsingCombinations:
    """Ensure build_parser().parse_args() accepts all argument combinations."""

    def test_parse_all_argument_combinations(self):
        parser = build_parser()
        combos = _build_all_pairs() + TRIPLE_COMBOS + EDGE_VALUE_COMBOS
        for combo in combos:
            ns = parser.parse_args(["sao paulo"] + combo)
            assert isinstance(ns, argparse.Namespace)


class TestArgumentMainCombinations:
    """Ensure main() does not crash on any argument combination."""

    @pytest.fixture(autouse=True)
    def _setup_main_mocks(self, tmp_path):
        cache_file = tmp_path / "cache.db"
        config_file = tmp_path / "config.json"
        history_file = tmp_path / "history.json"

        def _mock_requests_get(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            url_str = str(url)
            if "geocoding" in url_str:
                resp.json.return_value = {"results": [_FAKE_GEO]}
            elif "air-quality" in url_str:
                resp.json.return_value = _FAKE_AQI
            else:
                resp.json.return_value = _FAKE_WEATHER
            return resp

        patches = [
            patch("bom_clima.api.requests.get", side_effect=_mock_requests_get),
            patch("bom_clima.cli.detect_location", return_value=_FAKE_DETECT),
            patch("builtins.input", return_value="sao paulo"),
            patch("bom_clima.cache.CACHE_FILE", cache_file),
            patch("bom_clima.config.CONFIG_FILE", config_file),
            patch("bom_clima.history.HISTORY_FILE", history_file),
            patch("bom_clima.constants.CONFIG_DIR", tmp_path / "cfg"),
            patch("bom_clima.constants.CACHE_DIR", tmp_path / "cache"),
            patch("bom_clima.constants.DATA_DIR", tmp_path / "data"),
            patch("bom_clima.formatters._get_documents_dir", return_value=tmp_path / "Documents"),
        ]
        for p in patches:
            p.start()
        yield
        for p in patches:
            p.stop()

    def test_main_all_argument_combinations(self):
        from bom_clima.cli import main

        scenarios = [
            (["sao paulo"], _build_all_pairs() + TRIPLE_COMBOS + EDGE_VALUE_COMBOS),
            (["sao paulo, rio de janeiro"], _build_all_pairs() + EDGE_VALUE_COMBOS),
        ]
        for city, combos in scenarios:
            for combo in combos:
                argv = ["bom-clima"] + city + combo
                with patch("sys.argv", argv):
                    try:
                        main()
                    except SystemExit:
                        pass
                    except Exception as exc:
                        raise AssertionError(f"main() crashed for argv={argv!r}") from exc

    def test_main_full_pipeline(self, tmp_path):
        out = str(tmp_path / "weather")
        sys_args = [
            "bom-clima", "sao paulo, rio de janeiro",
            "--compare", "--days", "7", "--hours", "12",
            "--aqi", "--imperial", "--best-day",
            "--vs-yesterday", "--verbose", "--no-cache",
            "--export", "json", "--output", out,
        ]
        with patch("sys.argv", sys_args):
            try:
                from bom_clima.cli import main
                main()
            except SystemExit:
                pass


# ---------------------------------------------------------------------------
# Regressions for the bug fixes. Each test reproduces the original crash or
# wrong value; see the fix comments in the source for why it matters.
# ---------------------------------------------------------------------------


class TestConfigPersistenceRegressions:
    """--config-set used to persist one-shot flag overrides, and to accept
    values that crashed every later run."""

    def _args(self, **over):
        base = {
            "imperial": False, "hours": None, "days": None, "no_color": False,
            "config_set": None, "config_show": False, "lang": None,
            "no_cache": False, "verbose": False,
        }
        base.update(over)
        return type("Args", (), base)()

    def test_config_set_does_not_persist_flag_overrides(self, tmp_path):
        from bom_clima import cli as cli_mod

        cfg_file = tmp_path / "config.json"
        with (
            patch("bom_clima.config.CONFIG_FILE", cfg_file),
            patch("bom_clima.cli.save_config", save_config),
        ):
            cli_mod.apply_config_overrides(
                dict(load_config()),
                self._args(imperial=True, days=3, hours=2, config_set=["color=true"]),
            )
        saved = json.loads(cfg_file.read_text("utf-8"))
        # Only what was explicitly persisted.
        assert saved["color"] is True
        assert saved["unit_system"] == "metric"
        assert saved["forecast_days"] == 5
        assert saved["forecast_hours"] == 6

    @pytest.mark.parametrize("pair", [
        "history_limit=abc", "history_limit=50.5",
        "forecast_days=abc", "forecast_hours=xyz",
        "forecast_days=999", "color=no", "unit_system=kelvin", "lang=xx",
    ])
    def test_config_set_rejects_values_that_crash_later(self, tmp_path, pair):
        from bom_clima import cli as cli_mod

        cfg_file = tmp_path / "config.json"
        with (
            patch("bom_clima.config.CONFIG_FILE", cfg_file),
            patch("bom_clima.cli.save_config", save_config),
        ):
            cli_mod.apply_config_overrides(
                dict(load_config()), self._args(config_set=[pair])
            )
        if cfg_file.exists():
            saved = json.loads(cfg_file.read_text("utf-8"))
            # Whatever landed on disk must still be a usable type.
            for key in ("history_limit", "forecast_days", "forecast_hours"):
                assert not isinstance(saved.get(key), str)
            assert saved.get("color") in (True, False)

    @pytest.mark.parametrize("payload", ["[]", "42", "null", '"hello"'])
    def test_load_config_survives_non_dict_file(self, tmp_path, payload):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(payload, "utf-8")
        with patch("bom_clima.config.CONFIG_FILE", cfg_file):
            cfg = load_config()
        assert cfg["forecast_days"] == 5

    def test_load_config_replaces_out_of_range_numbers(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(
            json.dumps({"forecast_days": "7", "forecast_hours": 0, "history_limit": "50"}),
            "utf-8",
        )
        with patch("bom_clima.config.CONFIG_FILE", cfg_file):
            cfg = load_config()
        assert cfg["forecast_days"] == 5
        assert cfg["forecast_hours"] == 6
        assert cfg["history_limit"] == 50


class TestHistoryRegressions:
    def test_load_history_survives_non_list_payload(self, tmp_path):
        from bom_clima.history import add_history, load_history

        for payload in ("null", '{"a":1}', '"sp"', "123"):
            with patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"):
                (tmp_path / "h.json").write_text(payload, "utf-8")
                add_history("TestCity", 1.0, 2.0)
                assert isinstance(load_history(), list)

    def test_save_history_coerces_fractional_limit(self, tmp_path):
        from bom_clima.history import load_history, save_history

        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"):
            save_history([{"city": "a"}, {"city": "b"}], 50.5)
            assert len(load_history()) == 2
            save_history([{"city": "a"}], None)
            assert isinstance(load_history(), list)

    def test_corrupt_history_is_preserved(self, tmp_path):
        from bom_clima.history import load_history

        hist = tmp_path / "h.json"
        hist.write_text("{corrupt", "utf-8")
        with patch("bom_clima.history.HISTORY_FILE", hist):
            assert load_history() == []
        # Moved aside rather than overwritten on the next write.
        assert (tmp_path / "h.json.corrupt").read_text("utf-8") == "{corrupt"


class TestCacheRegressions:
    def test_corrupt_and_future_rows_are_misses(self, tmp_path):
        import sqlite3
        import time

        from bom_clima import cache as cache_mod

        db = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE geo_cache (query TEXT PRIMARY KEY, data TEXT, ts REAL)")
        conn.execute("INSERT INTO geo_cache VALUES ('null_row', NULL, ?)", (time.time(),))
        conn.execute("INSERT INTO geo_cache VALUES ('bad', '{not json', ?)", (time.time(),))
        conn.execute("INSERT INTO geo_cache VALUES ('future', '{\"x\":1}', ?)", (time.time() + 99999,))
        conn.execute("INSERT INTO geo_cache VALUES ('null_ts', '{\"x\":3}', NULL)")
        conn.execute("INSERT INTO geo_cache VALUES ('num_data', '5', ?)", (time.time(),))
        conn.execute("INSERT INTO geo_cache VALUES ('list_data', '[1]', ?)", (time.time(),))
        conn.execute("INSERT INTO geo_cache VALUES ('good', '{\"x\":2}', ?)", (time.time(),))
        conn.commit()
        conn.close()

        with patch.object(cache_mod, "CACHE_FILE", db):
            assert cache_mod.cache_get_geo("null_row") is None
            assert cache_mod.cache_get_geo("bad") is None
            assert cache_mod.cache_get_geo("future") is None
            # A NULL timestamp used to raise TypeError in the subtraction, and
            # a valid-JSON-but-not-dict payload was returned as a hit and blew
            # up later at cidade_info["latitude"].
            assert cache_mod.cache_get_geo("null_ts") is None
            assert cache_mod.cache_get_geo("num_data") is None
            assert cache_mod.cache_get_geo("list_data") is None
            assert cache_mod.cache_get_geo("good") == {"x": 2}

    def test_unusable_database_is_not_fatal(self, tmp_path):
        from bom_clima import cache as cache_mod

        db = tmp_path / "cache.db"
        db.write_text("this is not a sqlite file", "utf-8")
        with patch.object(cache_mod, "CACHE_FILE", db):
            assert cache_mod.cache_get_geo("k") is None
            cache_mod.cache_set_geo("k", {"a": 1})
            assert cache_mod.cache_cleanup() == 0


class TestMarkupInjectionRegressions:
    """City names reach Rich as markup. MarkupError is not a ValueError, so it
    used to escape the CLI's error handling and print a raw traceback."""

    @staticmethod
    def _payload():
        return {
            "current": {"time": "2026-04-29T14:00", "temperature_2m": 25.5,
                        "apparent_temperature": 27.0, "relative_humidity_2m": 65,
                        "wind_speed_10m": 15, "wind_direction_10m": 180,
                        "weather_code": 1, "rain": 0, "uv_index": 5.2},
            "daily": {"time": ["2026-04-29"], "temperature_2m_max": [28.0],
                      "temperature_2m_min": [18.0], "sunrise": ["2026-04-29T06:30"],
                      "sunset": ["2026-04-29T18:00"], "daylight_duration": [41400],
                      "precipitation_probability_max": [10], "precipitation_sum": [0.0],
                      "precipitation_hours": [0], "weather_code": [1]},
            "hourly": {},
        }

    def test_city_name_with_markup_in_card(self, capsys):
        from bom_clima import display as display_mod

        display_mod.display_weather(
            "A[/bold]B", self._payload(), {"unit_system": "metric", "color": False}
        )
        capsys.readouterr()

    def test_city_info_with_markup_in_card(self, capsys):
        from bom_clima import display as display_mod

        display_mod.display_weather(
            "Paris", self._payload(), {"unit_system": "metric", "color": False},
            city_info={"admin1": "Ile[/red]-de-France", "country": "FR"},
        )
        capsys.readouterr()

    def test_comparison_title_with_markup(self, capsys):
        from bom_clima import display as display_mod

        display_mod.display_comparison(
            [("Rio[/]X", self._payload(), {"unit_system": "metric", "color": False}, None)]
        )
        capsys.readouterr()

    def test_history_city_with_markup_renders_literally(self, capsys, tmp_path):
        from bom_clima import cli as cli_mod

        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"):
            (tmp_path / "h.json").write_text(
                json.dumps([{"city": "A[/bold]B", "lat": -23.5, "lon": -46.6,
                             "when": "2026-01-01T10:00"}]), "utf-8",
            )
            cli_mod.show_history()
        assert "A[/bold]B" in capsys.readouterr().out


class TestWeatherDataRegressions:
    def test_error_payload_is_not_treated_as_weather(self):
        from bom_clima.api import fetch_weather_data

        with patch("bom_clima.api.requests.get") as mock_get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"error": True, "reason": "Invalid latitude"}
            mock_get.return_value = resp
            with pytest.raises(ValueError):
                fetch_weather_data(-23.5, -46.6)

    @pytest.mark.parametrize("payload", [None, [1, 2], "oops"])
    def test_non_dict_payload_raises_value_error_not_type_error(self, payload):
        """A 200 with a null/array body must raise ValueError. It used to be
        returned (and cached for 30 min) as if it were weather, crashing later
        in display; and without the isinstance guard the membership check
        itself raises TypeError, escaping the CLI's `except ValueError`."""
        from bom_clima.api import fetch_weather_data

        with patch("bom_clima.api.requests.get") as mock_get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = payload
            mock_get.return_value = resp
            with pytest.raises(ValueError):
                fetch_weather_data(-23.5, -46.6)

    def test_aqi_outage_does_not_poison_cache(self, tmp_path):
        import requests

        from bom_clima import cache as cache_mod
        from bom_clima.api import fetch_weather_data

        with patch.object(cache_mod, "CACHE_FILE", tmp_path / "c.db"):
            good = {"current": {"time": "2026-10-10T12:00", "temperature_2m": 20},
                    "daily": {"time": ["2026-10-10"]}, "hourly": {}}

            def _resp(payload):
                r = MagicMock()
                r.raise_for_status.return_value = None
                r.json.return_value = payload
                return r

            with patch("bom_clima.api.requests.get") as mock_get:
                mock_get.side_effect = [_resp(good), requests.RequestException("outage")]
                first = fetch_weather_data(-23.5, -46.6, include_aqi=True)
                assert first["air_quality"] == {}
                # A later, healthy call must not be served the poisoned entry.
                mock_get.side_effect = [_resp(good), _resp({"current": {"us_aqi": 42}})]
                second = fetch_weather_data(-23.5, -46.6, include_aqi=True)
                assert second["air_quality"]["us_aqi"] == 42

    def test_no_cache_does_not_write(self, tmp_path):
        from bom_clima import cache as cache_mod
        from bom_clima.api import fetch_weather_data

        payload = {"current": {"time": "2026-10-10T12:00", "temperature_2m": 20},
                   "daily": {"time": ["2026-10-10"]}, "hourly": {}}
        with patch.object(cache_mod, "CACHE_FILE", tmp_path / "c.db"), \
             patch("bom_clima.api.requests.get") as mock_get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = payload
            mock_get.return_value = resp
            fetch_weather_data(1.0, 2.0, no_cache=True)
        # Nothing may be written, not even the table itself.
        db = tmp_path / "c.db"
        if db.exists():
            conn = sqlite3.connect(str(db))
            rows = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='weather_cache'"
            ).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM weather_cache").fetchone()[0] if rows else 0
            conn.close()
            assert count == 0

    def test_geo_cache_key_includes_language(self, tmp_path):
        from bom_clima import cache as cache_mod
        from bom_clima.api import search_city

        payload = {"results": [{"name": "Berlin", "latitude": 52.5, "longitude": 13.4}]}
        db = tmp_path / "geo.db"
        for lang in ("pt", "en"):
            with (
                patch.object(cache_mod, "CACHE_FILE", db),
                patch("bom_clima.i18n.LANG_FILE") as lf,
                patch("bom_clima.api.requests.get") as mock_get,
            ):
                lf.exists.return_value = False
                reset_lang_cache()
                with patch.dict(os.environ, {"LANG": f"{lang}_BR.UTF-8"}):
                    resp = MagicMock()
                    resp.raise_for_status.return_value = None
                    resp.json.return_value = payload
                    mock_get.return_value = resp
                    search_city("berlin")
        conn = sqlite3.connect(str(db))
        keys = [row[0] for row in conn.execute("SELECT query FROM geo_cache")]
        conn.close()
        # The API localises place names, so one key per language is required --
        # otherwise the second language shows the first's name for 7 days.
        assert sorted(keys) == ["en:berlin", "pt:berlin"]

    def test_detect_location_handles_null_city(self):
        from bom_clima.api import detect_location

        with patch("bom_clima.api.requests.get") as mock_get:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"latitude": -23.5, "longitude": -46.6,
                                      "city": None, "country": "Brazil"}
            mock_get.return_value = resp
            loc = detect_location()
        assert loc["city"] == ""


class TestFormatterRegressions:
    @pytest.mark.parametrize("deg,expected", [
        (-30, "NNO"), (-360, "N"), (-45, "NO"), (0, "N"), (180, "S"), (350, "N"),
    ])
    def test_wind_direction_handles_negative_angles(self, deg, expected):
        from bom_clima.formatters import wind_direction

        assert wind_direction(deg) == expected

    def test_score_never_exceeds_100(self):
        from bom_clima.formatters import score_days

        dados = {
            "current": {"time": "2026-10-10T12:00"},
            "daily": {"time": ["2026-10-10"], "temperature_2m_max": [22],
                      "temperature_2m_min": [22], "precipitation_probability_max": [0],
                      "wind_speed_10m_max": [0], "sunshine_duration": [86400]},
        }
        for _label, score in score_days(dados):
            assert 0 <= score <= 100

    def test_score_survives_null_cells_and_short_arrays(self):
        from bom_clima.formatters import score_days

        base = {"current": {"time": "2026-10-11T12:00"}, "daily": {
            "time": ["2026-10-10", "2026-10-11"],
            "temperature_2m_max": [20, None], "temperature_2m_min": [10, None],
            "precipitation_probability_max": [10, None], "wind_speed_10m_max": [5, None],
            "sunshine_duration": [40000, None],
        }}
        assert score_days(base)
        short = {"current": {"time": "2026-10-11T12:00"},
                 "daily": {"time": ["2026-10-10", "2026-10-11", "2026-10-12"],
                           "temperature_2m_max": [20, 21]}}
        assert score_days(short)

    def test_rain_alert_uses_one_day_not_the_whole_window(self):
        from bom_clima.formatters import detect_extremes

        dados = {
            "current": {"time": "2026-10-10T12:00", "wind_speed_10m": 5, "uv_index": 2},
            "daily": {"time": [f"2026-10-{i:02d}" for i in range(10, 25)],
                      "temperature_2m_max": [20] * 15, "temperature_2m_min": [10] * 15,
                      "precipitation_sum": [3.0] * 15},
            "hourly": {"time": [], "cape": []},
        }
        # 3 mm/day over 15 days totals 45 mm, which tripped the *daily* 30 mm
        # threshold and reported "45 mm in 24h".
        assert not [e for e in detect_extremes(dados) if "45" in e]

    def test_recommendations_follow_today_not_index_zero(self):
        from bom_clima.formatters import generate_recommendations

        dados = {
            "current": {"time": "2026-10-10T12:00", "temperature_2m": 30,
                        "wind_speed_10m": 5, "visibility": 10000, "uv_index": 3},
            "daily": {"time": ["2026-10-09", "2026-10-10"],
                      "precipitation_probability_max": [95, 0]},
        }
        # past_days=1 shifts the arrays; index 0 is yesterday at 95%.
        recs = generate_recommendations(dados, {"unit_system": "metric"})
        assert recs == []

    def test_xml_escapes_quotes_in_attributes(self):
        import xml.etree.ElementTree as ET

        from bom_clima.formatters import _to_xml

        xml = _to_xml('Sao "Paulo" & <test>', {"current": {"temperature_2m": 20}})
        assert ET.fromstring(xml).get("city") == 'Sao "Paulo" & <test>'

    def test_export_creates_missing_output_directory(self, tmp_path):
        from bom_clima.formatters import export_data

        dest = tmp_path / "missing" / "nested" / "w.json"
        export_data({"current": {}, "daily": {}}, "X", "json", str(dest))
        assert dest.exists()

    def test_export_with_output_does_not_create_documents_dir(self, tmp_path):
        from bom_clima.formatters import export_all_formats

        docs = tmp_path / "Documents"
        out = tmp_path / "out.json"
        with patch("bom_clima.formatters._get_documents_dir", return_value=docs):
            export_all_formats({"current": {}, "daily": {}}, "X", "json", str(out))
        assert not docs.exists()

    def test_invalid_export_format_reports_zero_written(self):
        from bom_clima.formatters import export_all_formats

        assert export_all_formats({"current": {}, "daily": {}}, "X", "pdf", None) == 0


class TestLanguageResolutionRegressions:
    """--lang and the config `lang` key used to be applied after the parser had
    already baked English help strings."""

    def test_lang_flag_applies_to_help(self, tmp_path):
        from bom_clima import cli as cli_mod

        with (
            patch("bom_clima.cli.show_help") as mock_help,
            patch("bom_clima.cli.load_config", return_value=dict(DEFAULT_CONFIG)),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "c.json"),
            patch("sys.argv", ["bom-clima", "--lang", "pt", "--help"]),
            pytest.raises(SystemExit),
        ):
            cli_mod.main()
        # set_lang runs before build_parser, so the translated strings are used.
        assert mock_help.called

    def test_config_lang_is_honoured(self):
        from bom_clima.cli import _resolve_lang

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            _resolve_lang({"lang": "es"}, ["bom-clima"])
            assert _current_lang() == "es"

    def test_flag_beats_config_lang(self):
        from bom_clima.cli import _resolve_lang

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            _resolve_lang({"lang": "es"}, ["bom-clima", "--lang", "pt"])
            assert _current_lang() == "pt"


class TestLocalePrecedence:
    def test_lc_all_wins_over_lang(self):
        import bom_clima.i18n as i18n_mod

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            with patch.dict(os.environ, {"LC_ALL": "C", "LANG": "pt_BR.UTF-8"}, clear=True):
                i18n_mod.reset_lang_cache()
                assert i18n_mod._current_lang() == "en"
            with patch.dict(os.environ, {"LC_ALL": "pt_BR.UTF-8", "LANG": "C"}, clear=True):
                i18n_mod.reset_lang_cache()
                assert i18n_mod._current_lang() == "pt"

    def test_lang_file_accepts_regional_code(self):
        import bom_clima.i18n as i18n_mod

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = True
            lf.read_text.return_value = "pt-BR"
            i18n_mod.reset_lang_cache()
            assert i18n_mod._current_lang() == "pt"

    def test_detection_does_not_mutate_process_locale(self):
        import locale

        import bom_clima.i18n as i18n_mod

        before = locale.setlocale(locale.LC_MESSAGES)
        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            i18n_mod.reset_lang_cache()
            i18n_mod._current_lang()
        assert locale.setlocale(locale.LC_MESSAGES) == before


class TestColorThresholds:
    @staticmethod
    def _color(val, unit="°C"):
        import bom_clima.display as d
        if not d.HAS_RICH:
            pytest.skip("rich not installed")
        old = d._COLORS_ENABLED
        d._COLORS_ENABLED = True
        try:
            return d._temp_color(val, unit)
        finally:
            d._COLORS_ENABLED = old

    @pytest.mark.parametrize("celsius,expected", [
        (35, "red"), (28, "yellow"), (18, "green"), (10, "cyan"), (5, "blue"),
    ])
    def test_threshold_values_take_the_upper_colour(self, celsius, expected):
        # With a strict > the boundary value itself fell through one step:
        # exactly 28C rendered green while the docs said yellow.
        assert f"[{expected}]" in self._color(celsius)

    def test_rain_threshold_boundaries(self):
        import bom_clima.display as d

        if not d.HAS_RICH:
            pytest.skip("rich not installed")
        old = d._COLORS_ENABLED
        d._COLORS_ENABLED = True
        try:
            assert "[red]" in d._rain_color(60)
            assert "[yellow]" in d._rain_color(20)
            assert "[green]" in d._rain_color(0)
        finally:
            d._COLORS_ENABLED = old


class TestNoAnsiInRedirectedOutput:
    def test_console_does_not_force_terminal(self):
        import bom_clima.display as d

        if not d.HAS_RICH:
            pytest.skip("rich not installed")
        # force_terminal=True wrote ANSI escapes into files and pipes.
        assert d.console is not None
        assert d.console.is_terminal is False or d.console.file is not None


class TestMoonPhaseReference:
    def test_reference_instant_is_the_real_new_moon(self):
        from datetime import datetime as dt

        from bom_clima.formatters import get_moon_phase

        new_moon = dt(2000, 1, 6, 18, 14)
        assert get_moon_phase(new_moon) == 0
        assert get_moon_phase(new_moon - dt.resolution * 3600) == 3

    def test_phase_tracks_the_day_within_the_cycle(self):
        from datetime import datetime as dt
        from datetime import timedelta

        from bom_clima.formatters import get_moon_phase

        new_moon = dt(2000, 1, 6, 18, 14)
        # Each bucket spans a quarter of the 29.53-day cycle.
        assert get_moon_phase(new_moon + timedelta(days=15.5)) == 2  # full
        assert get_moon_phase(new_moon + timedelta(days=10.0)) == 1  # waxing
        assert get_moon_phase(new_moon + timedelta(days=24.0)) == 3  # waning

    def test_out_of_range_index_does_not_crash(self):
        from bom_clima.formatters import moon_phase_name

        assert "New Moon" in moon_phase_name(-1, "en")
        assert "New Moon" in moon_phase_name(4, "en")


class TestComparePartialFailure:
    def test_one_bad_city_does_not_discard_the_others(self, tmp_path, capsys):
        """--compare used to exit on the first failure and display nothing."""
        from bom_clima.cli import main as cli_main

        calls = []

        def _fake_fetch(city, cfg, args):
            calls.append(city)
            if city == "nope":
                raise ValueError("not found")
            payload = _FAKE_WEATHER
            return city.title(), payload, _FAKE_GEO

        with (
            patch("bom_clima.cli._fetch_and_display", side_effect=_fake_fetch),
            patch("bom_clima.cli.ensure_app_dir"),
            patch("bom_clima.cache.CACHE_FILE", tmp_path / "c.db"),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "config.json"),
            patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"),
            patch("bom_clima.cli.display_weather"),
            patch("bom_clima.cli.display_comparison") as mock_compare,
            patch("bom_clima.cli.add_history"),
            patch("sys.argv", ["bom-clima", "aa,nope,bb", "--compare"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()

        assert exc.value.code == 1
        assert calls == ["aa", "nope", "bb"]
        # The two that resolved still get displayed.
        assert mock_compare.called
        assert len(mock_compare.call_args.args[0]) == 2

    def test_all_bad_cities_exit_non_zero_without_displaying(self, tmp_path):
        from bom_clima.cli import main as cli_main

        def _always_fail(city, cfg, args):
            raise ValueError("not found")

        with (
            patch("bom_clima.cli._fetch_and_display", side_effect=_always_fail),
            patch("bom_clima.cli.ensure_app_dir"),
            patch("bom_clima.cache.CACHE_FILE", tmp_path / "c.db"),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "config.json"),
            patch("bom_clima.cli.display_comparison") as mock_compare,
            patch("sys.argv", ["bom-clima", "aa,bb", "--compare"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 1
        assert not mock_compare.called


class TestStdoutReconfigureRegressions:
    """The cp1252/legacy-code-page fix must live in main() itself: the
    installed console script calls bom_clima.cli:main directly and never runs
    the bom-clima.py / __main__ shims."""

    def test_main_reconfigures_stdout_and_stderr(self, tmp_path):
        import sys as _sys

        from bom_clima.cli import main as cli_main

        class _RecordingStream:
            def __init__(self):
                self.reconfigured = []
            def reconfigure(self, **kwargs):
                self.reconfigured.append(kwargs)
            def write(self, s):
                pass
            def flush(self):
                pass

        out, err = _RecordingStream(), _RecordingStream()
        with (
            patch.object(_sys, "stdout", out),
            patch.object(_sys, "stderr", err),
            patch("bom_clima.cli.ensure_app_dir"),
            patch("bom_clima.cli.load_config", return_value=dict(DEFAULT_CONFIG)),
            patch("sys.argv", ["bom-clima", "--version"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 0
        assert {"errors": "replace"} in out.reconfigured
        assert {"errors": "replace"} in err.reconfigured


class TestCompareExportExitCode:
    """-e pdf used to exit 0 on --compare (return value ignored) while the
    single-city path exited 1 via _do_export."""

    def test_compare_invalid_export_format_exits_non_zero(self, tmp_path):
        from bom_clima.cli import main as cli_main

        def _fake_fetch(city, cfg, args):
            return city.title(), _FAKE_WEATHER, _FAKE_GEO

        with (
            patch("bom_clima.cli._fetch_and_display", side_effect=_fake_fetch),
            patch("bom_clima.cli.ensure_app_dir"),
            patch("bom_clima.cache.CACHE_FILE", tmp_path / "c.db"),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "config.json"),
            patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"),
            patch("bom_clima.cli.display_comparison") as mock_compare,
            patch("bom_clima.cli.add_history"),
            patch("sys.argv", ["bom-clima", "aa,bb", "--compare", "-e", "pdf"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 1
        assert mock_compare.called


class TestExportUnderOptimizeFlag:
    """export_all_formats used `assert documents is not None` for control flow,
    which python -O strips, turning the else branch into `None / str`."""

    def test_export_without_output_survives_python_optimize_flag(self, tmp_path):
        import subprocess
        import sys as _sys

        code = (
            "from bom_clima.formatters import export_all_formats;"
            "print(export_all_formats({'current': {}, 'daily': {}}, 'X', 'json', None))"
        )
        env = dict(os.environ)
        env["HOME"] = str(tmp_path)
        proc = subprocess.run(
            [_sys.executable, "-O", "-c", code],
            capture_output=True, text=True, env=env,
            cwd=Path(__file__).resolve().parent.parent,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        # r_print emits "Exported to: ..." on its own line; the return value
        # (files written) is the last line. Under the old `assert documents`
        # code this subprocess died with TypeError instead.
        assert proc.stdout.strip().splitlines()[-1] == "1"
