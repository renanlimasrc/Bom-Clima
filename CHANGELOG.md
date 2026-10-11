# Changelog

All notable changes to Bom Clima will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.1] - 2026-10-10

### Fixed
- `--help` printed the bare translation keys `help_config_set` and
  `help_config_show` in the CONFIGURATION group: both keys had been deleted
  from the locale files while `build_parser()` still asked for them, and `t()`
  falls back to returning the key itself rather than raising.
- An invalid `--export` format no longer writes its error to stdout on the
  `-o -` path. `bom-clima sp -e json,pdf -o - | jq` produced a valid payload
  followed by "Invalid format: pdf" and left jq with unparseable input; the
  message now goes to stderr, like every other human-facing note on that path.
- `--line` no longer prints nothing at all when the payload has no `current`
  block. It explains itself on stderr and falls back to the full card.
- A degraded `current` block no longer crashes the card. Open-Meteo can answer
  HTTP 200 with `current` absent, empty or `null`, and its cells are
  individually nullable; `format_weather_block()` raised `KeyError`,
  `TypeError` or `AttributeError` on every one of those. Rows without a reading
  are now omitted instead of defaulting, and — importantly — the WMO
  description, the rain figure and the min/max bar marker are omitted rather
  than falling back to 0, which would have claimed "Clear sky" and "no rain"
  for a city with no observation at all. The hourly table cuts at wall-clock
  time when the payload carries no reference instant.
- A degraded `daily` block no longer crashes the card either. `daily` absent,
  empty, `null` or short of a series raised `KeyError`/`AttributeError` on the
  direct `diario[...][idx]` reads; those rows are now omitted via `_at()`, and
  the min/max rows and bar marker go with them instead of rendering a
  fabricated "0.0°C". The forecast/hourly tables skip unparseable timestamps
  and degrade parallel-array cells to 0 rather than raising, and every
  `dados.get("daily"/"hourly", {})` became `or {}` so an explicit `null` cannot
  crash `today_index()` and friends the way it already could not for `current`.
- `--lang` no longer writes `~/.config/bom-clima/lang`. A one-off
  `bom-clima sp --lang en` used to persist the choice, and the file it wrote
  outranked `$LANG`, so the desktop locale stayed overridden for every later
  run — a `--lang` for a single command silently became permanent. Only an
  explicit `--config-set lang=` persists now, which is what the flag documents
  itself as doing.
- The city-disambiguation note no longer repeats the card: the
  "Multiple matches… / Other matches…" preamble is gone and only the refine
  hint remains, on one line, in the user's language.

### Removed
- `city_ambiguous` and `city_alternatives` translation keys (`en`, `pt`, `es`),
  along with the alternatives list they formatted.

## [0.4.0] - 2026-10-10

### Added
- `--line` prints one compact line (`Curitiba: 🌧️ 18.9°C`) instead of the
  cards, sized for a tmux/i3status bar or a shell prompt. Composes with
  `--compare`, multi-city queries and `--detect`.
- `-o -` streams the export to stdout instead of writing a file, following the
  convention curl/jq/pip use: `bom-clima sao paulo -e json -o - | jq`. Nothing
  else may reach stdout on that path — the cards are suppressed, and the
  "Data exported to" confirmation and the city-disambiguation note go to stderr,
  so `jq` reads the payload and nothing else. `-e` without `-o` still writes to
  `~/Documents/<city>.<fmt>`.

### Changed
- `--help` now derives its option list from the argument parser instead of
  repeating all ~27 options by hand. Adding a flag no longer needs two edits —
  the hand-written copy had already drifted into a broken column and a mid-word
  line wrap. The panel, the group icons and the examples are unchanged.
- City disambiguation notes and the `--detect` location line now go to stderr.
  They were already on stderr in the first case, but a note on stdout corrupted
  exactly what `--line` and `-o -` exist to hand to a pipe.
- The daily forecast ceiling is a single constant, `MAX_FORECAST_DAYS`, instead
  of `15` spelled out in the CLI, the config sanitiser and the API client — and
  `16` in the API client, which disagreed with the other three.
- The tests import at the top of the file like the rest of the module.

### Fixed
- The `--export` help row printed the format list twice, appending
  `(json, csv, yaml, xml)` to a translation that already named them.
- Short flags are listed before long ones in `--help`; argparse preserved the
  declaration order, which rendered `-V` as `--verbose, -V`.
