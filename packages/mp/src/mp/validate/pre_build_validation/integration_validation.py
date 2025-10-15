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

from mp.core.unix import NonFatalCommandError
from mp.validate.validators import IntegrationValidator

if TYPE_CHECKING:
    import pathlib


class IntegrationValidation:
    name: str = "Integration Validation"

    @staticmethod
    def run(integration_path: pathlib.Path) -> None:
        """Check if the integration and its components passes all checks.

        Args:
            integration_path: Path to the integration directory.

        Raises:
        NonFatalCommandError: If the integration is invalid or if another error
                      occurs during the check.

        """
        try:
            integration = IntegrationValidator(integration_path)
            integration.run_all_validations()
        except NonFatalCommandError as e:
            raise NonFatalCommandError(str(e)) from e
