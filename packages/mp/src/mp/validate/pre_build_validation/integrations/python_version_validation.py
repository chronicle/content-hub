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

import dataclasses
from typing import TYPE_CHECKING

import mp.core.constants
from mp.core.data_models.integrations.integration_meta.metadata import PythonVersion
from mp.core.exceptions import FatalValidationError
from mp.validate.utils import load_integration_def

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class PythonVersionValidation:
    name: str = "Python Version Validation"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Check python version file existence, content, and consistency.

        Args:
            integration_path: Path to the integration directory.

        Raises:
            FatalValidationError: If the python version file is missing, empty, or
                inconsistent with pyproject.toml.

        """
        python_version_path: Path = integration_path / mp.core.constants.PYTHON_VERSION_FILE
        if not python_version_path.exists():
            msg = f"Integration is missing a `{mp.core.constants.PYTHON_VERSION_FILE}` file."
            raise FatalValidationError(msg)

        python_version: str = python_version_path.read_text(encoding="utf-8").strip()
        if not python_version:
            msg = f"The `{mp.core.constants.PYTHON_VERSION_FILE}` file is empty."
            raise FatalValidationError(msg)

        integration_def: YamlFileContent = load_integration_def(integration_path)

        metadata_version: str | None = integration_def.get(
            "python_version", PythonVersion.PY_3_11.to_string()
        )

        if python_version != metadata_version:
            msg = (
                f"The version in `{mp.core.constants.PYTHON_VERSION_FILE}` ('{python_version}') "
                f"does not match the version in `{mp.core.constants.DEFINITION_FILE}` "
                f"('{metadata_version}')."
            )
            raise FatalValidationError(msg)
