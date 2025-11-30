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

import base64
import unittest.mock
from typing import TYPE_CHECKING

import mp.core.constants
import mp.core.file_utils

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import Products


def test_discover_managers_built(tmp_path: Path) -> None:
    (tmp_path / mp.core.constants.INTEGRATION_DEF_FILE.format(tmp_path.name)).touch()
    (tmp_path / "manager0.py").touch()
    (tmp_path / "manager1.json").touch()

    out_managers_dir: Path = tmp_path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
    out_managers_dir.mkdir(parents=True)
    (out_managers_dir / "manager1.py").touch()
    (out_managers_dir / "manager2.py").touch()

    assert mp.core.file_utils.is_built(tmp_path)
    managers: list[str] = mp.core.file_utils.discover_core_modules(tmp_path)
    assert set(managers) == {"manager1", "manager2"}


def test_discover_managers_not_built(tmp_path: Path) -> None:
    (tmp_path / mp.core.constants.PROJECT_FILE).touch()

    common_scripts_dir: Path = tmp_path / mp.core.constants.CORE_SCRIPTS_DIR
    common_scripts_dir.mkdir(parents=True)
    (common_scripts_dir / "manager1.py").touch()
    (common_scripts_dir / "manager2.py").touch()

    assert not mp.core.file_utils.is_built(tmp_path)
    managers = mp.core.file_utils.discover_core_modules(tmp_path)
    assert set(managers) == {"manager1", "manager2"}


def test_get_integrations_and_groups_from_paths(tmp_path: Path) -> None:
    commercial_dir: Path = tmp_path / mp.core.constants.COMMERCIAL_DIR_NAME
    commercial_dir.mkdir()
    (commercial_dir / "integration1").mkdir()
    (commercial_dir / "integration1" / mp.core.constants.PROJECT_FILE).touch()
    (commercial_dir / "group1").mkdir()
    (commercial_dir / "group1" / "integration2").mkdir()
    (commercial_dir / "group1" / "integration2" / mp.core.constants.PROJECT_FILE).touch()

    community_dir: Path = tmp_path / mp.core.constants.COMMUNITY_DIR_NAME
    community_dir.mkdir()
    (community_dir / "integration3").mkdir()
    (community_dir / "integration3" / mp.core.constants.PROJECT_FILE).touch()
    (community_dir / "group2").mkdir()
    (community_dir / "group2" / "integration4").mkdir()
    (community_dir / "group2" / "integration4" / mp.core.constants.PROJECT_FILE).touch()

    powerups_dir: Path = tmp_path / mp.core.constants.POWERUPS_DIR_NAME
    powerups_dir.mkdir()
    (powerups_dir / "integration5").mkdir()
    (powerups_dir / "integration5" / mp.core.constants.PROJECT_FILE).touch()
    (powerups_dir / "group3").mkdir()
    (powerups_dir / "group3" / "integration6").mkdir()
    (powerups_dir / "group3" / "integration6" / mp.core.constants.PROJECT_FILE).touch()

    products: Products[set[Path]] = mp.core.file_utils.get_integrations_and_groups_from_paths(
        commercial_dir, community_dir, powerups_dir
    )

    assert products.integrations == {
        commercial_dir / "integration1",
        community_dir / "integration3",
        powerups_dir / "integration5",
    }
    assert products.groups == {
        commercial_dir / "group1",
        community_dir / "group2",
        powerups_dir / "group3",
    }


def test_is_python_file(tmp_path: Path) -> None:
    (tmp_path / "test.py").touch()
    (tmp_path / "test.txt").touch()

    assert mp.core.file_utils.is_python_file(tmp_path / "test.py")
    assert not mp.core.file_utils.is_python_file(tmp_path / "test.txt")
    assert not mp.core.file_utils.is_python_file(tmp_path / "not_exists")


