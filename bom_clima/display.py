"""Display module for Bom Clima — Rich and plain text output."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from .formatters import (
    detect_extremes,
    dewpoint_comfort,
    display_width,
    format_duration,
    format_time_remaining,
    format_timestamp,
    generate_recommendations,
    get_aqi_label,
    get_moon_phase,
    get_weekday_name,
    get_wmo,
    moon_phase_name,
    rain_window_summary,
    wind_arrow,
    wind_direction,
)
from .i18n import _current_lang, t

try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console: Console | None = Console(force_terminal=True)
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False

_COLORS_ENABLED = True


def _use_rich() -> bool:
    return HAS_RICH and _COLORS_ENABLED


def r_print(text_str: str) -> None:
    if _use_rich():
        assert console is not None
        console.print(text_str)
    else:
        print(text_str)


def r_rule(title: str, char: str = "=") -> None:
    if _use_rich():
        assert console is not None
        console.rule(f" {title} ", style="bold blue", characters=char)
    else:
        sep = char * 44
        print(f"\n{sep}")
        print(f"  {title}")
        print(sep)


def r_panel(content: str, title: str = "") -> None:
    if _use_rich():
        assert console is not None
        console.print(Panel(content, title=title, border_style="cyan", expand=False, width=None))
    else:
        if title:
            r_rule(title)
        r_print(content)


def _build_rich_table(headers: list[str], rows: list[list[str]], show_header: bool = True) -> "Table":
    table = Table(show_header=show_header, header_style="bold cyan", show_edge=False)
    table.row_styles = ["", "dim"]
    for h in headers:
        table.add_column(h)
    for row in rows:
        table.add_row(*row)
    return table


def r_table(headers: list[str], rows: list[list[str]], title: str = "", show_header: bool = True) -> None:
    if _use_rich():
        assert console is not None
        table: Table | Panel = _build_rich_table(headers, rows, show_header=show_header)
        if title:
            table = Panel(table, title=title, border_style="cyan", expand=False)
        console.print(table)
    else:
        if title:
            r_rule(title)
        col_w = [max(len(str(r[i])) if i < len(r) else 0 for r in rows) for i in range(len(headers))]
        col_w = [max(col_w[i], len(headers[i])) for i in range(len(headers))]
        fmt = "  ".join(f"{{:<{w}}}" for w in col_w)
        if show_header:
            print(fmt.format(*headers))
            print("  ".join("-" * w for w in col_w))
        for row in rows:
            padded = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
            print(fmt.format(*padded))


COLOR_TEMP = [(35, "red"), (28, "yellow"), (18, "green"), (10, "cyan"), (-99, "blue")]
COLOR_RAIN = [(60, "red"), (20, "yellow"), (-1, "green")]


def _colorize(text: str, val: float, steps: Sequence[tuple[float, str]]) -> str:
    if not HAS_RICH:
        return text
    for threshold, color in steps:
        if val > threshold:
            return f"[{color}]{text}[/{color}]"
    return text


def _temp_color(val: float, unit_sym: str) -> str:
    return _colorize(f"{val}{unit_sym}", val, COLOR_TEMP)


def _rain_color(val: int | float) -> str:
    return _colorize(f"{val}%", float(val), COLOR_RAIN)


def _build_temp_bar(temp: float, t_min: float, t_max: float, unit_sym: str, bar_w: int = 14) -> str:
    if t_max <= t_min:
        return ""
    pos = int((temp - t_min) / (t_max - t_min) * bar_w)
    pos = max(0, min(bar_w, pos))
    left = "=" * pos
    right = "=" * (bar_w - pos)
    return f"   {t_min}{unit_sym} [{left}.{right}] {t_max}{unit_sym}"


def format_weather_block(
    nome: str,
    dados: dict,
    cfg: dict[str, Any],
    city_info: dict | None = None,
) -> str:
    atual = dados["current"]
    diario = dados["daily"]
    lang = _current_lang()
    unit_sym = "°F" if cfg.get("unit_system") == "imperial" else "°C"
    wind_unit = "mph" if cfg.get("unit_system") == "imperial" else "km/h"
    precip_unit = "in" if cfg.get("unit_system") == "imperial" else "mm"

    wmo_code = atual.get("weather_code", 0)
    wmo_desc, _wmo_icon = get_wmo(wmo_code, lang)

    location_str = nome
    if city_info:
        parts = [nome]
        if city_info.get("admin1") and city_info["admin1"] != nome:
            parts.append(city_info["admin1"])
        if city_info.get("country"):
            parts.append(city_info["country"])
        location_str = ", ".join(parts)

    entries: list[tuple[str, str, str]] = []
    entries.append(("", location_str, ""))
    try:
        dt_updated = datetime.fromisoformat(atual["time"])
        updated_display = f"{dt_updated.strftime('%H:%M')} ({dt_updated.strftime('%d/%m/%Y')})"
    except ValueError:
        updated_display = atual["time"]
    entries.append(("", t("updated"), updated_display))
    entries.append(("", wmo_desc, ""))

    entries.append(("", "", ""))
    entries.append(("", t("temperature"), f"{atual['temperature_2m']}{unit_sym}"))
    entries.append(("", t("feels_like"), f"{atual['apparent_temperature']}{unit_sym}"))
    entries.append(("", t("max_today"), f"{diario['temperature_2m_max'][0]}{unit_sym}"))
    entries.append(("", t("min_today"), f"{diario['temperature_2m_min'][0]}{unit_sym}"))

    t_now = atual["temperature_2m"]
    t_min = diario["temperature_2m_min"][0]
    t_max = diario["temperature_2m_max"][0]
    bar_line = _build_temp_bar(t_now, t_min, t_max, unit_sym)
    if bar_line:
        entries.append(("  ", "", bar_line))

    entries.append(("", "", ""))
    entries.append(("", t("humidity"), f"{atual['relative_humidity_2m']}%"))
    dir_name = wind_direction(atual["wind_direction_10m"])
    arrow = wind_arrow(atual["wind_direction_10m"])
    entries.append(("", t("wind"), f"{atual['wind_speed_10m']} {wind_unit} {arrow} ({dir_name})"))
    gusts = atual.get("wind_gusts_10m")
    if gusts and gusts > 0:
        entries.append(("", t("wind_gusts"), f"{gusts} {wind_unit}"))
    pressure = atual.get("pressure_msl")
    if pressure:
        entries.append(("", t("pressure"), f"{pressure} {t('pressure_unit')}"))
    cloud = atual.get("cloud_cover")
    if cloud is not None:
        entries.append(("", t("cloud_cover"), f"{cloud}%"))
    dew = atual.get("dew_point_2m")
    if dew is not None:
        comfort = dewpoint_comfort(float(dew), lang)
        entries.append(("", t("dew_point"), f"{dew}{unit_sym} ({comfort})"))
    vis = atual.get("visibility")
    if vis is not None:
        entries.append(("", t("visibility_label"), f"{vis / 1000:.1f} {t('visibility_unit')}"))

    entries.append(("", "", ""))
    entries.append(("", t("rain_now"), f"{atual.get('rain', 0)} {precip_unit}"))
    entries.append(("", t("rain_chance"), f"{diario['precipitation_probability_max'][0]}%"))
    entries.append(("", t("total_precip"), f"{diario['precipitation_sum'][0]} {precip_unit}"))
    entries.append(("", t("rain_hours"), f"{diario['precipitation_hours'][0]} h"))

    entries.append(("", "", ""))
    entries.append(("", t("sunrise"), format_timestamp(diario["sunrise"][0]) + format_time_remaining(diario["sunrise"][0])))
    entries.append(("", t("sunset"), format_timestamp(diario["sunset"][0]) + format_time_remaining(diario["sunset"][0])))
    entries.append(("", t("day_length"), format_duration(diario["daylight_duration"][0])))
    entries.append(("", t("uv_index"), str(atual.get("uv_index", "N/A"))))

    entries.append(("", "", ""))

    aqi_data = dados.get("air_quality", {})
    if aqi_data:
        aqi_val = aqi_data.get("us_aqi", "N/A")
        if aqi_val != "N/A":
            aqi_label = get_aqi_label(float(aqi_val), lang)
            entries.append(("", t("aqi"), f"{aqi_val} ({aqi_label})"))
            if "pm2_5" in aqi_data:
                entries.append(("", t("pm25_label"), f"{aqi_data['pm2_5']} {t('aqi_unit')}"))

    moon = get_moon_phase()
    moon_name = moon_phase_name(moon, lang)
    entries.append(("", t("moon_phase"), moon_name))

    lines: list[str] = []
    sep_lines: list[tuple[str, str]] = []
    for emoji, label, value in entries:
        if not emoji and not label and not value:
            sep_lines.append(("", ""))
            continue
        if emoji == "  " and not label and value:
            lines.append(value)
            continue
        if value:
            full_label = f"{label}:" if label else ""
            sep_lines.append((full_label, value))
        elif label:
            sep_lines.append((label, ""))
        else:
            sep_lines.append((emoji, ""))

    max_label = max((display_width(lbl) for lbl, _ in sep_lines if lbl and lbl.strip()), default=0)

    for label, value in sep_lines:
        if not label and not value:
            lines.append("")
            continue
        if value:
            pad = max_label - display_width(label)
            lines.append(f"{label}{' ' * pad} {value}")
        else:
            lines.append(label)

    return "\n".join(lines)


def display_weather(
    nome: str,
    dados: dict,
    cfg: dict[str, Any],
    city_info: dict | None = None,
    show_forecast: bool = True,
    show_hourly: bool = True,
) -> None:
    global _COLORS_ENABLED
    _COLORS_ENABLED = cfg.get("color", True)
    block = format_weather_block(nome, dados, cfg, city_info=city_info)
    r_panel(block, title=f"  {t('current_weather')} {nome.capitalize()}  ")

    if not show_forecast and not show_hourly:
        r_print("")
        return

    lang = _current_lang()
    unit_sym = "°F" if cfg.get("unit_system") == "imperial" else "°C"

    hourly = dados.get("hourly", {})
    hours = cfg.get("forecast_hours", 6)
    if show_hourly and hourly:
        atual = dados["current"]
        now_str = atual["time"]
        now_dt = datetime.fromisoformat(now_str)
        hourly_headers = [t("tbl_hour"), t("tbl_temp"), t("tbl_rain_pct"), t("tbl_wind"), t("condition_short")]
        hourly_rows: list[list[str]] = []
        wind_unit = "mph" if cfg.get("unit_system") == "imperial" else "km/h"
        for i, ts in enumerate(hourly["time"]):
            ts_dt = datetime.fromisoformat(ts)
            if ts_dt <= now_dt:
                continue
            if len(hourly_rows) >= hours:
                break
            h_code = hourly["weather_code"][i]
            h_desc, _h_icon = get_wmo(h_code, lang)
            hourly_rows.append([
                ts_dt.strftime("%H:%M"),
                _temp_color(hourly["temperature_2m"][i], unit_sym),
                _rain_color(hourly["precipitation_probability"][i]),
                f"{hourly['wind_speed_10m'][i]} {wind_unit}",
                h_desc,
            ])

        if hourly_rows:
            r_table(hourly_headers, hourly_rows, title=t("next_hours"))

    days = cfg.get("forecast_days", 5)
    diario = dados["daily"]
    if show_forecast and len(diario.get("time", [])) > 0:
        forecast_headers = [t("tbl_date"), t("condition_short"), t("tbl_min"), t("tbl_max"), t("tbl_rain_pct")]
        forecast_rows: list[list[str]] = []
        for i in range(min(days, len(diario["time"]))):
            dt = datetime.fromisoformat(diario["time"][i])
            weekday = get_weekday_name(dt, lang)
            data_fmt = dt.strftime(f"%d/%m ({weekday})")
            code = diario["weather_code"][i] if "weather_code" in diario else 0
            _, _icon = get_wmo(code, lang)
            forecast_rows.append([
                data_fmt,
                get_wmo(code, lang)[0],
                _temp_color(diario["temperature_2m_min"][i], unit_sym),
                _temp_color(diario["temperature_2m_max"][i], unit_sym),
                _rain_color(diario["precipitation_probability_max"][i]),
            ])

        r_table(forecast_headers, forecast_rows, title=t("forecast_days").format(n=days))

    alerts = dados.get("alerts", [])
    if alerts:
        r_rule(f"\u26a0\ufe0f {t('alerts')}")
        for alert in alerts:
            alert_lines = [
                f"\U0001f534 {alert.get('event', t('alert_event'))}",
                f"\U0001f4dd {alert.get('description', '')}",
                f"\U0001f550 {t('alert_from')}: {alert.get('start', '')} {t('alert_until')}: {alert.get('end', '')}",
            ]
            r_panel("\n".join(alert_lines))

    extremes = detect_extremes(dados)
    if extremes:
        r_rule(f"\U0001f6a8 {t('alerts')}")
        for ext in extremes:
            r_print(f"  \u26a0\ufe0f  {ext}")
        r_print("")

    recs = generate_recommendations(dados, cfg)
    rain_summary = rain_window_summary(dados)
    rain_now = dados.get("current", {}).get("rain", 0)

    if rain_summary:
        recs.append(f"\U0001f327\ufe0f {t('rain_window')}: {', '.join(rain_summary)}")
    elif not rain_now:
        recs.append(f"\u2705 {t('no_rain_expected')}")

    if recs:
        rec_rows = [[r] for r in recs]
        r_table([""], rec_rows, title=t("recommendations"), show_header=False)
        r_print("")


def display_comparison(
    cidades_dados: list[tuple[str, dict, dict[str, Any], dict | None]],
) -> None:
    global _COLORS_ENABLED
    if cidades_dados:
        first_cfg = cidades_dados[0][2]
        _COLORS_ENABLED = first_cfg.get("color", True)
    blocks: list = []
    for nome, dados, cfg, city_info in cidades_dados:
        block = format_weather_block(nome, dados, cfg, city_info=city_info)
        if _use_rich():
            blocks.append(Panel(block, title=nome, border_style="cyan", padding=(0, 1)))
        else:
            r_panel(block, title=nome)
    if _use_rich() and blocks:
        assert console is not None
        columns = Columns(blocks, equal=True, expand=False, padding=(0, 2))
        console.print(columns)
    r_print("")
