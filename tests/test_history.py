#
# test_history.py - Tests for Bom Clima
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


class TestAddHistory:
    def test_add_history(self, tmp_path):
        with (
            patch("bom_clima.history.HISTORY_FILE", tmp_path / "history.json"),
            patch("bom_clima.config.CONFIG_FILE", tmp_path / "config.json"),
        ):
            from bom_clima.history import add_history, load_history
            add_history("TestCity", 1.0, 2.0)
            history = load_history()
            assert len(history) == 1
            assert history[0]["city"] == "TestCity"

    def test_history_limit_zero_empties(self, tmp_path):
        from bom_clima.history import load_history, save_history
        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "history.json"):
            save_history([{"city": "a"}, {"city": "b"}], 0)
            assert load_history() == []


class TestHistoryRegressions:
    def test_load_history_survives_non_list_payload(self, tmp_path):
        from bom_clima.history import add_history, load_history

        for payload in ("null", '{"a":1}', '"sp"', "123"):
            with patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"):
                (tmp_path / "h.json").write_text(payload, "utf-8")
                add_history("TestCity", 1.0, 2.0)
                assert isinstance(load_history(), list)

    def test_save_history_coerces_fractional_limit(self, tmp_path):
        from bom_clima.history import load_history, save_history

        with patch("bom_clima.history.HISTORY_FILE", tmp_path / "h.json"):
            save_history([{"city": "a"}, {"city": "b"}], 50.5)
            assert len(load_history()) == 2
            save_history([{"city": "a"}], None)
            assert isinstance(load_history(), list)

    def test_corrupt_history_is_preserved(self, tmp_path):
        from bom_clima.history import load_history

        hist = tmp_path / "h.json"
        hist.write_text("{corrupt", "utf-8")
        with patch("bom_clima.history.HISTORY_FILE", hist):
            assert load_history() == []
        # Moved aside rather than overwritten on the next write.
        assert (tmp_path / "h.json.corrupt").read_text("utf-8") == "{corrupt"
