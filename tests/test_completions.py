#
# test_completions.py - Tests for Bom Clima
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

from pathlib import Path

import pytest

from bom_clima.cli import build_parser

COMPLETIONS_DIR = Path(__file__).resolve().parent.parent / "completions"
COMPLETION_FILES = ("bom-clima.bash", "_bom-clima", "bom-clima.fish")


class TestCompletions:
    """The completion scripts are static files; this is the drift guard.
    A flag added to build_parser() without touching them fails here."""

    def _long_options(self) -> set[str]:
        return {
            option[2:]
            for action in build_parser()._actions
            for option in action.option_strings
            if option.startswith("--")
        }

    @pytest.mark.parametrize("name", COMPLETION_FILES)
    def test_every_long_option_is_completed(self, name):
        text = (COMPLETIONS_DIR / name).read_text("utf-8")
        missing = sorted(opt for opt in self._long_options() if opt not in text)
        assert not missing, f"{name} nao completa: {missing}"
