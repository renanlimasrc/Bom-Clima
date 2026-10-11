# Bom Clima

A beautiful, feature-rich command-line weather application powered by Open-Meteo API. Get weather forecasts, air quality, moon phases, and more — all from your terminal.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/Version-0.4.1-blue.svg)
![License](https://img.shields.io/badge/License-GPL%202.0-blue.svg)

## ✨ Features

### Core Features
- **Multi-city search** — Query multiple cities in a single command (comma-separated)
- **5-day forecast** (up to 15 days available) with daily min/max temperatures
- **Hourly forecast** — Up to 24 hours of detailed hourly data with condition descriptions
- **Multiple languages** — Supports Portuguese (pt), English (en), and Spanish (es) with automatic locale detection
- **Unit systems** — Metric (°C, km/h, mm) and Imperial (°F, mph, in) support
- **Air Quality Index (AQI)** — PM2.5, US AQI with quality labels (Good to Very Poor)
- **Moon phases** — Current moon phase with emoji icons (New, Waxing, Full, Waning)

> **Note:** the `--alerts` flag was removed. It called
> `https://api.open-meteo.com/v1/warnings`, which returns HTTP 404 — there is no
> public severe-weather endpoint in the Open-Meteo API, so the flag could never
> report an alert. Extreme weather is still detected locally (see below).

### Smart Insights
- **Smart recommendations** — Context-aware advice: umbrella, sunscreen, jacket, light clothes, outdoor exercise, wind care, fog driving
- **Rain window detection** — Scans next 24h for rain periods with time and probability
- **Extreme weather alerts** — Automatic detection: heat wave (>35°C), cold snap (<0°C), strong wind (>50 km/h), heavy rain (>30 mm), thunderstorm, extreme UV (>8)
- **Best day scoring** — Ranks forecast days for outdoor activities (`--best-day`)
- **Dew point comfort** — Comfort level based on dew point (Dry/Comfortable/Muggy/Oppressive)

### Display & UI
- **Colored output** — Beautiful terminal output with Rich library, automatic fallback for non-Rich environments
- **Monochrome cards** — `--no-color` keeps the card layout with zero ANSI codes
- **One-line output** (`--line`) — `São Paulo: 🌤️ 21.6°C`, sized for a tmux/i3status bar or shell prompt
- **Side-by-side comparison** (`--compare`) — Compare weather between multiple cities
- **Localized weekday names** — Days appear in your system's language (Seg/Mon/Lun)
- **Temperature bar** — Visual temperature range display (`18°C [====.====] 28°C`)
- **Color-coded values** — Temperature and rain probability change color based on severity

### Data & Export
- **Multiple export formats** — JSON, CSV, YAML, and XML
- **Pipeable JSON** (`-e json -o -`) — Write to stdout instead of a file, so `| jq` just works
- **Smart file naming** — Automatic unique filenames when exporting multiple cities
- **SQLite cache** — Speeds up repeated queries (geo: 7 days, weather: 30 minutes)
- **Query history** — Track your recent weather searches (configurable limit)
- **Persistent configuration** — Save defaults via `~/.config/bom-clima/config.json`

### Configuration Options
- **Default city** — Set a default city to query when none is provided
- **Language preference** — Persist language choice across sessions
- **Forecast defaults** — Configure default forecast days and hours
- **Color toggle** — Enable/disable colored output
- **History limit** — Control how many queries are kept in history

## 🚀 Installation

### From Package (Recommended)

#### Arch Linux
```bash
./scripts/package-arch.sh
sudo pacman -U bom-clima-*.pkg.tar.zst
```

### From Source
```bash
git clone https://github.com/renanlimasrc/Bom-Clima.git
cd Bom-Clima
pip install .
bom-clima --help
```

### From Git (development)
```bash
git clone https://github.com/renanlimasrc/Bom-Clima.git
cd Bom-Clima
pip install -e .
bom-clima --help
```

## 📖 Usage

### Basic Usage
```bash
# Simple query (supports multiple words)
bom-clima sao paulo
bom-clima new york

# Multiple cities (comma-separated)
bom-clima "tokyo,london"
bom-clima "sao paulo,rio de janeiro"

# Compare cities side by side
bom-clima "tokyo,london" --compare

# Auto-detect location via IP
bom-clima --detect
```

### Forecast Options
```bash
# 10-day forecast (max: 15 days)
bom-clima sao paulo --days 10

# 24-hour hourly forecast
bom-clima sao paulo --hours 24

# Imperial units (°F, mph, inches)
bom-clima --imperial new york
```

### Advanced Features
```bash
# Include air quality (PM2.5, US AQI)
bom-clima sao paulo --aqi

# Best day for outdoor activities
bom-clima sao paulo --best-day

# Compare with yesterday
bom-clima sao paulo --vs-yesterday

# Disable colored output
bom-clima sao paulo --no-color

# Bypass cache (fetch fresh data)
bom-clima sao paulo --no-cache

# Show debug information
bom-clima sao paulo --verbose
```

### Statusbar and Prompt
```bash
# One compact line, sized for tmux / i3status / a shell prompt
bom-clima sao paulo --line
# São Paulo: 🌤️ 20.3°C
```

### Pipeable JSON
```bash
# `-o -` writes to stdout instead of a file
bom-clima sao paulo -e json -o - | jq '.data.current.temperature_2m'
# 20.3

# Every forecast date, one per line
bom-clima sao paulo -e json -o - | jq -c '.data.daily.time[]'
```

On the `-o -` path stdout carries **only** the payload: the cards are
suppressed and every human-facing message goes to stderr, so `jq` reads the
JSON and nothing else. `--export` without `--output` still writes to
`~/Documents/<city>.<fmt>`.

### Export Data
```bash
# Export to JSON
bom-clima sao paulo --export json -o weather.json

# Export to CSV
bom-clima sao paulo --export csv

# Multiple formats at once
bom-clima sao paulo --export json,yaml,xml

# Export multiple cities with unique filenames
bom-clima "sao paulo,rio" --export json -o /tmp/weather
# Creates: /tmp/weather_São_Paulo.json and /tmp/weather_Rio_de_Janeiro.json
```

### Configuration
```bash
# Set the language for this run only (does not persist)
bom-clima --lang en london

# Set it permanently
bom-clima --config-set lang=en

# Set persistent configuration
bom-clima --config-set city_default='sao paulo'
bom-clima --config-set forecast_days=7
bom-clima --config-set forecast_hours=24
bom-clima --config-set color=false

# Show current configuration
bom-clima --config-show

# View query history
bom-clima --history
```

## 🔧 Command-Line Options

| Option | Description |
|--------|-------------|
| `CITY...` | Name(s) of the city(ies). Supports multiple and comma-separated |
| `--detect` | Auto-detect location via IP |
| `--compare` | Compare cities side by side |
| `--days N` | Number of days in forecast (default: 5, max: 15) |
| `--hours N` | Number of hours in hourly forecast (default: 6) |
| `--aqi` | Include air quality (PM2.5, US AQI) |
| `--at HH[:MM]` | Show the weather at a specific hour |
| `--rain` | Show only rain windows in the next 24h |
| `--line` | Print one compact line (statusbar/prompt) |
| `--imperial` | Use imperial units (°F, mph, in) |
| `--no-color` | Disable colored output |
| `--export FMT` | Export data: json, csv, yaml, or xml (comma-separated) |
| `--output FILE` | Output file (default: ~/Documents/<city>.<fmt>); `-` writes to stdout |
| `--lang LANG` | Set the language for this run: pt, en, es |
| `--config-set K=V` | Set persistent configuration |
| `--config-show` | Show current configuration |
| `--history` | Show query history |
| `--best-day` | Show the best day this week for outdoor activities |
| `--vs-yesterday` | Compare today's temperature with yesterday |
| `--no-cache` | Bypass cache and fetch fresh data |
| `--verbose, -V` | Show debug information |
| `--help, -h` | Show help message |
| `--version, -v` | Show version |

## 🌍 Language Support

The app automatically detects your system language:
- **Portuguese (pt)** — Full support (default for Brazilian/Portuguese systems)
- **English (en)** — Full support (default for most systems)
- **Spanish (es)** — Full support

Override with: `bom-clima --lang pt london`

## 📁 File Locations

App data follows the XDG Base Directory Specification:
- `~/.config/bom-clima/config.json` — Persistent configuration (unit system, default city, forecast days, etc.)
- `~/.config/bom-clima/lang` — Language preference file
- `~/.cache/bom-clima/cache.db` — SQLite cache for geo and weather data
- `~/.local/share/bom-clima/history.json` — Query history (last 50 queries by default)

## 📝 Examples

### Example 1: Simple Query (Portuguese)
```bash
$ bom-clima sao paulo
```
```
╭────────   Clima atual em São Paulo   ─────────╮
│ São Paulo, Brasil                             │
│    19.1°C [=.=============] 28.2°C            │
│ Atualizado:                21:30 (10/10/2026) │
│ Principalmente limpo                          │
│ Temperatura:               20.3°C             │
│ Sensação térmica:          22.8°C             │
│ Máxima hoje:               28.2°C             │
│ Mínima hoje:               19.1°C             │
│ Umidade:                   95%                │
│ Vento:                     7.2 km/h → (E)     │
│ Rajadas:                   23.4 km/h          │
│ Pressão:                   1018.5 hPa         │
│ Nuvens:                    34%                │
│ Ponto de orvalho:          19.4°C (Abafado)   │
│ Visibilidade:              12.1 km            │
│ Chuva atual:               0.0 mm             │
│ Chance de chuva:           97%                │
│ Precipitação total:        9.1 mm             │
│ Horas de chuva:            9.0 h              │
│ Amanhecer:                 05:38 (-15h 52min) │
│ Anoitecer:                 18:09 (-3h 21min)  │
│ Duração do dia:            12h 31min          │
│ Índice UV:                 0.0                │
│ Índice de Qualidade do Ar: 85 (Regular)       │
│ PM2.5:                     32.8 µg/m³         │
│ Fase da lua:               🌘 Minguante       │
╰───────────────────────────────────────────────╯
╭─────────────────────── Próximas horas ───────────────────────╮
│  Hora  ┃ Temp   ┃ Chuva % ┃ Vento    ┃ Cond                  │
│ ━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━ │
│  22:00 │ 20.1°C │ 9%      │ 5.5 km/h │ Principalmente limpo  │
│  23:00 │ 19.8°C │ 4%      │ 4.5 km/h │ Principalmente limpo  │
│  00:00 │ 19.5°C │ 2%      │ 6.2 km/h │ Parcialmente nublado  │
│  01:00 │ 19.2°C │ 2%      │ 7.4 km/h │ Parcialmente nublado  │
│  02:00 │ 18.9°C │ 4%      │ 6.1 km/h │ Principalmente limpo  │
│  03:00 │ 18.8°C │ 6%      │ 6.0 km/h │ Nublado               │
╰──────────────────────────────────────────────────────────────╯
╭─────────────────────────── Previsão 5 dias ───────────────────────────╮
│  Data        ┃ Cond                      ┃ Mín    ┃ Máx    ┃ Chuva %  │
│ ━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━ │
│  10/10 (Sáb) │ Pancadas moderadas        │ 19.1°C │ 28.2°C │ 97%      │
│  11/10 (Dom) │ Pancadas leves            │ 18.5°C │ 26.3°C │ 100%     │
│  12/10 (Seg) │ Trovoada                  │ 18.3°C │ 27.0°C │ 97%      │
│  13/10 (Ter) │ Trovoada com granizo leve │ 17.8°C │ 26.5°C │ 78%      │
│  14/10 (Qua) │ Trovoada                  │ 19.4°C │ 27.8°C │ 92%      │
╰───────────────────────────────────────────────────────────────────────╯
╭──────  Alertas e recomendações  ───────╮
│ ⚠️  Risco de tempestade! CAPE: 1870    │
│ ⚠️  UV extremo! Índice 8               │
│ ✔️  Leve guarda-chuva (chuva esperada) │
╰────────────────────────────────────────╯
```

### Example 2: Compare Cities with Export
```bash
$ bom-clima "sao paulo,rio" --compare --export json -o /tmp/weather
```
Exports to: `/tmp/weather_São_Paulo.json` and `/tmp/weather_Rio_de_Janeiro.json`

### Example 3: One line for a statusbar
```bash
$ bom-clima sao paulo --line
```
```
São Paulo: 🌤️ 20.3°C
```

## 🏃 Running Tests

```bash
cd Bom-Clima
python -m pytest tests/test_bom_clima.py -v
```

259 tests, covering the formatters, the cache, the CLI parser, every pairwise
argument combination and the regression for each fix in the
[changelog](CHANGELOG.md). The same run must be clean under
`ruff check bom_clima/ tests/` and `mypy bom_clima/`.

## 📜 License

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, see <https://www.gnu.org/licenses/>.

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## 🙏 Acknowledgments

- Weather data provided by [Open-Meteo](https://open-meteo.com/)
- Geocoding by [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- Beautiful terminal output powered by [Rich](https://github.com/Textualize/rich)

---

**Made with ❤️ for weather enthusiasts**
