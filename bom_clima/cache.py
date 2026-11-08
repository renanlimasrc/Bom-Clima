"""Cache module for Bom Clima — SQLite-backed geocoding and weather cache.

The cache is strictly an optimisation. A read-only or full disk must never cost
the user a forecast that was fetched successfully, so every failure mode here
degrades to a miss instead of propagating.
"""

import json
import sqlite3
import threading
import time

from .constants import CACHE_FILE, CACHE_TTL_GEO, CACHE_TTL_IP, CACHE_TTL_WEATHER, ensure_app_dir

# CREATE TABLE is idempotent but not free, and cache_cleanup() used to scan both
# tables on every single invocation. Keying the "already done" flags on the
# cache path keeps tests that patch CACHE_FILE per-test correct while skipping
# the work for the rest of the process. The lock keeps two fetch threads from
# racing the first schema creation.
_SCHEMA_LOCK = threading.Lock()
_schema_ready_for: str | None = None
_cleanup_done_for: str | None = None

_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS geo_cache (
        query TEXT PRIMARY KEY, data TEXT NOT NULL, ts REAL
    )""",
    """CREATE TABLE IF NOT EXISTS weather_cache (
        key TEXT PRIMARY KEY, data TEXT NOT NULL, ts REAL
    )""",
    """CREATE TABLE IF NOT EXISTS ip_cache (
        key TEXT PRIMARY KEY, data TEXT NOT NULL, ts REAL
    )""",
)


def get_db() -> sqlite3.Connection | None:
    global _schema_ready_for
    ensure_app_dir()
    cache_path = str(CACHE_FILE)
    try:
        conn = sqlite3.connect(cache_path)
    except sqlite3.Error:
        return None
    try:
        if _schema_ready_for == cache_path:
            return conn
        with _SCHEMA_LOCK:
            if _schema_ready_for == cache_path:
                return conn
            for statement in _SCHEMA_STATEMENTS:
                conn.execute(statement)
            conn.commit()
            _schema_ready_for = cache_path
        return conn
    except sqlite3.Error:
        conn.close()
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


def cache_get_ip() -> dict | None:
    conn = get_db()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT data, ts FROM ip_cache WHERE key = 'current'"
        ).fetchone()
        return _read_row(row, CACHE_TTL_IP)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def cache_set_ip(data: dict) -> None:
    conn = get_db()
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ip_cache (key, data, ts) VALUES ('current', ?, ?)",
            (json.dumps(data), time.time()),
        )
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def cache_cleanup() -> int:
    global _cleanup_done_for
    cache_path = str(CACHE_FILE)
    if _cleanup_done_for == cache_path:
        # Once per process: main() called this on every invocation and the
        # DELETE scans added up for no benefit within a single run.
        return 0
    removed = 0
    conn = get_db()
    if conn is None:
        _cleanup_done_for = cache_path
        return 0
    failed = False
    try:
        now = time.time()
        for table, ttl in (
            ("geo_cache", CACHE_TTL_GEO),
            ("weather_cache", CACHE_TTL_WEATHER),
            ("ip_cache", CACHE_TTL_IP),
        ):
            cur = conn.execute(f"DELETE FROM {table} WHERE ts < ?", (now - ttl,))
            removed += cur.rowcount
        conn.commit()
    except sqlite3.Error:
        failed = True
    finally:
        conn.close()
    if not failed:
        # Keep the flag unset on error so the next invocation retries.
        _cleanup_done_for = cache_path
    return removed
