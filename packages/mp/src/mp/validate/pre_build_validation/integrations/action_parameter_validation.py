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
from mp.core.data_models.integrations.action.parameter import ActionParameter, ActionParamType
from mp.core.exceptions import NonFatalValidationError
from mp.core.utils import filter_and_map_yaml_files
from mp.validate.utils import DEF_FILE_NAME_KEY, load_components_defs

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import ActionName, YamlFileContent

PARAMETERS_KEY: str = "parameters"
OPT_PARAMS: frozenset[ActionParamType] = frozenset({
    ActionParamType.from_string("DDL"),
    ActionParamType.from_string("MULTI_CHOICE_PARAMETER"),
    ActionParamType.from_string("MULTI_VALUES"),
})


@dataclasses.dataclass(slots=True, frozen=True)
class ActionParametersValuesValidation:
    name: str = "Action Parameters Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Validate all actions parameters type, default value, and optional values.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If the integration has actions with invalid parameters.

        """
        component_defs: dict[str, list[YamlFileContent]] = load_components_defs(
            validation_path, constants.ACTIONS_DIR
        )

        actions_data: list[tuple[ActionName, list[ActionParameter]]] = filter_and_map_yaml_files(
            component_defs.get(constants.ACTIONS_DIR, []),
            _has_parameters,
            _extract_name_and_parameters,
        )

        invalid_multiple_options: dict[ActionName, list[str]] = {}
        invalid_non_multiple_options: dict[ActionName, list[str]] = {}
        invalid_default_value: dict[ActionName, list[str]] = {}

        for action_name, action_parameters in actions_data:
            for parameter in action_parameters:
                param_name: str = parameter["name"]
                param_type: ActionParamType = ActionParamType.from_string(parameter["type"])
                optional_values: list[str] | None = parameter.get("optional_values")
                default_value: str | bool | float | int | None = parameter.get("default_value")
                if _is_optional_values_type(param_type) and optional_values is None:
                    invalid_multiple_options.setdefault(action_name, []).append(param_name)
                elif optional_values is not None and not _is_optional_values_type(param_type):
                    invalid_non_multiple_options.setdefault(action_name, []).append(param_name)

                if not _is_valid_default_value(optional_values, default_value):
                    invalid_default_value.setdefault(action_name, []).append(param_name)

        if invalid_multiple_options or invalid_non_multiple_options or invalid_default_value:
            msg = (
                f"Integration '{validation_path.name}' contains actions with invalid parameters:"
                f"\n  - Invalid multiple options parameters: "
                f"{_format_error_dict(invalid_multiple_options)}"
                f"\n    Multiple options parameters must have optional values"
                f"\n  - Invalid non-multiple options parameters: "
                f"{_format_error_dict(invalid_non_multiple_options)}"
                f"\n    Non-multiple options parameters must not have optional values"
                f"\n  - Invalid default value: "
                f"{_format_error_dict(invalid_default_value)}"
                f"\n    The default value of a multiple options parameter must be one "
                f"of the options"
            )
            raise NonFatalValidationError(msg)


def _has_parameters(yaml_content: YamlFileContent) -> bool:
    """Filter function to check if a component has parameters.

    Returns:
        True if the component has parameters.

    """
    return yaml_content.get(PARAMETERS_KEY, False)


def _extract_name_and_parameters(
    yaml_content: YamlFileContent,
) -> tuple[ActionName, list[ActionParameter]]:
    """Extract the action name and parameters into a tuple.

    Returns:
        The action's name and parameters as a tuple.

    """
    return yaml_content.get(DEF_FILE_NAME_KEY, ""), yaml_content.get(PARAMETERS_KEY, [])


def _is_optional_values_type(param_type: ActionParamType) -> bool:
    return param_type in OPT_PARAMS


def _is_valid_default_value(
    optional_values: list[str] | None,
    default_value: str | bool | float | None,  # noqa: FBT001
) -> bool:
    return (
        default_value in {None, ""} or optional_values is None or default_value in optional_values
    )


def _format_error_dict(error_dict: dict[ActionName, list[str]]) -> str:
    if not error_dict:
        return "None"

    return ", ".join(
        f"{', '.join(sorted(params))} from {action_name}"
        for action_name, params in sorted(error_dict.items())
    )
