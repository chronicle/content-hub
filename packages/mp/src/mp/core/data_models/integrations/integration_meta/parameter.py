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
import mp.core.validators
from mp.core import exclusions
from mp.core.data_models.abc import Buildable
from mp.core.data_models.integrations.script.parameter import ScriptParamType


class BuiltIntegrationParameter(TypedDict):
    PropertyName: str
    PropertyDisplayName: str
    Value: str | bool | float | int | None
    PropertyDescription: NotRequired[str]
    IsMandatory: bool
    PropertyType: int
    IntegrationIdentifier: str


class NonBuiltIntegrationParameter(TypedDict):
    name: str
    display_name: NotRequired[str]
    default_value: NotRequired[str | bool | float | int | None]
    description: str
    is_mandatory: bool
    type: str
    integration_identifier: str


class IntegrationParameter(Buildable[BuiltIntegrationParameter, NonBuiltIntegrationParameter]):
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.PARAM_NAME_MAX_LENGTH,
        ),
        pydantic.AfterValidator(mp.core.validators.validate_param_name),
    ]
    display_name: Annotated[
        str | None,
        pydantic.Field(
            default=None,
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
        ),
    ] = None
    description: Annotated[
        str,
        pydantic.AfterValidator(mp.core.validators.validate_param_short_description),
    ]
    is_mandatory: bool
    type_: ScriptParamType
    integration_identifier: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=exclusions.get_script_identifier_regex(),
        ),
    ]
    default_value: str | bool | float | int | None

    @classmethod
    def _from_built(cls, built: BuiltIntegrationParameter) -> Self:
        property_name = built["PropertyName"]
        property_display_name = built.get("PropertyDisplayName")
        display_name = (
            property_display_name
            if property_display_name and property_display_name != property_name
            else None
        )
        return cls(
            name=property_name,
            display_name=display_name,
            default_value=built["Value"],
            description=v if (v := built.get("PropertyDescription")) is not None else "",
            is_mandatory=built.get("IsMandatory", False),
            type_=ScriptParamType(int(built["PropertyType"])),
            integration_identifier=built["IntegrationIdentifier"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltIntegrationParameter) -> Self:
        return cls(
            name=non_built["name"],
            display_name=non_built.get("display_name"),
            default_value=non_built.get("default_value"),
            description=non_built["description"],
            is_mandatory=non_built["is_mandatory"],
            type_=ScriptParamType.from_string(non_built["type"]),
            integration_identifier=non_built["integration_identifier"],
        )

    def to_built(self) -> BuiltIntegrationParameter:
        """Turn the object into a `BuiltIntegrationParameter`.

        Returns:
            The "built" representation of the object.

        """
        return BuiltIntegrationParameter(
            IntegrationIdentifier=self.integration_identifier,
            IsMandatory=self.is_mandatory,
            PropertyDescription=self.description,
            PropertyDisplayName=self.display_name or self.name,
            PropertyName=self.name,
            PropertyType=self.type_.value,
            Value=self.default_value,
        )

    def to_non_built(self) -> NonBuiltIntegrationParameter:
        """Turn the object into a `NonBuiltIntegrationParameter`.

        Returns:
            The "non-built" representation of the object.

        """
        non_built: NonBuiltIntegrationParameter = NonBuiltIntegrationParameter(
            name=self.name,
            default_value=self.default_value,
            type=self.type_.to_string(),
            description=self.description,
            is_mandatory=self.is_mandatory,
            integration_identifier=self.integration_identifier,
        )
        if self.display_name is not None:
            non_built["display_name"] = self.display_name
        return non_built