def test_is_integration(tmp_path: Path) -> None:
    commercial_dir: Path = tmp_path / mp.core.constants.COMMERCIAL_DIR_NAME
    community_dir: Path = tmp_path / mp.core.constants.COMMUNITY_DIR_NAME
    powerups_dir: Path = tmp_path / mp.core.constants.POWERUPS_DIR_NAME

    integration_dir_comm: Path = community_dir / "integration"
    integration_dir_com: Path = commercial_dir / "integration"
    integration_dir_power: Path = powerups_dir / "integration"

    commercial_dir.mkdir()
    community_dir.mkdir()
    powerups_dir.mkdir()

    integration_dir_comm.mkdir()
    integration_dir_com.mkdir()
    integration_dir_power.mkdir()

    (integration_dir_comm / mp.core.constants.PROJECT_FILE).touch()
    (integration_dir_com / mp.core.constants.PROJECT_FILE).touch()
    (integration_dir_power / mp.core.constants.PROJECT_FILE).touch()

    assert mp.core.file_utils.is_integration(integration_dir_com)
    assert mp.core.file_utils.is_integration(integration_dir_comm)
    assert mp.core.file_utils.is_integration(integration_dir_power)
    assert not mp.core.file_utils.is_integration(tmp_path)


def test_is_group(tmp_path: Path) -> None:
    commercial_dir: Path = tmp_path / mp.core.constants.COMMERCIAL_DIR_NAME
    community_dir: Path = tmp_path / mp.core.constants.COMMUNITY_DIR_NAME
    powerups_dir: Path = tmp_path / mp.core.constants.POWERUPS_DIR_NAME

    commercial_dir.mkdir()
    community_dir.mkdir()
    powerups_dir.mkdir()

    group_dir_commercial: Path = commercial_dir / "group"
    group_dir_community: Path = community_dir / "group"
    group_dir_power: Path = powerups_dir / "group"
    group_dir_commercial.mkdir()
    group_dir_community.mkdir()
    group_dir_power.mkdir()

    (group_dir_community / "integration1").mkdir()
    (group_dir_community / "integration1" / mp.core.constants.PROJECT_FILE).touch()
    (group_dir_commercial / "integration2").mkdir()
    (group_dir_commercial / "integration2" / mp.core.constants.PROJECT_FILE).touch()
    (group_dir_power / "integration3").mkdir()
    (group_dir_power / "integration3" / mp.core.constants.PROJECT_FILE).touch()

    assert mp.core.file_utils.is_group(group_dir_commercial)
    assert mp.core.file_utils.is_group(group_dir_community)
    assert mp.core.file_utils.is_group(group_dir_power)
    assert not mp.core.file_utils.is_group(tmp_path)


def test_get_all_integrations_paths(tmp_path: Path) -> None:
    with unittest.mock.patch(
        "mp.core.file_utils.integrations.file_utils.create_or_get_integrations_path",
        return_value=tmp_path,
    ):
        community_paths = mp.core.file_utils.get_all_integrations_paths(
            mp.core.constants.COMMUNITY_DIR_NAME
        )
        commercial_paths = mp.core.file_utils.get_all_integrations_paths(
            mp.core.constants.COMMERCIAL_DIR_NAME
        )

        expected_community_paths = [
            tmp_path / dir_name
            for dir_name in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT[
                mp.core.constants.COMMUNITY_DIR_NAME
            ]
        ]
        expected_commercial_paths = [
            tmp_path / dir_name
            for dir_name in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT[
                mp.core.constants.COMMERCIAL_DIR_NAME
            ]
        ]
        assert community_paths == expected_community_paths
        assert commercial_paths == expected_commercial_paths


def test_replace_file_content(tmp_path: Path) -> None:
    test_file: Path = tmp_path / "test.txt"
    test_file.write_text("original content", encoding="utf-8")

    def replace_fn(content: str) -> str:
        return content.replace("original", "new")

    mp.core.file_utils.replace_file_content(test_file, replace_fn)
    assert test_file.read_text(encoding="utf-8") == "new content"

    def replace_fn2(content: str) -> str:
        return content.replace("new content", "final content")

    mp.core.file_utils.replace_file_content(test_file, replace_fn2)
    assert test_file.read_text(encoding="utf-8") == "final content"


