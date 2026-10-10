"""CLI module for Bom Clima — argument parsing and main entry point."""

import argparse
import contextlib
import os
import sys
from typing import Any

from . import __version__
from .api import detect_location, fetch_weather_data, search_cities
from .cache import cache_cleanup
from .config import _sanitize, load_config, save_config
from .constants import VALID_CONFIG_KEYS, ensure_app_dir
from .display import (
    HAS_RICH,
    _set_colors_enabled,
    display_best_day,
    display_comparison,
    display_weather,
    r_escape,
    r_panel,
    r_print,
)
from .formatters import export_all_formats, rain_window_summary, score_days, today_index, unit_symbols
from .history import add_history, load_history
from .i18n import set_lang, t

_INT_CONFIG_KEYS = ("forecast_days", "forecast_hours", "history_limit")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bom-clima",
        description=t("parser_description"),
        epilog=t("parser_epilog"),
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    search = p.add_argument_group(t("grp_search"))
    search.add_argument("city", nargs="*", help=t("help_city"))
    search.add_argument("-d", "--detect", action="store_true", help=t("help_detect"))
    search.add_argument("-c", "--compare", action="store_true", help=t("help_compare"))

    disp = p.add_argument_group(t("grp_display"))
    disp.add_argument("-D", "--days", type=int, default=None, help=t("help_days") + " (max: 15)")
    disp.add_argument("-H", "--hours", type=int, default=None, help=t("help_hours"))
    disp.add_argument("-q", "--aqi", action="store_true", help=t("help_aqi"))
    disp.add_argument("--at", metavar="HH[:MM]", default=None, help=t("help_at"))
    disp.add_argument("--rain", action="store_true", help=t("help_rain"))
    disp.add_argument("-i", "--imperial", action="store_true", help=t("help_imperial"))
    disp.add_argument("-n", "--no-color", action="store_true", help=t("help_no_color"))

    modes = p.add_argument_group(t("grp_modes"))
    modes.add_argument("-y", "--history", action="store_true", help=t("help_history"))
    modes.add_argument("--no-cache", action="store_true", help=t("no_cache_help"))
    modes.add_argument("--verbose", "-V", action="store_true", help=t("verbose_help"))

    smart = p.add_argument_group(t("grp_smart"))
    smart.add_argument("--best-day", action="store_true", help=t("help_best_day"))
    smart.add_argument("--vs-yesterday", action="store_true", help=t("help_vs_yesterday"))

    export = p.add_argument_group(t("grp_export"))
    export.add_argument("-e", "--export", help=t("help_export_fmt") + " (json, csv, yaml, xml)")
    export.add_argument("--output", "-o", help=t("help_output"))

    cfg_grp = p.add_argument_group(t("grp_config"))
    cfg_grp.add_argument("-l", "--lang", choices=["pt", "en", "es"], help=t("help_lang"))
    cfg_grp.add_argument("-s", "--config-set", metavar="KEY=VALUE", action="append", help=t("help_config_set"))
    cfg_grp.add_argument("-S", "--config-show", action="store_true", help=t("help_config_show"))

    info = p.add_argument_group(t("grp_info"))
    info.add_argument("--help", "-h", action="store_true", help=t("help_help"))
    info.add_argument("--version", "-v", action="store_true", help=t("help_version"))

    return p


