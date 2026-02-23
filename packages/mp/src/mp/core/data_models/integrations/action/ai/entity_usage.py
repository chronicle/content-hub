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
                """### Entity Types Determination Logic

**Field Definition:** `entity_types` (List of `EntityType`)

This field identifies the specific categories of entities an action processes. It is critical to
distinguish between actions that perform operations **on** SecOps entities versus actions that
simply process general data.

#### **1. Assessment Criteria**

* **Presence of Entities:** An action "runs on entities" if it iterates over the `target_entities`
  attribute or uses entity-specific identifiers to perform its task.
* **Empty State:** If the action works on other data sources (e.g., fetching a static URL, checking
  global system status) without referencing specific entities, this list **must be empty**.
* **Avoid String Matching:** Do not assume an action uses entities just because the variable name
  `entity` appears in the code. Verify that the logic actually interacts with the SecOps entity
  object model.

#### **2. Filtering & Scope**

* **Specific Types:** If the code filters entities by type (e.g., `if entity.type == "USER"`), list
  only those specific types.
* **Unfiltered (Global) Scope:** If the action processes the `target_entities` list without any
  type-based filtering, it is considered to run on **all** supported entity types.
  In this case, include every available `EntityType` from the metadata.
* **The `GenericEntity` Distinction:** `GenericEntity` is a specific, standalone entity type.
  Do **not** use it as a placeholder for "all types." Only include it if the action explicitly
  supports the `GenericEntity` type or if no filters are applied (as part of the full list).

#### **3. Logic Summary Table**

| If the code... | Then `entity_types` should be... |
| --- | --- |
| Does not reference `target_entities` | `[]` (Empty List) |
| Filters for specific types (IP, Host) | Only the specific types identified: `["IP", "HOSTNAME"]` |
| Processes all entities without any filtering | **All** possible entity types from the metadata |
| Explicitly checks for "Generic" type only | `["GenericEntity"]` |"""
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
