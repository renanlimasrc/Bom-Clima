#
# test_cache.py - Tests for Bom Clima
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


import sqlite3
from unittest.mock import patch

from bom_clima.cache import (
    cache_cleanup,
    cache_get_geo,
    cache_get_weather,
    cache_set_geo,
    cache_set_weather,
)


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


class TestCacheRegressions:
    def test_corrupt_and_future_rows_are_misses(self, tmp_path):
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


class TestIpCache:
    """--detect IP geolocation is cached for 10 minutes."""

    def test_roundtrip(self, tmp_path):
        from bom_clima.cache import cache_get_ip, cache_set_ip

        assert cache_get_ip() is None
        cache_set_ip({"lat": -23.5, "lon": -46.6, "city": "Sao Paulo", "country": "Brazil"})
        assert cache_get_ip() == {"lat": -23.5, "lon": -46.6, "city": "Sao Paulo", "country": "Brazil"}

    def test_expired_entry_is_a_miss(self, tmp_path):
        import sqlite3
        import time

        from bom_clima import cache as cache_mod
        from bom_clima.cache import cache_get_ip

        cache_mod.cache_set_ip({"lat": 1.0, "lon": 2.0, "city": "x", "country": "y"})
        with sqlite3.connect(str(cache_mod.CACHE_FILE)) as conn:
            conn.execute("UPDATE ip_cache SET ts = ?", (time.time() - 700,))
        assert cache_get_ip() is None

    def test_corrupt_row_is_a_miss(self, tmp_path):
        import time

        from bom_clima import cache as cache_mod
        from bom_clima.cache import cache_get_ip

        conn = cache_mod.get_db()
        conn.execute(
            "INSERT INTO ip_cache (key, data, ts) VALUES ('current', 'not json', ?)",
            (time.time(),),
        )
        conn.commit()
        conn.close()
        assert cache_get_ip() is None

    def test_cleanup_runs_once_per_process_per_path(self, tmp_path):
        import sqlite3
        import time

        from bom_clima import cache as cache_mod
        from bom_clima.cache import cache_cleanup, cache_set_geo

        cache_set_geo("k", {"results": []})
        cache_cleanup()  # first pass runs (and marks the path done)
        # An entry expired *after* the first cleanup must survive the second
        # call in the same process: cleanup is once-per-process now.
        with sqlite3.connect(str(cache_mod.CACHE_FILE)) as conn:
            conn.execute("UPDATE geo_cache SET ts = ?", (time.time() - 700 * 86400,))
        assert cache_cleanup() == 0
        with sqlite3.connect(str(cache_mod.CACHE_FILE)) as conn:
            rows = conn.execute("SELECT COUNT(*) FROM geo_cache").fetchone()[0]
        assert rows == 1
