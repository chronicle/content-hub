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


class AiCategories(BaseModel):
    enrichment: Annotated[
        bool,
        Field(
            description=(
                "whether this code is considered an enrich action."
                " An enrichment action is one that only fetches data and does not modify any"
                " entities or data outside or inside of Google SecOps. It is okay if it does modify"
                " entities, create insights or create case wall logs. This means the 'fetches_data'"
                " field must be true, and the 'can_mutate_external_data' field must be false."
                " Usually 'can_mutate_internal_data' is false, but determine this based on"
                " the 'internal_data_mutation_explanation' to make sure it doesn't modify any data"
                " that isn't allowed. The results of 'can_update_entities', "
                " 'can_create_insight', and 'can_create_case_wall_logs'"
                " can either be true or false."
            )
        ),
    ]
