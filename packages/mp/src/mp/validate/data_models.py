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

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, TypeAlias

if TYPE_CHECKING:
    from typing import TypeAlias

PRE_BUILD: str = "Pre-Build"
BUILD: str = "Build"
POST_BUILD: str = "Post-Build"


class Configurations(NamedTuple):
    only_pre_build: bool


class ContentType(Enum):
    INTEGRATION = "Integration"
    PLAYBOOK = "Playbook"


class ValidationTypes(Enum):
    """Enum representing the various stages of a build process."""

    PRE_BUILD = "Pre-Build"
    BUILD = "Build"
    POST_BUILD = "Post-Build"


class ValidationResults:
    def __init__(self, content_name: str, validation_type: ValidationTypes) -> None:
        self.integration_name: str = content_name
        self.validation_type: ValidationTypes = validation_type
        self.validation_report: ValidationReport = ValidationReport(content_name)
        self.is_success: bool = True


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    validation_name: str
    info: str = ""


@dataclass(slots=True)
class ValidationReport:
    """Data model to store validation errors for a specific content."""

    content_name: str
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
        """Convert the ValidationReport object into a dictionary.

        Returns:
            A dictionary representation of the validation report suitable for JSON export.

        """
        return {
            "integration_name": self.content_name,
            "failed_non_fatal_validations": [
                {"validation_name": issue.validation_name, "info": issue.info}
                for issue in self.failed_non_fatal_validations
            ],
            "failed_fatal_validations": [
                {"validation_name": issue.validation_name, "info": issue.info}
                for issue in self.failed_fatal_validations
            ],
        }


class Validator(Protocol):
    name: str

    def run(self, validation_path: Path) -> None:
        """Execute the validation process on the specified path.

        Args:
            validation_path: A `Path` object pointing to the directory
                or file that needs to be validated.

        """


FullReport: TypeAlias = dict[str, list[ValidationResults]]
ValidationFn: TypeAlias = Callable[[Path], ValidationResults]
