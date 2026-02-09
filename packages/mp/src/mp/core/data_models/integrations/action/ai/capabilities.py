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


class ActionCapabilities(BaseModel):
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
        ),
    ]
    can_mutate_internal_data: Annotated[
        bool,
        Field(
            description=(
                "Whether the action mutates or changes any data in any internal system inside"
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
        ),
    ]
    can_update_entities: Annotated[bool, Field(description="Whether the action updates entities.")]
    can_create_insight: Annotated[bool, Field(description="Whether the action creates insights.")]
    can_modify_alert_data: Annotated[
        bool, Field(description="Whether the action can modify data of alerts.")
    ]
    can_create_case_comments: Annotated[
        bool, Field(description="Whether the action creates case comments.")
    ]
