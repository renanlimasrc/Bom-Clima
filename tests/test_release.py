#
# test_release.py - Tests for Bom Clima
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

"""Release hygiene: the version, changelog and packaging metadata must agree.

The version lives only in bom_clima/__init__.py; these tests fail if a bump
forgets the changelog, or if a hardcoded version sneaks back in.
"""

import re
from pathlib import Path

import bom_clima

ROOT = Path(__file__).resolve().parent.parent


class TestReleaseConsistency:
    def test_version_is_a_semver_triple(self):
        assert re.fullmatch(r"\d+\.\d+\.\d+", bom_clima.__version__)

    def test_changelog_has_a_section_for_the_current_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text("utf-8")
        assert f"## [{bom_clima.__version__}]" in changelog

    def test_pyproject_uses_dynamic_version_from_init(self):
        pyproject = (ROOT / "pyproject.toml").read_text("utf-8")
        assert 'dynamic = ["version"]' in pyproject
        assert 'path = "bom_clima/__init__.py"' in pyproject
        hardcoded = re.search(r'(?m)^version = "', pyproject)
        assert hardcoded is None

    def test_readme_badge_tracks_github_releases(self):
        readme = (ROOT / "README.md").read_text("utf-8")
        assert "img.shields.io/github/v/release" in readme
        assert "Version-0." not in readme

    def test_requirements_txt_does_not_come_back(self):
        # dependencies live in pyproject.toml only; a second file drifts
        assert not (ROOT / "requirements.txt").exists()

    def test_arch_packaging_script_reads_version_from_init(self):
        # version lives only in bom_clima/__init__.py; the script used to read
        # ['project']['version'] from pyproject.toml, which is now dynamic
        script = (ROOT / "scripts/package-arch.sh").read_text("utf-8")
        assert "__init__.py" in script
        assert "['project']['version']" not in script
        assert "[\"project\"][\"version\"]" not in script
