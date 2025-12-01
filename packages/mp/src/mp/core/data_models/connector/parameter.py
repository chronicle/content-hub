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

from typing import Annotated, NotRequired, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
import mp.core.validators
from mp.core.data_models.script.parameter import ScriptParamType


class ParamMode(mp.core.data_models.abc.RepresentableEnum):
    REGULAR = 0
    SCRIPT = 2


class BuiltConnectorParameter(TypedDict):
    Name: str
    Description: str
    IsMandatory: bool
    IsAdvanced: bool
    Type: int
    Mode: int
    DefaultValue: str | float | bool | int | None


class NonBuiltConnectorParameter(TypedDict):
    name: str
    description: str
    is_mandatory: bool
    is_advanced: bool
    type: str
    mode: str
    default_value: NotRequired[str | float | bool | int | None]


class ConnectorParameter(
    mp.core.data_models.abc.Buildable[BuiltConnectorParameter, NonBuiltConnectorParameter],
):
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.PARAM_NAME_MAX_LENGTH,
            pattern=mp.core.constants.PARAM_DISPLAY_NAME_REGEX,
        ),
        pydantic.AfterValidator(mp.core.validators.validate_param_name),
    ]
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
    ]
    is_mandatory: bool
    is_advanced: bool
    type_: ScriptParamType
    mode: ParamMode
    default_value: str | bool | float | int | None

    @classmethod
    def _from_built(cls, built: BuiltConnectorParameter) -> ConnectorParameter:
        return cls(
            name=built["Name"],
            description=built["Description"],
            is_mandatory=built["IsMandatory"],
            is_advanced=built.get("IsAdvanced", False),
            type_=ScriptParamType(int(built["Type"])),
            default_value=built["DefaultValue"],
            mode=ParamMode(built["Mode"]),
        )

    @classmethod
    def _from_non_built(
        cls,
        non_built: NonBuiltConnectorParameter,
    ) -> ConnectorParameter:
        return cls(
            name=non_built["name"],
            description=non_built["description"],
            is_mandatory=non_built["is_mandatory"],
            is_advanced=non_built["is_advanced"],
            type_=ScriptParamType.from_string(non_built["type"]),
            default_value=non_built.get("default_value"),
            mode=ParamMode.from_string(non_built["mode"]),
        )

    def to_built(self) -> BuiltConnectorParameter:
        """Turn the object into a BuiltConnectorParameter.

        Returns:
            The BuiltConnectorParameter typed dict representation of the object

        """
        return BuiltConnectorParameter(
            Name=self.name,
            Description=self.description,
            IsMandatory=self.is_mandatory,
            IsAdvanced=self.is_advanced,
            Type=self.type_.value,
            DefaultValue=self.default_value,
            Mode=self.mode.value,
        )

    def to_non_built(self) -> NonBuiltConnectorParameter:
        """Turn the object into a NonBuiltConnectorParameter.

        Returns:
            The NonBuiltConnectorParameter typed dict representation of the object

        """
        non_built: NonBuiltConnectorParameter = NonBuiltConnectorParameter(
            name=self.name,
            default_value=self.default_value,
            type=self.type_.to_string(),
            description=self.description,
            is_mandatory=self.is_mandatory,
            is_advanced=self.is_advanced,
            mode=self.mode.to_string(),
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
