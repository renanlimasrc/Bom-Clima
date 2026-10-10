#!/usr/bin/env python3
#
# bom-clima.py - Query weather for cities using the Open-Meteo API.
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

"""Backward-compatible entry point — delegates to bom_clima.cli:main (Bom Clima)."""

import contextlib
import sys

from bom_clima.cli import main

if __name__ == "__main__":
    # Windows consoles still default to a legacy code page (cp1252/cp437) and the
    # cards are full of emoji, arrows and weather glyphs. Without this even
    # `--version` dies with UnicodeEncodeError on a supported platform.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):
            _stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    main()
