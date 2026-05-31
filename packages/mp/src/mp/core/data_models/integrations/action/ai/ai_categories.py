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

from mp.core.data_models.abc import RepresentableEnum


class AiCategories(BaseModel):
    reasoning: Annotated[
        str,
        Field(
            title="Categorization Reasoning",
            description=(
                "Step-by-step reasoning evaluating the action against all available AI "
                "categories. Explicitly state why the action matches or "
                "does not match the criteria before setting their boolean flags."
            ),
        ),
    ] = ""
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

Few other constraints:

* Actions named Ping must not be categorized as enrichment actions.

* Actions that download files must not be categorized as enrichment actions.

Here's a pseudocode example of how to determine whether an action is an enrichment
action:

```
def is_enrichment_action(action):
    # Rule 0.1: Ping actions are not enrichment actions
    if action.name == "Ping":
        return False

    # Rule 0.2 Actions that download files are not enrichment actions
    if is_download_action(action):
        return False

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
    remediation: Annotated[
        bool,
        Field(
            description=(
                """Field Definition: A Remediation Action is a specialized task designed to mitigate or resolve a
 security threat or incident. An action is classified as "Remediation" if it matches one of the following criteria:
 Here's a pseudocode example of how to determine whether an action is a remediation action:
```
def is_remediation_action(action):
    # Rule 1: Check for Identity-Based Remediation
    # Disables authentication, forces MFA setups, or invalidates current credentials
    if action.disables_identity or action.forces_identity_mfa or action.resets_identity_password:
        return True

    # Rule 2: Check for Infrastructure-Based Blocking (IPs)
    # Blocks specific IPs from performing operations via firewall rules, EDR constraints, or blocklists
    if action.blocks_ip:
        return True

    # Rule 3: Check for Network/Web-Based Blocking (Domains & URLs)
    # Prevents network communication with domains or URLs identified as malicious
    if action.blocks_malicious_domain or action.blocks_malicious_url:
        return True

    # Rule 4: Check for Email-Based Isolation
    # Isolates suspicious emails into a secure area to protect the recipient's inbox
    if action.quarantines_email:
        return True

    # If the action does not execute any of the above defensive behaviors, it is not remediation
    return False
```"""
            )
        ),
    ]  # TODO change description


class ActionAiCategory(RepresentableEnum):
    ENRICHMENT = "Enrichment"
    REMEDIATION = "Remediation"


AI_CATEGORY_TO_DEF_AI_CATEGORY: dict[str, ActionAiCategory] = {
    "enrichment": ActionAiCategory.ENRICHMENT,
    "remediation": ActionAiCategory.REMEDIATION,
}
