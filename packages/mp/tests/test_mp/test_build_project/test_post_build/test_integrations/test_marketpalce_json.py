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

import mp.build_project.post_build.integrations.marketplace_json
import mp.core.constants
import test_mp.common

if TYPE_CHECKING:
    from pathlib import Path


def test_write_marketplace_json(
    tmp_path: Path,
    built_integration: Path,
    marketplace_json: Path,
) -> None:
    commercial: Path = tmp_path / mp.core.constants.COMMERCIAL_REPO_NAME
    shutil.copytree(built_integration.parent, commercial, dirs_exist_ok=True)

    mp.build_project.post_build.integrations.marketplace_json.write_marketplace_json(commercial)

    actual, expected = test_mp.common.get_json_content(
        actual=commercial / marketplace_json.name,
        expected=marketplace_json,
    )
    assert actual == expected
