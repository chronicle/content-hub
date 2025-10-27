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

from typing import TYPE_CHECKING, Protocol

import typer

from mp.core.exceptions import FatalValidationError, NonFatalValidationError
from mp.validate.data_models import ValidationResults, ValidationTypes

from .required_dependencies_validation import RequiredDevDependenciesValidation
from .uv_lock_validation import UvLockValidation as UvLockValidation
from .version_bump_validation import VersionBumpValidation as VersionBumpValidation

if TYPE_CHECKING:
    from pathlib import Path


class Validator(Protocol):
    name: str

    def run(self, validation_path: Path) -> None:
        """Execute the validation process on the specified path.

        Args:
            validation_path: A `Path` object pointing to the directory
                or file that needs to be validated.

        """


class PreBuildValidations:
    def __init__(self, integration_path: Path) -> None:
        self.integration_path: Path = integration_path
        self.results: ValidationResults = ValidationResults(
            integration_path.name, ValidationTypes.PRE_BUILD
        )

    def run_pre_build_validation(self) -> None:
        """Run all the pre-build validations.

        Raises:
            typer.Exit: If a `FatalValidationError` is encountered during any
                of the validation checks.

        """
        for validator in self._get_validation():
            try:
                validator.run(self.integration_path)

            except NonFatalValidationError as e:
                self.results.validation_report.add_non_fatal_validation(validator.name, str(e))
                self.results.is_success = False

            except FatalValidationError as error:
                raise typer.Exit(code=1) from error

    @classmethod
    def _get_validation(cls) -> list[Validator]:
        return [UvLockValidation(), VersionBumpValidation(), RequiredDevDependenciesValidation()]
