#
# test_i18n.py - Tests for Bom Clima
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


import os
from unittest.mock import patch

from bom_clima.i18n import _current_lang, reset_lang_cache, set_lang, t


class TestI18n:
    def test_set_lang_applies_without_persisting(self):
        """`--lang` must not reach ~/.config/bom-clima/lang.

        It used to, so a one-off `bom-clima sp --lang en` overrode the desktop
        locale for every later run -- and the file it wrote shadowed LANG.
        """
        reset_lang_cache()
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("pt")
            mock_file.write_text.assert_not_called()
        assert _current_lang() == "pt"
        reset_lang_cache()

    def test_set_lang_persists_when_asked(self):
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("en", persist=True)
            # The encoding is explicit: without it the file is written in the
            # process's preferred encoding, which is not utf-8 on Windows.
            mock_file.write_text.assert_called_once_with("en", "utf-8")

    def test_set_lang_invalid(self):
        with patch("bom_clima.i18n.LANG_FILE") as mock_file:
            set_lang("fr")
            mock_file.write_text.assert_not_called()

    def test_current_lang_from_env(self):
        reset_lang_cache()
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=False), \
             patch("bom_clima.i18n.LANG_FILE") as mock_file:
            mock_file.exists.return_value = False
            assert _current_lang() == "en"
        reset_lang_cache()

    def test_t_returns_translated_key(self):
        reset_lang_cache()
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}), \
             patch("bom_clima.i18n.LANG_FILE") as mock_file:
            mock_file.exists.return_value = False
            result = t("temperature")
            assert result == "Temperature"


class TestLocalePrecedence:
    def test_lc_all_wins_over_lang(self):
        import bom_clima.i18n as i18n_mod

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            with patch.dict(os.environ, {"LC_ALL": "C", "LANG": "pt_BR.UTF-8"}, clear=True):
                i18n_mod.reset_lang_cache()
                assert i18n_mod._current_lang() == "en"
            with patch.dict(os.environ, {"LC_ALL": "pt_BR.UTF-8", "LANG": "C"}, clear=True):
                i18n_mod.reset_lang_cache()
                assert i18n_mod._current_lang() == "pt"

    def test_lang_file_accepts_regional_code(self):
        import bom_clima.i18n as i18n_mod

        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = True
            lf.read_text.return_value = "pt-BR"
            i18n_mod.reset_lang_cache()
            assert i18n_mod._current_lang() == "pt"

    def test_detection_does_not_mutate_process_locale(self):
        import locale

        import bom_clima.i18n as i18n_mod

        before = locale.setlocale(locale.LC_MESSAGES)
        with patch("bom_clima.i18n.LANG_FILE") as lf:
            lf.exists.return_value = False
            i18n_mod.reset_lang_cache()
            i18n_mod._current_lang()
        assert locale.setlocale(locale.LC_MESSAGES) == before


class TestReferencedKeysExistInEveryLocale:
    """t() falls back to returning the key itself; a key referenced in code but
    missing from a locale lands in the UI as a bare `some_key`. Scan every
    t("literal") in the package and check all three locale files."""

    def test_every_referenced_key_is_defined(self):
        import json
        import re
        from pathlib import Path

        import bom_clima

        src = Path(bom_clima.__file__).parent
        referenced = set()
        for py in src.glob("*.py"):
            referenced.update(re.findall(r'\bt\(\s*"([A-Za-z0-9_]+)"', py.read_text("utf-8")))
        locales = Path(bom_clima.__file__).parent / "locales"
        missing = {}
        for path in sorted(locales.glob("*.json")):
            table = set(json.loads(path.read_text("utf-8")))
            absent = sorted(referenced - table)
            if absent:
                missing[path.name] = absent
        assert not missing, f"chaves referenciadas e nao definidas: {missing}"
