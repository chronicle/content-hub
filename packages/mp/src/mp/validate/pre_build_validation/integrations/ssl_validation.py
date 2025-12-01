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
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from mp.core.exceptions import NonFatalValidationError
from mp.validate.utils import load_components_defs, load_integration_def

if TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import YamlFileContent


class SSLValidation:
    name: str = "SSL Validation"

    def run(self, integration_path: pathlib.Path) -> None:  # noqa: PLR6301
        """Run validation for SSL parameters in the integration and its connectors.

        Args:
            integration_path: The path to the integration directory.

        Raises:
            NonFatalValidationError: If there are any SSL parameter validation errors
                in the integration or its connectors.

        """
        integration_def: YamlFileContent = load_integration_def(integration_path)

        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            integration_path, constants.CONNECTORS_DIR
        )

        integration_validation_output: str | None = validate_ssl_parameter_from_yaml(
            integration_def
        )

        invalid_connectors_outputs: list[str] = []
        for connector in component_defs.get(constants.CONNECTORS_DIR, []):
            connector_validation_output: str | None = validate_ssl_parameter_from_yaml(connector)
            if connector_validation_output:
                invalid_connectors_outputs.append(connector_validation_output)

        if integration_validation_output or invalid_connectors_outputs:
            msg = (
                f"Integration '{integration_path.name}' has problems with SSL parameter:"
                f"\n  - In integration definition: {integration_validation_output}"
                f"\n  - In connectors: {', '.join(invalid_connectors_outputs) or 'None'}"
            )
            raise NonFatalValidationError(msg)


def validate_ssl_parameter_from_yaml(yaml_content: YamlFileContent) -> str | None:
    """Filter function to check if a component has a valid SSL parameter or is in excluded list.

    Returns:
        An error message if the component's ssl parameter is not valid, else None.

    """
    return _validate_ssl_parameter(yaml_content["name"], yaml_content.get("parameters", []))


def _validate_ssl_parameter(
    script_name: str,
    parameters: list[YamlFileContent],
) -> str | None:
    """Validate the Verify SSL parameter.

    Validates the presence and correctness of a 'Verify SSL' parameter in the provided
    integration or connector's parameters. Ensures that the parameter exists, is of the
    correct type, and has the correct default value unless the script is explicitly
    excluded from verification.

    Args:
        script_name: The name of the integration or connector script.
        parameters: collection of parameters associated with the component.

    Returns:
        An error message if the parameter is invalid, else None.

    """
    if script_name in constants.EXCLUDED_NAMES_WITHOUT_VERIFY_SSL:
        return None

    ssl_param: YamlFileContent = next(
        (p for p in parameters if p["name"] in constants.VALID_SSL_PARAM_NAMES),
        None,
    )
    msg: str
    if ssl_param is None:
        msg = f"{script_name} is missing a 'Verify SSL' parameter"

    elif ssl_param["type"] != ScriptParamType.BOOLEAN.to_string():
        msg = f"The 'verify ssl' parameter in {script_name} must be of type 'boolean'"

    elif script_name in constants.EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE:
        return None

    elif not ssl_param["default_value"]:
        msg = f"The default value of the 'Verify SSL' param in {script_name} must be a boolean true"
    else:
        return None

    return msg
