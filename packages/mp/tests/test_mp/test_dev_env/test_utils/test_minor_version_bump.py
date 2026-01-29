# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest
import toml
import typer
import yaml

from mp.core.config import get_marketplace_path
from mp.dev_env.sub_commands.integration.minor_version_bump import minor_version_bump

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

INTEGRATIONS_CACHE_FOLDER_PATH: Path = get_marketplace_path() / ".integrations_cache"


@pytest.fixture
def sandbox(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    built_integration: Path,
    non_built_integration: Path,
) -> Iterator[dict[str, Path]]:
    """Creates a per-test sandbox by cloning the built and non-built integration.

    Yields:
        dict[str, Path]: A dictionary with convenient resolved paths:
            - "BUILT": path to the built integration sandbox
            - "NON_BUILT": path to the non-built integration sandbox
            - "DEF_FILE": path to the integration definition file
            - "VERSION_CACHE": path to the version_cache.yaml inside the
              integration-specific cache folder
            - "TMP_ROOT": the test's temporary root directory

    Cleanup:
        After the test finishes, the integration-specific cache directory under
        INTEGRATIONS_CACHE_FOLDER_PATH is removed to avoid cross-test pollution.
    """
    worker_id: str = getattr(request.config, "workerinput", {}).get("workerid", "gw0")
    integration_name: str = f"mock_integration_{worker_id}"

    built_dst: Path = tmp_path / "mock_built_integration" / integration_name
    non_built_dst: Path = tmp_path / "commercial" / integration_name
    built_dst.parent.mkdir(parents=True, exist_ok=True)
    non_built_dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(built_integration, built_dst)
    shutil.copytree(non_built_integration, non_built_dst)

    def_path: Path = built_dst / f"Integration-{integration_name}.def"
    shutil.move(built_dst / "Integration-mock_integration.def", def_path)

    version_cache_path: Path = (
        INTEGRATIONS_CACHE_FOLDER_PATH / integration_name / "version_cache.yaml"
    )

    try:
        yield {
            "BUILT": built_dst,
            "NON_BUILT": non_built_dst,
            "DEF_FILE": def_path,
            "VERSION_CACHE": version_cache_path,
            "TMP_ROOT": tmp_path,
        }
    finally:
        shutil.rmtree(INTEGRATIONS_CACHE_FOLDER_PATH / integration_name, ignore_errors=True)


class TestMinorVersionBump:
    def test_run_first_time_success(self, sandbox: dict[str, Path]) -> None:
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        assert INTEGRATIONS_CACHE_FOLDER_PATH.exists()
        assert sandbox["VERSION_CACHE"].exists()
        assert _load_cached_version(sandbox["VERSION_CACHE"]) == 2.2
        assert _load_built_version(sandbox["DEF_FILE"]) == 2.2

    def test_dependencies_not_changed_success(self, sandbox: dict[str, Path]) -> None:
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        old_version_cached = _load_cached_version(sandbox["VERSION_CACHE"])
        old_version_def_file = _load_built_version(sandbox["DEF_FILE"])

        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        assert _load_cached_version(sandbox["VERSION_CACHE"]) == old_version_cached
        assert _load_built_version(sandbox["DEF_FILE"]) == old_version_def_file

    def test_dependencies_changed_success(self, sandbox: dict[str, Path]) -> None:
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        old_version_cached = _load_cached_version(sandbox["VERSION_CACHE"])
        old_version_def_file = _load_built_version(sandbox["DEF_FILE"])

        _add_dependencies(sandbox["NON_BUILT"])
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        assert _load_cached_version(sandbox["VERSION_CACHE"]) == old_version_cached - 0.1
        assert _load_built_version(sandbox["DEF_FILE"]) == old_version_def_file - 0.1

        _remove_dependencies(sandbox["NON_BUILT"])

    def test_major_version_changed_success(self, sandbox: dict[str, Path]) -> None:
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        old_version_cached = _load_cached_version(sandbox["VERSION_CACHE"])
        old_version_def_file = _load_built_version(sandbox["DEF_FILE"])

        pyproject_path = sandbox["NON_BUILT"] / "pyproject.toml"
        pyproject_data = toml.load(pyproject_path)
        pyproject_data["project"]["version"] = 3.0
        with pyproject_path.open("w") as f:
            toml.dump(pyproject_data, f)

        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)
        assert _load_cached_version(sandbox["VERSION_CACHE"]) == old_version_cached + 1.0
        assert _load_built_version(sandbox["DEF_FILE"]) == old_version_def_file + 1.0

        pyproject_data = toml.load(pyproject_path)
        pyproject_data["project"]["version"] = "2.0"
        with pyproject_path.open("w") as f:
            toml.dump(pyproject_data, f)

    def test_cache_file_invalid_schema_recovers_success(self, sandbox: dict[str, Path]) -> None:
        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)
        cache_file = sandbox["VERSION_CACHE"]
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump({"hash": "some_hash", "next_version_change": 0.1}, f)

        minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

        assert _load_cached_version(sandbox["VERSION_CACHE"]) == 2.2
        assert _load_built_version(sandbox["DEF_FILE"]) == 2.2

    def test_pyproject_toml_missing_raises_error_fail(self, sandbox: dict[str, Path]) -> None:
        (sandbox["NON_BUILT"] / "pyproject.toml").unlink()

        with pytest.raises(typer.Exit):
            minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)

    def test_def_file_missing_raises_error_fail(self, sandbox: dict[str, Path]) -> None:
        sandbox["DEF_FILE"].unlink()

        with pytest.raises(typer.Exit):
            minor_version_bump(sandbox["BUILT"], sandbox["NON_BUILT"], sandbox["BUILT"].name)


def _load_cached_version(version_cache_path: Path) -> float:
    with version_cache_path.open("r", encoding="utf-8") as f:
        versions_cache = yaml.safe_load(f)
        return versions_cache["version"]


def _load_built_version(def_file_path: Path) -> float:
    with def_file_path.open("r", encoding="utf-8") as f:
        def_file = json.load(f)
        return def_file["Version"]


def _add_dependencies(non_built_integration_path: Path) -> None:
    pyproject_path = non_built_integration_path / "pyproject.toml"
    pyproject_data = toml.load(pyproject_path)
    deps = pyproject_data["project"].setdefault("dependencies", [])
    deps.append("numpy==2.2.6")
    with pyproject_path.open("w") as f:
        toml.dump(pyproject_data, f)


def _remove_dependencies(non_built_integration_path: Path) -> None:
    pyproject_path = non_built_integration_path / "pyproject.toml"
    pyproject_data = toml.load(pyproject_path)
    pyproject_data["project"]["dependencies"].pop()
    with pyproject_path.open("w") as f:
        toml.dump(pyproject_data, f)
