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

from pydantic import dataclasses

from mp.core import constants
from mp.core.exceptions import NonFatalValidationError
from mp.validate.utils import (
    load_components_defs,
    validate_ssl_parameter_from_yaml,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import YamlFileContent


@dataclasses.dataclass(slots=True, frozen=True)
class SslParameterExistsInConnectorsValidation:
    name: str = "SSL Connectors Validation"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Run validation for SSL parameters in the integration's connectors.

        Args:
            integration_path: The path to the integration directory.

        Raises:
            NonFatalValidationError: If there are any SSL parameter validation errors
                in the integration's connectors.

        """
        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            integration_path, constants.CONNECTORS_DIR
        )

        invalid_connectors_outputs: list[str] = []
        for connector in component_defs.get(constants.CONNECTORS_DIR, []):
            connector_validation_output: str | None = validate_ssl_parameter_from_yaml(connector)
            if connector_validation_output:
                invalid_connectors_outputs.append(connector_validation_output)

        if invalid_connectors_outputs:
            msg = "- " + "\n- ".join(invalid_connectors_outputs)
            raise NonFatalValidationError(msg)
