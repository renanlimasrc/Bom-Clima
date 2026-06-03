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
from bom_clima.cli import _calc_dynamic_interval, _validate_positive, apply_config_overrides, build_parser
from bom_clima.config import load_config
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
        assert get_wmo(999, "pt") == ("Limpo", "\u2600\ufe0f")

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
        content = export_data(mock_weather_response, "Sao Paulo", "yaml")
        assert "city: Sao Paulo" in content
        assert "current:" in content

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


class TestI18n:
    def test_set_lang(self):
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("en")
            mock_file.write_text.assert_called_once_with("en")

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


class TestCalcDynamicInterval:
    def test_no_hourly_data(self):
        dados = {"hourly": {}}
        assert _calc_dynamic_interval(dados, 60) == 60

    def test_high_rain_probability(self):
        dados = {
            "hourly": {
                "time": ["2026-04-29T15:00", "2026-04-29T16:00"],
                "precipitation_probability": [80, 75],
            }
        }
        result = _calc_dynamic_interval(dados, 60)
        assert result <= 60

    def test_moderate_rain_probability(self):
        dados = {
            "hourly": {
                "time": ["2026-04-29T15:00", "2026-04-29T16:00"],
                "precipitation_probability": [50, 45],
            }
        }
        result = _calc_dynamic_interval(dados, 60)
        assert 45 <= result <= 60


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


class TestAddHistory:
    def test_add_history(self, tmp_path):
        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "history.json"):
            from bom_clima.history import add_history, load_history
            add_history("TestCity", 1.0, 2.0)
            history = load_history()
            assert len(history) == 1
            assert history[0]["city"] == "TestCity"


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


class TestRainWindowSummary:
    def test_no_rain(self, mock_weather_response):
        from bom_clima.formatters import rain_window_summary
        result = rain_window_summary(mock_weather_response)
        assert len(result) == 0


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
