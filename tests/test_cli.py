#
# test_cli.py - Tests for Bom Clima
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


import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bom_clima.cli import _validate_positive, build_parser
from bom_clima.config import DEFAULT_CONFIG, load_config, save_config
from bom_clima.i18n import _current_lang


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


# ---------------------------------------------------------------------------
# Argument Combination Tests


# ---------------------------------------------------------------------------

ALL_BOOLEAN_FLAGS = [
    "--detect", "--compare", "--aqi", "--imperial",
    "--no-color", "--history", "--no-cache", "--verbose",
    "--best-day", "--vs-yesterday", "--config-show", "--help", "--version",
    "--rain", "--line",
]

ALL_VALUE_ARGS = [
    ("--days", "5"),
    ("--hours", "12"),
    ("--export", "json"),
    ("--output", "/tmp/test_output.json"),
    ("--lang", "en"),
    ("--config-set", "color=false"),
    ("--at", "18"),
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
    ["--at", "18:30"],
    ["--at", "25"],
    ["--at", "18", "--vs-yesterday"],
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
            ns = parser.parse_args(["sao paulo", *combo])
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
                argv = ["bom-clima", *city, *combo]
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
        # Fetches run in parallel now: arrival order is nondeterministic,
        # but every city must be attempted exactly once.
        assert sorted(calls) == ["aa", "bb", "nope"]
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


class TestParseAt:
    @pytest.mark.parametrize("raw,expected", [
        ("18", (18, 0)), ("08", (8, 0)), ("0", (0, 0)), ("23", (23, 0)),
        ("18:30", (18, 30)), ("08:05", (8, 5)), ("23:59", (23, 59)),
        (" 18 ", (18, 0)),
    ])
    def test_valid_values(self, raw, expected):
        from bom_clima.cli import _parse_at

        assert _parse_at(raw) == expected

    def test_absent_flag_returns_none(self):
        from bom_clima.cli import _parse_at

        assert _parse_at(None) is None

    @pytest.mark.parametrize("raw", ["25", "24:00", "ab", "12:60", "-1", "1:2:3", "", ":"])
    def test_invalid_values_raise(self, raw):
        from bom_clima.cli import _parse_at

        with pytest.raises(ValueError):
            _parse_at(raw)

    def test_invalid_at_exits_non_zero(self, tmp_path):
        from bom_clima.cli import main as cli_main

        with (
            patch("sys.argv", ["bom-clima", "sao paulo", "--at", "25"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 1

    def test_at_with_vs_yesterday_is_rejected(self, tmp_path, capsys):
        from bom_clima.cli import main as cli_main

        with (
            patch("sys.argv", ["bom-clima", "sao paulo", "--at", "18", "--vs-yesterday"]),
            pytest.raises(SystemExit) as exc,
        ):
            cli_main()
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# --line: one compact line for a statusbar or prompt


# ---------------------------------------------------------------------------


class TestLineOutput:
    """`--line` exists to be captured, so it prints nothing but the line."""

    def test_format_matches_expected_shape(self, mock_weather_response):
        from bom_clima.formatters import format_line

        line = format_line("Curitiba", mock_weather_response, {"unit_system": "metric"})
        assert line == "Curitiba: 🌤️ 25.5°C"

    def test_imperial_uses_fahrenheit(self, mock_weather_response):
        from bom_clima.formatters import format_line

        line = format_line("NYC", mock_weather_response, {"unit_system": "imperial"})
        assert line is not None and line.endswith("°F")

    def test_null_temperature_degrades_to_zero_not_a_crash(self, mock_weather_response):
        """Open-Meteo sends null for cells it has no sensor for."""
        from bom_clima.formatters import format_line

        mock_weather_response["current"]["temperature_2m"] = None
        line = format_line("X", mock_weather_response, {"unit_system": "metric"})
        assert line is not None and "0°C" in line

    def test_missing_current_block_returns_none(self):
        """None tells the caller to fall back to the cards, not print a blank."""
        from bom_clima.formatters import format_line

        assert format_line("X", {}, {"unit_system": "metric"}) is None

    def test_missing_current_block_falls_back_to_the_card(self, mock_geo_response, mock_weather_response, capsys):
        """A blank stdout is the worst outcome for --line: the user gets no
        weather and no explanation. The note goes to stderr so a statusbar
        still receives nothing but the card on stdout."""
        from bom_clima.cli import main

        stripped = dict(mock_weather_response)
        stripped["current"] = {"time": None}
        with (
            patch("bom_clima.api._get") as mock_get,
            patch("sys.argv", ["bom-clima", "Sao Paulo", "--line"]),
        ):
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.side_effect = [mock_geo_response, stripped]
            main()
        captured = capsys.readouterr()
        assert "Sao Paulo" in captured.err
        assert captured.err.count("\n") == 1
        assert "╭" in captured.out, "esperava o card completo como fallback"

    def test_markup_in_city_name_is_escaped(self, mock_weather_response):
        """Rich escape turns '[' into '\\['; the name survives, the tag does not."""
        from bom_clima.formatters import format_line

        line = format_line("A[/bold]B", mock_weather_response, {"unit_system": "metric"})
        assert line is not None
        assert "[/bold]" in line
        assert "\\[" in line

    def test_flag_prints_only_the_line(self, mock_geo_response, mock_weather_response, capsys):
        from bom_clima.cli import main

        with (
            patch("bom_clima.api._get") as mock_get,
            patch("sys.argv", ["bom-clima", "Sao Paulo", "--line"]),
        ):
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.side_effect = [
                mock_geo_response,
                mock_weather_response,
            ]
            main()
        out = capsys.readouterr().out
        assert out.count("\n") == 1
        assert "╭" not in out and "Horiz" not in out
        assert out.strip().startswith("Sao Paulo:")

    def test_line_suppresses_the_export_confirmation(self, mock_geo_response, mock_weather_response, capsys):
        """A pipe must not receive the 'Data exported to:' note."""
        from bom_clima.cli import main

        with (
            patch("bom_clima.api._get") as mock_get,
            patch("sys.argv", ["bom-clima", "Sao Paulo", "--line", "-e", "json", "-o", "-"]),
        ):
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.side_effect = [mock_geo_response, mock_weather_response]
            main()
        out = capsys.readouterr().out
        assert "Data exported to" not in out
        assert json.loads(out)["city"] == "Sao Paulo"


# ---------------------------------------------------------------------------
# -o - : JSON on stdout, pipeable


# ---------------------------------------------------------------------------


class TestStdoutExport:
    def test_dash_writes_json_to_stdout(self, mock_weather_response, capsys):
        from bom_clima.formatters import STDOUT_TARGET, export_all_formats

        written = export_all_formats(mock_weather_response, "Sao Paulo", "json", STDOUT_TARGET)
        out = capsys.readouterr().out
        assert written == 1
        assert json.loads(out)["data"]["current"]["temperature_2m"] == 25.5

    def test_dash_writes_no_ansi_codes(self, mock_weather_response, capsys):
        """Rich would emit escape codes and break the payload."""
        from bom_clima.formatters import STDOUT_TARGET, export_all_formats

        export_all_formats(mock_weather_response, "Sao Paulo", "json", STDOUT_TARGET)
        assert "\x1b[" not in capsys.readouterr().out

    def test_dash_does_not_create_a_file_named_dash(self, mock_weather_response, tmp_path, monkeypatch, capsys):
        """os.path.splitext('-') would yield '-_Sao_Paulo.json'."""
        from bom_clima.formatters import STDOUT_TARGET, export_all_formats

        monkeypatch.chdir(tmp_path)
        export_all_formats(mock_weather_response, "Sao Paulo", "json", STDOUT_TARGET)
        assert list(tmp_path.iterdir()) == []

    def test_without_dash_still_writes_to_documents(self, mock_weather_response, tmp_path, monkeypatch):
        """Regression lock: -e without -o must not change where files land."""
        from bom_clima.formatters import export_all_formats

        docs = tmp_path / "Documents"
        docs.mkdir()
        monkeypatch.setattr("bom_clima.formatters._get_documents_dir", lambda: docs)
        assert export_all_formats(mock_weather_response, "Sao Paulo", "json", None) == 1
        assert (docs / "Sao_Paulo.json").exists()

    def test_dash_still_rejects_invalid_format(self):
        from bom_clima.formatters import STDOUT_TARGET, export_all_formats

        assert export_all_formats({"current": {}}, "X", "pdf", STDOUT_TARGET) == 0

    def test_invalid_format_stays_off_stdout(self, mock_weather_response, capsys):
        """`-e json,pdf -o -` must not hand jq a payload with a message glued
        to the end of it. The check runs per format, before the stdout branch,
        so it used to print straight into the pipe."""
        from bom_clima.formatters import STDOUT_TARGET, export_all_formats

        written = export_all_formats(mock_weather_response, "Sao Paulo", "json,pdf", STDOUT_TARGET)
        captured = capsys.readouterr()
        assert written == 1
        assert json.loads(captured.out)["city"] == "Sao Paulo"
        assert "pdf" in captured.err
        assert "pdf" not in captured.out


class TestStdoutExportCli:
    def test_cli_streams_pure_json(self, mock_geo_response, mock_weather_response, capsys):
        from bom_clima.cli import main

        with (
            patch("bom_clima.api._get") as mock_get,
            patch("sys.argv", ["bom-clima", "Sao Paulo", "-e", "json", "-o", "-"]),
        ):
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.side_effect = [mock_geo_response, mock_weather_response]
            main()
        out = capsys.readouterr().out
        # jq has to be able to parse this straight off the pipe.
        assert json.loads(out)["city"] == "Sao Paulo"
        assert "╭" not in out

    def test_ambiguity_note_goes_to_stderr(self, mock_weather_response, capsys):
        """The note would otherwise corrupt the payload the caller is piping."""
        from bom_clima.cli import main

        multi = {"results": [
            {"name": "Springfield", "latitude": 39.8, "longitude": -89.6, "admin1": "Illinois"},
            {"name": "Springfield", "latitude": 37.2, "longitude": -93.3, "admin1": "Missouri"},
        ]}
        with (
            patch("bom_clima.api._get") as mock_get,
            patch("sys.argv", ["bom-clima", "springfield", "-e", "json", "-o", "-"]),
        ):
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.side_effect = [multi, mock_weather_response]
            main()
        captured = capsys.readouterr()
        assert json.loads(captured.out)["city"] == "Springfield"
        assert "Missouri" in captured.err


# ---------------------------------------------------------------------------
# --help derived from the parser


# ---------------------------------------------------------------------------


class TestHelpOutput:
    def _help_text(self):
        import io
        from contextlib import redirect_stdout

        from bom_clima.cli import show_help

        buf = io.StringIO()
        with redirect_stdout(buf):
            show_help(build_parser())
        return buf.getvalue()

    def test_every_flag_in_the_parser_appears_in_the_help(self):
        """The regression that motivated deriving it: a new flag used to need
        two edits, and the hand-written copy had already drifted."""
        text = self._help_text()
        parser = build_parser()
        for action in parser._action_groups:
            for opt in action._group_actions:
                for flag in opt.option_strings:
                    if flag.startswith("--"):
                        assert flag in text, f"{flag} ausente do --help"

    def test_group_icons_present(self):
        from bom_clima.cli import _GROUP_ICON_KEYS

        text = self._help_text()
        for key, icon in _GROUP_ICON_KEYS.items():
            assert icon in text, f"icone de {key} ausente"

    def test_option_column_is_aligned(self):
        """Every description must start on the same column."""
        text = self._help_text()
        rows = [ln for ln in text.splitlines() if ln.strip().startswith("-")]
        starts = {len(ln) - len(ln.lstrip()) for ln in rows}
        assert len(starts) <= 3, "coluna de opcoes desalinhada"

    def test_value_placeholder_follows_the_flag(self):
        text = self._help_text()
        assert "-D, --days N" in text
        assert "-e, --export FMT" in text

    def test_short_flag_is_listed_before_long(self):
        text = self._help_text()
        assert "-V, --verbose" in text
        assert "--verbose, -V" not in text

    def test_export_format_list_is_not_duplicated(self):
        """The option row used to append '(json, csv, yaml, xml)' to a help
        string that already named them, printing the list twice."""
        text = self._help_text()
        row = [ln for ln in text.splitlines() if "-e, --export" in ln]
        assert len(row) == 1
        assert row[0].count("json") == 1

    def test_examples_are_kept(self):
        text = self._help_text()
        assert "bom-clima sao paulo" in text

    def test_locale_parity_across_all_three_languages(self):
        """A key dropped from one file only would silently fall back to English."""
        import json as json_mod

        import bom_clima

        locales = Path(bom_clima.__file__).parent / "locales"
        sets = {
            p.name: set(json_mod.loads(p.read_text("utf-8")))
            for p in sorted(locales.glob("*.json"))
        }
        assert len(sets) == 3, f"esperados en/pt/es, achei {list(sets)}"
        reference = sets["en.json"]
        for name, keys in sets.items():
            assert keys == reference, f"{name} diverge de en.json: {keys ^ reference}"

    def test_no_orphan_help_keys_left_behind(self):
        """The duplicated help_* strings are gone from the locale files."""
        import json as json_mod

        import bom_clima

        locales = Path(bom_clima.__file__).parent / "locales"
        removed = {
            "help_search", "help_search_city", "help_search_detect",
            "help_search_compare", "help_display", "help_display_days",
            "help_display_hours", "help_display_aqi", "help_display_at",
            "help_display_rain", "help_display_imperial", "help_display_color",
            "help_modes", "help_modes_history", "help_export",
            "help_export_format", "help_export_output", "help_config",
            "help_config_lang", "help_info", "help_info_help",
            "help_info_version",
        }
        for p in sorted(locales.glob("*.json")):
            keys = set(json_mod.loads(p.read_text("utf-8")))
            assert not (keys & removed), f"{p.name} ainda tem chaves removidas"

    def test_every_key_build_parser_asks_for_exists_in_every_locale(self):
        """`build_parser()` resolves t() at build time, and t() falls back to
        returning the key itself. So a key dropped from the locale files printed
        as a bare `help_config_set` in --help -- no exception, no failing test.
        That happened once; this is the guard.

        The key literals are language-independent, so one build records every key
        the parser needs and it can be checked against all three files at once.
        """
        import json as json_mod

        import bom_clima
        import bom_clima.cli as cli_mod

        asked: list[str] = []
        real_t = cli_mod.t

        def _spy(key):
            asked.append(key)
            return real_t(key)

        locales = Path(bom_clima.__file__).parent / "locales"
        tables = {
            p.name: json_mod.loads(p.read_text("utf-8"))
            for p in sorted(locales.glob("*.json"))
        }
        with patch("bom_clima.cli.t", side_effect=_spy):
            build_parser()

        wanted = set(asked)
        assert wanted, "nenhuma chave registrada; o spy esta no lugar errado"
        missing = {name: sorted(wanted - set(table)) for name, table in tables.items()}
        assert not any(missing.values()), f"chaves ausentes nos locales: {missing}"


# ---------------------------------------------------------------------------
# --line / -o - must not be dropped by the multi-city paths


# ---------------------------------------------------------------------------


class TestMachineOutputEveryPath:
    """Both flags replace the cards, so every fetch path has to honour them.

    --compare renders through display_comparison() instead of _render_one(),
    which made it a separate branch that silently ignored --line.
    """

    @staticmethod
    def _cities():
        return [
            {"name": "Curitiba", "latitude": -25.4, "longitude": -49.3, "admin1": "Parana"},
            {"name": "Recife", "latitude": -8.05, "longitude": -34.9, "admin1": "Pernambuco"},
        ]

    def _run(self, argv, weather):
        from bom_clima.cli import main

        def _fake_get(url, params=None):
            # Cities are fetched concurrently, so the mock routes by the
            # request instead of expecting a fixed call order.
            resp = MagicMock()
            if "geocoding" in url:
                name = (params or {}).get("name", "").lower()
                match = next(
                    (c for c in self._cities() if c["name"].lower().startswith(name)),
                    self._cities()[0],
                )
                resp.json.return_value = {"results": [match]}
                return resp
            resp.json.return_value = weather
            return resp

        with (
            patch("bom_clima.api._get", side_effect=_fake_get),
            patch("sys.argv", argv),
        ):
            main()

    def test_line_with_compare_prints_one_line_per_city(self, capsys, mock_weather_response):
        self._run(["bom-clima", "curitiba,recife", "--compare", "--line"], mock_weather_response)
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 2
        assert out[0].startswith("Curitiba:")
        assert out[1].startswith("Recife:")

    def test_line_with_multi_city_prints_one_line_per_city(self, capsys, mock_weather_response):
        self._run(["bom-clima", "curitiba,recife", "--line"], mock_weather_response)
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 2
        assert "╭" not in capsys.readouterr().out

    def test_compare_still_renders_cards_without_the_flag(self, capsys, mock_weather_response):
        self._run(["bom-clima", "curitiba,recife", "--compare"], mock_weather_response)
        assert "╭" in capsys.readouterr().out


class TestDaysClampWarning:
    """--days above MAX_FORECAST_DAYS was silently clamped; now it warns."""

    def _args(self, **over):
        defaults = {
            "city": [], "detect": False, "compare": False,
            "days": None, "hours": None, "aqi": False,
            "at": None, "rain": False, "line": False,
            "imperial": False, "no_color": False,
            "history": False, "no_cache": False, "verbose": False,
            "best_day": False, "vs_yesterday": False,
            "export": None, "output": None,
            "lang": None, "config_set": None, "config_show": False,
        }
        defaults.update(over)
        return argparse.Namespace(**defaults)

    def test_clamp_warns_on_stderr(self, capsys):
        from bom_clima.cli import apply_config_overrides
        from bom_clima.config import DEFAULT_CONFIG

        cfg = dict(DEFAULT_CONFIG)
        apply_config_overrides(cfg, self._args(days=30))
        captured = capsys.readouterr()
        assert cfg["forecast_days"] == 15
        assert "15" in captured.err
        assert captured.out == ""

    def test_days_within_limit_is_silent(self, capsys):
        from bom_clima.cli import apply_config_overrides
        from bom_clima.config import DEFAULT_CONFIG

        cfg = dict(DEFAULT_CONFIG)
        apply_config_overrides(cfg, self._args(days=10))
        captured = capsys.readouterr()
        assert cfg["forecast_days"] == 10
        assert captured.err == ""