- `-o -` with several cities no longer builds a literal `-_Sao_Paulo.json`
  file: `os.path.splitext("-")` used to run before the stdout target was
  recognised.
- `--line` and `-o -` no longer crash on a `null` temperature cell, which
  Open-Meteo sends for readings it has no sensor for.

### Removed
- 25 duplicated `help_*` translation keys (`en`, `pt`, `es`) that only the
  hand-written help copy read. 169 keys per locale became 148.

## [0.3.1] - 2026-10-10

### Changed
- City disambiguation no longer prompts: the first (most populous) candidate
  always wins, and ambiguous queries print the alternatives with their states
  plus a refine hint (city + state, comma-separated) on stderr. Prompting kept
  surfacing phantom GeoNames micro-localities (e.g. a population-less
  "Guarulhos" in Rio de Janeiro).

## [0.3.0] - 2026-10-10

### Added
- Retry with exponential backoff on transient HTTP failures (connection
  errors, timeouts, 500/502/503/504): 4 attempts, no more instant failure on
  a momentary outage.
- `--at HH[:MM]` shows the weather at a specific hour in a compact card; a
  past hour resolves to tomorrow. Rejected in combination with
  `--vs-yesterday`.
- `--rain` renders only the 24h rain windows (or the no-rain message) and
  composes with every fetch path including `--compare`.
- City disambiguation: ambiguous queries use the first (most populous)
  candidate and list the alternatives with their states on stderr, with a
  refine hint (city + state, comma-separated). All candidates share one
  cache entry.

## [0.2.9] - 2026-10-10

### Fixed
- `--config-set` no longer persists one-shot flag overrides: a single
  `bom-clima "sp" --imperial --days 3 --config-set color=true` used to save
  imperial and 3 days as the permanent default.
- `--config-set` validates values per key, so `history_limit=abc` no longer
  breaks every later run with a TypeError, and `color=no` no longer persists a
  truthy string.
- A damaged `config.json` or `history.json` no longer crashes every command; a
  corrupted history file is moved to `.corrupt` instead of being silently
  overwritten.
- City names, regions and cached history entries are escaped before reaching
  Rich. Text containing `[` previously raised `MarkupError`, which is not a
  `ValueError` and so escaped the CLI's error handling and printed a traceback.
- The geocoding cache key includes the language, so `--lang en` no longer keeps
  showing the pt place name for 7 days.
- A failed air-quality request is no longer cached, so a transient outage no
  longer makes `--aqi` report "N/A" for the next 30 minutes.
- `--no-cache` no longer writes to the cache.
- Responses of `{"error": true}` are no longer cached and no longer crash display.
- The cache degrades to a miss on any SQLite error instead of aborting a run
  whose weather was already fetched.
- `wind_direction` handles negative angles; `score_days` stays within 0-100 and
  tolerates `null` cells; the rain alert uses one day instead of the whole window.
- Recommendations follow today's index instead of index 0, which was yesterday
  under `--vs-yesterday`.
- YAML and XML exports handle apostrophes and quotes in place names.
- `-e pdf` exits non-zero, and `--output` without `--export` is no longer ignored.

- The legacy-code-page stdout fix now lives in `main()` itself, so the
  installed `bom-clima` console script (which never runs the
  `bom-clima.py`/`__main__` shims) is covered too.
- Non-object API payloads (HTTP 200 with a `null`/array body) raise ValueError
  instead of being returned and cached as weather.
- `--compare` with an invalid export format exits non-zero like the
  single-city path does.
- `export_all_formats` no longer relies on `assert` for control flow, so
  `python -O` keeps working.
- Cache rows with a NULL timestamp or a non-dict payload are treated as a miss
  instead of raising TypeError.

- `--lang` (and the `lang` key in `config.json`, previously ignored) is now
  resolved before the argument parser is built, so `--lang pt --help` and the
  validation errors are printed in the requested language.
- `--no-color` now applies to `--help` as well, and the Rich console no longer
  forces terminal mode, so redirected output and pipes are free of ANSI escapes
  and `NO_COLOR` is honoured.
- `--best-day` and `--vs-yesterday` are no longer ignored by `--compare`.
- `--compare` keeps and displays the cities that resolved; a failing city is
  reported on stderr and only fails the run when nothing resolved.
- `city_default` is split on commas like the CLI positional, so `--compare`
  works with a configured default city.
