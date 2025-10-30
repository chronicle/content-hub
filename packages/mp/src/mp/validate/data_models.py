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

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeAlias


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    validation_name: str
    info: str = ""


@dataclass(slots=True)
class ValidationReport:
    """Data model to store validation errors for a specific integration."""

    integration_name: str
    failed_non_fatal_validations: list[ValidationIssue] = field(default_factory=list)
    failed_fatal_validations: list[ValidationIssue] = field(default_factory=list)

    def add_non_fatal_validation(self, validation_name: str, info: str) -> None:
        """Add a non-fatal validation issue to the report.

        Args:
            validation_name: The name of the validation that failed.
            info: Detailed information regarding the non-fatal issue.

        """
        self.failed_non_fatal_validations.append(
            ValidationIssue(validation_name=validation_name, info=info)
        )

    def add_fatal_validation(self, validation_name: str, info: str) -> None:
        """Add a fatal validation issue to the report.

        Args:
            validation_name: The name of the validation that failed critically.
            info: Detailed information regarding the fatal issue.

        """
        self.failed_fatal_validations.append(
            ValidationIssue(validation_name=validation_name, info=info)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the ValidationReport object into a dictionary..

        Returns:
            A dictionary representation of the validation report suitable for JSON export.

        """
        return {
            "integration_name": self.integration_name,
            "failed_non_fatal_validations": [
                {"validation_name": issue.validation_name, "info": issue.info}
                for issue in self.failed_non_fatal_validations
            ],
            "failed_fatal_validations": [
                {"validation_name": issue.validation_name, "info": issue.info}
                for issue in self.failed_fatal_validations
            ],
        }


class ValidationTypes(Enum):
    """Enum representing the various stages of a build process."""

    PRE_BUILD = "Pre-Build"
    BUILD = "Build"
    POST_BUILD = "Post-Build"


class ValidationResults:
    def __init__(self, integration_name: str, validation_type: ValidationTypes) -> None:
        self.integration_name: str = integration_name
        self.validation_type: ValidationTypes = validation_type
        self.validation_report: ValidationReport = ValidationReport(integration_name)
        self.is_success: bool = True


FullReport: TypeAlias = dict[str, list[ValidationResults]]