def show_help() -> None:
    lines = []
    title = t("help_title")
    sep = "\u2014"
    lines.append(f"  \U0001f324\ufe0f  Bom Clima v{__version__} {sep} {title.split(sep)[1].strip() if sep in title else title}")
    lines.append("")
    lines.append(f"  {t('help_usage')}")
    lines.append("    bom-clima [CITY...] [OPTIONS]")
    lines.append("")
    lines.append(f"  \U0001f4cd {t('help_search')}")
    lines.append(f"    CITY...           {t('help_search_city')}")
    lines.append(f"    -d, --detect      {t('help_search_detect')}")
    lines.append(f"    -c, --compare     {t('help_search_compare')}")
    lines.append("")
    lines.append(f"  \U0001f4ca {t('help_display')}")
    lines.append(f"    -D, --days N      {t('help_display_days')}")
    lines.append(f"    -H, --hours N     {t('help_display_hours')}")
    lines.append(f"    -q, --aqi         {t('help_display_aqi')}")
    lines.append(f"    --at HH[:MM]      {t('help_display_at')}")
    lines.append(f"    --rain            {t('help_display_rain')}")
    lines.append(f"    -i, --imperial    {t('help_display_imperial')}")
    lines.append(f"    -n, --no-color    {t('help_display_color')}")
    lines.append("")
    lines.append(f"  \U0001f504 {t('help_modes')}")
    lines.append(f"    -y, --history     {t('help_modes_history')}")
    lines.append(f"    --no-cache        {t('no_cache_help')}")
    lines.append(f"    -V, --verbose     {t('verbose_help')}")
    lines.append("")
    lines.append(f"  \U0001f4a1 {t('grp_smart')}")
    lines.append(f"    --best-day        {t('help_best_day')}")
    lines.append(f"    --vs-yesterday    {t('help_vs_yesterday')}")
    lines.append("")
    lines.append(f"  \U0001f4be {t('help_export')}")
    lines.append(f"    -e, --export FMT  {t('help_export_format')}")
    lines.append(f"    -o, --output FILE {t('help_export_output')}")
    lines.append("")
    lines.append(f"  \u2699\ufe0f  {t('help_config')}")
    lines.append(f"    -l, --lang LANG   {t('help_config_lang')}")
    lines.append(f"    -s, --config-set K=V  {t('help_config_set')}")
    lines.append(f"    -S, --config-show {t('help_config_show')}")
    lines.append("")
    lines.append(f"  \u2139\ufe0f  {t('help_info')}")
    lines.append(f"    -h, --help        {t('help_info_help')}")
    lines.append(f"    -v, --version     {t('help_info_version')}")
    lines.append("")
    lines.append(f"  {t('help_examples')}")
    lines.append(f"    {t('help_ex_simple')}")
    lines.append(f"    {t('help_ex_compare')}")
    lines.append(f"    {t('help_ex_imperial')}")
    lines.append(f"    {t('help_ex_detect')}")
    lines.append(f"    {t('help_ex_export')}")
    lines.append(f"    {t('help_ex_lang')}")
    lines.append(f"    {t('help_ex_config')}")
    lines.append("")

    content = "\n".join(lines)

    if HAS_RICH:
        from rich.panel import Panel

        from .display import console as rich_console
        assert rich_console is not None
        rich_console.print(Panel(content, title=f"\U0001f324\ufe0f  {t('help_title')}", border_style="bold cyan"))
    else:
        print("=" * 60)
        print(f"  \U0001f324\ufe0f  {t('help_title')}")
        print("=" * 60)
        print(content)


def show_history() -> None:
    history = load_history()
    if not history:
        r_print(f"\U0001f4ed {t('no_history')}")
        return
    headers = ["#", t("hist_city"), t("hist_lat"), t("hist_lon"), t("hist_when")]
    rows: list[list[str]] = []
    for idx, entry in enumerate(reversed(history), 1):
        # history.json is a file the user can edit by hand; its city string goes
        # straight into a Rich table, where '[' would be read as a markup tag.
        rows.append([
            str(idx),
            r_escape(entry.get("city", "")),
            str(entry.get("lat", "")),
            str(entry.get("lon", "")),
            str(entry.get("when", ""))[:16].replace("T", " "),
        ])
    from .display import r_table
    r_table(headers, rows, title=t("history_title"))


