"""Cache module for Bom Clima — SQLite-backed geocoding and weather cache.

The cache is strictly an optimisation. A read-only or full disk must never cost
the user a forecast that was fetched successfully, so every failure mode here
degrades to a miss instead of propagating.
"""

import json
import sqlite3
import time

from .constants import CACHE_FILE, CACHE_TTL_GEO, CACHE_TTL_WEATHER, ensure_app_dir


def get_db() -> sqlite3.Connection | None:
    ensure_app_dir()
    try:
        conn = sqlite3.connect(str(CACHE_FILE))
        conn.execute(
            """CREATE TABLE IF NOT EXISTS geo_cache (
                query TEXT PRIMARY KEY, data TEXT NOT NULL, ts REAL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS weather_cache (
                key TEXT PRIMARY KEY, data TEXT NOT NULL, ts REAL
            )"""
        )
        conn.commit()
        return conn
    except sqlite3.Error:
        return None


def _read_row(row: tuple | None, ttl: float) -> dict | None:
    """Decode a cache row, honouring its TTL. Returns None on any problem."""
    if row is None:
        return None
    data, ts = row
    # ts is nullable in databases created by older versions, and data can hold
    # anything if the file was tampered with. Both used to raise TypeError here,
    # which the callers (catching only sqlite3.Error) did not handle.
    if not isinstance(ts, (int, float)):
        return None
    # The lower bound matters: a timestamp in the future (clock skew, NTP step,
    # shared cache) would otherwise make an arbitrarily old entry look fresh.
    if not 0 <= time.time() - ts < ttl:
        return None
    try:
        result: dict = json.loads(data)
    except (TypeError, ValueError):
        return None
    if not isinstance(result, dict):
        return None
    return result


def cache_get_geo(query: str) -> dict | None:
    conn = get_db()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT data, ts FROM geo_cache WHERE query = ?", (query,)
        ).fetchone()
        return _read_row(row, CACHE_TTL_GEO)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def cache_set_geo(query: str, data: dict) -> None:
    conn = get_db()
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT OR REPLACE INTO geo_cache (query, data, ts) VALUES (?, ?, ?)",
            (query, json.dumps(data), time.time()),
        )
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def cache_get_weather(key: str) -> dict | None:
    conn = get_db()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT data, ts FROM weather_cache WHERE key = ?", (key,)
        ).fetchone()
        return _read_row(row, CACHE_TTL_WEATHER)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def cache_set_weather(key: str, data: dict) -> None:
    conn = get_db()
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT OR REPLACE INTO weather_cache (key, data, ts) VALUES (?, ?, ?)",
            (key, json.dumps(data), time.time()),
        )
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def cache_cleanup() -> int:
    removed = 0
    conn = get_db()
    if conn is None:
        return 0
    try:
        now = time.time()
        cur = conn.execute(
            "DELETE FROM geo_cache WHERE ts < ?", (now - CACHE_TTL_GEO,)
        )
        removed += cur.rowcount
        cur = conn.execute(
            "DELETE FROM weather_cache WHERE ts < ?", (now - CACHE_TTL_WEATHER,)
        )
        removed += cur.rowcount
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return removed