def test_remove_paths_if_exists_can_remove_files(
    tmp_path: Path,
    mock_get_marketplace_path: str,
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        test_file: Path = tmp_path / "test.txt"
        test_file.touch()
        assert test_file.exists()

        mp.core.file_utils.remove_paths_if_exists(test_file)
        assert not test_file.exists()

        # Check if it fails when a file does not exist
        mp.core.file_utils.remove_paths_if_exists(test_file)
        assert not test_file.exists()


def test_remove_paths_if_exists_can_remove_dirs(
    tmp_path: Path,
    mock_get_marketplace_path: str,
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        test_subdir: Path = tmp_path / "subdir"
        test_subdir.mkdir()
        assert test_subdir.exists()

        mp.core.file_utils.remove_paths_if_exists(test_subdir)
        assert not test_subdir.exists()

        # Check if it fails when a folder does not exist
        mp.core.file_utils.remove_paths_if_exists(test_subdir)
        assert not test_subdir.exists()


def test_is_built(tmp_path: Path) -> None:
    integration_dir: Path = tmp_path / "integration"
    integration_dir.mkdir()

    def_file_name: str = mp.core.constants.INTEGRATION_DEF_FILE.format(
        integration_dir.name,
    )
    (integration_dir / def_file_name).touch()
    assert mp.core.file_utils.is_built(integration_dir)

    (integration_dir / def_file_name).unlink()
    (integration_dir / mp.core.constants.PROJECT_FILE).touch()
    assert not mp.core.file_utils.is_built(integration_dir)
    assert not mp.core.file_utils.is_built(tmp_path)


def test_is_half_built(tmp_path: Path) -> None:
    integration_dir: Path = tmp_path / "integration"
    integration_dir.mkdir()

    def_file_name: str = mp.core.constants.INTEGRATION_DEF_FILE.format(
        integration_dir.name,
    )
    (integration_dir / mp.core.constants.PROJECT_FILE).touch()
    (integration_dir / def_file_name).touch()
    assert mp.core.file_utils.is_half_built(integration_dir)

    (integration_dir / def_file_name).unlink()
    assert not mp.core.file_utils.is_half_built(integration_dir)

    (integration_dir / mp.core.constants.PROJECT_FILE).unlink()
    (integration_dir / def_file_name).touch()
    assert not mp.core.file_utils.is_half_built(integration_dir)
    assert not mp.core.file_utils.is_half_built(tmp_path)


def test_remove_and_create_dir(tmp_path: Path, mock_get_marketplace_path: str) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        test_dir: Path = tmp_path / "test"
        test_dir.mkdir()
        assert test_dir.exists()

        new_file: Path = test_dir / "file.txt"
        new_file.touch()
        assert new_file.exists()

        mp.core.file_utils.recreate_dir(test_dir)

        assert test_dir.exists()
        assert not new_file.exists()


def test_base64_to_png_file_writes_correct_content(tmp_path: Path) -> None:
    sample_bytes: bytes = b"test png data"
    output_file: Path = tmp_path / "test.png"

    mp.core.file_utils.base64_to_png_file(sample_bytes, output_file)

    assert output_file.exists()
    assert output_file.read_bytes() == sample_bytes


def test_text_to_svg_file_writes_correct_content(tmp_path: Path) -> None:
    sample_svg: str = "<svg>test</svg>"
    output_file: Path = tmp_path / "test.svg"

    mp.core.file_utils.text_to_svg_file(sample_svg, output_file)

    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == sample_svg


def test_svg_path_to_text(tmp_path: Path) -> None:
    sample_svg: str = "<svg>test</svg>"
    input_file: Path = tmp_path / "test.svg"
    input_file.write_text(sample_svg, encoding="utf-8")
    non_existent_file = tmp_path / "not_real.svg"

    assert mp.core.file_utils.svg_path_to_text(input_file) == sample_svg
    assert mp.core.file_utils.svg_path_to_text(non_existent_file) is None


def test_png_path_to_bytes(tmp_path: Path) -> None:
    sample_bytes = b"valid png bytes"
    with unittest.mock.patch(
        "mp.core.file_utils.integrations.file_utils.validate_png_content", return_value=sample_bytes
    ):
        input_file = tmp_path / "test.png"
        input_file.write_bytes(sample_bytes)
        non_existent_file = tmp_path / "not_real.png"

        expected_b64_string = base64.b64encode(sample_bytes).decode("utf-8")

        assert mp.core.file_utils.png_path_to_bytes(input_file) == expected_b64_string
        assert mp.core.file_utils.png_path_to_bytes(non_existent_file) is None
