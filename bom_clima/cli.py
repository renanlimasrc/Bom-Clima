"""CLI module for Bom Clima — argument parsing and main entry point."""

import argparse
import os
import sys
from typing import Any

from . import __version__
from .api import detect_location, fetch_weather_data, search_city
from .cache import cache_cleanup
from .config import load_config, save_config
from .constants import VALID_CONFIG_KEYS, ensure_app_dir
from .display import (
    HAS_RICH,
    _set_colors_enabled,
    display_best_day,
    display_comparison,
    display_weather,
    r_panel,
    r_print,
    r_rule,
)
from .formatters import export_all_formats, score_days
from .history import add_history, load_history
from .i18n import reset_lang_cache, set_lang, t


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
    disp.add_argument("-a", "--alerts", action="store_true", help=t("help_alerts"))
    disp.add_argument("-q", "--aqi", action="store_true", help=t("help_aqi"))
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
    lines.append(f"    -a, --alerts      {t('help_display_alerts')}")
    lines.append(f"    -q, --aqi         {t('help_display_aqi')}")
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
    r_rule(t("history_title"))
    headers = ["#", t("hist_city"), t("hist_lat"), t("hist_lon"), t("hist_when")]
    rows: list[list[str]] = []
    for idx, entry in enumerate(reversed(history), 1):
        rows.append([
            str(idx),
            entry["city"],
            str(entry["lat"]),
            str(entry["lon"]),
            entry["when"][:16],
        ])
    from .display import r_table
    r_table(headers, rows)
    r_print("")


def apply_config_overrides(cfg: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
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
        cfg["lang"] = args.lang
        reset_lang_cache()
    if args.config_set:
        for pair in args.config_set:
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k not in VALID_CONFIG_KEYS:
                    print(f"Warning: unknown config key '{k}'")
                    continue
                if v.lower() in ("true", "false"):
                    v = v.lower() == "true"
                elif v.isdigit():
                    v = int(v)
                elif v.replace(".", "", 1).isdigit():
                    v = float(v)
                cfg[k] = v
                save_config(cfg)
    _set_colors_enabled(cfg.get("color", True))
    if args.config_show:
        labels = [f"{k}:" for k in cfg]
        max_w = max(len(l) for l in labels) if labels else 0
        content = "\n".join(
            f"  {l}{' ' * (max_w - len(l))} {v}"
            for l, v in zip(labels, cfg.values())
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
) -> None:
    """Export weather data for a city, handling unique filenames for multi-city exports."""
    if output:
        base, ext = os.path.splitext(output)
        safe_nome = nome.replace(" ", "_").replace("/", "_")
        dest = f"{base}_{safe_nome}{ext or '.json'}"
    else:
        dest = None
    export_all_formats(dados, nome, export_fmt, dest)


def _show_vs_yesterday(dados: dict) -> None:
    daily = dados.get("daily", {})
    temps_max = daily.get("temperature_2m_max", [])
    if len(temps_max) < 2:
        return
    yesterday_max = temps_max[0]
    today_max = temps_max[1]
    delta = round(today_max - yesterday_max, 1)
    if delta > 0:
        text = t("vs_warmer").format(delta=f"+{delta}")
    elif delta < 0:
        text = t("vs_colder").format(delta=delta)
    else:
        text = t("vs_same")
    r_panel(text, title=t("vs_yesterday"))


def _fetch_and_display(
    city: str,
    cfg: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, dict, dict]:
    cidade_info = search_city(city, no_cache=args.no_cache)
    past_days = 1 if getattr(args, "vs_yesterday", False) else 0
    dados = fetch_weather_data(
        cidade_info["latitude"],
        cidade_info["longitude"],
        unit_system=cfg.get("unit_system", "metric"),
        include_alerts=args.alerts,
        include_aqi=args.aqi,
        forecast_days=cfg.get("forecast_days", 5),
        past_days=past_days,
        no_cache=args.no_cache,
        verbose=args.verbose,
    )
    nome = cidade_info.get("name", city)
    return nome, dados, cidade_info


def main() -> None:
    ensure_app_dir()
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"\U0001f324\ufe0f  Bom Clima v{__version__}")
        sys.exit(0)

    if args.help:
        show_help()
        sys.exit(0)

    _validate_positive(args.days, "--days")
    _validate_positive(args.hours, "--hours")

    cfg = load_config()
    cfg = apply_config_overrides(cfg, args)

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
            dados = fetch_weather_data(
                loc["lat"], loc["lon"],
                unit_system=cfg.get("unit_system", "metric"),
                include_alerts=args.alerts,
                include_aqi=args.aqi,
                forecast_days=cfg.get("forecast_days", 5),
                past_days=past_days,
                no_cache=args.no_cache,
                verbose=args.verbose,
            )
            display_weather(city_name, dados, cfg)
            if args.vs_yesterday:
                _show_vs_yesterday(dados)
            add_history(city_name, loc["lat"], loc["lon"])
            if args.export:
                export_all_formats(dados, city_name, args.export, args.output)
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
            cities = [default.strip()]
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
        for city in cities:
            try:
                nome, dados, cidade_info = _fetch_and_display(city, cfg, args)
                resultados.append((nome, dados, cfg, cidade_info))
                add_history(city, cidade_info["latitude"], cidade_info["longitude"])
            except ValueError as e:
                print(f"\n{e}\n")
                sys.exit(1)
        display_comparison(resultados)
        if args.export:
            for nome, dados, _, _ in resultados:
                _export_city_data(dados, nome, args.export, args.output)
    elif len(cities) == 1:
        try:
            nome, dados, cidade_info = _fetch_and_display(cities[0], cfg, args)
        except ValueError as e:
            print(f"\n{e}\n")
            sys.exit(1)
        display_weather(nome, dados, cfg, city_info=cidade_info)
        if args.best_day:
            dias = score_days(dados)
            if dias:
                dias.sort(key=lambda x: x[1], reverse=True)
                headers = [t("tbl_date"), t("best_day_score")]
                rows = [[d[0], f"{d[1]:.0f}"] for d in dias[:3]]
                display_best_day(headers, rows, t("best_day"))
        if args.vs_yesterday:
            _show_vs_yesterday(dados)
        add_history(cities[0], cidade_info["latitude"], cidade_info["longitude"])
        if args.export:
            export_all_formats(dados, nome, args.export, args.output)
    else:
        for city in cities:
            try:
                nome, dados, cidade_info = _fetch_and_display(city, cfg, args)
            except ValueError as e:
                print(f"\n{e}\n")
                sys.exit(1)
            display_weather(nome, dados, cfg, city_info=cidade_info)
            if args.vs_yesterday:
                _show_vs_yesterday(dados)
            add_history(city, cidade_info["latitude"], cidade_info["longitude"])
            if args.export:
                _export_city_data(dados, nome, args.export, args.output)
