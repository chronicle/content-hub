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
from . import datamodels
from TIPCommon.types import SingleJson


def build_list_security_policies(
    raw_data: SingleJson,
) -> list[datamodels.ListSecurityPolicy]:
    """Build a list of security policies object from JSON data.

    Args:
        raw_data (SingleJson): The JSON data representing security policies.

    Returns:
        list[datamodels.ListSecurityPolicy]: A list of security policy objects.
    """
    return [
        datamodels.ListSecurityPolicy.from_json(policy_json=policy_json)
        for policy_json in raw_data
    ]


def build_create_or_update_security_policy(
    raw_data: SingleJson,
) -> datamodels.CreateOrUpdateSecurityPolicy:
    """Build a create or update security policy object from JSON data.

    Args:
        raw_data (SingleJson): The JSON data representing the security policy.

    Returns:
        CreateOrUpdateSecurityPolicy: The created or updated security policy object.
    """
    return datamodels.CreateOrUpdateSecurityPolicy.from_json(policy_json=raw_data)
