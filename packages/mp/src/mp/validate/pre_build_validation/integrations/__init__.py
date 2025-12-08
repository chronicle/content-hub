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

from mp.core.exceptions import FatalValidationError, NonFatalValidationError
from mp.validate.data_models import ValidationResults, ValidationTypes

from .custom_validation import NoCustomComponentsInIntegrationValidation
from .disabled_validation import NoDisabledComponentsInIntegrationValidation
from .documentation_link_validation import IntegrationHasDocumentationLinkValidation
from .mapping_rules_validation import IntegrationHasMappingRulesIfHasConnectorValidation
from .ping_validation import IntegrationHasPingActionValidation
from .required_dependencies_validation import RequiredDevDependenciesValidation
from .structure_validation import IntegrationFileStructureValidation
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
    def __init__(self, validation_path: Path) -> None:
        self.validation_path: Path = validation_path
        self.results: ValidationResults = ValidationResults(
            validation_path.name, ValidationTypes.PRE_BUILD
        )

    def run_pre_build_validation(self) -> None:
        """Run all the pre-build validations."""
        validations: list[Validator] = get_priority_validations() + get_validations()

        for validator in validations:
            try:
                validator.run(self.validation_path)

            except NonFatalValidationError as e:
                self._handle_non_fatal_error(validator.name, str(e))

            except FatalValidationError as e:
                self._handle_fatal_error(validator.name, str(e))
                return

    def _handle_fatal_error(self, validation_name: str, error_msg: str) -> None:
        self.results.validation_report.add_fatal_validation(validation_name, error_msg)
        self.results.is_success = False

    def _handle_non_fatal_error(self, validation_name: str, error_msg: str) -> None:
        self.results.validation_report.add_non_fatal_validation(validation_name, error_msg)
        self.results.is_success = False


def get_validations() -> list[Validator]:
    """Get a list of all available pre-build validations, that are not priority.

    Returns:
        A list of all `Validator` instances.

    """
    return [
        UvLockValidation(),
        VersionBumpValidation(),
        RequiredDevDependenciesValidation(),
        NoCustomComponentsInIntegrationValidation(),
        NoDisabledComponentsInIntegrationValidation(),
        IntegrationHasPingActionValidation(),
        IntegrationHasMappingRulesIfHasConnectorValidation(),
        IntegrationHasDocumentationLinkValidation(),
    ]


def get_priority_validations() -> list[Validator]:
    """Get a list of the available pre-build validations, that should run first.

    Returns:
        A list of all priority `Validator` instances.

    """
    return [
        IntegrationFileStructureValidation(),
    ]
