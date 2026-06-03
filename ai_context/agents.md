# Bom Clima — AI Agent Context

## Project Overview

**Bom Clima** is a cross-platform CLI weather application written in Python. It fetches weather data from the [Open-Meteo API](https://open-meteo.com/) and displays it in the terminal with rich formatting or plain text fallback.

- **Version**: 0.2.1
- **License**: GPL-2.0
- **Python**: >= 3.10
- **Author**: ninrod

## Tech Stack

| Category       | Technology                          |
|----------------|-------------------------------------|
| Language       | Python 3.10+                        |
| HTTP Client    | `requests` (>= 2.28.0)             |
| Terminal UI    | `rich` (>= 13.0.0) — optional      |
| Cache          | SQLite (stdlib)                     |
| Testing        | `pytest` (>= 7.0)                  |
| Linting        | `ruff` (>= 0.1.0)                  |
| Type Checking  | `mypy` (>= 1.0) + `types-requests`  |

## Project Structure

```
Bom-Clima/
├── bom-clima.py              # Backward-compatible entry point (delegates to bom_clima.cli:main)
├── bom_clima/                    # Main package
│   ├── __init__.py           # Package init, __version__ = "0.2.1"
│   ├── __main__.py           # python -m bom_clima entry point
│   ├── api.py                # HTTP client for Open-Meteo APIs
│   ├── cache.py              # SQLite-backed cache (geo + weather)
│   ├── cli.py                # Argument parsing, main() entry point
│   ├── config.py             # Persistent JSON config management
│   ├── constants.py          # URLs, WMO codes, compass, file paths
│   ├── display.py            # Rich/plain text rendering
│   ├── formatters.py         # Export (JSON/CSV/YAML/XML), formatting helpers
│   ├── history.py            # Query history (JSON file)
│   ├── i18n.py               # Internationalization engine
│   └── locales/              # Translation files
│       ├── en.json
│       ├── pt.json
│       └── es.json
├── tests/
│   └── test_bom_clima.py     # 100 unit tests
├── pyproject.toml            # Project metadata, tool config
├── requirements.txt          # Runtime dependencies
├── .gitignore
├── LICENSE
└── README.md
```

## Module Reference

### `cli.py` — CLI Entry Point (427 lines)

The main orchestrator. Handles argument parsing, config loading, and dispatches to the appropriate mode.

**Key functions:**
- `build_parser()` → `argparse.ArgumentParser` — Constructs CLI argument parser
- `main()` — Entry point: parses args, loads config, dispatches to single/compare/watch/detect mode
- `watch_mode(cidade, cfg, interval, args)` — Auto-refresh loop with dynamic intervals
- `apply_config_overrides(cfg, args)` — Merges CLI flags into config dict
- `_calc_dynamic_interval(dados, base_interval)` — Adjusts watch interval based on rain probability
- `_fetch_and_display(city, cfg, args)` — Fetches weather data for a single city
- `_export_city_data(dados, nome, export_fmt, output)` — Export with unique filenames for multi-city

**CLI argument groups:**
- **Search**: `city`, `--detect`, `--compare`
- **Display**: `--days`, `--hours`, `--alerts`, `--aqi`, `--imperial`, `--no-color`
- **Modes**: `--watch SEC`, `--history`, `--no-cache`, `--verbose`
- **Smart**: `--best-day`, `--vs-yesterday`
- **Export**: `--export FMT`, `--output FILE`
- **Config**: `--lang`, `--config-set K=V`, `--config-show`
- **Info**: `--help`, `--version`

### `api.py` — API Client (151 lines)

HTTP client for Open-Meteo geocoding, weather, air quality, and alerts APIs.

**Key functions:**
- `detect_location() → dict | None` — IP-based geolocation via ipapi.co
- `search_city(nome, no_cache=False) → dict` — Geocoding via Open-Meteo, with cache
- `fetch_weather_data(lat, lon, ...) → dict` — Main weather fetch (current + daily + hourly)

**API parameters sent:**
- `current`: temperature_2m, relative_humidity_2m, apparent_temperature, precipitation, rain, wind_speed_10m, wind_direction_10m, wind_gusts_10m, weather_code, uv_index, pressure_msl, visibility, dew_point_2m, cloud_cover
- `daily`: temperature_2m_max/min, sunrise, sunset, daylight_duration, precipitation_probability_max, precipitation_sum, precipitation_hours, weather_code, wind_speed_10m_max, wind_direction_10m_dominant, sunshine_duration, uv_index_max
- `hourly`: temperature_2m, apparent_temperature, rain, relative_humidity_2m, precipitation_probability, wind_speed_10m, cloud_cover, weather_code, uv_index, is_day, cape

### `cache.py` — SQLite Cache (94 lines)

Two tables: `geo_cache` and `weather_cache`. Each row has `query/key`, `data` (JSON), and `ts` (timestamp).

**TTL values (from constants.py):**
- `CACHE_TTL_GEO` = 604800 seconds (7 days)
- `CACHE_TTL_WEATHER` = 1800 seconds (30 minutes)

**Key functions:**
- `cache_get_geo(query) / cache_set_geo(query, data)`
- `cache_get_weather(key) / cache_set_weather(key, data)`
- `cache_cleanup()` — Removes expired entries

### `config.py` — Configuration (31 lines)

Manages persistent config at `~/.config/bom-clima/config.json`.

**Default config:**
```python
DEFAULT_CONFIG = {
    "unit_system": "metric",    # "metric" | "imperial"
    "city_default": None,       # str | None
    "forecast_days": 5,         # 1-15
    "forecast_hours": 6,        # int
    "color": True,              # bool
    "history_limit": 50,        # int
    "lang": None,               # "pt" | "en" | "es" | None (auto-detect)
}
```

**Valid config keys** (enforced in `cli.py`):
`unit_system`, `city_default`, `forecast_days`, `forecast_hours`, `color`, `history_limit`, `lang`

### `constants.py` — Constants (103 lines)

All static data lives here:

- **API URLs**: `BASE_URL_GEO`, `BASE_URL_WEATHER`, `BASE_URL_AIR`, `BASE_URL_ALERTS`, `IP_API_URL`
- **WMO_CODES**: Dict mapping WMO weather codes → `{pt: (desc, icon), en: ..., es: ...}` (30 codes)
- **COMPASS**: 16-point compass directions (N, NNE, NE, ... NNO)
- **WIND_ARROWS**: Unicode arrow symbols per compass point (↑, ↗, →, ↘, ↓, ↙, ←, ↖)
- **AQI_LABELS**: Air quality labels per language (Good → Very Poor)
- **WEEKDAYS**: Short weekday names per language
- **File paths**: `APP_DIR`, `CONFIG_FILE`, `CACHE_FILE`, `HISTORY_FILE`, `LANG_FILE`
- **ensure_app_dir()** — Creates the app directory (called once from `main()`, avoids module-level side effects)
- **DEWPOINT_COMFORT** — Dew point comfort thresholds per language
- **EXTREME_*** — Thresholds for extreme weather detection (heat >35°C, cold <0°C, wind >50km/h, rain >30mm, UV >8, CAPE >1500)
- **DAY_SCORE_IDEAL_TEMP** — Ideal temperature (22°C) for day scoring

### `display.py` — Display Rendering (373 lines)

Handles both Rich and plain text output. Auto-detects Rich availability.

**Visual features:**
- Temperature color coding via `_temp_color(val, unit_sym)` — blue (<10°C), cyan (10-18°C), green (18-28°C), yellow (28-35°C), red (>35°C)
- Rain probability color coding via `_rain_color(val)` — green (<20%), yellow (20-60%), red (>60%)
- Temperature bar via `_build_temp_bar(temp, t_min, t_max, unit_sym)` — shows current position between daily min/max
- Unicode wind direction arrows (↑, ↗, →, ↘, ↓, ↙, ←, ↖) — from `formatters.wind_arrow()`
- Alternating row styles (`row_styles = ["", "dim"]`) in Rich tables
- Section separators (empty lines) between logical groups in weather block

**Key functions:**
- `r_print(text)` — Print with Rich or fallback to print()
- `r_rule(title)` — Horizontal rule separator
- `r_panel(content, title)` — Panel/box display
- `r_table(headers, rows, title)` — Table display
- `format_weather_block(nome, dados, cfg, city_info)` → str — Builds the main weather info block
- `display_weather(nome, dados, cfg, ...)` — Renders full weather output (panel + hourly + forecast + alerts)
- `display_comparison(cidades_dados)` — Side-by-side city comparison using Rich Columns

**Rich availability**: Checked via `HAS_RICH` global. If `rich` is not installed, all display functions fall back to plain text.

### `formatters.py` — Formatters & Export (385 lines)

Data formatting and export utilities.

**Key functions:**
- `wind_direction(degrees) → str` — Converts degrees to compass direction
- `wind_arrow(degrees) → str` — Returns Unicode arrow for wind direction (↑, ↗, →, ↘, ↓, ↙, ←, ↖)
- `format_duration(segundos) → str` — Seconds → "Xh Ymin"
- `format_timestamp(timestamp) → str` — ISO timestamp → "HH:MM"
- `format_time_remaining(timestamp) → str` — Time until/since event
- `get_weekday_name(dt, lang) → str` — Localized weekday abbreviation
- `get_wmo(code, lang) → tuple[str, str]` — WMO code → (description, emoji)
- `get_aqi_label(aqi, lang) → str` — AQI value → quality label
- `get_moon_phase(date) → int` — Returns 0-3 (New, Waxing, Full, Waning)
- `display_width(text) → int` — Calculates display width (handles emoji)
- `export_data(dados, nome, fmt, output)` — Exports to JSON/CSV/YAML/XML
- `export_all_formats(dados, nome, export_str, output)` — Exports to multiple formats
- `dewpoint_comfort(dp, lang) → str` — Classifies dew point as dry/comfortable/muggy/oppressive
- `generate_recommendations(dados, cfg) → list[str]` — Smart clothing/activity advice based on weather
- `detect_extremes(dados) → list[str]` — Flags heat waves, cold snaps, storms, extreme wind/rain/UV
- `rain_window_summary(dados) → list[str]` — Lists upcoming rain hours in the next 24h
- `score_days(dados) → list[tuple[str, float]]` — Scores each forecast day (0-100) for outdoor activities

### `history.py` — Query History (35 lines)

Simple JSON-based history at `~/.local/share/bom-clima/history.json`.

**Key functions:**
- `load_history() → list[dict]` — Load history from file
- `save_history(history, limit)` — Save with configurable limit
- `add_history(city, lat, lon)` — Append new entry with timestamp

### `i18n.py` — Internationalization (105 lines)

Loads translations from `bom_clima/locales/{lang}.json` files.

**Language detection order:**
1. `~/.config/bom-clima/lang` file (persisted via `--lang` flag)
2. `$LANG` environment variable
3. `locale.getlocale()` system locale
4. Windows `GetUserDefaultUILanguage()` API
5. Fallback: `"en"`

**Key functions:**
- `t(key) → str` — Get translated string for current language
- `_current_lang() → str` — Detect/cache current language
- `set_lang(lang)` — Persist language choice
- `reset_lang_cache()` — Clear cached language (used in tests)

**Supported languages**: `en`, `pt`, `es`

## Data Flow

```
User runs: bom-clima "sao paulo" --aqi --days 7

1. cli.main()
   ├── ensure_app_dir() → mkdir ~/.config/bom-clima/, ~/.cache/bom-clima/, ~/.local/share/bom-clima/
   ├── build_parser() → parse args
   ├── load_config() + apply_config_overrides()
   ├── cities = ["sao paulo"]
   └── _fetch_and_display("sao paulo", cfg, args)
       ├── search_city("sao paulo")
       │   ├── cache_get_geo("sao paulo") → cache hit? return cached
       │   └── requests.get(BASE_URL_GEO) → Open-Meteo Geocoding API
       │       └── cache_set_geo("sao paulo", result)
       ├── fetch_weather_data(lat, lon, unit_system, include_aqi, forecast_days)
       │   ├── cache_get_weather(key) → cache hit? return cached
       │   ├── requests.get(BASE_URL_WEATHER) → Open-Meteo Forecast API
       │   ├── requests.get(BASE_URL_AIR) → Open-Meteo Air Quality API
       │   └── cache_set_weather(key, result)
       └── display_weather(nome, dados, cfg, city_info)
           ├── format_weather_block() → Rich Panel
           ├── hourly forecast table
           ├── daily forecast table
           └── alerts (if any)
```

## API Endpoints

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Geocoding | `https://geocoding-api.open-meteo.com/v1/search` | City name → lat/lon |
| Forecast | `https://api.open-meteo.com/v1/forecast` | Current + daily + hourly weather |
| Air Quality | `https://air-quality-api.open-meteo.com/v1/air-quality` | PM2.5, US AQI |
| Alerts | `https://api.open-meteo.com/v1/warnings` | Severe weather warnings |
| IP Location | `https://ipapi.co/json/` | Auto-detect user location |

## File Locations

All app data follows the XDG Base Directory Specification:

| File | Path | Purpose |
|------|------|---------|
| `config.json` | `~/.config/bom-clima/` | Persistent configuration |
| `lang` | `~/.config/bom-clima/` | Language preference |
| `cache.db` | `~/.cache/bom-clima/` | SQLite cache (geo + weather) |
| `history.json` | `~/.local/share/bom-clima/` | Query history |

## Testing

**Location**: `tests/test_bom_clima.py` (781 lines, 100 tests)

**Test classes:**
- `TestWindDirection` — Compass direction conversion
- `TestWmoCodes` — WMO weather code lookups
- `TestFormatting` — Duration, timestamp, icon formatting
- `TestApiCalls` — Mocked API calls (geo, detect)
- `TestExport` — JSON/CSV/YAML/XML export
- `TestConfig` — Config loading, overrides, validation
- `TestMoonPhase` — Moon phase calculation
- `TestCache` — SQLite cache roundtrip
- `TestFormatWeatherBlock` — Weather block rendering
- `TestI18n` — Language detection, translations
- `TestCityParsing` — Comma/space separated city parsing
- `TestCLIArguments` — Argument parsing
- `TestDisplayWidth` — Unicode display width
- `TestDocumentsDir` — Documents directory detection
- `TestCalcDynamicInterval` — Dynamic watch interval logic
- `TestValidatePositive` — Input validation
- `TestGetAqiLabel` — AQI classification
- `TestGetWeekdayName` — Weekday translation
- `TestFormatTimeRemaining` — Time remaining display
- `TestAddHistory` — History write operations
- `TestExportAllFormats` — Multi-format export orchestration
- `TestDisplayWeather` — Main weather display
- `TestDisplayComparison` — City comparison display
- `TestDewpointComfort` — Dewpoint comfort classification
- `TestGenerateRecommendations` — Smart recommendation logic
- `TestDetectExtremes` — Extreme weather detection
- `TestRainWindowSummary` — Rain scheduling analysis
- `TestScoreDays` — Day scoring for outdoor activities

**Key fixtures:**
- `mock_lang_for_tests` (autouse) — Forces English locale
- `mock_geo_response` — Fake geocoding response
- `mock_weather_response` — Fake weather data
- `mock_weather_with_aqi` — Fake weather + air quality data

**Run tests:**
```bash
python -m pytest tests/test_bom_clima.py -v
```

## Development Commands

```bash
# Run tests
python -m pytest tests/test_bom_clima.py -v

# Lint
ruff check bom_clima/ tests/

# Type check
mypy bom_clima/

# Run the app
python bom-clima.py sao paulo
```

## Code Conventions

- **Line length**: 110 characters (ruff config)
- **Target version**: Python 3.10
- **Type hints**: Required for all function definitions (`disallow_untyped_defs = true`)
- **Lint rules**: E, F, W, I, N, UP, B, SIM, RUF (ignores E501 line length)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Imports**: Relative imports within package (e.g., `from .constants import ...`)
- **Error handling**: `ValueError` for user-facing errors, `requests.RequestException` for API errors
- **Translations**: All user-facing strings go through `t(key)` function
- **Rich fallback**: All display functions check `HAS_RICH` and fall back to plain text
- **Cache keys**: Weather cache uses `"{lat:.4f}_{lon:.4f}_{unit_system}_{include_aqi}_{forecast_days}"`
- **Type annotations**: `json.loads()` returns require explicit `dict` or `list[dict]` type annotations to satisfy mypy
