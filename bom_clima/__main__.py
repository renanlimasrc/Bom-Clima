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

"""Entry point for Bom Clima CLI weather application."""

import contextlib
import sys

from bom_clima.cli import main

if __name__ == "__main__":
    # See bom-clima.py: Windows consoles default to a legacy code page and the
    # cards do not fit in it.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):
            _stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    main()
