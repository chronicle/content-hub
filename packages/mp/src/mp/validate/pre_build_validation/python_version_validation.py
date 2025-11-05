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

from mp.core import constants
from mp.core.data_models.integration_meta.metadata import PythonVersion
from mp.core.exceptions import NonFatalValidationError
from mp.validate.utils import load_integration_def

if TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import YamlFileContent


class PythonVersionFileValidation:
    name: str = "Python Version File Validation"

    def run(self, validation_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Validate the integration's python version in the '.python-version' file.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the '.python-version' file doesn't exist, or the
            version in it doesn't match the version in "pyproject.toml".

        """
        py_version_file: pathlib.Path = validation_path / constants.PYTHON_VERSION_FILE

        if not py_version_file.is_file():
            msg = f"Missing {constants.PYTHON_VERSION_FILE} file"
            raise NonFatalValidationError(msg)

        python_version: str = py_version_file.read_text(encoding="utf-8")

        integration_def: YamlFileContent = load_integration_def(validation_path)
        metadata_version: str = integration_def.get(
            "python_version", PythonVersion.PY_3_11.to_string()
        )

        if python_version != metadata_version:
            msg = (
                f"Make sure the version in the {constants.PYTHON_VERSION_FILE} matches"
                f" the lowest supported version configured in {constants.PROJECT_FILE}"
            )
            raise NonFatalValidationError(msg)
