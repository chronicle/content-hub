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

from typing import Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
import mp.core.validators


class ActionParamType(mp.core.data_models.abc.RepresentableEnum):
    STRING = 0
    INTEGER = 0
    BOOLEAN = 1
    PLAYBOOK_NAME = 2
    USER = 3
    STAGE = 4
    CLOSE_CASE_REASONS = 5
    CLOSE_ROOT_CAUSE = 6
    CASE_PRIORITIES = 7
    EMAIL_CONTENT = 10
    CONTENT = 11
    PASSWORD = 12
    ENTITY_TYPE = 13
    MULTI_VALUES = 14
    DDL = 15
    CODE = 16
    TIME_SPAN_SECONDS = 17
    MULTI_CHOICE_PARAMETER = 21
    NULL = -1


OPT_TYPES: set[ActionParamType] = {
    ActionParamType.DDL,
    ActionParamType.MULTI_CHOICE_PARAMETER,
    ActionParamType.MULTI_VALUES,
}


class BuiltActionParameter(TypedDict):
    Description: str
    IsMandatory: bool
    Name: str
    OptionalValues: list[str] | None
    Type: int
    Value: str | bool | int | float | None
    DefaultValue: str | bool | int | float | None


class NonBuiltActionParameter(TypedDict):
    description: str
    is_mandatory: bool
    name: str
    optional_values: NotRequired[list[str] | None]
    type: str
    default_value: NotRequired[str | bool | int | float | None]


class ActionParameter(
    mp.core.data_models.abc.Buildable[BuiltActionParameter, NonBuiltActionParameter],
):
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
    ]
    is_mandatory: bool
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.PARAM_NAME_MAX_LENGTH,
            pattern=mp.core.constants.PARAM_DISPLAY_NAME_REGEX,
        ),
        pydantic.AfterValidator(mp.core.validators.validate_param_name),
    ]
    optional_values: list[str] | None
    type_: ActionParamType
    default_value: str | bool | float | int | None

    @classmethod
    def _from_built(cls, built: BuiltActionParameter) -> Self:
        """Create the obj from a built action param dict.

        Args:
            built: the built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            description=built["Description"],
            is_mandatory=built["IsMandatory"],
            name=built["Name"],
            optional_values=built.get("OptionalValues"),
            type_=ActionParamType(int(built["Type"])),
            default_value=built.get("Value", built.get("DefaultValue")),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltActionParameter) -> Self:
        """Create the obj from a non-built action param dict.

        Args:
            non_built: the non-built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            description=non_built["description"],
            is_mandatory=non_built["is_mandatory"],
            name=non_built["name"],
            optional_values=non_built.get("optional_values"),
            type_=ActionParamType.from_string(non_built["type"]),
            default_value=non_built.get("default_value"),
        )

    def to_built(self) -> BuiltActionParameter:
        """Create a built action param dict.

        Returns:
            A built version of the action parameter dict

        """
        return BuiltActionParameter(
            DefaultValue=self.default_value,
            Description=self.description,
            IsMandatory=self.is_mandatory,
            Name=self.name,
            Type=self.type_.value,
            Value=self.default_value,
            OptionalValues=self.optional_values,
        )

    def to_non_built(self) -> NonBuiltActionParameter:
        """Create a non-built action param dict.

        Returns:
            A non-built version of the action parameter dict

        """
        non_built: NonBuiltActionParameter = NonBuiltActionParameter(
            name=self.name,
            default_value=self.default_value,
            type=self.type_.to_string(),
            optional_values=self.optional_values,
            description=self.description,
            is_mandatory=self.is_mandatory,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
