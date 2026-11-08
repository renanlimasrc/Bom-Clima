#
# test_config.py - Tests for Bom Clima
# Copyright (C) 2026  ninrod
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.


from unittest.mock import patch

import pytest

from bom_clima.cli import apply_config_overrides
from bom_clima.config import load_config
from bom_clima.constants import VALID_CONFIG_KEYS


class TestConfig:
    def test_load_default_config(self):
        with patch("bom_clima.config.CONFIG_FILE") as mock_file:
            mock_file.exists.return_value = False
            cfg = load_config()
            assert cfg["unit_system"] == "metric"
            assert cfg["forecast_days"] == 5

    def test_apply_config_overrides_imperial(self):
        cfg = {"unit_system": "metric"}
        args = type("Args", (), {
            "imperial": True, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["unit_system"] == "imperial"

    def test_config_set_inf_does_not_crash(self):
        cfg = {"forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": ["forecast_days=inf"], "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch("bom_clima.cli.save_config"):
            result = apply_config_overrides(cfg, args)
        assert result["forecast_days"] == 5

    def test_apply_config_overrides_hours_days(self):
        cfg = {"forecast_hours": 12, "forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": 24, "days": 7,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["forecast_hours"] == 24
        assert result["forecast_days"] == 7

    def test_apply_config_overrides_days_capped_at_15(self):
        cfg = {"forecast_days": 5}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": 20,
            "no_color": False, "config_set": None, "config_show": False,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        result = apply_config_overrides(cfg, args)
        assert result["forecast_days"] == 15

    def test_apply_config_set_validates_keys(self):
        cfg = {"unit_system": "metric"}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": ["invalid_key=test"],
            "config_show": False, "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch("bom_clima.cli.save_config"):
            result = apply_config_overrides(cfg, args)
        assert "invalid_key" not in result

    def test_valid_config_keys(self):
        assert "unit_system" in VALID_CONFIG_KEYS
        assert "city_default" in VALID_CONFIG_KEYS
        assert "forecast_days" in VALID_CONFIG_KEYS

    def test_config_show_renders_panel(self):
        from bom_clima import cli as cli_mod
        cfg = {"unit_system": "metric", "color": True}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": True,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch.object(cli_mod, "r_panel") as mock_panel, \
             pytest.raises(SystemExit):
            cli_mod.apply_config_overrides(cfg, args)
        mock_panel.assert_called_once()
        content, kwargs = mock_panel.call_args.args[0], mock_panel.call_args.kwargs
        assert "unit_system:" in content
        assert "metric" in content
        assert "color:" in content
        assert "True" in content
        assert kwargs["title"] == "Configuration"

    def test_config_show_syncs_colors(self):
        from bom_clima import cli as cli_mod
        cfg = {"unit_system": "metric", "color": True}
        args = type("Args", (), {
            "imperial": False, "hours": None, "days": None,
            "no_color": False, "config_set": None, "config_show": True,
            "lang": None, "no_cache": False, "verbose": False,
        })()
        with patch.object(cli_mod, "_set_colors_enabled") as mock_set, \
             patch.object(cli_mod, "r_panel"), \
             pytest.raises(SystemExit):
            cli_mod.apply_config_overrides(cfg, args)
        mock_set.assert_called_once_with(True)
