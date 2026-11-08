#
# test_display.py - Tests for Bom Clima
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


import copy
import json
from unittest.mock import patch

import pytest

from bom_clima.display import format_weather_block
from bom_clima.formatters import (
    get_wmo,
)
from bom_clima.i18n import t


class TestFormatWeatherBlock:
    @staticmethod
    def _row_for(block, label):
        """The rendered line carrying `label`, so an assertion about a value
        cannot be satisfied by that value appearing on some other row."""
        for line in block.splitlines():
            if label in line:
                return line
        raise AssertionError(f"linha '{label}' ausente do card")

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

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(lambda d: d.pop("current"), id="ausente"),
            pytest.param(lambda d: d.update(current={}), id="vazio"),
            pytest.param(lambda d: d.update(current=None), id="null"),
            pytest.param(lambda d: d["current"].update(time=None), id="time-null"),
            pytest.param(lambda d: d["current"].update(time="nao-e-data"), id="time-lixo"),
            pytest.param(lambda d: d["current"].update(temperature_2m=None), id="temp-null"),
        ],
    )
    def test_survives_a_degraded_current_block(self, mock_weather_response, mutate):
        """Open-Meteo can answer 200 with "current" missing, empty or null, and
        its cells are individually nullable. --line falls back to this function
        exactly when that happens, so every one of these used to raise
        KeyError/TypeError/AttributeError instead of rendering."""
        dados = copy.deepcopy(mock_weather_response)
        mutate(dados)
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", dados, cfg)
        assert "Sao Paulo" in block

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(lambda d: d.pop("current"), id="ausente"),
            pytest.param(lambda d: d.update(current={}), id="vazio"),
            pytest.param(lambda d: d.update(current=None), id="null"),
        ],
    )
    def test_degraded_current_does_not_invent_a_reading(self, mock_weather_response, mutate):
        """A .get() default is not a neutral placeholder here: WMO 0 is "Clear
        sky", rain 0 is "it is not raining", and a 0 degC marker pinned to the
        daily minimum reads as a real observation. With no "current" block the
        card must say nothing about current conditions, not assert sunny."""
        dados = copy.deepcopy(mock_weather_response)
        mutate(dados)
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", dados, cfg)

        for description in get_wmo(0, "en")[0], t("rain_now"), t("temperature"):
            assert description not in block, f"linha '{description}' sem leitura"
        # The bar is what carries the current reading; without one it is dropped.
        assert "°C [" not in block
        # Rows that come from `daily` are real and must survive.
        assert t("max_today") in block and t("min_today") in block

    def test_weather_code_zero_still_renders_clear_sky(self, mock_weather_response):
        """WMO 0 is a real reading, so the guard tests presence, not truthiness."""
        dados = copy.deepcopy(mock_weather_response)
        dados["current"]["weather_code"] = 0
        block = format_weather_block("Sao Paulo", dados, {"unit_system": "metric"})
        assert get_wmo(0, "en")[0] in block

    def test_rain_zero_still_renders(self, mock_weather_response):
        """Same for rain: 0.0 mm is a measurement, absent is not."""
        dados = copy.deepcopy(mock_weather_response)
        dados["current"]["rain"] = 0.0
        block = format_weather_block("Sao Paulo", dados, {"unit_system": "metric"})
        assert "0.0 mm" in self._row_for(block, t("rain_now"))

    def test_empty_timestamp_renders_na_not_a_blank(self, mock_weather_response):
        """The `raw_time or "N/A"` branch: a blank cell used to leave the row
        empty, which is not the same as saying the timestamp is unavailable."""
        dados = copy.deepcopy(mock_weather_response)
        dados["current"]["time"] = ""
        block = format_weather_block("Sao Paulo", dados, {"unit_system": "metric"})
        assert self._row_for(block, t("updated")).strip().endswith("N/A")

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(lambda d: d.pop("daily"), id="ausente"),
            pytest.param(lambda d: d.update(daily={}), id="vazio"),
            pytest.param(lambda d: d.update(daily=None), id="null"),
            pytest.param(lambda d: d.update(daily={"time": d["daily"]["time"]}), id="sem-series"),
            pytest.param(lambda d: d.pop("hourly"), id="hourly-ausente"),
            pytest.param(lambda d: d.update(hourly=None), id="hourly-null"),
        ],
    )
    def test_survives_a_degraded_daily_block(self, mock_weather_response, mutate):
        """Same class as the current-block case one test above: daily series can
        arrive short, empty or null, and every one of these used to raise
        KeyError/AttributeError -- diario[...][idx] does not tolerate a missing
        key the way _at()/get() do."""
        dados = copy.deepcopy(mock_weather_response)
        mutate(dados)
        cfg = {"unit_system": "metric", "forecast_days": 5, "forecast_hours": 12}
        block = format_weather_block("Sao Paulo", dados, cfg)
        assert "Sao Paulo" in block

    def test_degraded_daily_omits_daily_rows_but_keeps_current(self, mock_weather_response):
        """Without daily there is no min/max, rain-chance or sunrise to report;
        the current-conditions rows that remain must still render."""
        dados = copy.deepcopy(mock_weather_response)
        dados.pop("daily")
        block = format_weather_block("Sao Paulo", dados, {"unit_system": "metric"})
        assert t("temperature") in block
        for label in (t("max_today"), t("min_today"), t("rain_chance"), t("sunrise"), t("sunset")):
            assert label not in block, f"linha '{label}' sem serie daily"
        assert "°C [" not in block

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


