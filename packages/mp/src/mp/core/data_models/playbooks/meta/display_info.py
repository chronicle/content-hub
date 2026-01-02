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
from mp.core.data_models.abc import Buildable, RepresentableEnum


class PlaybookType(RepresentableEnum):
    PLAYBOOK = 0
    BLOCK = 1


class PlaybookDisplayInfoType(RepresentableEnum):
    Playbook = 1
    Block = 2


PLAYBOOK_TYPE_TO_DISPLAY_INFO_TYPE = {
    PlaybookType.PLAYBOOK.value: PlaybookDisplayInfoType.Playbook.value,
    PlaybookType.BLOCK.value: PlaybookDisplayInfoType.Block.value,
}


class PlaybookContributionType(RepresentableEnum):
    Unspecified = 0
    Google = 1
    THIRD_PARTY = 2
    Partner = 3


class BuiltPlaybookDisplayInfo(TypedDict):
    Identifier: Annotated[str, pydantic.Field(pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX)]
    FileName: str
    Type: int
    DisplayName: str
    Description: str
    CreateTime: int
    UpdateTime: int
    Version: float
    Author: str
    ContactEmail: str
    Integrations: list[str]
    DependentPlaybookIds: list[str]
    Tags: list[str]
    Source: int
    Verified: bool
    Standalone: bool
    HasAlertOverview: bool


class NonBuiltPlaybookDisplayInfo(TypedDict):
    type: str
    content_hub_display_name: str
    description: str
    author: str
    contact_email: str
    tags: list[str]
    contribution_type: str
    should_display_in_content_hub: bool
    acknowledge_debug_data_included: bool
    is_google_verified: NotRequired[bool]


class PlaybookDisplayInfo(Buildable[BuiltPlaybookDisplayInfo, NonBuiltPlaybookDisplayInfo]):
    type: PlaybookType = PlaybookType.PLAYBOOK
    content_hub_display_name: str = "String value"
    description: str = "String value"
    author: str = "String value"
    contact_email: str = "String value"
    tags: Annotated[list[str], pydantic.Field(default_factory=list)]
    contribution_type: PlaybookContributionType = PlaybookContributionType.THIRD_PARTY
    is_google_verified: bool = False
    should_display_in_content_hub: bool = False
    allowed_debug_data: bool = False

    @classmethod
    def _from_built(cls, _: BuiltPlaybookDisplayInfo) -> Self:  # ty:ignore[invalid-method-override]
        return cls()  # ty:ignore[missing-argument]

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltPlaybookDisplayInfo) -> Self:
        return cls(
            type=PlaybookType.from_string(non_built["type"]),
            content_hub_display_name=non_built["content_hub_display_name"],
            description=non_built["description"],
            author=non_built["author"],
            contact_email=non_built["contact_email"],
            tags=non_built["tags"],
            contribution_type=PlaybookContributionType.from_string(
                non_built["contribution_type"].upper()
            ),
            is_google_verified=non_built.get("is_google_verified", False),
            should_display_in_content_hub=non_built["should_display_in_content_hub"],
            allowed_debug_data=non_built["acknowledge_debug_data_included"],
        )

    def to_built(self) -> BuiltPlaybookDisplayInfo:
        """Convert the PlaybookDisplayInfo to its "built" representation.

        Returns:
            A BuiltPlaybookDisplayInfo dictionary.

        """
        return BuiltPlaybookDisplayInfo(
            Identifier="",
            FileName=self.content_hub_display_name,
            Type=self.type.value,
            DisplayName=self.content_hub_display_name,
            Description=self.description,
            Author=self.author,
            CreateTime=0,
            ContactEmail=self.contact_email,
            UpdateTime=0,
            Version=0.0,
            Integrations=[],
            DependentPlaybookIds=[],
            Tags=self.tags,
            Source=self.contribution_type.value,
            Verified=self.is_google_verified,
            Standalone=self.should_display_in_content_hub,
            HasAlertOverview=False,
        )

    def to_non_built(self) -> NonBuiltPlaybookDisplayInfo:
        """Convert the PlaybookDisplayInfo to its "non-built" representation.

        Returns:
            A NonBuiltPlaybookDisplayInfo dictionary.

        """
        non_built: NonBuiltPlaybookDisplayInfo = NonBuiltPlaybookDisplayInfo(
            type=self.type.to_string(),
            content_hub_display_name=self.content_hub_display_name,
            description=self.description,
            author=self.author,
            contact_email=self.contact_email,
            tags=self.tags,
            should_display_in_content_hub=self.should_display_in_content_hub,
            contribution_type=self.contribution_type.to_string(),
            acknowledge_debug_data_included=self.allowed_debug_data,
        )
        return non_built
