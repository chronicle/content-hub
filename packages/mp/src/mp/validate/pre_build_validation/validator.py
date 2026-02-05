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

from mp.core.exceptions import FatalValidationError, NonFatalValidationError
from mp.validate.data_models import ContentType, ValidationResults, ValidationTypes, Validator
from mp.validate.pre_build_validation.integrations import get_integration_pre_build_validations
from mp.validate.pre_build_validation.playbooks import get_playbooks_pre_build_validations

if TYPE_CHECKING:
    from pathlib import Path


class PreBuildValidations:
    def __init__(self, validation_path: Path, content_type: ContentType) -> None:
        self.validation_path: Path = validation_path
        self.content_type: ContentType = content_type
        self.results: ValidationResults = ValidationResults(
            validation_path.name, ValidationTypes.PRE_BUILD
        )

    def run_pre_build_validation(self) -> None:
        """Run all the pre-build validations."""
        validations: list[Validator] = _get_content_validations(self.content_type)

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


def _get_content_validations(content_type: ContentType) -> list[Validator]:
    if content_type == ContentType.INTEGRATION:
        return get_integration_pre_build_validations()

    if content_type == ContentType.PLAYBOOK:
        return get_playbooks_pre_build_validations()

    return []