def _coerce_config_value(key: str, raw: str) -> Any:
    """Convert a --config-set string into the type its key expects.

    Raises ValueError for anything the key cannot hold. This check is what stops
    a bad value from reaching config.json: history_limit, forecast_days and
    forecast_hours are read back as numbers, and a string there crashes every
    later run, not just the one that set it.
    """
    if key == "lang" and raw.lower() in ("null", "none", ""):
        return None
    if raw.lower() in ("true", "false"):
        value: Any = raw.lower() == "true"
    else:
        try:
            value = int(raw)
        except ValueError:
            try:
                value = float(raw)
            except ValueError:
                value = raw

    if key == "color":
        if not isinstance(value, bool):
            raise ValueError("expected true or false")
    elif key in _INT_CONFIG_KEYS:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("expected an integer")
        if key == "forecast_days" and not 1 <= value <= 15:
            raise ValueError("expected an integer between 1 and 15")
        if key == "forecast_hours" and value < 1:
            raise ValueError("expected an integer of at least 1")
        if key == "history_limit" and value < 0:
            raise ValueError("expected an integer of at least 0")
    elif key == "unit_system" and value not in ("metric", "imperial"):
        raise ValueError("expected metric or imperial")
    elif key == "lang" and value not in ("pt", "en", "es", None):
        raise ValueError("expected pt, en, es or null")
    return value


def apply_config_overrides(cfg: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    # "lang" is documented in DEFAULT_CONFIG but nothing read it, so a value
    # set there (or by hand) had no effect at all.
    if cfg.get("lang") in ("pt", "en", "es"):
        set_lang(cfg["lang"])

    pending: dict[str, Any] = {}
    if args.config_set:
        for pair in args.config_set:
            if "=" not in pair:
                r_print(t("config_set_invalid").format(pair=pair))
                continue
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key not in VALID_CONFIG_KEYS:
                r_print(t("config_key_unknown").format(key=key))
                continue
            try:
                pending[key] = _coerce_config_value(key, value)
            except ValueError as exc:
                r_print(t("config_value_invalid").format(key=key, reason=str(exc)))

    if pending:
        # Persist only what --config-set asked for. Saving `cfg` here would also
        # persist the one-shot flag overrides applied below, so a single
        # `--imperial --days 3 --config-set color=true` would silently make
        # imperial and 3 days the permanent default.
        save_config({**load_config(), **pending})
        cfg.update(pending)
        if pending.get("lang") in ("pt", "en", "es"):
            set_lang(pending["lang"])

    if args.imperial:
        cfg["unit_system"] = "imperial"
    if args.hours is not None:
        cfg["forecast_hours"] = args.hours
    if args.days is not None:
        cfg["forecast_days"] = min(args.days, 15)
    if args.no_color:
        cfg["color"] = False
    if args.lang:
        set_lang(args.lang)

    cfg = _sanitize(cfg)
    _set_colors_enabled(cfg.get("color", True))
    if args.config_show:
        labels = [f"{key}:" for key in cfg]
        max_w = max((len(lbl) for lbl in labels), default=0)
        content = "\n".join(
            f"  {lbl}{' ' * (max_w - len(lbl))} {value}"
            for lbl, value in zip(labels, cfg.values(), strict=True)
        )
        r_panel(content, title=t("config_title"))
        sys.exit(0)
    return cfg


def _validate_positive(value: int | None, flag: str) -> None:
    if value is not None and value < 1:
        print(t("validation_positive").format(flag=flag, value=value))
        build_parser().print_help()
        sys.exit(1)


def _export_city_data(
    dados: dict,
    nome: str,
    export_fmt: str,
    output: str | None,
) -> int:
    """Export weather data for a city, handling unique filenames for multi-city exports."""
    if output:
        base, ext = os.path.splitext(output)
        safe_nome = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in nome)[:80]
        dest = f"{base}_{safe_nome}{ext or '.json'}"
    else:
        dest = None
    return export_all_formats(dados, nome, export_fmt, dest)


def _do_export(dados: dict, nome: str, fmt: str, output: str | None, per_city: bool) -> None:
    """Run an export and exit non-zero when nothing could be written.

    `-e pdf` used to print "invalid format" and exit 0, so scripts could not
    tell a failed export from a successful one.
    """
    written = (
        _export_city_data(dados, nome, fmt, output)
        if per_city
        else export_all_formats(dados, nome, fmt, output)
    )
    if not written:
        sys.exit(1)


