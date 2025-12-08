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

from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc

from .parameter import (
    BuiltConnectorParameter,
    ConnectorParameter,
    NonBuiltConnectorParameter,
)
from .rule import BuiltConnectorRule, ConnectorRule, NonBuiltConnectorRule

if TYPE_CHECKING:
    from pathlib import Path


class BuiltConnectorMetadata(TypedDict):
    Creator: str
    Description: str
    DocumentationLink: str | None
    Integration: str
    IsConnectorRulesSupported: bool
    IsCustom: bool
    IsEnabled: bool
    Name: str
    Parameters: list[BuiltConnectorParameter]
    Rules: list[BuiltConnectorRule]
    Version: float


class NonBuiltConnectorMetadata(TypedDict):
    creator: str
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    documentation_link: str | None
    integration: str
    is_connector_rules_supported: bool
    is_custom: NotRequired[bool]
    is_enabled: NotRequired[bool]
    name: str
    parameters: list[NonBuiltConnectorParameter]
    rules: list[NonBuiltConnectorRule]
    version: NotRequired[float]


class ConnectorMetadata(
    mp.core.data_models.abc.ComponentMetadata[BuiltConnectorMetadata, NonBuiltConnectorMetadata]
):
    file_name: str
    creator: str
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    documentation_link: pydantic.HttpUrl | pydantic.FileUrl | None
    integration: str
    is_connector_rules_supported: bool
    is_custom: bool
    is_enabled: bool
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    parameters: Annotated[
        list[ConnectorParameter],
        pydantic.Field(max_length=mp.core.constants.MAX_PARAMETERS_LENGTH),
    ]
    rules: list[ConnectorRule]
    version: float

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create ConnectorMetadata objects from a built integration path.

        Args:
            path: The path to the built integration.

        Returns:
            A list of ConnectorMetadata objects.

        """
        meta_path: Path = path / mp.core.constants.OUT_CONNECTORS_META_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.CONNECTORS_META_SUFFIX}")
        ]

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create ConnectorMetadata objects from a non-built integration path.

        Args:
            path: The path to the non-built integration.

        Returns:
            A list of ConnectorMetadata objects.

        """
        meta_path: Path = path / mp.core.constants.CONNECTORS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_non_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltConnectorMetadata) -> Self:
        return cls(
            file_name=file_name,
            creator=built["Creator"],
            description=built["Description"],
            documentation_link=built["DocumentationLink"],
            integration=built["Integration"],
            is_connector_rules_supported=built["IsConnectorRulesSupported"],
            is_custom=built["IsCustom"],
            is_enabled=built["IsEnabled"],
            name=built["Name"],
            parameters=[ConnectorParameter.from_built(param) for param in built["Parameters"]],
            rules=[ConnectorRule.from_built(rule) for rule in built.get("Rules", [])],
            version=built.get("Version", mp.core.constants.MINIMUM_SCRIPT_VERSION),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltConnectorMetadata) -> Self:
        return cls(
            file_name=file_name,
            creator=non_built["creator"],
            description=non_built["description"],
            documentation_link=non_built.get("documentation_link"),
            integration=non_built["integration"],
            is_connector_rules_supported=non_built["is_connector_rules_supported"],
            is_custom=non_built.get("is_custom", False),
            is_enabled=non_built.get("is_enabled", True),
            name=non_built["name"],
            parameters=[
                ConnectorParameter.from_non_built(param) for param in non_built["parameters"]
            ],
            rules=[ConnectorRule.from_non_built(rule) for rule in non_built["rules"]],
            version=non_built.get("version", mp.core.constants.MINIMUM_SCRIPT_VERSION),
        )

    def to_built(self) -> BuiltConnectorMetadata:
        """Convert the connector metadata to a built dictionary.

        Returns:
            A built version of the connector metadata dictionary.

        """
        return BuiltConnectorMetadata(
            Creator=self.creator,
            Description=self.description,
            DocumentationLink=(
                str(self.documentation_link) or None
                if self.documentation_link is not None
                else None
            ),
            Integration=self.integration,
            IsConnectorRulesSupported=self.is_connector_rules_supported,
            IsCustom=self.is_custom,
            IsEnabled=self.is_enabled,
            Name=self.name,
            Parameters=[param.to_built() for param in self.parameters],
            Rules=[rule.to_built() for rule in self.rules],
            Version=self.version,
        )

    def to_non_built(self) -> NonBuiltConnectorMetadata:
        """Convert the connector metadata to a non-built dictionary.

        Returns:
            A non-built version of the connector metadata dictionary.

        """
        return NonBuiltConnectorMetadata(
            name=self.name,
            parameters=[param.to_non_built() for param in self.parameters],
            description=self.description,
            integration=self.integration,
            documentation_link=(
                str(self.documentation_link) or None
                if self.documentation_link is not None
                else None
            ),
            rules=[rule.to_non_built() for rule in self.rules],
            is_connector_rules_supported=self.is_connector_rules_supported,
            creator=self.creator,
        )
