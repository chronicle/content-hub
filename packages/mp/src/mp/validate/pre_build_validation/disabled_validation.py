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
from mp.core.exceptions import NonFatalValidationError
from mp.core.utils import filter_yaml_files_and_extract_key
from mp.validate.utils import (
    DEF_FILE_NAME_KEY,
    load_components_defs,
)

if TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import ActionName, ConnectorName, JobName, YamlFileContent


class NoDisabledComponentsInIntegrationValidation:
    name: str = "Disabled Components Validation"

    def run(self, validation_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Check if any of the integration components are marked as disabled.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If any of the integration components are marked as disabled.

        """
        components: list[str] = [
            constants.ACTIONS_DIR,
            constants.JOBS_DIR,
            constants.CONNECTORS_DIR,
        ]
        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, *components
        )

        disabled_actions: list[ActionName] = filter_yaml_files_and_extract_key(
            component_defs.get(constants.ACTIONS_DIR, []), _is_disabled, DEF_FILE_NAME_KEY
        )
        disabled_connectors: list[ConnectorName] = filter_yaml_files_and_extract_key(
            component_defs.get(constants.CONNECTORS_DIR, []), _is_disabled, DEF_FILE_NAME_KEY
        )
        disabled_jobs: list[JobName] = filter_yaml_files_and_extract_key(
            component_defs.get(constants.JOBS_DIR, []), _is_disabled, DEF_FILE_NAME_KEY
        )

        if disabled_actions or disabled_connectors or disabled_jobs:
            msg: str = (
                f"{validation_path.name} contains disabled scripts:"
                f"\nDisabled actions: {', '.join(disabled_actions) or None}"
                f"\nDisabled connectors: {', '.join(disabled_connectors) or None}"
                f"\nDisabled jobs: {', '.join(disabled_jobs) or None}"
            )
            raise NonFatalValidationError(msg)


def _is_disabled(yaml_content: YamlFileContent) -> bool:
    """Filter function to check if a component is disabled.

    Returns:
        True if the component is disabled.

    """
    return not yaml_content.get("is_enabled", True)