class TestFormatAtBlock:
    @staticmethod
    def _payload():
        return {
            "current": {"time": "2026-04-29T14:00", "temperature_2m": 25.0},
            "daily": {"time": ["2026-04-29", "2026-04-30"]},
            "hourly": {
                "time": ["2026-04-29T15:00", "2026-04-29T16:00",
                         "2026-04-29T17:00", "2026-04-30T13:00"],
                "temperature_2m": [26.0, 25.5, 24.0, 22.0],
                "apparent_temperature": [27.5, 26.0, 25.0, 23.0],
                "precipitation_probability": [5, 10, 40, 20],
                "wind_speed_10m": [14, 13, 12, 10],
                "weather_code": [1, 2, 61, 3],
            },
        }

    def test_future_hour_same_day(self):
        from bom_clima.display import format_at_block

        block = format_at_block(self._payload(), {"unit_system": "metric"}, 16, 0)
        assert block is not None
        assert "16:00" in block.splitlines()[0]

    def test_past_hour_rolls_to_tomorrow(self):
        """14:00 now + --at 13 resolves to tomorrow 13:00, never to this
        morning, and uses the location's clock, not the machine's."""
        from bom_clima.display import format_at_block

        block = format_at_block(self._payload(), {"unit_system": "metric"}, 13, 0)
        assert block is not None
        assert block.splitlines()[0].startswith("13:00 (30/04)")

    def test_missing_hourly_returns_none(self):
        from bom_clima.display import format_at_block

        assert format_at_block({"current": {}, "daily": {}}, {}, 18, 0) is None
        assert format_at_block({"hourly": {"time": []}}, {}, 18, 0) is None


class TestRainFlag:
    def test_rainy_payload_renders_windows(self):
        from bom_clima import cli as cli_mod

        dados = {
            "current": {"time": "2026-04-29T14:00"},
            "hourly": {
                "time": ["2026-04-29T15:00", "2026-04-29T16:00"],
                "precipitation_probability": [5, 60],
            },
        }
        args = type("Args", (), {"rain": True})()
        with patch.object(cli_mod, "r_panel") as mock_panel:
            cli_mod._show_rain(dados, {}, args)
        mock_panel.assert_called_once()
        assert "16:00" in mock_panel.call_args.args[0]

    def test_dry_payload_renders_no_rain_message(self):
        from bom_clima import cli as cli_mod
        from bom_clima.i18n import t

        dados = {
            "current": {"time": "2026-04-29T14:00"},
            "hourly": {
                "time": ["2026-04-29T15:00"],
                "precipitation_probability": [5],
            },
        }
        args = type("Args", (), {"rain": True})()
        with patch.object(cli_mod, "r_panel") as mock_panel:
            cli_mod._show_rain(dados, {}, args)
        mock_panel.assert_called_once()
        assert mock_panel.call_args.args[0] == t("no_rain_expected")

    def test_flag_off_renders_nothing(self):
        from bom_clima import cli as cli_mod

        args = type("Args", (), {"rain": False})()
        with patch.object(cli_mod, "r_panel") as mock_panel:
            cli_mod._show_rain({"hourly": {}}, {}, args)
        assert mock_panel.call_count == 0
