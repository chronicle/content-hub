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

import contextlib
import dataclasses

from cloud_identity.core.datamodels import OrgUnit, Policy


@dataclasses.dataclass(slots=True)
class CloudIdentity:
    policies: dict[str, Policy] = dataclasses.field(default_factory=dict)
    org_units: dict[str, OrgUnit] = dataclasses.field(default_factory=dict)
    _fail_requests_active: bool = False

    @contextlib.contextmanager
    def fail_requests(self):
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def add_policy(self, policy: Policy) -> None:
        self.policies[policy.get_id()] = policy

    def create_policy(self, policy: Policy) -> Policy:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for CreatePolicy")

        if not policy.name:
            policy_id = f"mock_policy_{len(self.policies) + 1}"
            policy.name = f"policies/{policy_id}"

        self.add_policy(policy)
        return policy

    def patch_policy(self, policy: Policy) -> Policy:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for PatchPolicy")

        policy_id = policy.get_id()
        self.policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Policy:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetPolicy")

        if policy_id in self.policies:
            return self.policies[policy_id]
        raise Exception(f"Policy {policy_id} not found")

    def add_org_unit(self, org_unit: OrgUnit) -> None:
        if org_unit.org_unit_path:
            self.org_units[org_unit.org_unit_path] = org_unit
        if org_unit.name:
            self.org_units[org_unit.name] = org_unit

    def get_org_units(self) -> list[OrgUnit]:
        seen_ids = set()
        unique_units = []
        for ou in self.org_units.values():
            if ou.org_unit_id not in seen_ids:
                seen_ids.add(ou.org_unit_id)
                unique_units.append(ou)
        return unique_units
