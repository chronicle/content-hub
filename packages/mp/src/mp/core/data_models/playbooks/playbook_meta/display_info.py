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

from typing import Annotated, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils


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
    dependent_playbook_ids: list[str]
    tags: list[str]
    contribution_type: str
    is_google_verified: bool
    should_display_in_content_hub: bool


class PlaybookType(mp.core.data_models.abc.RepresentableEnum):
    PLAYBOOK = 0
    BLOCK = 1


class PlaybookContributionType(mp.core.data_models.abc.RepresentableEnum):
    THIRD_PARTY = 0
    PARTNER = 1
    GOOGLE = 2


class PlaybookDisplayInfo(
    mp.core.data_models.abc.Buildable[BuiltPlaybookDisplayInfo, NonBuiltPlaybookDisplayInfo]
):
    type: PlaybookType
    content_hub_display_name: str
    description: str
    author: str
    contact_email: str
    dependent_playbook_ids: list[str]
    tags: list[str]
    contribution_type: PlaybookContributionType
    is_google_verified: bool
    should_display_in_content_hub: bool
    has_alert_overview: bool = False
    dependent_playbook_ids: list[str]
    integrations: list[str]
    identifier: str
    file_name: str
    create_time: int
    update_time: int
    version: float

    @classmethod
    def _from_built(cls, built: BuiltPlaybookDisplayInfo) -> Self:
        return cls(
            identifier=built["Identifier"],
            file_name=built["FileName"],
            create_time=built["CreateTime"],
            update_time=built["UpdateTime"],
            version=built["Version"],
            type=PlaybookType(built["Type"]),
            content_hub_display_name=built["DisplayName"],
            description=built["Description"],
            author=built["Author"],
            contact_email=built["ContactEmail"],
            dependent_playbook_ids=built["DependentPlaybookIds"],
            tags=built["Tags"],
            contribution_type=PlaybookContributionType(built["Source"]),
            is_google_verified=built["Verified"],
            should_display_in_content_hub=built["Standalone"],
            has_alert_overview=built["HasAlertOverview"],
            integrations=built["Integrations"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltPlaybookDisplayInfo) -> Self:
        return cls(
            type=PlaybookType.from_string(non_built["type"]),
            content_hub_display_name=non_built["content_hub_display_name"],
            description=non_built["description"],
            author=non_built["author"],
            contact_email=non_built["contact_email"],
            tags=non_built["tags"],
            contribution_type=PlaybookContributionType.from_string(non_built["contribution_type"]),
            is_google_verified=non_built["is_google_verified"],
            should_display_in_content_hub=non_built["should_display_in_content_hub"],
            dependent_playbook_ids=[],
            integrations=[],
            identifier="",
            file_name="",
            create_time=-1,
            update_time=-1,
            version=0.0,
        )

    def to_built(self) -> BuiltPlaybookDisplayInfo:
        return BuiltPlaybookDisplayInfo(
            DisplayName=self.content_hub_display_name,
            Description=self.description,
            Author=self.author,
            ContactEmail=self.contact_email,
            DependentPlaybookIds=self.dependent_playbook_ids,
            Tags=self.tags,
            Source=self.contribution_type.value,
            Verified=self.is_google_verified,
            HasAlertOverview=self.has_alert_overview,
            Integrations=self.integrations,
            FileName=self.file_name,
            CreateTime=self.create_time,
            UpdateTime=self.update_time,
            Version=self.version,
            Identifier=self.identifier,
            Standalone=self.should_display_in_content_hub,
            Type=self.type.value,
        )

    def to_non_built(self) -> NonBuiltPlaybookDisplayInfo:
        non_built: NonBuiltPlaybookDisplayInfo = NonBuiltPlaybookDisplayInfo(
            type=self.type.to_string(),
            content_hub_display_name=self.content_hub_display_name,
            description=self.description,
            author=self.author,
            contact_email=self.contact_email,
            dependent_playbook_ids=self.dependent_playbook_ids,
            tags=self.tags,
            should_display_in_content_hub=self.should_display_in_content_hub,
            contribution_type=self.contribution_type.to_string(),
            is_google_verified=self.is_google_verified,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
