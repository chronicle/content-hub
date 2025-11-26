"""Data structures for representing the full details of a built integration.

This module defines TypedDicts that capture all the necessary information
for a built integration, extending beyond the basic metadata. This includes
details about supported actions and additional attributes relevant to the
full representation of an integration.
"""

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

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mp.core.data_models.integrations.integration_meta.feature_tags import BuiltFeatureTags
    from mp.core.data_models.integrations.integration_meta.parameter import (
        BuiltIntegrationParameter,
    )


class BuiltSupportedAction(TypedDict):
    Name: str
    Description: str


class FullDetailsExtraAttrs(TypedDict):
    LatestReleasePublishTimeUnixTime: NotRequired[int | None]
    UpdateNotificationExpired: NotRequired[int | None]
    NewNotificationExpired: NotRequired[int | None]
    HasConnectors: bool
    SupportedActions: Sequence[BuiltSupportedAction]


class BuiltFullDetailsIntegrationMetadata(TypedDict):
    Categories: Sequence[str]
    Description: str
    FeatureTags: NotRequired[BuiltFeatureTags]
    DisplayName: str
    Identifier: str
    PythonVersion: int
    DocumentationLink: str
    ImageBase64: str
    IntegrationProperties: Sequence[BuiltIntegrationParameter]
    ShouldInstalledInSystem: bool
    IsAvailableForCommunity: bool
    MarketingDisplayName: str
    MinimumSystemVersion: float
    SVGImage: str
    Version: float
    LatestReleasePublishTimeUnixTime: NotRequired[int]
    UpdateNotificationExpired: NotRequired[int]
    NewNotificationExpired: NotRequired[int]
    HasConnectors: bool
    SupportedActions: Sequence[BuiltSupportedAction]