def _show_best_day(dados: dict, cfg: dict[str, Any], args: argparse.Namespace) -> None:
    """Render the best-day card. Available on every fetch path, not just the
    single-city one, where --best-day used to be silently ignored."""
    if not getattr(args, "best_day", False):
        return
    dias = score_days(dados, unit_system=cfg.get("unit_system", "metric"))
    if not dias:
        return
    dias.sort(key=lambda x: x[1], reverse=True)
    headers = [t("tbl_date"), t("best_day_score")]
    rows = [[d[0], f"{d[1]:.0f}"] for d in dias[:3]]
    display_best_day(headers, rows, t("best_day"))


def _show_vs_yesterday(dados: dict, unit_system: str = "metric") -> None:
    daily = dados.get("daily", {})
    temps_max = daily.get("temperature_2m_max", [])
    idx = today_index(dados)
    if idx < 1 or len(temps_max) <= idx:
        return
    yesterday_max = temps_max[idx - 1]
    today_max = temps_max[idx]
    delta = round(today_max - yesterday_max, 1)
    t_unit = unit_symbols(unit_system)[0]
    if delta > 0:
        text = t("vs_warmer").format(delta=f"+{delta}", unit=t_unit)
    elif delta < 0:
        text = t("vs_colder").format(delta=delta, unit=t_unit)
    else:
        text = t("vs_same")
    r_panel(text, title=t("vs_yesterday"))


def _show_rain(dados: dict, cfg: dict[str, Any], args: argparse.Namespace) -> None:
    """Render only the 24h rain windows. Available on every fetch path, so
    --rain composes with --compare and multi-city runs instead of being
    silently ignored there."""
    if not getattr(args, "rain", False):
        return
    rainy = rain_window_summary(dados)
    if rainy:
        r_panel("\n".join(rainy), title=t("rain_window"))
    else:
        r_panel(t("no_rain_expected"), title=t("rain_window"))


def _parse_at(raw: str | None) -> tuple[int, int] | None:
    """Parse --at into (hour, minute). Returns None when the flag is absent.

    Raises ValueError for anything outside 00:00-23:59, including bare "24",
    negative values and non-numeric input.
    """
    if raw is None:
        return None
    text = raw.strip()
    parts = text.split(":")
    if len(parts) > 2:
        raise ValueError(t("invalid_at").format(value=raw))
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) == 2 else 0
    except ValueError:
        raise ValueError(t("invalid_at").format(value=raw)) from None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(t("invalid_at").format(value=raw))
    return hour, minute


def _describe_candidate(c: dict) -> str:
    bits = [str(c.get("name", "?"))]
    if c.get("admin1"):
        bits.append(str(c["admin1"]))
    if c.get("country"):
        bits.append(str(c["country"]))
    coords = ""
    if c.get("latitude") is not None and c.get("longitude") is not None:
        coords = f" ({c['latitude']:.2f}, {c['longitude']:.2f})"
    return ", ".join(bits) + coords


def _resolve_city(city: str, no_cache: bool) -> dict:
    """Geocode, always taking the first (most populous) candidate.

    When the query is ambiguous the alternatives are listed on stderr, with a
    hint showing how to refine (city + state, comma-separated — the only form
    the geocoding API understands). There is deliberately no prompt: GeoNames
    holds phantom micro-localities (e.g. a population-less "Guarulhos" in Rio
    de Janeiro), so asking would keep suggesting places that don't exist.
    """
    candidates = search_cities(city, no_cache=no_cache)
    if len(candidates) <= 1:
        return candidates[0]
    picked = candidates[0]
    alternatives = "; ".join(_describe_candidate(c) for c in candidates[1:])
    lines = [
        t("city_ambiguous").format(query=city.strip(), name=picked.get("name", "?")),
        t("city_alternatives").format(alternatives=alternatives),
    ]
    admin1 = candidates[1].get("admin1")
    if admin1:
        lines.append(t("city_refine_hint").format(example=f"{city.strip()}, {admin1}"))
    # Plain print: this is a note, not a card, and Rich would parse any '['
    # in API place names as markup tags.
    print("\n".join(lines), file=sys.stderr)
    return picked


