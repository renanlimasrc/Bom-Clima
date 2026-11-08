# Bom Clima — AI Agent Context

## Project Overview

**Bom Clima** is a cross-platform CLI weather application written in Python. It fetches
weather data from the [Open-Meteo API](https://open-meteo.com/) and displays it in the
terminal with rich formatting or a plain/monochrome fallback.

- **License**: GPL-2.0-or-later (see `LICENSE`; source headers say "v2 or later")
- **Python**: >= 3.10
- **Author**: ninrod

## Tech Stack

| Category       | Technology                          |
|----------------|-------------------------------------|
| Language       | Python 3.10+                        |
| HTTP Client    | `requests` (>= 2.28.0)              |
| Terminal UI    | `rich` (>= 13.0.0) — optional       |
| Cache          | SQLite (stdlib)                     |
| Testing        | `pytest` (>= 7.0)                   |
| Linting        | `ruff` (>= 0.1.0)                   |
| Type Checking  | `mypy` (>= 1.0) + `types-requests`  |
| Packaging      | `hatchling` (dynamic version)       |

## Project Structure

```
Bom-Clima/
├── bom-clima.py              # Backward-compatible entry shim → bom_clima.cli:main
├── bom_clima/                # Main package
│   ├── __init__.py           # Package init; __version__ (single source of truth)
│   ├── __main__.py           # python -m bom_clima entry shim
│   ├── api.py                # HTTP client: retry, geocoding, weather, AQI, IP detect
│   ├── cache.py              # SQLite caches (geo, weather, ip) — degrades to miss
│   ├── cli.py                # Argument parsing, main(), --help renderer
│   ├── config.py             # Persistent JSON config (~/.config/bom-clima)
│   ├── constants.py          # URLs, WMO codes, compass, XDG paths, TTLs
│   ├── display.py            # Rich/plain rendering of cards, tables, panels
│   ├── formatters.py         # Formatting helpers + JSON/CSV/YAML/XML export
│   ├── history.py            # Query history (JSON, atomic writes)
│   ├── i18n.py               # Translations (en/pt/es), locale detection
│   ├── types.py              # TypedDicts for the API boundary (CityCandidate, …)
│   └── locales/              # en.json, pt.json, es.json
├── tests/                    # Pytest suite, one file per module under test
│   ├── conftest.py           # Shared fixtures (autouse: English locale, isolated state)
│   ├── test_api.py           # incl. detect_location IP cache
│   ├── test_cache.py         # incl. once-per-process cleanup
│   ├── test_cli.py           # parser, --help, output paths, pairwise combinations
│   ├── test_completions.py   # anti-drift guard for completions/
│   ├── test_config.py
│   ├── test_display.py
│   ├── test_export.py        # incl. YAML/XML round-trip (PyYAML, optional)
│   ├── test_formatters.py
│   ├── test_history.py
│   └── test_i18n.py          # locale parity + referenced-keys scan
├── completions/              # bash / zsh / fish completions (static, anti-drift test)
├── scripts/package-arch.sh   # Arch Linux packaging
├── pyproject.toml            # Metadata, tool configs; version is dynamic (hatch)
├── CHANGELOG.md
└── README.md
```

There is no CI by deliberate decision — keep `pytest`, `ruff check bom_clima/ tests/` and
`mypy bom_clima/` green locally instead.

## Key Design Points

### Fetching & caching

- `api._get()` retries transient failures (connection errors, timeouts, 5xx) with
  exponential backoff (0.5s base ×4 attempts); other errors fail immediately.
- `search_cities()` geocodes and returns every candidate; `search_city()` takes the
  first. Ambiguous queries print a one-line refine hint to **stderr** (never stdout),
  then take the first candidate. Geocoding results are cached for 7 days, keyed by
  language + query (the API localises place names).
- `fetch_weather_data()` returns a `WeatherResponse` (TypedDict); internally blocks
  stay `dict[str, Any]`. HTTP-200-with-`{"error": …}` bodies are rejected before display.
  Weather cache TTL is 30 minutes; an incomplete response (AQI outage) is **not** cached.
- `detect_location()` (--detect) caches the IP geolocation for 10 minutes (`ip_cache`)
  and is bypassed by `--no-cache`.
- Cache cleanup runs once per process per cache path (module-level flag); schema is
  created once per process as well, guarded by a lock for the multi-threaded fetch path.
- Multi-city and `--compare` fetch in parallel via `ThreadPoolExecutor` (max 8 workers),
  preserving command-line order for display and history; failures are reported per city,
  and one bad city doesn't sink the rest.

### Output paths

- `--line` prints one compact line (statusline/prompt). `-o -` streams the export to
  stdout. In both cases cards are suppressed and stdout stays machine-clean;
  human notes (detect label, ambiguity hint, `--verbose` debug, clamp warnings) go to
  **stderr**.
- `--help` is derived from `build_parser()` itself (single source of truth);
  `tests/test_help_output`-style tests guarantee every flag appears in it.
- Rich is optional; with colors disabled the cards render fully monochrome.

### Configuration

- `~/.config/bom-clima/config.json` — `unit_system`, `city_default`, `forecast_days`,
  `forecast_hours`, `color`, `history_limit`, `lang`. Values are sanitised at the
  boundary (`_sanitize`), and `--config-set` validates types/ranges
  (`_coerce_config_value`) before persisting.
- `--lang` applies to the current run only; only `--config-set lang=…` persists it.
  Language resolution: `--lang` flag > config `lang` > LANG file > LC_ALL/LC_MESSAGES/
  LANGUAGE/LANG > system locale > Windows API > English.
- `--days` above `MAX_FORECAST_DAYS` (15) is clamped with a **stderr warning**
  (`days_clamped` in the locales).

### i18n

- All user-facing strings go through `t(key)`. `t()` falls back to returning the key,
  so missing keys are caught by tests, not by users:
  - `tests/test_i18n.py::TestReferencedKeysExistInEveryLocale` scans every `t("…")` in
    the package and requires the key in all three locales.
  - A parity test requires identical key sets in `en/pt/es`.

### Versioning & packaging

- Version lives **only** in `bom_clima/__init__.py` (`__version__`); hatchling reads it
  (`[tool.hatch.version]`). README's badge reads the GitHub release.
- PEP 639 metadata: `license = "GPL-2.0-or-later"`, `license-files = ["LICENSE"]`.
- There is no `requirements.txt` — dependencies live in `pyproject.toml` (`pip install -e ".[dev]"`).
- Dev extras include `pyyaml` (export round-trip tests) and `build`.
- Wheels ship `bom_clima/locales/*.json` (package data); verify with `python -m build`.

## Development Commands

```bash
python -m pytest tests/ -q          # full suite
ruff check bom_clima/ tests/        # lint
mypy bom_clima/                     # type check
python -m build                     # build sdist+wheel (needs `build`)
python bom-clima.py sao paulo       # run the app
```

## Release

1. Bump `__version__` in `bom_clima/__init__.py` (the single source of truth —
   hatchling reads it via `[tool.hatch.version]`).
2. In `CHANGELOG.md`, rename `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and add a
   fresh empty `[Unreleased]` above it.
3. Keep `pytest`, `ruff`, `mypy` green — `tests/test_release.py` fails if the
   changelog or packaging drift from `__version__`.
4. `rm -rf dist && python -m build` — verify the wheel ships `locales/` and `LICENSE`.
5. Commit everything, tag `vX.Y.Z`, push the commit and the tag, then
   `gh release create vX.Y.Z dist/*` with the changelog section as notes.

## Code Conventions

- **Line length**: 110 characters (ruff config)
- **Type hints**: Required for all function definitions (`disallow_untyped_defs = true`)
- **Imports**: Relative within the package
- **Errors**: `ValueError` for user-facing errors; API failures → `ValueError(t(…))`
- **`json.loads()`**: explicit `dict`/`list[dict]` annotations for mypy
- **New locale keys**: add to `en/pt/es` together; the referenced-keys test enforces it
- **Tests**: one file per module (`test_<module>.py`); fixtures in `conftest.py`
  (English locale autouse, isolated XDG paths via tmp_path)
- **Rich fallback**: every display function must degrade gracefully without rich
  and with colors disabled
- **Cache**: never propagate cache errors to the user; degrade to a miss
- **Do not commit** unless asked; keep `git status` clean of scratch files

## File Locations

| File | Path | Purpose |
|------|------|---------|
| `config.json` | `~/.config/bom-clima/` | Persistent configuration |
| `lang` | `~/.config/bom-clima/` | Language preference (via `--config-set lang=`) |
| `cache.db` | `~/.cache/bom-clima/` | SQLite caches (geo, weather, ip) |
| `history.json` | `~/.local/share/bom-clima/` | Query history |
