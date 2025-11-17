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
from mp.core.data_models.integrations.script.parameter import ScriptParamType


class BuiltJobParameter(TypedDict):
    Name: str
    Description: str
    IsMandatory: bool
    Type: int
    DefaultValue: str | float | bool | int | None


class NonBuiltJobParameter(TypedDict):
    name: str
    description: str
    is_mandatory: bool
    type: str
    default_value: NotRequired[str | float | bool | int | None]


class JobParameter(mp.core.data_models.abc.Buildable[BuiltJobParameter, NonBuiltJobParameter]):
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.PARAM_NAME_MAX_LENGTH,
            pattern=mp.core.constants.PARAM_DISPLAY_NAME_REGEX,
        ),
        pydantic.AfterValidator(mp.core.validators.validate_param_name),
    ]
    description: Annotated[
        str, pydantic.Field(max_length=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH)
    ]
    is_mandatory: bool
    type_: ScriptParamType
    default_value: str | bool | float | int | None

    @classmethod
    def _from_built(cls, built: BuiltJobParameter) -> Self:
        return cls(
            name=built["Name"],
            description=built.get("Description", ""),
            is_mandatory=built["IsMandatory"],
            type_=ScriptParamType(int(built["Type"])),
            default_value=built.get("DefaultValue"),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltJobParameter) -> Self:
        return cls(
            name=non_built["name"],
            description=non_built["description"],
            is_mandatory=non_built["is_mandatory"],
            type_=ScriptParamType.from_string(non_built["type"]),
            default_value=non_built.get("default_value"),
        )

    def to_built(self) -> BuiltJobParameter:
        """Turn the object into a BuiltJobParameter.

        Returns:
            The BuiltJobParameter typed dict representation of the object

        """
        return BuiltJobParameter(
            Name=self.name,
            Description=self.description,
            IsMandatory=self.is_mandatory,
            Type=self.type_.value,
            DefaultValue=self.default_value,
        )

    def to_non_built(self) -> NonBuiltJobParameter:
        """Turn the object into a NonBuiltJobParameter.

        Returns:
            The NonBuiltJobParameter typed dict representation of the object

        """
        non_built: NonBuiltJobParameter = NonBuiltJobParameter(
            name=self.name,
            default_value=self.default_value,
            type=self.type_.to_string(),
            description=self.description,
            is_mandatory=self.is_mandatory,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
