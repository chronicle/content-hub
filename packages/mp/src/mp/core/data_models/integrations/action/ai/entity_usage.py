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
    entity_types: Annotated[
        list[EntityType],
        Field(
            description=(
                "The types of the entities the action runs on, if it runs on"
                " entities. Use the code and the metadata json to determine this field."
                " If an action runs on entities it most likely will use the target_entities"
                " attribute to go over the entities or filter them by type or other"
                " attributes. It is possible that an action doesn't run on entities."
                " In that case leave this list empty. An action that doesn't use any entity doesn't"
                " run on a generic entity, but simply it works on other sources of data."
                " Make sure you check this carefully and distinguish correctly between actions that"
                " run on/use entities and ones that don't. Then, if it does use entities, make sure"
                " to check which types of entities (specific ones or all of them). Note that it is"
                " possible for the code to contain the word 'entity' in some variables, but it"
                " doesn't always mean it uses entities."
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
                " their 'is_vulnerable' attribute"
            )
        ),
    ]
    filters_by_is_enriched: Annotated[
        bool,
        Field(
            description=(
                "Whether the code runs on entities and filters the entities it runs on by"
                " their 'is_enriched' attribute"
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
