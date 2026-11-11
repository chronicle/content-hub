from __future__ import annotations

import datetime
import re

from TIPCommon.types import SingleJson

from g_suite.core.datamodels import (
    Browser,
    ExtensionDetails,
    OrgUnit,
    RequestingDevice,
    RequestingUser,
    ResolvedPolicy,
    UserActivityEvent,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from g_suite.tests.core.product import Product


class ApiSession(MockSession[MockRequest, MockResponse, Product]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            # auth flows
            self.sign_out,
            self.get_access_token,
            self.get_default_service_account,
            self.get_service_account_token,
            self.get_oauth_token,
            # users
            self.get_list_users,
            self.post_create_user,
            self.put_update_user,
            self.delete_user,
            self.get_user,
            # groups
            self.post_create_group,
            self.delete_group,
            self.get_group,
            self.get_group_settings,
            # group members
            self.get_list_group_members,
            self.post_add_group_member,
            self.delete_remove_group_member,
            # org units
            self.post_create_ou,
            self.put_update_ou,
            self.delete_ou,
            self.get_list_ou,
            # role assignments & roles
            self.get_list_role_assignments,
            self.get_role,
            # chrome / extension endpoints
            self.get_user_activity_events,
            self.get_host_browser_details,
            self.get_extension_details,
            self.get_extension_requesting_users,
            self.get_extension_requesting_devices,
            # extension policy endpoints
            self.post_block_extension,
            self.post_resolve_policy,
            self.post_delete_extension,
        ]

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    @router.post(r"/admin/directory/v1/users/\w+@[a-zA-Z]+\.com/signOut")
    def sign_out(self, request: MockRequest) -> MockResponse:
        """Sign out a user."""
        username = re.search(r"\w+@[a-zA-Z]+\.com", request.url.path).group()
        try:
            user = self._product.get_user(username)
            user.is_logged_in = False
        except KeyError:
            return MockResponse(status_code=404, content={})
        return MockResponse()

    @router.post(
        r"/v1/projects/-/serviceAccounts/\w+@[a-zA-Z]+\.com:generateAccessToken"
    )
    def get_access_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "accessToken": "xxxx.yyyy",
                "expireTime": (
                    datetime.datetime.now() + datetime.timedelta(seconds=3600)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    @router.get("/computeMetadata/v1/instance/service-accounts/default/")
    def get_default_service_account(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "email": "default@domain.com",
                "scopes": ["test-scope"],
                "aliases": ["default"],
            },
            headers={"content-type": "application/json"},
        )

    @router.get(
        r"/computeMetadata/v1/instance/service-accounts/\w+@[a-zA-Z]+\.com/token"
    )
    def get_service_account_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            {"access_token": "xxxx.yyyy", "expires_in": 3599, "token_type": "Bearer"},
            headers={"content-type": "application/json"},
        )

    @router.post("/token")
    def get_oauth_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            {"access_token": "xxxx.yyyy", "expires_in": 3599, "token_type": "Bearer"}
        )

    # ------------------------------------------------------------------
    # User endpoints
    # ------------------------------------------------------------------

    @router.get(r"/admin/directory/v1/users$")
    def get_list_users(self, _: MockRequest) -> MockResponse:
        """Mock listing directory users (used by Ping, ListUsers)."""
        users = self._product.get_directory_users()
        return MockResponse(content={"users": users, "nextPageToken": None})

    @router.post(r"/admin/directory/v1/users$")
    def post_create_user(self, request: MockRequest) -> MockResponse:
        """Mock creating a new directory user, returning 409 if email already exists."""
        payload: SingleJson = request.kwargs.get("json", {})
        primary_email = payload.get("primaryEmail", "newuser@domain.com")
        # Check for duplicate email
        existing = self._product.get_directory_user(primary_email)
        if existing is not None:
            return MockResponse(
                content={"error": {"code": 409, "message": "Entity already exists."}},
                status_code=409,
            )
        user_data: SingleJson = {
            "primaryEmail": primary_email,
            "name": payload.get("name", {"givenName": "Test", "familyName": "User"}),
            "id": "mock-user-id",
            "kind": "admin#directory#user",
        }
        self._product.add_directory_user(user_data)
        return MockResponse(content=user_data)

    @router.put(r"/admin/directory/v1/users/[\w.%+\-@]+")
    def put_update_user(self, request: MockRequest) -> MockResponse:
        """Mock updating a directory user by primary email."""
        match = re.search(r"/admin/directory/v1/users/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        email = match.group(1)
        existing = self._product.get_directory_user(email)
        if existing is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        payload: SingleJson = request.kwargs.get("json", {})
        updated = {**existing, **payload}
        # Replace the stored entry
        self._product.remove_directory_user(email)
        self._product.add_directory_user(updated)
        return MockResponse(content=updated)

    @router.delete(r"/admin/directory/v1/users/[\w.%+\-@]+")
    def delete_user(self, request: MockRequest) -> MockResponse:
        """Mock deleting a directory user by primary email."""
        match = re.search(r"/admin/directory/v1/users/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        email = match.group(1)
        found = self._product.remove_directory_user(email)
        if not found:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        return MockResponse(content={})

    @router.get(r"/admin/directory/v1/users/[\w.%+\-@]+")
    def get_user(self, request: MockRequest) -> MockResponse:
        """Mock fetching a single directory user by primary email."""
        match = re.search(r"/admin/directory/v1/users/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        email = match.group(1).lower()
        user_data = self._product.get_directory_user(email)
        if user_data is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        return MockResponse(content=user_data)

    # ------------------------------------------------------------------
    # Group endpoints
    # ------------------------------------------------------------------

    @router.post(r"/admin/directory/v1/groups$")
    def post_create_group(self, request: MockRequest) -> MockResponse:
        """Mock creating a new group."""
        payload: SingleJson = request.kwargs.get("json", {})
        email = payload.get("email", "newgroup@domain.com")
        group_data: SingleJson = {
            "id": "mock-group-id",
            "email": email,
            "name": payload.get("name", "Mock Group"),
            "description": payload.get("description", ""),
            "kind": "admin#directory#group",
        }
        self._product.set_group(email, group_data)
        return MockResponse(content=group_data)

    @router.delete(r"/admin/directory/v1/groups/[\w.%+\-@]+")
    def delete_group(self, request: MockRequest) -> MockResponse:
        """Mock deleting a group by email."""
        match = re.search(r"/admin/directory/v1/groups/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        email = match.group(1)
        found = self._product.remove_group(email)
        if not found:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        return MockResponse(content={})

    @router.get(r"/admin/directory/v1/groups/[\w.%+\-@]+")
    def get_group(self, request: MockRequest) -> MockResponse:
        """Mock fetching a group by email (used by GetGroupDetails, ListGroupPrivileges)."""
        match = re.search(r"/admin/directory/v1/groups/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        email = match.group(1)
        group_data = self._product.get_group(email)
        if group_data is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        return MockResponse(content=group_data)

    @router.get(r"/groups/v1/groups/[\w.%+\-@]+")
    def get_group_settings(self, request: MockRequest) -> MockResponse:
        """Mock fetching group settings (used by GetGroupDetails)."""
        match = re.search(r"/groups/v1/groups/([\w.%+\-@]+)", request.url.path)
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        # The URL may have ?alt=json appended; strip it
        email = match.group(1).split("?")[0]
        settings = self._product.get_group_settings(email)
        if settings is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {email}"}},
            )
        return MockResponse(content=settings)

    # ------------------------------------------------------------------
    # Group member endpoints
    # ------------------------------------------------------------------

    @router.get(r"/admin/directory/v1/groups/[\w.%+\-@]+/members")
    def get_list_group_members(self, request: MockRequest) -> MockResponse:
        """Mock listing members of a group."""
        match = re.search(
            r"/admin/directory/v1/groups/([\w.%+\-@]+)/members", request.url.path
        )
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        group_email = match.group(1)
        members = self._product.get_group_members(group_email)
        if members is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {group_email}"}},
            )
        return MockResponse(content={"members": members, "nextPageToken": None})

    @router.post(r"/admin/directory/v1/groups/[\w.%+\-@]+/members")
    def post_add_group_member(self, request: MockRequest) -> MockResponse:
        """Mock adding a member to a group."""
        match = re.search(
            r"/admin/directory/v1/groups/([\w.%+\-@]+)/members", request.url.path
        )
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        group_email = match.group(1)
        # Group must exist
        if self._product.get_group(group_email) is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {group_email}"}},
            )
        payload: SingleJson = request.kwargs.get("json", {})
        member_email = payload.get("email", "unknown@domain.com")
        # Check for existing member (409 Conflict)
        existing_members = self._product.get_group_members(group_email)
        if any(m.get("email") == member_email for m in existing_members):
            return MockResponse(
                status_code=409,
                content={"error": {"message": "Member already exists."}},
            )
        member_data: SingleJson = {
            "kind": "admin#directory#member",
            "email": member_email,
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "id": "mock-member-id",
        }
        self._product.add_group_member(group_email, member_data)
        return MockResponse(content=member_data)

    @router.delete(r"/admin/directory/v1/groups/[\w.%+\-@]+/members/[\w.%+\-@]+")
    def delete_remove_group_member(self, request: MockRequest) -> MockResponse:
        """Mock removing a member from a group."""
        match = re.search(
            r"/admin/directory/v1/groups/([\w.%+\-@]+)/members/([\w.%+\-@]+)",
            request.url.path,
        )
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        group_email = match.group(1)
        member_email = match.group(2)
        if self._product.get_group(group_email) is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {group_email}"}},
            )
        found = self._product.remove_group_member(group_email, member_email)
        if not found:
            return MockResponse(
                status_code=404,
                content={
                    "error": {"message": f"Resource Not Found: {member_email}"}
                },
            )
        return MockResponse(content={})

    # ------------------------------------------------------------------
    # Org unit endpoints
    # ------------------------------------------------------------------

    @router.post(r"/admin/directory/v1/customer/[\w_]+/orgunits$")
    def post_create_ou(self, request: MockRequest) -> MockResponse:
        """Mock creating an organizational unit."""
        payload: SingleJson = request.kwargs.get("json", {})
        ou_name = payload.get("name", "MockOU")
        ou_data: SingleJson = {
            "kind": "admin#directory#orgUnit",
            "name": ou_name,
            "description": payload.get("description", ""),
            "orgUnitPath": f"/{ou_name}",
            "orgUnitId": "id:mock_ou_id",
            "parentOrgUnitPath": payload.get("parentOrgUnitPath", "/"),
            "parentOrgUnitId": "id:parent_id",
            "etag": '"mock-etag"',
        }
        return MockResponse(content=ou_data)

    @router.put(r"/admin/directory/v1/customer/[\w_]+/orgunits/.+")
    def put_update_ou(self, request: MockRequest) -> MockResponse:
        """Mock updating an organizational unit."""
        payload: SingleJson = request.kwargs.get("json", {})
        ou_name = payload.get("name", "UpdatedOU")
        ou_data: SingleJson = {
            "kind": "admin#directory#orgUnit",
            "name": ou_name,
            "description": payload.get("description", ""),
            "orgUnitPath": f"/{ou_name}",
            "orgUnitId": "id:mock_ou_id",
            "parentOrgUnitPath": "/",
            "parentOrgUnitId": "id:parent_id",
            "etag": '"mock-etag"',
        }
        return MockResponse(content=ou_data)

    @router.delete(r"/admin/directory/v1/customer/[\w_]+/orgunits/.+")
    def delete_ou(self, _request: MockRequest) -> MockResponse:
        """Mock deleting an organizational unit."""
        return MockResponse(content={})

    @router.get(r"/admin/directory/v1/customer/my_customer/orgunits")
    def get_list_ou(self, _: MockRequest) -> MockResponse:
        """Mock listing organizational units."""
        ou_list: list[OrgUnit] = self._product.get_org_units()
        ou_jsons: list[SingleJson] = [ou.as_json() for ou in ou_list]
        return MockResponse(content={"organizationUnits": ou_jsons})

    # ------------------------------------------------------------------
    # Role assignments & role endpoints
    # ------------------------------------------------------------------

    @router.get(r"/admin/directory/v1/customer/[\w_]+/roleassignments")
    def get_list_role_assignments(self, request: MockRequest) -> MockResponse:
        """Mock listing role assignments for a user."""
        params = request.kwargs.get("params", {}) or {}
        user_key = params.get("userKey", "")
        assignments = self._product.get_role_assignments(user_key)
        return MockResponse(content={"items": assignments, "nextPageToken": None})

    @router.get(r"/admin/directory/v1/customer/[\w_]+/roles/[\w]+")
    def get_role(self, request: MockRequest) -> MockResponse:
        """Mock fetching a role by ID."""
        match = re.search(
            r"/admin/directory/v1/customer/[\w_]+/roles/([\w]+)", request.url.path
        )
        if not match:
            return MockResponse(status_code=400, content={"error": {"message": "Bad request"}})
        role_id = match.group(1)
        role_data = self._product.get_role(role_id)
        if role_data is None:
            return MockResponse(
                status_code=404,
                content={"error": {"message": f"Resource Not Found: {role_id}"}},
            )
        return MockResponse(content=role_data)

    # ------------------------------------------------------------------
    # Chrome / extension / activity endpoints (existing routes preserved)
    # ------------------------------------------------------------------

    @router.get(r"/admin/reports/v1/activity/users/.*/applications/.*")
    def get_user_activity_events(self, requests: MockRequest) -> MockResponse:
        """Mock the API endpoint for fetching user activity events."""
        match: re.Match[str] | None = re.search(
            r"/admin/reports/v1/activity/users/(.*?)/applications/(.*)",
            requests.url.path,
        )
        if not match:
            return MockResponse(
                status_code=400, content={"error": "Invalid request URL in mock"}
            )

        request_user_key: str = match.group(1)
        request_app_name: str = match.group(2)

        all_activities: list[UserActivityEvent] = (
            self._product.get_user_activity_events()
        )
        user_filtered_activities: list[UserActivityEvent] = (
            self._filter_activities_by_user(all_activities, request_user_key)
        )
        filtered_activities: list[UserActivityEvent] = self._filter_activities_by_app(
            user_filtered_activities, request_app_name
        )

        if not filtered_activities:
            return MockResponse(
                status_code=404,
                content={"error": {"message": "No matching activity found."}},
            )

        response_data: SingleJson = {
            "items": [activity.to_json() for activity in filtered_activities]
        }
        return MockResponse(status_code=200, content=response_data)

    def _filter_activities_by_user(
        self,
        activities: list[UserActivityEvent],
        user_key: str,
    ) -> list[UserActivityEvent]:
        if user_key == "all":
            return activities
        return [
            activity
            for activity in activities
            if activity.to_json().get("actor", {}).get("email") == user_key
        ]

    def _filter_activities_by_app(
        self,
        activities: list[UserActivityEvent],
        app_name: str,
    ) -> list[UserActivityEvent]:
        if app_name == "all":
            return activities
        filtered: list[UserActivityEvent] = []
        for activity in activities:
            activity_json = activity.to_json()
            app_match: bool = any(
                event.get("name", "").lower() == app_name.lower()
                for event in activity_json.get("events", [])
            )
            if app_match:
                filtered.append(activity)
        return filtered

    @router.get(
        r"/admin/directory/v1.1beta1/customer/my_customer/devices/chromebrowsers"
    )
    def get_host_browser_details(self, _: MockRequest) -> MockResponse:
        """Mock the API endpoint for fetching host browser details."""
        browser_details_list: list[Browser] = self._product.get_host_browser_details()
        json_details: list[SingleJson] = [
            detail.as_json() for detail in browser_details_list
        ]
        return MockResponse(content={"browsers": json_details})

    @router.get(r"/v1/customers/my_customer/apps/chrome/.*")
    def get_extension_details(self, _: MockRequest) -> MockResponse:
        """Mock the API endpoint for fetching extension details."""
        details_list: list[ExtensionDetails] = self._product.get_extension_details()
        if not details_list:
            return MockResponse(
                status_code=404, content={"error": {"message": "Not Found"}}
            )
        return MockResponse(content=details_list[0].to_json())

    @router.get(r"/v1/customers/my_customer/apps:fetchUsersRequestingExtension")
    def get_extension_requesting_users(self, _: MockRequest) -> MockResponse:
        """Mock the API endpoint for fetching users who requested an extension."""
        users_list: list[RequestingUser] = self._product.get_requesting_users()
        json_users: list[SingleJson] = [user.to_json() for user in users_list]
        return MockResponse(content={"userDetails": json_users})

    @router.get(r"/v1/customers/my_customer/apps:fetchDevicesRequestingExtension")
    def get_extension_requesting_devices(self, _: MockRequest) -> MockResponse:
        """Mock the API endpoint for fetching devices that requested an extension."""
        devices_list: list[RequestingDevice] = self._product.get_requesting_devices()
        json_devices: list[SingleJson] = [device.to_json() for device in devices_list]
        return MockResponse(content={"deviceDetails": json_devices})

    @router.post(r"/v1/customers/my_customer/policies/orgunits:batchModify")
    def post_block_extension(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for blocking an extension."""
        error_response: MockResponse | None = self._validate_ou_in_payload(request)
        if error_response:
            return error_response
        return MockResponse(content={})

    @router.post(r"/v1/customers/my_customer/policies/orgunits:batchInherit")
    def post_delete_extension(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for deleting (inheriting) an extension policy."""
        error_response: MockResponse | None = self._validate_ou_in_payload(request)
        if error_response:
            return error_response
        return MockResponse(content={})

    def _validate_ou_in_payload(self, request: MockRequest) -> MockResponse | None:
        extraction_result: tuple[str, str] | MockResponse = (
            self._extract_ou_id_from_payload(request)
        )
        if isinstance(extraction_result, MockResponse):
            return extraction_result
        request_ou_id, target_resource = extraction_result
        if not self._is_valid_org_unit(request_ou_id):
            return MockResponse(
                status_code=404,
                content={
                    "error": {"message": f"Resource not found: {target_resource}"}
                },
            )
        return None

    def _extract_ou_id_from_payload(
        self,
        request: MockRequest,
    ) -> tuple[str, str] | MockResponse:
        try:
            payload: SingleJson | None = request.kwargs.get("json")
            if not payload:
                return MockResponse(
                    status_code=400,
                    content={
                        "error": {"message": "Request is missing a JSON payload."}
                    },
                )
            target_resource: str = payload["requests"][0]["policyTargetKey"][
                "targetResource"
            ]
            request_ou_id: str = target_resource.split("/")[-1]
            return request_ou_id, target_resource
        except (KeyError, IndexError, TypeError):
            return MockResponse(
                status_code=400,
                content={"error": {"message": "Invalid payload format."}},
            )

    def _is_valid_org_unit(self, org_unit_id: str) -> bool:
        all_org_units: list[OrgUnit] = self._product.get_org_units()
        return any(
            ou.as_json().get("orgUnitId", "").split(":")[-1] == org_unit_id
            for ou in all_org_units
        )

    @router.post(r"/v1/customers/my_customer/policies:resolve")
    def post_resolve_policy(self, _: MockRequest) -> MockResponse:
        """Mock the API endpoint for resolving policies."""
        resolved_policies: list[ResolvedPolicy] = self._product.get_resolved_policies()
        json_policies: list[SingleJson] = [
            policy.to_json() for policy in resolved_policies
        ]
        return MockResponse(content={"resolvedPolicies": json_policies})