def _fetch_and_display(
    city: str,
    cfg: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, dict, dict]:
    cidade_info = _resolve_city(city, no_cache=args.no_cache)
    past_days = 1 if getattr(args, "vs_yesterday", False) else 0
    dados = fetch_weather_data(
        cidade_info["latitude"],
        cidade_info["longitude"],
        unit_system=cfg.get("unit_system", "metric"),
        include_aqi=args.aqi,
        forecast_days=cfg.get("forecast_days", 5),
        past_days=past_days,
        no_cache=args.no_cache,
        verbose=args.verbose,
    )
    nome = cidade_info.get("name", city)
    return nome, dados, cidade_info


def _resolve_lang(cfg: dict[str, Any], argv: list[str] | None = None) -> None:
    """Settle the language before the parser is built.

    build_parser() calls t() for every help string and the validation messages
    call t() too, so deciding the language later meant that `--lang pt --help`
    and `--lang pt --days 0` both printed English. The `lang` key in
    config.json is documented but used to be ignored entirely.

    The flag wins over the config value.
    """
    tokens = sys.argv[1:] if argv is None else argv
    flag: str | None = None
    for i, token in enumerate(tokens):
        value = None
        if token.startswith("--lang="):
            value = token.split("=", 1)[1]
        elif token in ("--lang", "-l") and i + 1 < len(tokens):
            value = tokens[i + 1]
        if value in ("pt", "en", "es"):
            flag = value
            break

    configured = cfg.get("lang")
    chosen = flag or (configured if configured in ("pt", "en", "es") else None)
    if chosen:
        set_lang(chosen)


