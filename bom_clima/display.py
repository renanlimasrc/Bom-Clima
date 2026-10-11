"""Display module for Bom Clima — Rich and plain text output."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, cast

from .formatters import (
    _at,
    _num,
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
    today_index,
    wind_arrow,
    wind_direction,
)
from .i18n import _current_lang, t

try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.markup import escape as _markup_escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    # force_terminal=None lets Rich auto-detect: forcing it on wrote ANSI escapes
    # into redirected files and pipes, and ignored the NO_COLOR convention.
    console: Console | None = Console(force_terminal=None, no_color=None)
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False

_COLORS_ENABLED = True


def _use_rich() -> bool:
    return HAS_RICH


def _colors_active() -> bool:
    return HAS_RICH and _COLORS_ENABLED


def _style_if_active(style: str) -> str | None:
    return style if _colors_active() else None


def r_escape(text: object) -> str:
    """Neutralise Rich markup in text that did not come from our own code.

    City names, admin regions and cache/history files can contain '[' and ']',
    which Rich parses as markup tags. Unescaped they either crash with
    MarkupError -- not a ValueError, so it escapes the CLI's error handling --
    or silently inject styling into the card.
    """
    if not HAS_RICH:
        return str(text)
    return _markup_escape(str(text))


def r_plain(text: object) -> "Text | str":
    """Render text literally, with no markup interpretation at all."""
    if not HAS_RICH:
        return str(text)
    return Text(str(text))


def _set_colors_enabled(enabled: bool) -> None:
    global _COLORS_ENABLED
    _COLORS_ENABLED = enabled
    if console is not None:
        # None means "auto", which is what lets Rich honour NO_COLOR. Rich's own
        # attribute is typed as a plain bool, hence the cast.
        console.no_color = cast(bool, True if not enabled else None)


def r_print(text_str: str) -> None:
    if _use_rich():
        assert console is not None
        console.print(text_str)
    else:
        print(text_str)


def r_rule(title: str, char: str = "=") -> None:
    if _use_rich():
        assert console is not None
        console.rule(f" {title} ", style=_style_if_active("bold blue") or "", characters=char)
    else:
        sep = char * 44
        print(f"\n{sep}")
        print(f"  {title}")
        print(sep)


def r_panel(content: str, title: str = "") -> None:
    if _use_rich():
        assert console is not None
        # Titles carry city names straight from the geocoding API, so they are
        # rendered as literal Text rather than parsed as markup.
        console.print(Panel(content, title=r_plain(title), border_style="cyan", expand=False, width=None))
    else:
        if title:
            r_rule(title)
        r_print(content)


def _build_rich_table(headers: list[str], rows: list[list[str]], show_header: bool = True) -> "Table":
    table = Table(show_header=show_header, header_style=_style_if_active("bold cyan"), show_edge=False)
    table.row_styles = ["", "dim"] if _colors_active() else ["", ""]
    for h in headers:
        table.add_column(h)
    for row in rows:
        table.add_row(*row)
    return table


def _table_lines(
    headers: list[str],
    rows: list[list[str]],
    show_header: bool = True,
    total_width: int | None = None,
    center: bool = False,
) -> list[str]:
    col_w = [max(len(str(r[i])) if i < len(r) else 0 for r in rows) for i in range(len(headers))]
    col_w = [max(col_w[i], len(headers[i])) for i in range(len(headers))]
    if total_width is not None:
        diff = total_width - sum(col_w) - 2 * (len(headers) - 1)
        if diff > 0:
            total = sum(col_w)
            extra = [int(diff * w / total) for w in col_w]
            extra[-1] += diff - sum(extra)
            col_w = [c + e for c, e in zip(col_w, extra, strict=True)]
    fmt = "  ".join(f"{{:^{w}}}" if center else f"{{:<{w}}}" for w in col_w)
    lines: list[str] = []
    if show_header:
        lines.append(fmt.format(*headers))
        lines.append("  ".join("-" * w for w in col_w))
    for row in rows:
        padded = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        lines.append(fmt.format(*padded))
    return lines


def r_table(headers: list[str], rows: list[list[str]], title: str = "", show_header: bool = True) -> None:
    if _use_rich():
        assert console is not None
        table: Table | Panel = _build_rich_table(headers, rows, show_header=show_header)
        if title:
            table = Panel(table, title=r_plain(title), border_style="cyan", expand=False)
        console.print(table)
    else:
        if title:
            r_rule(title)
        for line in _table_lines(headers, rows, show_header):
            print(line)


BEST_DAY_CARD_WIDTH = 40

# Marker for the temperature bar, which is laid out unpadded at its own
# position rather than as a normal label/value row.
_BAR_SENTINEL = "\x00bar"


def display_best_day(headers: list[str], rows: list[list[str]], title: str) -> None:
    inner = BEST_DAY_CARD_WIDTH - 2
    if _use_rich():
        assert console is not None
        table = _build_rich_table(headers, rows)
        col1 = max(len(headers[1]), 15)
        table.columns[0].width = max(inner - 7 - col1, len(headers[0]))
        table.columns[1].width = col1
        for col in table.columns:
            col.justify = "center"
        console.print(Panel(table, title=title, border_style="cyan", expand=False))
    else:
        sep = "=" * BEST_DAY_CARD_WIDTH
        print(f"\n{sep}")
        print(f"  {title}")
        print(sep)
        lines = _table_lines(headers, rows, total_width=inner, center=True)
        r_print("\n".join(f"  {line}" for line in lines))


COLOR_TEMP = [(35, "red"), (28, "yellow"), (18, "green"), (10, "cyan"), (-99, "blue")]
COLOR_RAIN = [(60, "red"), (20, "yellow"), (-1, "green")]


def _colorize(text: str, val: float, steps: Sequence[tuple[float, str]]) -> str:
    if not _colors_active():
        return text
    # >= on every step: with > the boundary value itself fell through to the
    # next colour, so exactly 28C rendered green instead of yellow.
    for threshold, color in steps:
        if val >= threshold:
            return f"[{color}]{text}[/{color}]"
    return text


def _temp_color(val: float, unit_sym: str) -> str:
    text = f"{val}{unit_sym}"
    # Thresholds are Celsius; imperial values arrive in Fahrenheit.
    compare = (val - 32) * 5 / 9 if unit_sym == "°F" else val
    return _colorize(text, compare, COLOR_TEMP)


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
    # Open-Meteo answers HTTP 200 with a payload missing "current" when a single
    # timeseries is unavailable, and the "current" cells are individually
    # nullable; "daily" series can likewise arrive short or absent. Reads below
    # go through _at()/get() with presence tests so a degraded payload omits
    # rows instead of raising -- --line falls through to this function precisely
    # when "current" is unusable.
    atual = dados.get("current") or {}
    diario = dados.get("daily") or {}
    lang = _current_lang()
    unit = cfg.get("unit_system", "metric")
    unit_sym = "°F" if unit == "imperial" else "°C"
    wind_unit = "mph" if unit == "imperial" else "km/h"
    precip_unit = "in" if unit == "imperial" else "mm"
    idx = today_index(dados)

    # Cells the "current" block may simply not have are skipped rather than
    # rendered as a fabricated default. A .get() default here is not a neutral
    # placeholder: WMO 0 means "Clear sky" and rain 0 means "it is not raining",
    # so the card would state weather it has no reading for. Same rule for every
    # row below, and for the min/max bar, which would otherwise pin its marker
    # at the daily minimum.
    temp_now = atual.get("temperature_2m")

    # Names from the geocoding API are interpolated into a Rich-rendered body,
    # so they must be escaped or they get parsed as markup tags.
    location_str = r_escape(nome)
    if city_info:
        parts = [location_str]
        if city_info.get("admin1") and city_info["admin1"] != nome:
            parts.append(r_escape(city_info["admin1"]))
        if city_info.get("country"):
            parts.append(r_escape(city_info["country"]))
        location_str = ", ".join(parts)

    entries: list[tuple[str, str, str]] = []
    entries.append(("", location_str, ""))

    # Right below the place name: the min/max bar is the day's shape at a
    # glance, so it belongs at the top where the eye lands first.
    # Raw daily cells are tracked separately from their numeric coercion: _num()
    # turns a missing cell into 0.0, which would fabricate a "0.0°C" min/max row
    # and pin the bar marker -- same fabricated-default class as the WMO/rain
    # rows above.
    raw_min = _at(diario.get("temperature_2m_min"), idx)
    raw_max = _at(diario.get("temperature_2m_max"), idx)
    t_min = _num(raw_min)
    t_max = _num(raw_max)
    if temp_now is not None and raw_min is not None and raw_max is not None:
        bar_line = _build_temp_bar(_num(temp_now), t_min, t_max, unit_sym)
        if bar_line:
            # _BAR_SENTINEL marks it for the layout pass: the bar carries its own
            # indent and must not be padded like a label/value row. The old code
            # jumped the queue via an `emoji == "  "` check instead, which put the
            # bar ahead of the city name too.
            entries.append(("", _BAR_SENTINEL, bar_line))

    raw_time = atual.get("time")
    if isinstance(raw_time, str):
        try:
            dt_updated = datetime.fromisoformat(raw_time)
            now_dt: datetime | None = dt_updated
            updated_display = f"{dt_updated.strftime('%H:%M')} ({dt_updated.strftime('%d/%m/%Y')})"
        except ValueError:
            # Unparseable, but still worth showing verbatim; empty falls back to
            # the same "N/A" the absent case uses, so the row is never blank.
            now_dt = None
            updated_display = raw_time or "N/A"
    else:
        # null/absent timestamp: still worth a row, but there is nothing to
        # parse. "N/A" is what the uv/aqi rows below already use.
        now_dt = None
        updated_display = "N/A"
    entries.append(("", t("updated"), updated_display))

    # WMO 0 is a real reading ("Clear sky"), so this tests for presence, not
    # truthiness.
    wmo_code = atual.get("weather_code")
    if wmo_code is not None:
        wmo_desc, _wmo_icon = get_wmo(wmo_code, lang)
        entries.append(("", wmo_desc, ""))

    if temp_now is not None:
        entries.append(("", t("temperature"), f"{temp_now}{unit_sym}"))
    feels = atual.get("apparent_temperature")
    if feels is not None:
        entries.append(("", t("feels_like"), f"{feels}{unit_sym}"))
    if raw_max is not None:
        entries.append(("", t("max_today"), f"{t_max}{unit_sym}"))
    if raw_min is not None:
        entries.append(("", t("min_today"), f"{t_min}{unit_sym}"))

    humidity = atual.get("relative_humidity_2m")
    if humidity is not None:
        entries.append(("", t("humidity"), f"{humidity}%"))
    wind_deg = atual.get("wind_direction_10m") or 0
    dir_name = wind_direction(wind_deg)
    arrow = wind_arrow(wind_deg)
    wind_now = atual.get("wind_speed_10m")
    if wind_now is not None:
        entries.append(("", t("wind"), f"{wind_now} {wind_unit} {arrow} ({dir_name})"))
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
        comfort = dewpoint_comfort(float(dew), lang, unit_system=unit)
        entries.append(("", t("dew_point"), f"{dew}{unit_sym} ({comfort})"))
    vis = atual.get("visibility")
    if vis is not None:
        entries.append(("", t("visibility_label"), f"{vis / 1000:.1f} {t('visibility_unit')}"))

    rain_now = atual.get("rain")
    if rain_now is not None:
        entries.append(("", t("rain_now"), f"{rain_now} {precip_unit}"))
    # Every daily row below is presence-tested via _at(): diario may be {},
    # None-coerced to {} above, or simply miss a series, and a direct
    # diario[...][idx] would raise KeyError on exactly the degraded payloads
    # the current-block hardening was built for.
    rain_chance = _at(diario.get("precipitation_probability_max"), idx)
    if rain_chance is not None:
        entries.append(("", t("rain_chance"), f"{rain_chance}%"))
    total_precip = _at(diario.get("precipitation_sum"), idx)
    if total_precip is not None:
        entries.append(("", t("total_precip"), f"{total_precip} {precip_unit}"))
    rain_hours = _at(diario.get("precipitation_hours"), idx)
    if rain_hours is not None:
        entries.append(("", t("rain_hours"), f"{rain_hours} h"))

    sunrise = _at(diario.get("sunrise"), idx)
    if isinstance(sunrise, str) and sunrise:
        entries.append(("", t("sunrise"), format_timestamp(sunrise) + format_time_remaining(sunrise, now=now_dt)))
    sunset = _at(diario.get("sunset"), idx)
    if isinstance(sunset, str) and sunset:
        entries.append(("", t("sunset"), format_timestamp(sunset) + format_time_remaining(sunset, now=now_dt)))
    day_len = _at(diario.get("daylight_duration"), idx)
    if isinstance(day_len, (int, float)) and not isinstance(day_len, bool):
        entries.append(("", t("day_length"), format_duration(day_len)))
    entries.append(("", t("uv_index"), str(atual.get("uv_index", "N/A"))))

    aqi_data = dados.get("air_quality", {})
    if aqi_data:
        aqi_val = aqi_data.get("us_aqi", "N/A")
        if aqi_val != "N/A":
            aqi_label = get_aqi_label(float(aqi_val), lang)
            entries.append(("", t("aqi"), f"{aqi_val} ({aqi_label})"))
            if "pm2_5" in aqi_data:
                entries.append(("", t("pm25_label"), f"{aqi_data['pm2_5']} {t('aqi_unit')}"))

    # Use the queried location's date rather than the machine's: near local
    # midnight the machine clock can be a day ahead of the city being forecast.
    moon = get_moon_phase(now_dt.replace(tzinfo=None) if now_dt else None)
    moon_name = moon_phase_name(moon, lang)
    entries.append(("", t("moon_phase"), moon_name))

    lines: list[str] = []
    sep_lines: list[tuple[str, str]] = []
    for emoji, label, value in entries:
        if label == _BAR_SENTINEL:
            sep_lines.append((label, value))
            continue
        if value:
            full_label = f"{label}:" if label else ""
            sep_lines.append((full_label, value))
        elif label:
            sep_lines.append((label, ""))
        else:
            sep_lines.append((emoji, ""))

    max_label = max((display_width(lbl) for lbl, val in sep_lines if val and lbl.strip()), default=0)

    for label, value in sep_lines:
        if label == _BAR_SENTINEL:
            # The bar carries its own leading indent and must not be padded.
            lines.append(value)
        elif value:
            pad = max_label - display_width(label)
            lines.append(f"{label}{' ' * pad} {value}")
        else:
            lines.append(label)

    return "\n".join(lines)


def format_at_block(dados: dict, cfg: dict[str, Any], hour: int, minute: int) -> str | None:
    """Describe the weather at a specific hour, as a card body.

    Returns None when the hourly series cannot answer (missing or empty), so
    callers fall back to the regular tables. A time that already passed today
    resolves to the same hour tomorrow: the comparison uses the location's own
    clock (timezone=auto), never the machine's.
    """
    hourly = (dados.get("hourly") or {})
    times = hourly.get("time") if isinstance(hourly, dict) else None
    if not times:
        return None
    current = dados.get("current") or {}
    base = str(current.get("time") or "")[:10] or str(times[0])[:10]
    try:
        target = datetime.fromisoformat(f"{base}T{hour:02d}:{minute:02d}")
    except ValueError:
        return None
    try:
        now_dt = datetime.fromisoformat(str(current.get("time", "")))
    except (ValueError, TypeError):
        now_dt = None
    if now_dt is not None and target.replace(tzinfo=None) <= now_dt.replace(tzinfo=None):
        target += timedelta(days=1)
    pick = -1
    picked_dt = None
    for i, ts in enumerate(times):
        try:
            ts_dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if ts_dt.replace(tzinfo=None) >= target.replace(tzinfo=None):
            pick, picked_dt = i, ts_dt
            break
    if pick < 0 or picked_dt is None:
        return None
    lang = _current_lang()
    unit = cfg.get("unit_system", "metric")
    unit_sym = "°F" if unit == "imperial" else "°C"
    wind_unit = "mph" if unit == "imperial" else "km/h"
    temp = _num(_at(hourly.get("temperature_2m"), pick))
    feels = _num(_at(hourly.get("apparent_temperature"), pick))
    rain_p = _num(_at(hourly.get("precipitation_probability"), pick))
    wind = _num(_at(hourly.get("wind_speed_10m"), pick))
    desc, _icon = get_wmo(int(_num(_at(hourly.get("weather_code"), pick))), lang)
    lines = [
        picked_dt.strftime("%H:%M (%d/%m)"),
        f"{t('temperature')}: {_temp_color(temp, unit_sym)}",
        f"{t('feels_like')}: {feels}{unit_sym}",
        f"{t('rain_chance')}: {_rain_color(rain_p)}",
        f"{t('wind')}: {wind} {wind_unit}",
        desc,
    ]
    return "\n".join(lines)


def display_weather(
    nome: str,
    dados: dict,
    cfg: dict[str, Any],
    city_info: dict | None = None,
    show_forecast: bool = True,
    show_hourly: bool = True,
    at_hour: tuple[int, int] | None = None,
) -> None:
    _set_colors_enabled(cfg.get("color", True))
    block = format_weather_block(nome, dados, cfg, city_info=city_info)
    r_panel(block, title=f"  {t('current_weather')} {nome}  ")

    if at_hour is not None:
        at_block = format_at_block(dados, cfg, at_hour[0], at_hour[1])
        if at_block is not None:
            r_panel(at_block, title=t("at_title").format(time=f"{at_hour[0]:02d}:{at_hour[1]:02d}"))

    if not show_forecast and not show_hourly:
        r_print("")
        return

    lang = _current_lang()
    unit_sym = "°F" if cfg.get("unit_system") == "imperial" else "°C"

    hourly = dados.get("hourly") or {}
    hours = cfg.get("forecast_hours", 6)
    hourly_times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    if show_hourly and hourly_times:
        # Without a usable "current" there is no reference instant to cut the
        # hourly list at, so fall back to wall-clock -- same choice
        # rain_window_summary() makes. datetime.now() is naive, which is what
        # the fromisoformat timestamps below are too.
        now_str = (dados.get("current") or {}).get("time")
        try:
            now_dt = datetime.fromisoformat(now_str) if now_str else datetime.now()
        except (ValueError, TypeError):
            now_dt = datetime.now()
        hourly_headers = [t("tbl_hour"), t("tbl_temp"), t("tbl_rain_pct"), t("tbl_wind"), t("condition_short")]
        hourly_rows: list[list[str]] = []
        wind_unit = "mph" if cfg.get("unit_system") == "imperial" else "km/h"
        for i, ts in enumerate(hourly_times):
            try:
                ts_dt = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                continue
            if ts_dt <= now_dt:
                continue
            if len(hourly_rows) >= hours:
                break
            # Parallel arrays may be short or missing on a degraded payload;
            # _at()/_num() degrade to 0 rather than raising, and the table --
            # unlike the current-conditions card -- cannot omit a column.
            h_code = int(_num(_at(hourly.get("weather_code"), i)))
            h_desc, _h_icon = get_wmo(h_code, lang)
            hourly_rows.append([
                ts_dt.strftime("%H:%M"),
                _temp_color(_num(_at(hourly.get("temperature_2m"), i)), unit_sym),
                _rain_color(_num(_at(hourly.get("precipitation_probability"), i))),
                f"{_num(_at(hourly.get('wind_speed_10m'), i))} {wind_unit}",
                h_desc,
            ])

        if hourly_rows:
            r_table(hourly_headers, hourly_rows, title=t("next_hours"))

    days = cfg.get("forecast_days", 5)
    diario = dados.get("daily") or {}
    daily_times = diario.get("time") if isinstance(diario.get("time"), list) else []
    if show_forecast and daily_times:
        forecast_headers = [t("tbl_date"), t("condition_short"), t("tbl_min"), t("tbl_max"), t("tbl_rain_pct")]
        forecast_rows: list[list[str]] = []
        idx = today_index(dados)
        for i in range(idx, min(idx + days, len(daily_times))):
            try:
                dt = datetime.fromisoformat(daily_times[i])
            except (ValueError, TypeError):
                continue
            weekday = get_weekday_name(dt, lang)
            data_fmt = dt.strftime(f"%d/%m ({weekday})")
            code = int(_num(_at(diario.get("weather_code"), i)))
            _, _icon = get_wmo(code, lang)
            forecast_rows.append([
                data_fmt,
                get_wmo(code, lang)[0],
                _temp_color(_num(_at(diario.get("temperature_2m_min"), i)), unit_sym),
                _temp_color(_num(_at(diario.get("temperature_2m_max"), i)), unit_sym),
                _rain_color(_num(_at(diario.get("precipitation_probability_max"), i))),
            ])

        if forecast_rows:
            r_table(forecast_headers, forecast_rows, title=t("forecast_days").format(n=days))

    extremes = detect_extremes(dados, unit_system=cfg.get("unit_system", "metric"))
    recs = generate_recommendations(dados, cfg)

    if extremes or recs:
        parts: list[str] = []
        for ext in extremes:
            parts.append(f"\u26a0\ufe0f  {ext}")
        for rec in recs:
            parts.append(f"\u2714\ufe0f  {rec}")
        r_panel("\n".join(parts), title=f" {t('alerts_and_recs')} ")


def display_comparison(
    cidades_dados: list[tuple[str, dict, dict[str, Any], dict | None]],
) -> None:
    if cidades_dados:
        _set_colors_enabled(cidades_dados[0][2].get("color", True))
    blocks: list = []
    for nome, dados, cfg, city_info in cidades_dados:
        block = format_weather_block(nome, dados, cfg, city_info=city_info)
        if _use_rich():
            blocks.append(Panel(block, title=r_plain(nome), border_style="cyan", padding=(0, 1)))
        else:
            r_panel(block, title=nome)
    if _use_rich() and blocks:
        assert console is not None
        columns = Columns(blocks, equal=True, expand=False, padding=(0, 2))
        console.print(columns)
    r_print("")
