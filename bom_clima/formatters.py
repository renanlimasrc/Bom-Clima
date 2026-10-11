"""Formatting helpers for Bom Clima."""

import csv
import io
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from .constants import (
    AQI_LABELS,
    COMPASS,
    DAY_SCORE_IDEAL_TEMP,
    DEWPOINT_COMFORT,
    EXTREME_CAPE,
    EXTREME_COLD_C,
    EXTREME_HEAT_C,
    EXTREME_RAIN_DAILY_MM,
    EXTREME_UV,
    EXTREME_WIND_KMH,
    RAIN_PROB_THRESHOLD,
    RAIN_WINDOW_HOURS,
    WEEKDAYS,
    WIND_ARROWS,
    WMO_CODES,
)
from .i18n import _current_lang, t


def r_escape(text: object) -> str:
    """Local import shim -- display imports this module, so importing it here
    at module scope would be circular."""
    from .display import r_escape as _impl

    return _impl(text)


def _to_celsius(value: float, unit_system: str) -> float:
    return (value - 32.0) * 5.0 / 9.0 if unit_system == "imperial" else value


def _to_kmh(value: float, unit_system: str) -> float:
    return value * 1.60934 if unit_system == "imperial" else value


def _to_mm(value: float, unit_system: str) -> float:
    return value * 25.4 if unit_system == "imperial" else value


def unit_symbols(unit_system: str) -> tuple[str, str, str]:
    if unit_system == "imperial":
        return "°F", "mph", "in"
    return "°C", "km/h", "mm"


def _num(value: object, default: float = 0.0) -> float:
    """Coerce an API cell to a float.

    Open-Meteo sends `null` in cells it has no sensor for and json.loads passes
    that through untouched, so arithmetic on a raw cell raises TypeError.
    """
    if value is None:
        return default
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def _at(values: object, index: int, default: object = None) -> object:
    """Read index from a parallel array, tolerating short and missing ones."""
    if not isinstance(values, (list, tuple)) or not 0 <= index < len(values):
        return default
    return values[index]


def today_index(dados: dict) -> int:
    """Return the index of today inside the daily arrays (handles past_days offsets).

    Falls back to the last day in the payload when there is no usable "current"
    timestamp. Returning 0 unconditionally would silently point at yesterday
    whenever past_days shifts the arrays, which is exactly what --vs-yesterday
    asks for.
    """
    # `or {}`, not a .get() default: the default only covers an absent key, and
    # Open-Meteo can send an explicit "daily": null or "current": null.
    times = (dados.get("daily") or {}).get("time", [])
    if not times:
        return 0
    current_time = str((dados.get("current") or {}).get("time") or "")
    today = current_time[:10]
    if today:
        for i, ts in enumerate(times):
            if str(ts)[:10] == today:
                return i
    return max(0, len(times) - 1)


def wind_direction(degrees: float) -> str:
    # Normalise before the int() cast: int() truncates toward zero, so a
    # negative angle without the modulo lands one or two sectors off (-30 would
    # report N instead of NNO).
    idx = int((float(degrees) % 360 + 11.25) / 22.5) % 16
    return COMPASS[idx]


def wind_arrow(degrees: float) -> str:
    idx = int((float(degrees) % 360 + 11.25) / 22.5) % 16
    return WIND_ARROWS[COMPASS[idx]]


def format_duration(segundos: float) -> str:
    horas = int(segundos) // 3600
    minutos = (int(segundos) % 3600) // 60
    return f"{horas}h {minutos:02d}min"


