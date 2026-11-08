#
# test_export.py - Tests for Bom Clima
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


import json
import os
import tempfile
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest

from bom_clima.formatters import (
    _to_xml,
    export_data,
)


class TestExport:
    def test_export_json(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "json")
        data = json.loads(content)
        assert data["city"] == "Sao Paulo"
        assert "data" in data

    def test_export_csv(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "csv")
        assert "city" in content
        assert "temp_current" in content
        assert "Sao Paulo" in content

    def test_export_invalid_format(self, mock_weather_response):
        with pytest.raises(ValueError, match="Invalid format"):
            export_data(mock_weather_response, "Sao Paulo", "pdf")

    def test_export_to_file(self, mock_weather_response):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_data(mock_weather_response, "Sao Paulo", "json", f.name)
            assert os.path.exists(f.name)
            with open(f.name) as fh:
                file_content = json.loads(fh.read())
            assert file_content["city"] == "Sao Paulo"
            os.unlink(f.name)

    def test_export_yaml(self, mock_weather_response):
        yaml = pytest.importorskip("yaml")
        content = export_data(mock_weather_response, "Sao Paulo", "yaml")
        parsed = yaml.safe_load(content)
        assert parsed["city"] == "Sao Paulo"
        assert parsed["data"]["current"]

    def test_export_yaml_quotes_values_that_yaml_would_retype(self):
        """Unquoted scalars are re-read as bool/int/None, corrupting the data."""
        yaml = pytest.importorskip("yaml")
        dados = {
            "current": {"temperature_2m": 20.0, "rain": None, "note": "yes", "mode": "0755"},
            "daily": {},
        }
        parsed = yaml.safe_load(export_data(dados, "X", "yaml"))["data"]["current"]
        assert parsed["temperature_2m"] == 20.0 and isinstance(parsed["temperature_2m"], float)
        assert parsed["rain"] is None
        assert parsed["note"] == "yes"
        assert parsed["mode"] == "0755"

    def test_export_yaml_survives_apostrophes_in_city(self):
        yaml = pytest.importorskip("yaml")
        for city in ("O'Fallon", "Coeur d'Alene", "L'Haÿ-les-Roses"):
            out = export_data({"current": {}, "daily": {}}, city, "yaml")
            assert yaml.safe_load(out)["city"] == city

    def test_export_csv_uses_today_index(self):
        dados = {
            "current": {"time": "2026-08-12T16:00", "temperature_2m": 25,
                        "apparent_temperature": 27, "relative_humidity_2m": 65,
                        "wind_speed_10m": 15, "weather_code": 1, "rain": 0, "uv_index": 5},
            "daily": {"time": ["2026-08-11", "2026-08-12"],
                      "temperature_2m_max": [30, 28], "temperature_2m_min": [19, 18],
                      "precipitation_probability_max": [5, 10], "precipitation_sum": [0, 1],
                      "sunrise": ["2026-08-11T06:29", "2026-08-12T06:30"],
                      "sunset": ["2026-08-11T18:01", "2026-08-12T18:00"]},
        }
        content = export_data(dados, "X", "csv")
        assert "28" in content
        assert "06:30" in content
        assert "06:29" not in content

    def test_export_yaml_serializes_lists(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "yaml")
        assert "'['" not in content

    def test_export_xml(self, mock_weather_response):
        content = export_data(mock_weather_response, "Sao Paulo", "xml")
        assert '<?xml version="1.0"' in content
        assert 'city="Sao Paulo"' in content
        assert "<current>" in content

    def test_xml_escapes_special_chars(self):
        data = {"current": {"city": "Sao<Paulo&Co"}, "daily": {}}
        content = _to_xml("Sao<Paulo&Co", data)
        assert "Sao&lt;Paulo&amp;Co" in content


class TestExportAllFormats:
    def test_export_json(self, mock_weather_response, tmp_path):
        from bom_clima.formatters import export_all_formats
        with patch("bom_clima.formatters._get_documents_dir", return_value=tmp_path):
            export_all_formats(mock_weather_response, "Sao Paulo", "json", None)
            assert (tmp_path / "Sao_Paulo.json").exists()

    def test_export_multiple_formats(self, mock_weather_response, tmp_path):
        from bom_clima.formatters import export_all_formats
        with patch("bom_clima.formatters._get_documents_dir", return_value=tmp_path):
            export_all_formats(mock_weather_response, "Sao Paulo", "json,csv", None)
            assert (tmp_path / "Sao_Paulo.json").exists()
            assert (tmp_path / "Sao_Paulo.csv").exists()


class TestExportUnderOptimizeFlag:
    """export_all_formats used `assert documents is not None` for control flow,
    which python -O strips, turning the else branch into `None / str`."""

    def test_export_without_output_survives_python_optimize_flag(self, tmp_path):
        import subprocess
        import sys as _sys

        code = (
            "from bom_clima.formatters import export_all_formats;"
            "print(export_all_formats({'current': {}, 'daily': {}}, 'X', 'json', None))"
        )
        env = dict(os.environ)
        env["HOME"] = str(tmp_path)
        proc = subprocess.run(
            [_sys.executable, "-O", "-c", code],
            capture_output=True, text=True, env=env,
            cwd=Path(__file__).resolve().parent.parent,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        # r_print emits "Exported to: ..." on its own line; the return value
        # (files written) is the last line. Under the old `assert documents`
        # code this subprocess died with TypeError instead.
        assert proc.stdout.strip().splitlines()[-1] == "1"


class TestYamlXmlRoundTrip:
    """The YAML/XML serializers are hand-rolled; prove the output parses."""

    PAYLOAD: ClassVar[dict] = {
        "current": {"time": "2026-04-29T14:00", "temperature_2m": 25.5, "weather_code": 1},
        "daily": {"time": ["2026-04-29"], "temperature_2m_max": [28.0]},
    }

    def test_yaml_output_parses_with_yaml_loader(self):
        yaml = pytest.importorskip("yaml")

        from bom_clima.formatters import _to_yaml

        city = "O'Brien Corner #5: quoted \"there\""
        parsed = yaml.safe_load(_to_yaml(city, self.PAYLOAD))
        assert parsed["city"] == city
        assert parsed["data"]["current"]["temperature_2m"] == 25.5
        assert parsed["data"]["current"]["weather_code"] == 1

    def test_yaml_multiline_city_stays_parseable(self):
        yaml = pytest.importorskip("yaml")

        from bom_clima.formatters import _to_yaml

        parsed = yaml.safe_load(_to_yaml("line one\nline two", self.PAYLOAD))
        assert parsed["city"].split("\n")[0] == "line one" or "line one" in parsed["city"]

    def test_xml_output_parses_and_unescapes_city(self):
        import xml.etree.ElementTree as ET

        from bom_clima.formatters import _to_xml

        city = 'Sao "Paulo" & <test>'
        parsed = ET.fromstring(_to_xml(city, self.PAYLOAD))
        assert parsed.attrib["city"] == city

    def test_xml_values_with_special_chars_stay_well_formed(self):
        import xml.etree.ElementTree as ET

        from bom_clima.formatters import _to_xml

        dados = {"current": {"time": "2026-04-29T14:00", "description": "a&b\"<'>"},
                 "daily": {}}
        parsed = ET.fromstring(_to_xml("city\"&", dados))
        cells = [el.text for el in parsed.iter("description")]
        assert cells == ["a&b\"<'>"]
