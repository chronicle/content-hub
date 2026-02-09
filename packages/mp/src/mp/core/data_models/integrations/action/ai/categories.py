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
                """Field Definition: Is Enrichment Action

An Enrichment Action is a specialized task designed to gather supplemental context about alerts or
entities. To maintain data integrity and security, an action is only classified as "Enrichment" if
it meets the following criteria:

* Primary Purpose: The action must proactively fetch or retrieve data from an external or internal
  source.

* External State Preservation: The action must not create, update, or delete data in any external
  platform. It is strictly "Read-Only" regarding systems outside of Google SecOps.

* Internal State Constraints: The action must not modify existing Google SecOps data, with
  three specific exceptions. It is permitted only to:
    1. Add Case Comments.
    2. Create Case Insights.
    3. Update Entity fields/attributes (enriching the entity's profile).

Here's a pseudocode example of how to determine whether an action is an enrichment
action:

```
def is_enrichment_action(action):
    # Rule 1: Must fetch data to be considered enrichment
    if not action.fetches_data:
        return False

    # Rule 2: Absolute ban on mutating external systems
    if action.can_mutate_external_data:
        return False

    # Rule 3: Check for internal mutations
    if action.can_mutate_internal_data:
        # Define the only allowed internal mutations
        allowed_mutations = [
            action.can_create_insight,
            action.can_update_entities,
            action.can_add_comments
        ]

        # If it modifies internal data NOT in the allowed list, it's not enrichment
        if action.modifies_other_internal_fields(except_for=allowed_mutations):
            return False

    # If it passes all checks, it is a valid enrichment action
    return True
```"""
            )
        ),
    ]
