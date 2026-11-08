#
# test_formatters.py - Tests for Bom Clima
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


from pathlib import Path
from unittest.mock import patch

import pytest

from bom_clima.constants import WMO_CODES
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


class TestDisplayWidth:
    def test_ascii(self):
        assert display_width("hello") == 5

    def test_empty(self):
        assert display_width("") == 0


class TestDocumentsDir:
    def test_fallback_documents_dir(self):
        result = _get_documents_dir()
        assert isinstance(result, Path)


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


        xml = _to_xml('Sao "Paulo" & <test>', {"current": {"temperature_2m": 20}})
        assert ET.fromstring(xml).get("city") == 'Sao "Paulo" & <test>'

    def test_export_creates_missing_output_directory(self, tmp_path):

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
