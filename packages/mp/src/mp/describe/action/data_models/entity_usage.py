# Copyright 2026 Google LLC
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

from typing import Annotated

from pydantic import BaseModel, Field

from .entity_types import EntityType  # noqa: TC001


class EntityUsage(BaseModel):
    entity_scopes: Annotated[
        list[EntityType],
        Field(
            description=(
                "The scopes/types of the entities the action runs on, if it runs on"
                " entities. Use the code and the metadata json to determine this field"
            )
        ),
    ]
    filters_by_identifier: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their identifier or original identifier"
            )
        ),
    ]
    filters_by_creation_time: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their creation time"
            )
        ),
    ]
    filters_by_modification_time: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their modification time"
            )
        ),
    ]
    filters_by_additional_properties: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'additional_properties' attribute"
            )
        ),
    ]
    filters_by_case_identifier: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'case_identifier' attribute"
            )
        ),
    ]
    filters_by_alert_identifier: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'alert_identifier' attribute"
            )
        ),
    ]
    filters_by_entity_type: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'entity_type' attribute"
            )
        ),
    ]
    filters_by_is_internal: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_internal' attribute"
            )
        ),
    ]
    filters_by_is_suspicious: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_suspicious' attribute"
            )
        ),
    ]
    filters_by_is_artifact: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_artifact' attribute"
            )
        ),
    ]
    filters_by_is_vulnerable: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_enriched' attribute"
            )
        ),
    ]
    filters_by_is_enriched: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_vulnerable' attribute"
            )
        ),
    ]
    filters_by_is_pivot: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_pivot' attribute"
            )
        ),
    ]
