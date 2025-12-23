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
from mp.validate.utils import (
    load_components_defs,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationHasMappingRulesIfHasConnectorValidation:
    name: str = "Mapping Rules Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check if the integration has mapping rules if it has a connector.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration has a connector but doesn't
            have mapping rules.

        """
        if validation_path.name in constants.EXCLUDED_INTEGRATIONS_WITH_CONNECTORS_AND_NO_MAPPING:
            return

        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, constants.CONNECTORS_DIR
        )

        has_connectors: bool = bool(component_defs.get(constants.CONNECTORS_DIR))
        has_mapping: bool = (validation_path / constants.MAPPING_RULES_FILE).is_file()

        if has_connectors and not has_mapping:
            msg: str = (
                f"'{validation_path.name}' has connectors but doesn't have default mapping rules"
            )
            raise NonFatalValidationError(msg)
