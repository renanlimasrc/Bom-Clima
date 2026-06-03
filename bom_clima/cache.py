"""Cache module for Bom Clima — SQLite-backed geocoding and weather cache."""

import json
import sqlite3
import time

from .constants import CACHE_FILE, CACHE_TTL_GEO, CACHE_TTL_WEATHER, ensure_app_dir


def get_db() -> sqlite3.Connection:
    ensure_app_dir()
    conn = sqlite3.connect(str(CACHE_FILE))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS geo_cache (
            query TEXT PRIMARY KEY, data TEXT, ts REAL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS weather_cache (
            key TEXT PRIMARY KEY, data TEXT, ts REAL
        )"""
    )
    conn.commit()
    return conn


def cache_get_geo(query: str) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT data, ts FROM geo_cache WHERE query = ?", (query,)
        ).fetchone()
        if row and (time.time() - row[1]) < CACHE_TTL_GEO:
            result: dict = json.loads(row[0])
            return result
        return None
    finally:
        conn.close()


def cache_set_geo(query: str, data: dict) -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO geo_cache (query, data, ts) VALUES (?, ?, ?)",
            (query, json.dumps(data), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def cache_get_weather(key: str) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT data, ts FROM weather_cache WHERE key = ?", (key,)
        ).fetchone()
        if row and (time.time() - row[1]) < CACHE_TTL_WEATHER:
            result: dict = json.loads(row[0])
            return result
        return None
    finally:
        conn.close()


def cache_set_weather(key: str, data: dict) -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO weather_cache (key, data, ts) VALUES (?, ?, ?)",
            (key, json.dumps(data), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def cache_cleanup() -> int:
    removed = 0
    conn = get_db()
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
    finally:
        conn.close()
    return removed