def main() -> None:
    # Windows consoles still default to a legacy code page (cp1252/cp437) and
    # the cards are full of emoji and weather glyphs. This lives here rather
    # than only in the bom-clima.py / __main__ shims because the installed
    # console script ([project.scripts] bom-clima) calls main() directly and
    # would otherwise still die with UnicodeEncodeError.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):
            _stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    ensure_app_dir()
    cfg = load_config()
    _resolve_lang(cfg)
    parser = build_parser()
    args = parser.parse_args()

    # Settle colour before anything renders, --help included.
    _set_colors_enabled(cfg.get("color", True) and not args.no_color)

    if args.version:
        print(f"\U0001f324\ufe0f  Bom Clima v{__version__}")
        sys.exit(0)

    if args.help:
        show_help()
        sys.exit(0)

    _validate_positive(args.days, "--days")
    _validate_positive(args.hours, "--hours")

    try:
        at_hour = _parse_at(getattr(args, "at", None))
    except ValueError as e:
        print(f"\n{e}\n")
        sys.exit(1)
    if at_hour is not None and getattr(args, "vs_yesterday", False):
        # --vs-yesterday compares today's max against yesterday's; pinning the
        # view to one hour makes that comparison meaningless, so reject the
        # combination loudly instead of ignoring one of the flags.
        print(f"\n{t('at_vs_yesterday')}\n")
        sys.exit(1)

    cfg = apply_config_overrides(cfg, args)

    if args.output and not args.export:
        # Previously ignored in silence: the forecast rendered, no file appeared
        # and the exit code stayed 0.
        r_print(t("output_without_export"))
        sys.exit(1)

    if args.history:
        show_history()
        sys.exit(0)

    cache_cleanup()

    cities: list[str] = []
    city_arg_provided = bool(args.city)

    if args.detect:
        loc = detect_location()
        if loc:
            city_name = loc.get("city", t("detect_label"))
            if loc.get("country"):
                city_name += f", {loc['country']}"
            print(f"\U0001f4cd {t('detect_label')}: {city_name} (lat: {loc['lat']}, lon: {loc['lon']})")
            past_days = 1 if getattr(args, "vs_yesterday", False) else 0
            try:
                dados = fetch_weather_data(
                    loc["lat"], loc["lon"],
                    unit_system=cfg.get("unit_system", "metric"),
                    include_aqi=args.aqi,
                    forecast_days=cfg.get("forecast_days", 5),
                    past_days=past_days,
                    no_cache=args.no_cache,
                    verbose=args.verbose,
                )
            except ValueError as e:
                print(f"\n{e}\n")
                sys.exit(1)
            display_weather(city_name, dados, cfg, at_hour=at_hour)
            _show_best_day(dados, cfg, args)
            _show_rain(dados, cfg, args)
            if args.vs_yesterday:
                _show_vs_yesterday(dados, unit_system=cfg.get("unit_system", "metric"))
            add_history(city_name, loc["lat"], loc["lon"])
            if args.export:
                _do_export(dados, city_name, args.export, args.output, per_city=False)
            sys.exit(0)
        else:
            print(f"\u26a0\ufe0f {t('detect_fail')}")

    if city_arg_provided:
        raw = " ".join(args.city)
        cities = [c.strip() for c in raw.split(",") if c.strip()]
        if not cities:
            print(t("empty_city"))
            sys.exit(1)
    else:
        default = cfg.get("city_default")
        if default and isinstance(default, str) and default.strip():
            # Same comma splitting as the CLI positional: without it,
            # city_default="a,b" produced one geocoding query for "a,b".
            cities = [c.strip() for c in default.split(",") if c.strip()]
        else:
            prompt = t("enter_city")
            try:
                city_input = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(0)
            if not city_input:
                print(t("empty_city"))
                sys.exit(1)
            cities = [c.strip() for c in city_input.split(",") if c.strip()]
            if not cities:
                print(t("empty_city"))
                sys.exit(1)

    if args.compare and len(cities) > 1:
        resultados: list[tuple[str, dict, dict[str, Any], dict | None]] = []
        falhas: list[str] = []
        for city in cities:
            try:
                nome, dados, cidade_info = _fetch_and_display(city, cfg, args)
                resultados.append((nome, dados, cfg, cidade_info))
                add_history(city, cidade_info["latitude"], cidade_info["longitude"])
            except ValueError as e:
                falhas.append(f"{city}: {e}")
        if not resultados:
            print("\n".join(falhas))
            sys.exit(1)
        display_comparison(resultados)
        # These flags were documented as city-agnostic but only the multi-city
        # branch rendered them.
        if args.vs_yesterday:
            for _nome, dados, _cfg, _info in resultados:
                _show_vs_yesterday(dados, unit_system=cfg.get("unit_system", "metric"))
        for _nome, dados, _cfg, _info in resultados:
            _show_best_day(dados, cfg, args)
        for _nome, dados, _cfg, _info in resultados:
            _show_rain(dados, cfg, args)
        if args.export:
            for nome, dados, _, _ in resultados:
                _do_export(dados, nome, args.export, args.output, per_city=True)
        if falhas:
            # Partial success is worth showing; only fail the run if nothing worked.
            print("\n".join(falhas), file=sys.stderr)
            sys.exit(1)
    elif len(cities) == 1:
        try:
            nome, dados, cidade_info = _fetch_and_display(cities[0], cfg, args)
        except ValueError as e:
            print(f"\n{e}\n")
            sys.exit(1)
        display_weather(nome, dados, cfg, city_info=cidade_info, at_hour=at_hour)
        _show_best_day(dados, cfg, args)
        _show_rain(dados, cfg, args)
        if args.vs_yesterday:
            _show_vs_yesterday(dados, unit_system=cfg.get("unit_system", "metric"))
        add_history(cities[0], cidade_info["latitude"], cidade_info["longitude"])
        if args.export:
            _do_export(dados, nome, args.export, args.output, per_city=False)
    else:
        for city in cities:
            try:
                nome, dados, cidade_info = _fetch_and_display(city, cfg, args)
            except ValueError as e:
                print(f"\n{e}\n")
                sys.exit(1)
            display_weather(nome, dados, cfg, city_info=cidade_info, at_hour=at_hour)
            _show_best_day(dados, cfg, args)
            _show_rain(dados, cfg, args)
            if args.vs_yesterday:
                _show_vs_yesterday(dados, unit_system=cfg.get("unit_system", "metric"))
            add_history(city, cidade_info["latitude"], cidade_info["longitude"])
            if args.export:
                _do_export(dados, nome, args.export, args.output, per_city=True)
