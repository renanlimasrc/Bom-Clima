"""Formatting helpers for Bom Clima."""

import csv
import io
import json
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


def wind_direction(degrees: float) -> str:
    idx = int((degrees + 11.25) / 22.5) % 16
    return COMPASS[idx]


def wind_arrow(degrees: float) -> str:
    idx = int((degrees + 11.25) / 22.5) % 16
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


def format_time_remaining(timestamp: str) -> str:
    try:
        target = datetime.fromisoformat(timestamp)
        now = datetime.now(target.tzinfo)
        diff = target - now
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
    fallback: dict[str, tuple[str, str]] = {"pt": ("Limpo", "☀️"), "en": ("Clear sky", "☀️"), "es": ("Despejado", "☀️")}
    entry = WMO_CODES.get(code) or WMO_CODES.get(0) or fallback
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
    return f"{icons[phase_idx]} {names.get(lang, names['en'])[phase_idx]}"


def get_moon_phase(date: datetime | None = None) -> int:
    d = date or datetime.now()
    base = datetime(2000, 1, 6)
    diff = (d - base).days
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


def dewpoint_comfort(dp: float, lang: str | None = None) -> str:
    lang = lang or _current_lang()
    levels = DEWPOINT_COMFORT.get(lang, DEWPOINT_COMFORT["en"])
    for threshold, _key, label in levels:
        if dp <= threshold:
            return label
    return levels[-1][2]


def generate_recommendations(dados: dict, cfg: dict) -> list[str]:
    atual = dados.get("current", {})
    diario = dados.get("daily", {})
    temp = atual.get("temperature_2m", 20)
    uv = atual.get("uv_index", 0)
    rain_prob = diario.get("precipitation_probability_max", [0])[0]
    vento = atual.get("wind_speed_10m", 0)
    visibility = atual.get("visibility", 10000)
    recs: list[str] = []
    if rain_prob > 60:
        recs.append(t("rec_umbrella"))
    if uv and float(uv) > 6:
        recs.append(t("rec_sunscreen").format(uv=int(uv)))
    if temp < 15:
        recs.append(t("rec_jacket"))
    if temp > 30:
        recs.append(t("rec_light_clothes"))
    if rain_prob < 20 and 15 <= temp <= 28:
        recs.append(t("rec_good_run"))
    if vento > 40:
        recs.append(t("rec_windy_care"))
    if visibility and float(visibility) < 2000:
        recs.append(t("rec_fog_careful"))
    return recs


def detect_extremes(dados: dict) -> list[str]:
    atual = dados.get("current", {})
    diario = dados.get("daily", {})
    temp_max = max(diario.get("temperature_2m_max", [0])) if diario.get("temperature_2m_max") else 0
    temp_min = min(diario.get("temperature_2m_min", [0])) if diario.get("temperature_2m_min") else 0
    vento = atual.get("wind_speed_10m", 0)
    rain_total = sum(diario.get("precipitation_sum", [0])) if diario.get("precipitation_sum") else 0
    uv = atual.get("uv_index", 0)
    hourly = dados.get("hourly", {})
    cape_vals = hourly.get("cape", [])
    cape = max(cape_vals) if cape_vals else 0
    extremes: list[str] = []
    if temp_max > EXTREME_HEAT_C:
        extremes.append(t("extreme_heat").format(temp=temp_max))
    if temp_min < EXTREME_COLD_C:
        extremes.append(t("extreme_cold").format(temp=temp_min))
    if vento > EXTREME_WIND_KMH:
        extremes.append(t("extreme_wind").format(speed=int(vento)))
    if rain_total > EXTREME_RAIN_DAILY_MM:
        extremes.append(t("extreme_rain").format(precip=int(rain_total)))
    if cape > EXTREME_CAPE:
        extremes.append(t("extreme_storm").format(cape=int(cape)))
    if uv and float(uv) > EXTREME_UV:
        extremes.append(t("extreme_uv").format(uv=int(uv)))
    return extremes


def rain_window_summary(dados: dict) -> list[str]:
    hourly = dados.get("hourly", {})
    if not hourly or not hourly.get("time"):
        return []
    from datetime import datetime as dt
    now = dt.now()
    rainy: list[str] = []
    for i, ts in enumerate(hourly["time"]):
        try:
            ts_dt = dt.fromisoformat(ts)
            hours_diff = (ts_dt - now).total_seconds() / 3600
            if hours_diff < 0 or hours_diff > RAIN_WINDOW_HOURS:
                continue
            prob = hourly["precipitation_probability"][i]
            if prob >= RAIN_PROB_THRESHOLD:
                rainy.append(t("rain_time").format(time=ts_dt.strftime("%H:%M"), prob=prob))
        except (ValueError, IndexError):
            continue
    return rainy


