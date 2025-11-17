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

import shutil
from typing import TYPE_CHECKING

import mp.build_project.post_build.integrations.full_details_json
import mp.core.constants
import mp.core.data_models.integrations.integration
import test_mp.common

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.integrations.integration import BuiltFullDetails, Integration


def test_create_full_details_json(
    tmp_path: Path,
    built_integration: Path,
    full_details: Path,
) -> None:
    base_dir: Path = tmp_path / built_integration.parent.name
    shutil.copytree(built_integration.parent, base_dir)
    integration_path: Path = base_dir / built_integration.name
    py_version: Path = integration_path / mp.core.constants.PYTHON_VERSION_FILE
    py_version.write_text("3.11", encoding="utf-8")
    integration: Integration = (
        mp.core.data_models.integrations.integration.Integration.from_built_path(integration_path)
    )

    actual_full_details: BuiltFullDetails = integration.to_built_full_details()
    mp.build_project.post_build.integrations.full_details_json.write_full_details(
        actual_full_details, tmp_path
    )

    actual, expected = test_mp.common.get_json_content(tmp_path / full_details.name, full_details)
    assert actual == expected
