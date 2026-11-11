from __future__ import annotations
import abc

import dataclasses
from typing import Any, Iterable

from g_suite.core.datamodels import (
    Browser,
    ExtensionDetails,
    OrgUnit,
    RequestingDevice,
    RequestingUser,
    ResolvedPolicy,
    UserActivityEvent,
)


@dataclasses.dataclass
class User:
    username: str
    is_logged_in: bool = True


class Product(abc.ABC):

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._user_activity_events: list[UserActivityEvent] = []
        self._host_browser_details: list[Browser] = []
        self._extension_details: list[ExtensionDetails] = []
        self._requesting_users: list[RequestingUser] = []
        self._requesting_devices: list[RequestingDevice] = []
        self._org_units: list[OrgUnit] = []
        self._resolved_policies: list[ResolvedPolicy] = []
        # Fields for CRUD actions (Ping, CreateUser, UpdateUser, DeleteUser,
        # ListUsers, EnrichEntities, CreateGroup, DeleteGroup, GetGroupDetails,
        # AddMembersToGroup, RemoveMembersFromGroup, ListGroupMembers,
        # ListGroupPrivileges, ListUserPrivileges, CreateOU, DeleteOU,
        # UpdateOU, ListOUOfAccount)
        self._directory_users: list[dict[str, Any]] = []
        self._groups: dict[str, dict[str, Any]] = {}
        self._group_members: dict[str, list[dict[str, Any]]] = {}
        self._group_settings: dict[str, dict[str, Any]] = {}
        self._role_assignments: dict[str, list[dict[str, Any]]] = {}
        self._roles: dict[str, dict[str, Any]] = {}

    # --- sign-out user store (existing) ---

    def add_user(self, username: str) -> None:
        if username in self._users:
            return
        self._users[username] = User(username=username)

    def get_user(self, username: str) -> User:
        return self._users[username]

    # --- user activity events ---

    def add_user_activity_events(
        self,
        events: Iterable[UserActivityEvent],
    ) -> None:
        self._user_activity_events = list(events)

    def get_user_activity_events(self) -> list[UserActivityEvent]:
        return self._user_activity_events

    # --- browser details ---

    def add_host_browser_details(
        self,
        browser_details: Iterable[Browser],
    ) -> None:
        self._host_browser_details = list(browser_details)

    def get_host_browser_details(self) -> list[Browser]:
        return self._host_browser_details

    # --- extension details ---

    def add_extension_details(
        self,
        details: Iterable[ExtensionDetails],
    ) -> None:
        self._extension_details = list(details)

    def get_extension_details(self) -> list[ExtensionDetails]:
        return self._extension_details

    # --- requesting users / devices ---

    def add_requesting_users(
        self,
        users: Iterable[RequestingUser],
    ) -> None:
        self._requesting_users = list(users)

    def get_requesting_users(self) -> list[RequestingUser]:
        return self._requesting_users

    def add_requesting_devices(
        self,
        devices: Iterable[RequestingDevice],
    ) -> None:
        self._requesting_devices = list(devices)

    def get_requesting_devices(self) -> list[RequestingDevice]:
        return self._requesting_devices

    # --- org units ---

    def add_org_units(
        self,
        org_units: Iterable[OrgUnit],
    ) -> None:
        self._org_units = list(org_units)

    def get_org_units(self) -> list[OrgUnit]:
        return self._org_units

    # --- resolved policies ---

    def add_resolved_policies(
        self,
        policies: Iterable[ResolvedPolicy],
    ) -> None:
        self._resolved_policies = list(policies)

    def get_resolved_policies(self) -> list[ResolvedPolicy]:
        return self._resolved_policies

    # --- directory users (Ping, CreateUser, UpdateUser, DeleteUser, ListUsers, Enrich) ---

    def set_directory_users(self, users: list[dict[str, Any]]) -> None:
        """Replace the full directory user list."""
        self._directory_users = list(users)

    def get_directory_users(self) -> list[dict[str, Any]]:
        return self._directory_users

    def get_directory_user(self, email: str) -> dict[str, Any] | None:
        """Return the first user matching primary email."""
        for u in self._directory_users:
            if u.get("primaryEmail") == email:
                return u
        return None

    def add_directory_user(self, user_data: dict[str, Any]) -> None:
        self._directory_users.append(user_data)

    def remove_directory_user(self, email: str) -> bool:
        """Remove a directory user by email address."""
        before = len(self._directory_users)
        self._directory_users = [
            u for u in self._directory_users if u.get("primaryEmail") != email
        ]
        return len(self._directory_users) < before

    # --- groups ---

    def set_group(self, email: str, group_data: dict[str, Any]) -> None:
        self._groups[email] = group_data

    def get_group(self, email: str) -> dict[str, Any] | None:
        return self._groups.get(email)

    def remove_group(self, email: str) -> bool:
        if email in self._groups:
            del self._groups[email]
            return True
        return False

    # --- group members ---

    def set_group_members(self, group_email: str, members: list[dict[str, Any]]) -> None:
        self._group_members[group_email] = list(members)

    def get_group_members(self, group_email: str) -> list[dict[str, Any]]:
        return self._group_members.get(group_email, [])

    def add_group_member(self, group_email: str, member_data: dict[str, Any]) -> None:
        if group_email not in self._group_members:
            self._group_members[group_email] = []
        self._group_members[group_email].append(member_data)

    def remove_group_member(self, group_email: str, member_email: str) -> bool:
        """Remove a member from a group by email address."""
        if group_email not in self._group_members:
            return False
        before = len(self._group_members[group_email])
        self._group_members[group_email] = [
            m for m in self._group_members[group_email]
            if m.get("email") != member_email
        ]
        return len(self._group_members[group_email]) < before

    # --- group settings ---

    def set_group_settings(self, group_email: str, settings: dict[str, Any]) -> None:
        self._group_settings[group_email] = settings

    def get_group_settings(self, group_email: str) -> dict[str, Any] | None:
        return self._group_settings.get(group_email)

    # --- role assignments ---

    def set_role_assignments(
        self, user_key: str, assignments: list[dict[str, Any]]
    ) -> None:
        self._role_assignments[user_key] = list(assignments)

    def get_role_assignments(self, user_key: str) -> list[dict[str, Any]]:
        return self._role_assignments.get(user_key, [])

    # --- roles ---

    def set_role(self, role_id: str, role_data: dict[str, Any]) -> None:
        self._roles[role_id] = role_data

    def get_role(self, role_id: str) -> dict[str, Any] | None:
        return self._roles.get(role_id)
