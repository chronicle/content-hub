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

from mp.core.data_models.integration import Integration
from mp.core.unix import NonFatalCommandError

if TYPE_CHECKING:
    import pathlib


class CustomValidation:
    name: str = "Custom Component"

    @staticmethod
    def run(integration_path: pathlib.Path) -> None:
        """Check if the integration and its components are not marked as custom.

        Args:
            integration_path (pathlib.Path): Path to the integration directory.

        Raises:
        NonFatalCommandError: If the integration has a custom component or if another error
                      occurs during the check.

        """
        try:
            integration = Integration.from_non_built_path(integration_path)

            integration.raise_error_if_custom()
        except RuntimeError as e:
            raise NonFatalCommandError(e) from e
        except Exception as e:
            msg = (
                f"Could not perform custom content validation for "
                f"{integration_path.name}'. Reason: {e}"
            )
            raise NonFatalCommandError(msg) from e
