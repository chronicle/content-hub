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

from typing import TYPE_CHECKING

import mp.build_project.restructure.integrations.dependencies
import mp.core.constants

if TYPE_CHECKING:
    from pathlib import Path

    from mp.build_project.restructure.integrations.dependencies import Dependencies


TOML_CONTENT: str = """
[project]
name = "mock"
version = "1.0.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "me", email = "me@google.com" }
]
requires-python = ">=3.11"
dependencies = ["black>=24.10.0"]
"""


def test_restructure(tmp_path: Path) -> None:
    integration_path: Path = tmp_path / "integration"
    integration_path.mkdir()
    integration_out_path = tmp_path / "integration_out"
    integration_out_path.mkdir()
    dependencies: Dependencies = (
        mp.build_project.restructure.integrations.dependencies.Dependencies(
            path=integration_path,
            out_path=integration_out_path,
        )
    )

    pyproject_path: Path = dependencies.path / mp.core.constants.PROJECT_FILE
    pyproject_path.write_text(TOML_CONTENT, encoding="utf-8")

    dependencies.restructure()

    deps_path: Path = dependencies.out_path / mp.core.constants.OUT_DEPENDENCIES_DIR
    assert list(deps_path.iterdir())