def format_timestamp(timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%H:%M")
    except ValueError:
        return timestamp[-5:]


def format_time_remaining(timestamp: str, now: datetime | None = None) -> str:
    try:
        target = datetime.fromisoformat(timestamp).replace(tzinfo=None)
        current = (now or datetime.now()).replace(tzinfo=None)
        diff = target - current
        total_seconds = int(diff.total_seconds())
        hours = abs(total_seconds) // 3600
        minutes = (abs(total_seconds) % 3600) // 60
        signal = "+" if total_seconds > 0 else "-"
        if hours > 0:
            return f" ({signal}{hours}h {minutes}min)"
        return f" ({signal}{minutes}min)"
    except ValueError:
        return ""


def get_weekday_name(dt: datetime, lang: str | None = None) -> str:
    lang = lang or _current_lang()
    return WEEKDAYS.get(lang, WEEKDAYS["en"])[dt.weekday()]


def get_wmo(code: int, lang: str | None = None) -> tuple[str, str]:
    lang = lang or _current_lang()
    entry = WMO_CODES.get(code)
    if entry is None:
        entry = {"pt": ("Desconhecido", "\u2753"), "en": ("Unknown", "\u2753"), "es": ("Desconocido", "\u2753")}
    return entry.get(lang, entry.get("en", ("Unknown", "\u2753")))


def get_aqi_label(aqi: float, lang: str | None = None) -> str:
    lang = lang or _current_lang()
    labels = AQI_LABELS.get(lang, AQI_LABELS["en"])
    if aqi <= 50:
        return labels[0]
    elif aqi <= 100:
        return labels[1]
    elif aqi <= 150:
        return labels[2]
    elif aqi <= 200:
        return labels[3]
    return labels[4]


def moon_phase_name(phase_idx: int, lang: str) -> str:
    names = {
        "pt": ["Nova", "Crescente", "Cheia", "Minguante"],
        "en": ["New Moon", "Waxing", "Full Moon", "Waning"],
        "es": ["Nueva", "Creciente", "Llena", "Menguante"],
    }
    icons = ["\U0001f311", "\U0001f312", "\U0001f315", "\U0001f318"]
    lang = lang or "en"
    if not 0 <= phase_idx < 4:
        phase_idx = 0
    return f"{icons[phase_idx]} {names.get(lang, names['en'])[phase_idx]}"


def get_moon_phase(date: datetime | None = None) -> int:
    """Return the moon phase bucket (0 New, 1 Waxing, 2 Full, 3 Waning).

    The reference instant is the real new moon of 2000-01-06 18:14 UTC. Using
    midnight of that day, and counting whole days, shifted every result by about
    18 hours -- roughly a tenth of all calendar dates landed in the wrong
    bucket.
    """
    d = date or datetime.now()
    base = datetime(2000, 1, 6, 18, 14)
    diff = (d - base).total_seconds() / 86400.0
    cycle = 29.53059
    phase = (diff % cycle) / cycle
    if phase < 0.25:
        return 0
    elif phase < 0.5:
        return 1
    elif phase < 0.75:
        return 2
    return 3


def is_day_icon(timestamp: str) -> str:
    hour = int(timestamp[-8:-6])
    return "\U0001f319" if hour < 6 or hour >= 18 else "\u2600\ufe0f"


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        cp = ord(ch)
        if 0xFE00 <= cp <= 0xFE0F:
            continue
        if cp > 0x1F000 or (0x2000 <= cp <= 0x27BF):
            width += 2
        else:
            width += 1
    return width


def dewpoint_comfort(dp: float, lang: str | None = None, unit_system: str = "metric") -> str:
    lang = lang or _current_lang()
    dp = _to_celsius(float(dp), unit_system)
    levels = DEWPOINT_COMFORT.get(lang, DEWPOINT_COMFORT["en"])
    for threshold, _key, label in levels:
        if dp <= threshold:
            return label
    return levels[-1][2]


def generate_recommendations(dados: dict, cfg: dict) -> list[str]:
    atual = dados.get("current") or {}
    diario = (dados.get("daily") or {})
    unit = cfg.get("unit_system", "metric")
    temp = atual.get("temperature_2m", 20)
    uv = atual.get("uv_index", 0)
    rain_prob = _num(_at(diario.get("precipitation_probability_max"), today_index(dados)))
    vento = atual.get("wind_speed_10m", 0)
    visibility = atual.get("visibility", 10000)
    temp_c = _to_celsius(_num(temp, 20), unit)
    wind_kmh = _to_kmh(_num(vento), unit)
    recs: list[str] = []
    if rain_prob > 60:
        recs.append(t("rec_umbrella"))
    if uv and _num(uv) > 6:
        recs.append(t("rec_sunscreen").format(uv=int(_num(uv))))
    if temp_c < 15:
        recs.append(t("rec_jacket"))
    if temp_c > 30:
        recs.append(t("rec_light_clothes"))
    if rain_prob < 20 and 15 <= temp_c <= 28:
        recs.append(t("rec_good_run"))
    if wind_kmh > 40:
        recs.append(t("rec_windy_care"))
    if visibility and _num(visibility, 10000) < 2000:
        recs.append(t("rec_fog_careful"))
    return recs


def detect_extremes(dados: dict, unit_system: str = "metric") -> list[str]:
    atual = dados.get("current") or {}
    diario = (dados.get("daily") or {})
    idx = today_index(dados)
    max_series = diario.get("temperature_2m_max")
    min_series = diario.get("temperature_2m_min")
    temp_max = max((_num(v) for v in max_series[idx:]), default=0.0) if max_series else 0.0
    temp_min = min((_num(v) for v in min_series[idx:]), default=0.0) if min_series else 0.0
    vento = atual.get("wind_speed_10m", 0)
    # Today's rain only. Summing the whole remaining window against a *daily*
    # threshold produced a guaranteed false positive: 3 mm/day over --days 15
    # totals 45 mm and fired an "intense rain, 45 mm in 24h" alert that never
    # happened on any single day.
    rain_total = _num(_at(diario.get("precipitation_sum"), idx))
    # The daily UV maximum is the meteorologically meaningful figure; the
    # current reading is near zero before sunrise and after sunset, which hid
    # the alert exactly when it mattered.
    uv = max(
        _num(atual.get("uv_index")),
        _num(_at(diario.get("uv_index_max"), idx)),
    )
    hourly = (dados.get("hourly") or {})
    cape_vals = hourly.get("cape") or []
    cape = max((_num(v) for v in cape_vals), default=0.0)
    current_time = atual.get("time", "")
    if cape_vals and current_time:
        try:
            now_dt = datetime.fromisoformat(current_time).replace(tzinfo=None)
            future_cape = [
                _num(c) for ts, c in zip(hourly.get("time", []), cape_vals, strict=False)
                if datetime.fromisoformat(ts).replace(tzinfo=None) >= now_dt
            ]
            cape = max(future_cape, default=0.0)
        except (ValueError, TypeError):
            pass
    temp_max_c = _to_celsius(temp_max, unit_system)
    temp_min_c = _to_celsius(temp_min, unit_system)
    wind_kmh = _to_kmh(_num(vento), unit_system)
    rain_mm = _to_mm(rain_total, unit_system)
    t_unit, w_unit, p_unit = unit_symbols(unit_system)
    extremes: list[str] = []
    if temp_max_c > EXTREME_HEAT_C:
        extremes.append(t("extreme_heat").format(temp=temp_max, unit=t_unit))
    if temp_min_c < EXTREME_COLD_C:
        extremes.append(t("extreme_cold").format(temp=temp_min, unit=t_unit))
    if wind_kmh > EXTREME_WIND_KMH:
        extremes.append(t("extreme_wind").format(speed=int(_num(vento)), unit=w_unit))
    if rain_mm > EXTREME_RAIN_DAILY_MM:
        extremes.append(t("extreme_rain").format(precip=int(rain_total), unit=p_unit))
    if cape > EXTREME_CAPE:
        extremes.append(t("extreme_storm").format(cape=int(cape)))
    if uv > EXTREME_UV:
        extremes.append(t("extreme_uv").format(uv=int(uv)))
    return extremes


def format_line(nome: str, dados: dict, cfg: dict) -> str | None:
    """One compact line: 'Curitiba: 🌧️ 18.9°C'.

    Sized for a tmux/i3status bar or a shell prompt, where the multi-card output
    is unusable. Returns None when the payload has no current block; callers
    (_print_line_or_card) turn that into the full card rather than a blank
    line, so nothing is ever printed for nothing.
    """
    atual = dados.get("current")
    if not isinstance(atual, dict) or atual.get("time") is None:
        return None
    unit = cfg.get("unit_system", "metric")
    unit_sym = unit_symbols(unit)[0]
    temp = _num(atual.get("temperature_2m"))
    code = int(_num(atual.get("weather_code")))
    _desc, icon = get_wmo(code)
    return t("line_fmt").format(city=r_escape(nome), icon=icon, temp=temp, unit=unit_sym)


def rain_window_summary(dados: dict) -> list[str]:
    hourly = (dados.get("hourly") or {})
    if not isinstance(hourly, dict) or not hourly.get("time"):
        return []
    from datetime import datetime as dt
    current = dados.get("current") or {}
    now = dt.fromisoformat(current["time"]).replace(tzinfo=None) if current.get("time") else dt.now()
    probs = hourly.get("precipitation_probability") or []
    rainy: list[str] = []
    for i, ts in enumerate(hourly["time"]):
        try:
            ts_dt = dt.fromisoformat(ts).replace(tzinfo=None)
            hours_diff = (ts_dt - now).total_seconds() / 3600
            if hours_diff < 0 or hours_diff > RAIN_WINDOW_HOURS:
                continue
            # A null cell or a short/missing array used to raise TypeError /
            # KeyError here, outside the except below. Non-numeric cells carry
            # no information, so they are skipped, not crashed on.
            prob = _at(probs, i)
            if not isinstance(prob, (int, float)):
                continue
            if prob >= RAIN_PROB_THRESHOLD:
                rainy.append(t("rain_time").format(time=ts_dt.strftime("%H:%M"), prob=prob))
        except (ValueError, IndexError, KeyError, TypeError):
            continue
    return rainy


def score_days(dados: dict, unit_system: str = "metric") -> list[tuple[str, float]]:
    diario = (dados.get("daily") or {})
    if not diario or not diario.get("time"):
        return []
    from datetime import datetime as dt
    idx = today_index(dados)
    scores: list[tuple[str, float]] = []
    for i in range(idx, len(diario["time"])):
        date_str = diario["time"][i]
        date_dt = dt.fromisoformat(date_str)
        date_label = date_dt.strftime("%d/%m")
        temp_max = _num(_at(diario.get("temperature_2m_max"), i))
        temp_min = _num(_at(diario.get("temperature_2m_min"), i))
        rain_prob = _num(_at(diario.get("precipitation_probability_max"), i))
        wind_max = _num(_at(diario.get("wind_speed_10m_max"), i))
        sunshine = _num(_at(diario.get("sunshine_duration"), i))
        avg_c = _to_celsius((temp_max + temp_min) / 2, unit_system)
        wind_kmh = _to_kmh(wind_max, unit_system)
        score = 100.0
        score -= rain_prob * 1.2
        score -= abs(DAY_SCORE_IDEAL_TEMP - avg_c) * 3
        score -= wind_kmh * 0.5
        score += (sunshine / 3600) * 0.5
        # The sunshine bonus has no matching penalty, so a perfect day scored
        # 106 -- above the 0-100 range the card and the docs promise.
        scores.append((date_label, max(0.0, min(100.0, score))))
    return scores


def _to_yaml(nome: str, dados: dict) -> str:
    def _yaml_safe(val: object) -> str:
        if isinstance(val, (list, tuple, dict)):
            return json.dumps(val, ensure_ascii=False)
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "true" if val else "false"
        if not isinstance(val, (int, float)):
            # Quote every string, so numbers and YAML keywords keep their type
            # and apostrophes cannot break the scalar. YAML escapes a single
            # quote by doubling it.
            return "'" + str(val).replace("'", "''") + "'"
        s = str(val)
        if any(c in s for c in (":", "#", '"', "'", "\n", "[", "]", "{", "}")):
            return f"'{s}'"
        return s

    lines = [
        f"city: {_yaml_safe(nome)}",
        f"queried_at: {_yaml_safe(datetime.now().isoformat())}",
        "data:",
        "  current:",
    ]
    atual = dados.get("current") or {}
    for key, val in atual.items():
        lines.append(f"    {key}: {_yaml_safe(val)}")
    diario = (dados.get("daily") or {})
    if diario:
        lines.append("  daily:")
        for key in diario:
            lines.append(f"    {key}: {_yaml_safe(diario[key])}")
    return "\n".join(lines) + "\n"


def _to_xml(nome: str, dados: dict) -> str:
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        # The city name sits inside an attribute, so the quote must be escaped
        # too: xml.sax.saxutils.escape handles &, < and > but not ".
        f'<weather city="{xml_escape(str(nome), {chr(34): "&quot;"})}" '
        f'queried_at="{xml_escape(datetime.now().isoformat(), {chr(34): "&quot;"})}">',
    ]
    atual = dados.get("current") or {}
    if atual:
        xml.append("  <current>")
        for key, val in atual.items():
            xml.append(f"    <{key}>{xml_escape(str(val))}</{key}>")
        xml.append("  </current>")
    diario = (dados.get("daily") or {})
    if diario:
        xml.append("  <daily>")
        for key, val in diario.items():
            xml.append(f"    <{key}>{xml_escape(str(val))}</{key}>")
        xml.append("  </daily>")
    xml.append("</weather>")
    return "\n".join(xml) + "\n"