def score_days(dados: dict) -> list[tuple[str, float]]:
    diario = dados.get("daily", {})
    if not diario or not diario.get("time"):
        return []
    from datetime import datetime as dt
    scores: list[tuple[str, float]] = []
    for i in range(len(diario["time"])):
        date_str = diario["time"][i]
        date_dt = dt.fromisoformat(date_str)
        date_label = date_dt.strftime("%d/%m")
        temp_max = diario.get("temperature_2m_max", [0] * (i + 1))[i]
        temp_min = diario.get("temperature_2m_min", [0] * (i + 1))[i]
        rain_prob = diario.get("precipitation_probability_max", [0] * (i + 1))[i]
        wind_max = diario.get("wind_speed_10m_max", [0] * (i + 1))[i]
        sunshine = diario.get("sunshine_duration", [0] * (i + 1))[i]
        score = 100.0
        score -= rain_prob * 1.2
        score -= abs(DAY_SCORE_IDEAL_TEMP - (temp_max + temp_min) / 2) * 3
        score -= wind_max * 0.5
        score += (sunshine / 3600) * 0.5
        scores.append((date_label, max(0, score)))
    return scores


def _to_yaml(nome: str, dados: dict) -> str:
    def _yaml_safe(val: object) -> str:
        s = str(val)
        if any(c in s for c in (":", "#", '"', "'", "\n", "[", "]", "{", "}")):
            return f"'{s}'"
        return s

    lines = [
        f"city: {_yaml_safe(nome)}",
        f"queried_at: {datetime.now().isoformat()}",
        "data:",
        "  current:",
    ]
    atual = dados.get("current", {})
    for key, val in atual.items():
        lines.append(f"    {key}: {_yaml_safe(val)}")
    diario = dados.get("daily", {})
    if diario:
        lines.append("  daily:")
        for key in diario:
            lines.append(f"    {key}: {_yaml_safe(diario[key])}")
    return "\n".join(lines) + "\n"


def _to_xml(nome: str, dados: dict) -> str:
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<weather city="{xml_escape(nome)}" queried_at="{datetime.now().isoformat()}">',
    ]
    atual = dados.get("current", {})
    if atual:
        xml.append("  <current>")
        for key, val in atual.items():
            xml.append(f"    <{key}>{xml_escape(str(val))}</{key}>")
        xml.append("  </current>")
    diario = dados.get("daily", {})
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
        atual = dados["current"]
        diario = dados["daily"]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            t("csv_city"), t("csv_temp"), t("csv_feels"), t("csv_max"), t("csv_min"),
            t("csv_humidity"), t("csv_wind"), t("csv_rain"), t("csv_rain_chance"),
            t("csv_precip"), t("csv_sunrise"), t("csv_sunset"),
        ])
        writer.writerow([
            nome,
            atual["temperature_2m"],
            atual["apparent_temperature"],
            diario["temperature_2m_max"][0],
            diario["temperature_2m_min"][0],
            atual["relative_humidity_2m"],
            atual["wind_speed_10m"],
            atual.get("rain", 0),
            diario["precipitation_probability_max"][0],
            diario["precipitation_sum"][0],
            format_timestamp(diario["sunrise"][0]),
            format_timestamp(diario["sunset"][0]),
        ])
        content = buf.getvalue()
    elif fmt == "yaml":
        content = _to_yaml(nome, dados)
    elif fmt == "xml":
        content = _to_xml(nome, dados)
    else:
        raise ValueError(t("invalid_format").format(fmt=fmt))

    if output:
        Path(output).write_text(content, "utf-8")

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


def export_all_formats(dados: dict, nome: str, export_str: str, output: str | None) -> None:
    from .display import r_print

    formats = [f.strip() for f in export_str.split(",") if f.strip()]
    documents = _get_documents_dir()
    documents.mkdir(exist_ok=True)
    safe_name = nome.replace(" ", "_").replace("/", "_")
    for fmt in formats:
        fmt = fmt.lower()
        if fmt not in ("json", "csv", "yaml", "xml"):
            r_print(t("invalid_format").format(fmt=fmt))
            continue
        if output:
            base, _ = os.path.splitext(output)
            dest = f"{base}.{fmt}"
        else:
            dest = str(documents / f"{safe_name}.{fmt}")
        export_data(dados, nome, fmt, dest)
        r_print(t("exported_to").format(path=dest))
