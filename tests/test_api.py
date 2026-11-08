#
# test_api.py - Tests for Bom Clima
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
import sqlite3
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

from bom_clima.api import detect_location, search_city
from bom_clima.cache import (
    cache_get_geo,
)
from bom_clima.i18n import reset_lang_cache


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


class TestRetryRegressions:
    """Transient 5xx / connection errors used to fail the run outright. _get()
    retries them with exponential backoff; anything else fails immediately."""

    @staticmethod
    def _http_error(status):
        import requests

        resp = MagicMock()
        resp.status_code = status
        err = requests.HTTPError(f"{status} error")
        err.response = resp
        return err

    def test_success_after_transient_failures(self):
        import requests

        from bom_clima import api as api_mod

        ok = MagicMock()
        ok.raise_for_status.return_value = None
        with (
            patch.object(api_mod.requests, "get", side_effect=[
                requests.ConnectionError("down"),
                requests.Timeout("slow"),
                self._http_error(503),
                ok,
            ]) as mock_get,
            patch.object(api_mod.time, "sleep") as mock_sleep,
        ):
            assert api_mod._get("https://x.test") is ok
        assert mock_get.call_count == 4
        assert [c.args[0] for c in mock_sleep.call_args_list] == [0.5, 1.0, 2.0]

    def test_client_error_fails_without_sleeping(self):
        import requests

        from bom_clima import api as api_mod

        with (
            patch.object(api_mod.requests, "get", side_effect=self._http_error(404)) as mock_get,
            patch.object(api_mod.time, "sleep") as mock_sleep,
            pytest.raises(requests.HTTPError),
        ):
            api_mod._get("https://x.test")
        assert mock_get.call_count == 1
        assert mock_sleep.call_count == 0

    def test_persistent_outage_raises_after_four_attempts(self):
        import requests

        from bom_clima import api as api_mod

        with (
            patch.object(api_mod.requests, "get",
                          side_effect=requests.ConnectionError("down")) as mock_get,
            patch.object(api_mod.time, "sleep"),
            pytest.raises(requests.ConnectionError),
        ):
            api_mod._get("https://x.test")
        assert mock_get.call_count == 4


class TestDisambiguationRegressions:
    @staticmethod
    def _cands():
        return [
            {"name": "Springfield", "admin1": "Illinois", "country": "US",
             "latitude": 39.78, "longitude": -89.65},
            {"name": "Springfield", "admin1": "Missouri", "country": "US",
             "latitude": 37.21, "longitude": -93.29},
            {"name": "Springfield", "admin1": "Ohio", "country": "US",
             "latitude": 39.92, "longitude": -83.81},
        ]

    def test_search_cities_returns_every_candidate(self, tmp_path):
        from bom_clima import api as api_mod

        resp = MagicMock()
        resp.json.return_value = {"results": self._cands()}
        with (
            patch.object(api_mod, "_get", return_value=resp) as mock_get,
            patch.object(api_mod, "cache_set_geo") as mock_set,
        ):
            results = api_mod.search_cities("springfield", no_cache=True)
        assert len(results) == 3
        assert results[1]["admin1"] == "Missouri"
        assert mock_get.call_count == 1
        assert mock_set.call_count == 0

    def test_search_cities_caches_wrapper_once(self, tmp_path):
        from bom_clima import api as api_mod

        resp = MagicMock()
        resp.json.return_value = {"results": self._cands()}
        with patch.object(api_mod, "_get", return_value=resp) as mock_get:
            first = api_mod.search_cities("springfield")
            second = api_mod.search_cities("springfield")
        assert mock_get.call_count == 1
        assert first == second
        # One key holds every candidate, so a later pick can never overwrite
        # an earlier one.
        assert cache_get_geo("en:springfield") == {"results": self._cands()}

    def test_legacy_single_result_cache_still_reads(self, tmp_path):
        from bom_clima import api as api_mod

        with patch.object(api_mod, "cache_get_geo", return_value=dict(self._cands()[0])):
            assert api_mod.search_cities("springfield") == [self._cands()[0]]

    def test_ambiguous_picks_first_and_shows_only_the_hint(self, capsys):
        """No prompt: the most populous candidate wins, and stderr carries the
        refine hint alone. Naming the pick and listing every alternative just
        repeated what the card below already showed."""
        from bom_clima.cli import _resolve_city

        def _no_prompt(_prompt=""):
            raise AssertionError("must never prompt for input")

        with (
            patch("bom_clima.cli.search_cities", return_value=self._cands()),
            patch("builtins.input", side_effect=_no_prompt),
        ):
            picked = _resolve_city("springfield", no_cache=True)
        assert picked["admin1"] == "Illinois"
        err = capsys.readouterr().err
        assert err.strip().count("\n") == 0, "a dica deve ser uma unica linha"
        assert "springfield, Missouri" in err

    def test_single_candidate_is_silent(self, capsys):
        from bom_clima.cli import _resolve_city

        with patch("bom_clima.cli.search_cities", return_value=[self._cands()[0]]):
            picked = _resolve_city("springfield", no_cache=True)
        assert picked["admin1"] == "Illinois"
        assert capsys.readouterr().err == ""

    def test_no_hint_and_no_output_without_admin1(self, capsys):
        """With nothing to refine towards there is no tip to give, and no
        'multiple matches' preamble left over to print on its own."""
        from bom_clima.cli import _resolve_city

        cands = [dict(self._cands()[0]), {"name": "Nowhere"}]
        with patch("bom_clima.cli.search_cities", return_value=cands):
            _resolve_city("nowhere", no_cache=True)
        assert capsys.readouterr().err == ""

    def test_hint_follows_the_desktop_language(self, capsys):
        """The tip is user-facing text and must come out in pt on a pt desktop."""
        from bom_clima.cli import _resolve_city

        with (
            patch("bom_clima.cli.search_cities", return_value=self._cands()),
            patch.dict(os.environ, {"LANG": "pt_BR.UTF-8"}),
        ):
            reset_lang_cache()
            _resolve_city("springfield", no_cache=True)
            err = capsys.readouterr().err
            assert "Dica:" in err, err
        reset_lang_cache()

    def test_markup_in_names_does_not_crash_note(self, capsys):
        """The note goes through plain print (not Rich), so '[' in API place
        names is rendered literally instead of raising MarkupError."""
        from bom_clima.cli import _resolve_city

        cands = [
            dict(self._cands()[0], name="A[/bold]B"),
            self._cands()[1],
        ]
        with patch("bom_clima.cli.search_cities", return_value=cands):
            picked = _resolve_city("A[/bold]B", no_cache=True)
        assert picked["name"] == "A[/bold]B"
        assert "A[/bold]B" in capsys.readouterr().err

    def test_truncated_json_body_reads_as_not_found(self):
        import json as json_mod

        from bom_clima.api import search_cities

        resp = MagicMock()
        resp.json.side_effect = json_mod.JSONDecodeError("x", "y", 0)
        with (
            patch("bom_clima.api._get", return_value=resp),
            pytest.raises(ValueError, match="not found"),
        ):
            search_cities("sp", no_cache=True)