def export_data(
    dados: dict,
    nome: str,
    fmt: str,
    output: str | None = None,
) -> str:
    if fmt == "json":
        payload = {"city": nome, "queried_at": datetime.now().isoformat(), "data": dados}
        content = json.dumps(payload, indent=2, ensure_ascii=False)
    elif fmt == "csv":
        atual = dados.get("current") or {}
        diario = dados.get("daily") or {}
        idx = today_index(dados)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            t("csv_city"), t("csv_temp"), t("csv_feels"), t("csv_max"), t("csv_min"),
            t("csv_humidity"), t("csv_wind"), t("csv_rain"), t("csv_rain_chance"),
            t("csv_precip"), t("csv_sunrise"), t("csv_sunset"),
        ])
        writer.writerow([
            nome,
            atual.get("temperature_2m", ""),
            atual.get("apparent_temperature", ""),
            _at(diario.get("temperature_2m_max", []), idx, ""),
            _at(diario.get("temperature_2m_min", []), idx, ""),
            atual.get("relative_humidity_2m", ""),
            atual.get("wind_speed_10m", ""),
            atual.get("rain", 0),
            _at(diario.get("precipitation_probability_max", []), idx, ""),
            _at(diario.get("precipitation_sum", []), idx, ""),
            format_timestamp(str(_at(diario.get("sunrise", []), idx, "") or "")),
            format_timestamp(str(_at(diario.get("sunset", []), idx, "") or "")),
        ])
        content = buf.getvalue()
    elif fmt == "yaml":
        content = _to_yaml(nome, dados)
    elif fmt == "xml":
        content = _to_xml(nome, dados)
    else:
        raise ValueError(t("invalid_format").format(fmt=fmt))

    if output:
        dest = Path(output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, "utf-8")

    return content


