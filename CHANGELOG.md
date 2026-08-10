# Changelog

All notable changes to Bom Clima will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
