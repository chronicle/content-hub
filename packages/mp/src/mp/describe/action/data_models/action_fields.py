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


class ActionCapabilities(BaseModel):
    description: Annotated[
        str,
        Field(
            description=(
                "Detailed description that will be used by LLMs to understand what the action does."
                " This should be a concise yet informative summary of the action's purpose and"
                " expected outcome."
                " Use markdown formatting for clarity, as this is a description for LLMs."
            ),
            min_length=10,
            max_length=5_000,
        ),
    ]
    fetches_data: Annotated[
        bool,
        Field(
            description=(
                "Whether the action fetches additional contextual data on alerts/entities etc."
            ),
        ),
    ]
    can_mutate_external_data: Annotated[
        bool,
        Field(
            description=(
                "Whether the action mutates or changes any data in any external system outside"
                " Google SecOps."
            )
        ),
    ]
    external_data_mutation_explanation: Annotated[
        str | None,
        Field(
            description=(
                "If the action mutates external data outside Google SecOps, provide a brief"
                " explanation of how and why the data is changed. If not, leave null."
            ),
            min_length=20,
            max_length=200,
        ),
    ]
    can_mutate_internal_data: Annotated[
        bool,
        Field(
            description=(
                "Whether the action mutates or changes any data in any external system inside"
                " Google SecOps."
            )
        ),
    ]
    internal_data_mutation_explanation: Annotated[
        str | None,
        Field(
            description=(
                "If the action mutates internal data (meaning inside Google SecOps), provide a"
                " brief explanation of how and why the data is changed. If not, leave null."
            ),
            min_length=10,
            max_length=200,
        ),
    ]
    can_update_entities: Annotated[bool, Field(description="Whether the action updates entities.")]
    can_create_insight: Annotated[bool, Field(description="Whether the action creates insights.")]
    can_create_case_wall_logs: Annotated[
        bool, Field(description="Whether the action creates case wall logs.")
    ]
    can_create_case_comments: Annotated[
        bool, Field(description="Whether the action creates case comments.")
    ]
    entity_scopes: Annotated[
        list[EntityType],
        Field(
            description=(
                "The entity scopes that the action can operate on. For example, ['ip', 'domain']."
                " Determine this based on the code"
            ),
        ),
    ]
