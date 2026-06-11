# Bom Clima

A beautiful, feature-rich command-line weather application powered by Open-Meteo API. Get weather forecasts, air quality, moon phases, and more — all from your terminal.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Version](https://img.shields.io/badge/Version-0.2.1-blue.svg)
![License](https://img.shields.io/badge/License-GPL%202.0-blue.svg)

## ✨ Features

### Core Features
- **Multi-city search** — Query multiple cities in a single command (comma-separated or space-separated)
- **5-day forecast** (up to 15 days available) with daily min/max temperatures
- **Hourly forecast** — Up to 24 hours of detailed hourly data with condition descriptions
- **Multiple languages** — Supports Portuguese (pt), English (en), and Spanish (es) with automatic locale detection
- **Unit systems** — Metric (°C, km/h, mm) and Imperial (°F, mph, in) support
- **Air Quality Index (AQI)** — PM2.5, US AQI with quality labels (Good to Very Poor)
- **Moon phases** — Current moon phase with emoji icons (New, Waxing, Full, Waning)
- **Weather alerts** — Severe weather warnings when available (thunderstorms, heavy rain, etc.)

### Smart Insights
- **Smart recommendations** — Context-aware advice: umbrella, sunscreen, jacket, light clothes, outdoor exercise, wind care, fog driving
- **Rain window detection** — Scans next 24h for rain periods with time and probability
- **Extreme weather alerts** — Automatic detection: heat wave (>35°C), cold snap (<0°C), strong wind (>50 km/h), heavy rain (>30 mm), thunderstorm, extreme UV (>8)
- **Best day scoring** — Ranks forecast days for outdoor activities (`--best-day`)
- **Dew point comfort** — Comfort level based on dew point (Dry/Comfortable/Muggy/Oppressive)

### Display & UI
- **Colored output** — Beautiful terminal output with Rich library, automatic fallback for non-Rich environments
- **Watch mode** (`--watch`) — Auto-refresh weather every N seconds with **dynamic intervals** (adjusts based on rain probability)
- **Side-by-side comparison** (`--compare`) — Compare weather between multiple cities
- **Localized weekday names** — Days appear in your system's language (Seg/Mon/Lun)
- **Temperature bar** — Visual temperature range display (`18°C [====.====] 28°C`)
- **Color-coded values** — Temperature and rain probability change color based on severity

### Data & Export
- **Multiple export formats** — JSON, CSV, YAML, and XML
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

# Multiple cities (space or comma-separated)
bom-clima tokyo london
bom-clima "sao paulo,rio de janeiro"

# Compare cities side by side
bom-clima tokyo london --compare

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

# Include weather alerts
bom-clima miami --alerts

# Watch mode (update every 60 seconds)
# Note: Interval adjusts dynamically based on rain probability
bom-clima sao paulo --watch 60

# Best day for outdoor activities
bom-clima sao paulo --best-day

# Disable colored output
bom-clima sao paulo --no-color

# Bypass cache (fetch fresh data)
bom-clima sao paulo --no-cache

# Show debug information
bom-clima sao paulo --verbose
```

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
# Set language (persists to ~/.config/bom-clima/lang)
bom-clima --lang en london

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
| `--hours N` | Number of hours in hourly forecast (default: 12) |
| `--alerts` | Include weather alerts |
| `--aqi` | Include air quality (PM2.5, US AQI) |
| `--imperial` | Use imperial units (°F, mph, in) |
| `--no-color` | Disable colored output |
| `--watch SEC` | Monitor mode: update every N seconds (dynamic interval) |
| `--export FMT` | Export data: json, csv, yaml, or xml (comma-separated) |
| `--output FILE` | Output file (default: ~/Documents/<city>.<fmt>) |
| `--lang LANG` | Set language: pt, en, es |
| `--config-set K=V` | Set persistent configuration |
| `--config-show` | Show current configuration |
| `--history` | Show query history |
| `--best-day` | Show the best day this week for outdoor activities |
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
╭──────────── Clima atual em São paulo ────────────╮
│ São Paulo, São Paulo, Brasil                     │
│ Atualizado:              10:45 (30/04/2026)     │
│ Principalmente limpo                             │
│                                                  │
│ Temperatura:             23.7°C                  │
│ Sensação térmica:        27.6°C                  │
│ Máxima hoje:             28.0°C                  │
│ Mínima hoje:             18.0°C                  │
│   18.0°C [====.=========] 28.0°C                │
│                                                  │
│ Umidade:                 65%                     │
│ Vento:                   12 km/h ↘ (ESE)         │
│ Rajadas:                 20 km/h                 │
│ Pressão:                 1013 hPa                │
│ Nuvens:                  40%                     │
│ Ponto de orvalho:        16°C (Abafado)          │
│ Visibilidade:            10.0 km                 │
│                                                  │
│ Chuva atual:             0 mm                    │
│ Chance de chuva:         20%                     │
│ Precipitação total:      0 mm                    │
│ Horas de chuva:          0 h                     │
│                                                  │
│ Amanhecer:               06:15 (+2h 30min)       │
│ Anoitecer:               18:45 (-3h 15min)       │
│ Duração do dia:          12h 30min               │
│ Índice UV:               6                       │
│                                                  │
│ Índice de Qualidade do Ar: 42 (Bom)             │
│ PM2.5:                   12 µg/m³                │
│ Fase da lua:             🌓 Crescente            │
╰──────────────────────────────────────────────────╯

╭──────────────── Próximas horas ─────────────────╮
│ Hora  Temp    Chuva %  Vento       Cond          │
├─────────────────────────────────────────────────┤
│ 10:00 15.4°C  0%      10.6 km/h   Limpo         │
│ 11:00 17.7°C  0%      10.4 km/h   Parcialmente..│
│ 12:00 18.4°C  0%      9.8 km/h    Nublado       │
│ 13:00 18.8°C  1%      8.3 km/h    Nublado       │
│ 14:00 19.0°C  1%      8.1 km/h    Parcialmente..│
│ 15:00 18.9°C  2%      9.8 km/h    Parcialmente..│
╰─────────────────────────────────────────────────╯

╭───────────────── Previsão 5 dias ────────────────╮
│ Data        Cond               Mín    Máx  Chuva % │
├─────────────────────────────────────────────────────┤
│ 02/06 (Ter) Nublado            10.6°C 19.0°C  2%   │
│ 03/06 (Qua) Nublado            12.6°C 20.0°C  6%   │
│ 04/06 (Qui) Garoa leve         13.4°C 19.5°C  41%  │
│ 05/06 (Sex) Nublado            11.4°C 18.8°C  2%   │
│ 06/06 (Sáb) Nublado            11.4°C 21.2°C  0%   │
╰─────────────────────────────────────────────────────╯

╭────────────── Recomendações ──────────────╮
│ Leve um casaco (sensação de frio)          │
│ Baixa visibilidade — dirija com cuidado    │
│ ✅ Sem previsão de chuva nas próximas 24h  │
╰────────────────────────────────────────────╯
```

### Example 2: Compare Cities with Export
```bash
$ bom-clima "sao paulo,rio" --compare --export json -o /tmp/weather
```
Exports to: `/tmp/weather_São_Paulo.json` and `/tmp/weather_Rio_de_Janeiro.json`

## 🏃 Running Tests

```bash
cd Bom-Clima
python -m pytest tests/test_bom_clima.py -v
```

All 100 tests should pass

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
