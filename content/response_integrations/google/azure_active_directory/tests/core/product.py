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
import abc

import contextlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AzureADProduct(abc.ABC):
    users: dict[str, Any] = field(default_factory=dict)
    managers: dict[str, Any] = field(default_factory=dict)
    groups: dict[str, Any] = field(default_factory=dict)
    user_registration_details: dict[str, Any] = field(default_factory=dict)
    # group_id -> list of member raw dicts
    group_members: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # hostname -> list of device raw dicts
    devices: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # user_principal_name -> list of group IDs they belong to
    user_group_memberships: dict[str, list[str]] = field(default_factory=dict)
    # group_id -> set of member user IDs (for membership checks)
    group_member_ids: dict[str, set[str]] = field(default_factory=dict)
    # user_id -> revoke session response dict
    revoke_session_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    # simulate global API failure
    _fail_all_requests: bool = field(default=False)

    def add_user(self, user_principal_name: str, data: dict[str, Any]) -> None:
        self.users[user_principal_name.lower()] = data

    def get_user(self, user_principal_name: str) -> dict[str, Any] | None:
        return self.users.get(user_principal_name.lower())

    def add_manager(self, user_principal_name: str, manager_data: dict[str, Any]) -> None:
        self.managers[user_principal_name.lower()] = manager_data

    def get_manager(self, user_principal_name: str) -> dict[str, Any] | None:
        return self.managers.get(user_principal_name.lower())

    def add_group(self, group_id: str, data: dict[str, Any]) -> None:
        self.groups[group_id] = data

    def get_groups(self) -> list[dict[str, Any]]:
        return list(self.groups.values())

    def add_user_registration_details(
        self, user_principal_name: str, details: dict[str, Any]
    ) -> None:
        """Adds MFA registration details for a specific user."""
        self.user_registration_details[user_principal_name.lower()] = details

    def get_user_registration_details(
        self, user_principal_name: str
    ) -> dict[str, Any] | None:
        """Retrieves MFA details for a specific user."""
        return self.user_registration_details.get(user_principal_name.lower())

    def add_group_member(self, group_id: str, member: dict[str, Any]) -> None:
        """Adds a raw member dict to a group and tracks its id for membership checks."""
        self.group_members.setdefault(group_id, []).append(member)
        member_id = member.get("id", "")
        if member_id:
            self.group_member_ids.setdefault(group_id, set()).add(member_id)

    def get_group_members_list(self, group_id: str) -> list[dict[str, Any]]:
        return self.group_members.get(group_id, [])

    def add_device(self, hostname: str, device: dict[str, Any]) -> None:
        """Adds a device raw dict keyed by displayName (case-insensitive)."""
        self.devices.setdefault(hostname.lower(), []).append(device)

    def get_devices_by_hostname(self, hostname: str) -> list[dict[str, Any]]:
        return self.devices.get(hostname.lower(), [])

    def add_user_group_membership(
        self, user_principal_name: str, group_ids: list[str]
    ) -> None:
        """Records which groups a user belongs to (getMemberGroups response)."""
        self.user_group_memberships[user_principal_name.lower()] = group_ids

    def get_user_group_memberships(self, user_principal_name: str) -> list[str]:
        return self.user_group_memberships.get(user_principal_name.lower(), [])

    def is_user_in_group(self, user_id: str, group_id: str) -> bool:
        """Returns True if user_id is in the group's tracked member id set."""
        return user_id in self.group_member_ids.get(group_id, set())

    def set_revoke_session_result(
        self, user_id: str, result: dict[str, Any]
    ) -> None:
        """Configures the response returned when revoking a specific user's sessions."""
        self.revoke_session_results[user_id] = result

    def get_revoke_session_result(self, user_id: str) -> dict[str, Any]:
        return self.revoke_session_results.get(user_id, {"value": True})

    @contextlib.contextmanager
    def fail_all_requests(self):
        """Context manager that causes the mock session to return 500 for every call."""
        self._fail_all_requests = True
        try:
            yield
        finally:
            self._fail_all_requests = False
