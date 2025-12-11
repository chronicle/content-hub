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

from mp.core import constants
from mp.core.exceptions import NonFatalValidationError
from mp.core.utils import filter_and_map_yaml_files
from mp.validate.utils import (
    extract_name,
    load_components_defs,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import ActionName, YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationHasPingActionValidation:
    name: str = "Ping Action Existence Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check if the integration has a Ping Action.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration doesn't have a Ping Action.

        """
        if validation_path.name in constants.EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING:
            return

        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, constants.ACTIONS_DIR
        )

        ping_action: list[ActionName] = filter_and_map_yaml_files(
            component_defs.get(constants.ACTIONS_DIR, []), _is_ping, extract_name
        )

        if not ping_action:
            msg: str = f"{validation_path.name} doesn't implement a 'ping' action"
            raise NonFatalValidationError(msg)


def _is_ping(yaml_content: YamlFileContent) -> bool:
    """Filter function to check if a component is ping.

    Returns:
        True if the component name is ping.

    """
    return yaml_content.get("name", "").lower() == "ping"