- The moon phase uses the real reference instant (2000-01-06 18:14 UTC) instead
  of midnight of that day, and follows the queried location's date rather than
  the machine clock.
- Colour thresholds compare with `>=`: exactly 28C was rendering green and 20%
  rain green, instead of yellow.
- The temperature bar renders between "Min today" and "Humidity" instead of
  above the city name.
- Locale detection follows POSIX precedence (LC_ALL > LC_MESSAGES > LANGUAGE >
  LANG), accepts regional codes and a BOM in the `lang` file, and no longer
  mutates the process-wide LC_MESSAGES locale as a side effect.
- `mypy bom_clima/` runs again (the pinned `python_version` made it abort) and
  reports no errors.

### Removed
- `--alerts`. It called `https://api.open-meteo.com/v1/warnings`, which returns
  HTTP 404; there is no public severe-weather endpoint in the Open-Meteo API, so
  the flag could never report anything. Extreme weather is still detected locally.

## [0.2.8] - 2026-08-12

### Fixed
- CSV export now uses today's daily values instead of yesterday's when combined with `--vs-yesterday`
- `--config-set` rejects non-finite numeric values (`inf`, `nan`) that previously crashed
- `history_limit=0` now clears history instead of keeping every entry (`history[-0:]` gotcha)
- YAML export now emits valid YAML for list values (daily/hourly arrays)
- `--config-set lang=...` now persists the language, matching `--lang`
- Unknown WMO weather codes render as "Unknown" instead of "Clear sky"
- Extreme-weather detection no longer counts past-hour CAPE (a storm yesterday no longer flags today)
- Query history no longer crashes on legacy/malformed entries
- Panel title no longer mangles the city name via `capitalize()`

### Changed
- Weather cache key now includes `include_alerts` and `past_days`, fixing stale results for `--alerts` and `--vs-yesterday`
- Imperial units now correctly normalized for dew point comfort, recommendations, extreme detection, and day scoring (not only temperature colors)
- Time-remaining and rain-window calculations now use the location's local time
- Weather panel label column is no longer inflated by the city name/weather description
- `forecast_days` from config is clamped to 1–15
- Multi-city input is documented as comma-separated only (spaces are part of a single city name)

### Added
- `today_index()` helper keeps "today" correct when `--vs-yesterday` fetches past days
- Unit-conversion helpers (`_to_celsius`, `_to_kmh`, `_to_mm`, `unit_symbols`)
- Regression tests for all fixes above

## [0.2.7] - 2026-08-10

### Changed
- Query history (`--history`, `-y`) rendered as a panel card consistent with the other cards

## [0.2.6] - 2026-08-10

### Added
- `--vs-yesterday` now compares today's max temperature with yesterday's (fetches the past day from the API)
- Best-day card (`--best-day`) rendered as a centered, width-filling table card consistent with the other cards
- Config screen (`--config-show`) rendered as a panel card with values aligned in a column
- Temperature color unit tests covering metric (°C) and imperial (°F) ranges
- Pairwise argument combination tests for the CLI parser and `main()` integration

### Changed
- Removed `--watch` mode and the dynamic interval logic (`watch_mode()`, `_calc_dynamic_interval()`)
- Imperial mode temperature colors now normalize values to °C before applying thresholds; red starts at ≥ 35 °C (95 °F)
- Card layout is preserved when colors are disabled (`--no-color`): Rich panels/tables still render borders, fully monochrome with zero ANSI codes
- `--config-show` and `--history` no longer emit colors when `--no-color` is used (color state synced in early-exit paths)
- Help output now includes a Smart section (`--best-day`, `--vs-yesterday`)

### Fixed
- Rich markup (`[cyan]...[/cyan]`) leaking literally into `--no-color` output
- Temperatures below 35 °C shown red in imperial mode (°F values were compared against °C thresholds)
- Card borders disappearing in `--no-color` mode

## [0.2.5] - 2026-04-29

### Added
- Multi-city comparison (`--compare`)
- Air quality index (`--aqi`)
- Moon phases
- Smart recommendations
- Extreme weather detection
- Day scoring (`--best-day`)
- Export to JSON/CSV/YAML/XML
- SQLite cache
- Query history
- Persistent configuration
- i18n: English, Portuguese, Spanish

## [0.1.0] - 2026-01-01

### Added
- Initial release
- Basic weather query
- Rich terminal output
- Open-Meteo API integration