def _get_documents_dir() -> Path:
    if os.name == "nt":
        try:
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # type: ignore[attr-defined]
            return Path(buf.value)
        except (OSError, ImportError, AttributeError):
            return Path.home() / "Documents"
    if sys.platform == "darwin":
        return Path.home() / "Documents"
    xdg_config = Path.home() / ".config" / "user-dirs.dirs"
    if xdg_config.exists():
        for line in xdg_config.read_text().splitlines():
            if line.startswith("XDG_DOCUMENTS_DIR="):
                value = line.split("=", 1)[1].strip().strip('"')
                value = value.replace("$HOME", str(Path.home()))
                return Path(value)
    lang = _current_lang()
    if lang in ("pt", "es"):
        docs = Path.home() / "Documentos"
        if docs.exists():
            return docs
    return Path.home() / "Documents"


STDOUT_TARGET = "-"


def export_all_formats(dados: dict, nome: str, export_str: str, output: str | None) -> int:
    """Write each requested format. Returns the number of files actually written.

    `output == "-"` writes to stdout instead of a file, following the convention
    curl/jq/pip use. Nothing else may touch stdout on that path -- not the cards,
    not the confirmation line -- otherwise `bom-clima sp -e json -o - | jq` would
    feed jq a card followed by the payload. Those messages go to stderr instead.
    """
    from .display import r_escape, r_print

    formats = [f.strip() for f in export_str.split(",") if f.strip()]
    to_stdout = output == STDOUT_TARGET

    # On the stdout path every human-facing message has to stay off stdout: the
    # format check below runs per format, so `json,pdf` would otherwise print a
    # valid payload followed by an error and leave jq with unparseable input.
    def _warn(message: str) -> None:
        if to_stdout:
            print(message, file=sys.stderr)
        else:
            r_print(message)

    # Resolve eagerly but create lazily: _get_documents_dir() is pure (it only
    # reads), while mkdir must only run when ~/Documents is the destination.
    # Creating it unconditionally failed outright on a read-only $HOME even
    # though --output named a perfectly writable path.
    if not to_stdout:
        documents = _get_documents_dir()
        if output is None:
            documents.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in nome)[:80]

    written = 0
    for fmt in formats:
        fmt = fmt.lower()
        if fmt not in ("json", "csv", "yaml", "xml"):
            _warn(t("invalid_format").format(fmt=fmt))
            continue
        if to_stdout:
            sys.stdout.write(export_data(dados, nome, fmt))
            written += 1
            continue
        if output:
            base, _ = os.path.splitext(output)
            dest = f"{base}.{fmt}"
        else:
            dest = str(documents / f"{safe_name}.{fmt}")
        export_data(dados, nome, fmt, dest)
        written += 1
        # dest embeds the city name, which comes from the geocoding API.
        r_print(t("exported_to").format(path=r_escape(dest)))
    return written