class TestDetectLocationCache:
    """--detect IP geolocation should not hit ipapi.co on every run."""

    PAYLOAD: ClassVar[dict] = {"latitude": -23.5, "longitude": -46.6,
                            "city": "Sao Paulo",
                            "country_name": "Brazil"}
    LOCATION: ClassVar[dict] = {"lat": -23.5, "lon": -46.6,
                              "city": "Sao Paulo", "country": "Brazil"}

    def _mock_http(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        return resp

    def test_second_call_is_served_by_cache(self):
        from unittest.mock import patch

        from bom_clima.api import detect_location

        with patch("bom_clima.api._get", return_value=self._mock_http(self.PAYLOAD)) as mock_get:
            first = detect_location()
            second = detect_location()
        assert mock_get.call_count == 1
        assert first == second == self.LOCATION

    def test_no_cache_bypasses_cache_and_refetches(self):
        from unittest.mock import patch

        from bom_clima import cache as cache_mod
        from bom_clima.api import detect_location

        cache_mod.cache_set_ip({"lat": 1.0, "lon": 2.0, "city": "stale", "country": "stale"})
        with patch("bom_clima.api._get", return_value=self._mock_http(self.PAYLOAD)) as mock_get:
            result = detect_location(no_cache=True)
        assert mock_get.call_count == 1
        assert result == self.LOCATION

    def test_expired_cache_refetches(self):
        import sqlite3
        import time
        from unittest.mock import patch

        from bom_clima import cache as cache_mod
        from bom_clima.api import detect_location

        cache_mod.cache_set_ip(self.LOCATION)
        with sqlite3.connect(str(cache_mod.CACHE_FILE)) as conn:
            conn.execute("UPDATE ip_cache SET ts = ?", (time.time() - 700,))
        with patch("bom_clima.api._get", return_value=self._mock_http(self.PAYLOAD)) as mock_get:
            detect_location()
        assert mock_get.call_count == 1

    def test_corrupt_cache_refetches(self):
        import time
        from unittest.mock import patch

        from bom_clima import cache as cache_mod
        from bom_clima.api import detect_location

        conn = cache_mod.get_db()
        conn.execute(
            "INSERT INTO ip_cache (key, data, ts) VALUES ('current', 'garbage', ?)",
            (time.time(),),
        )
        conn.commit()
        conn.close()
        with patch("bom_clima.api._get", return_value=self._mock_http(self.PAYLOAD)) as mock_get:
            detect_location()
        assert mock_get.call_count == 1


class TestVerboseDebugGoesToStderr:
    """--verbose diagnostics must not corrupt a piped --line or -o -."""

    def test_debug_never_touches_stdout(self, mock_weather_response, capsys):
        from unittest.mock import patch

        from bom_clima.api import fetch_weather_data

        resp = MagicMock()
        resp.json.return_value = mock_weather_response
        with patch("bom_clima.api._get", return_value=resp):
            fetch_weather_data(1.0, 2.0, no_cache=True, verbose=True)
        captured = capsys.readouterr()
        assert "[debug]" in captured.err
        assert captured.out == ""

    def test_cache_hit_debug_also_stderr(self, mock_weather_response, capsys):
        from unittest.mock import patch

        from bom_clima.api import fetch_weather_data

        resp = MagicMock()
        resp.json.return_value = mock_weather_response
        with patch("bom_clima.api._get", return_value=resp):
            fetch_weather_data(3.0, 4.0)  # warm the cache
            capsys.readouterr()
            fetch_weather_data(3.0, 4.0, verbose=True)  # served from cache
        captured = capsys.readouterr()
        assert "cache hit" in captured.err
        assert captured.out == ""
