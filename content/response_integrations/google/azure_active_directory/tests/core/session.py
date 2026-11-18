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
import copy
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse, unquote
from requests.exceptions import HTTPError
from azure_active_directory.core.AzureADParser import AzureADParser
from azure_active_directory.tests.core.product import AzureADProduct


class MockResponse:
    """Mock response object for requests."""

    def __init__(self, json_data: Any, status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.content = json.dumps(json_data).encode("utf-8")
        self.text = json.dumps(json_data)

    def json(self) -> Any:
        """Return JSON data."""
        return self.json_data

    def raise_for_status(self) -> None:
        """Raise HTTPError if status code is 400 or higher."""
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}", response=self)


class AzureADSession:
    """Mock session object for Azure AD operations."""

    def __init__(
        self,
        product: AzureADProduct,
        raw_mock_data: dict[str, Any],
        parser: AzureADParser,
    ):
        self.product = product
        self.raw_mock_data = raw_mock_data
        self.parser = parser
        self.headers = {}
        self.verify = True

    def _maybe_fail(self) -> MockResponse | None:
        """Return a 500 error response when global failure mode is active."""
        if self.product._fail_all_requests:
            return MockResponse({"error": {"message": "Simulated API failure"}}, 500)
        return None

    def post(self, url: str, **_kwargs: Any) -> MockResponse:
        if (fail := self._maybe_fail()) is not None:
            return fail

        if "/oauth2/v2.0/token" in url:
            return MockResponse(
                {"access_token": "mock_token", "expires_in": 3599}
            )

        # getMemberGroups — returns list of group IDs for a user
        if "/getMemberGroups" in url:
            return self._handle_get_member_groups(url)

        # revokeSignInSessions
        if "/revokeSignInSessions" in url:
            return self._handle_revoke_sign_in_sessions(url)

        # add user to group  (v1.0/groups/{id}/members/$ref)
        if "/members/$ref" in url and "/groups/" in url:
            return MockResponse({}, 204)

        return MockResponse({"error": "Not Found"}, 404)

    def _handle_get_member_groups(self, url: str) -> MockResponse:
        """Return group IDs for a user's getMemberGroups call."""
        parts = urlparse(url).path.strip("/").split("/")
        try:
            users_idx = parts.index("users")
            upn = unquote(parts[users_idx + 1])
            group_ids = self.product.get_user_group_memberships(upn)
            return MockResponse({"value": group_ids})
        except (ValueError, IndexError):
            return MockResponse({"value": []})

    def _handle_revoke_sign_in_sessions(self, url: str) -> MockResponse:
        """Return revoke session result for a given user_id."""
        parts = urlparse(url).path.strip("/").split("/")
        try:
            users_idx = parts.index("users")
            user_id = unquote(parts[users_idx + 1])
            result = self.product.get_revoke_session_result(user_id)
            return MockResponse(result, 200)
        except (ValueError, IndexError):
            return MockResponse({"value": True}, 200)

    def get(self, url: str, **kwargs: Any) -> MockResponse:
        if (fail := self._maybe_fail()) is not None:
            return fail

        parsed_url = urlparse(url)
        path = parsed_url.path

        raw_params = kwargs.get("params", {})
        parsed_params = {}

        if isinstance(raw_params, str):
            query_string = raw_params.split("?")[-1]
            parsed_params = {k: v[0] for k, v in parse_qs(query_string).items()}
        elif isinstance(raw_params, dict):
            parsed_params = raw_params

        select_fields_str = parsed_params.get("$select")
        expand_fields_str = parsed_params.get("$expand")

        if path.endswith("/v1.0"):
            return MockResponse({}, 200)

        if "/manager" in path:
            return self._handle_manager_request(
                path, select_fields_str, expand_fields_str
            )

        if "/groups/" in path and "/members" in path:
            return self._handle_group_members_request(path, parsed_params)

        if "/groups" in path and "/members" not in path:
            return self._handle_list_groups_request(parsed_params)

        if "/devices" in path:
            return self._handle_devices_request(parsed_params)

        if "/memberOf" in path:
            return self._handle_member_of_request(path, parsed_params)

        if "userRegistrationDetails" in path:
            return self._handle_registration_details(parsed_params)

        # users list or search (no user ID in path)
        if path.rstrip("/").endswith("/users"):
            return self._handle_list_users_request(parsed_params)

        if "/users/" in path and "/manager" not in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 3 and parts[-2] == "users":
                return self._handle_get_user(parts[-1])

        return MockResponse({"error": "Not Found"}, 404)

    def _handle_get_user(self, encoded_upn: str) -> MockResponse:
        """Helper to handle fetching a specific user by UPN."""
        user_upn = unquote(encoded_upn)
        user_data = self.product.users.get(user_upn.lower())
        if user_data:
            return MockResponse(user_data, 200)
        return MockResponse({"error": {"message": "User not found"}}, 404)

    def _handle_list_users_request(self, params: dict) -> MockResponse:
        """Return all users, supporting $filter for finding users by displayName/mail."""
        filter_str = params.get("$filter", "")
        all_users = list(self.product.users.values())

        if filter_str:
            # Support simple `displayName eq 'X' or mail eq 'X'` etc. for get_user_id_with_filter
            matched = []
            for user in all_users:
                # try to find any attribute match in the filter
                conditions = re.findall(r"(\w+)\s+eq\s+'([^']*)'", filter_str)
                for attr, val in conditions:
                    if user.get(attr, "").casefold() == val.casefold():
                        matched.append(user)
                        break
            return MockResponse({"value": matched})

        return MockResponse({"value": all_users})

    def _handle_list_groups_request(self, params: dict) -> MockResponse:
        """Helper to handle list groups logic returning predefined responses."""
        all_groups_raw = self.product.get_groups()

        filter_str = params.get("$filter")

        if filter_str:
            if "startsWith(displayName," in filter_str:
                filter_val = filter_str.split("'")[1]
                all_groups_raw = [
                    group for group in all_groups_raw
                    if group.get("displayName", "").lower()
                    .startswith(filter_val.lower())
                ]
            # Support `displayName eq 'X' or mailNickname eq 'X'` (get_group_by_name)
            elif "eq '" in filter_str:
                conditions = re.findall(r"(\w+)\s+eq\s+'([^']*)'", filter_str)
                matched = []
                for group in all_groups_raw:
                    for attr, val in conditions:
                        if group.get(attr, "") == val:
                            matched.append(group)
                            break
                all_groups_raw = matched

        order_by = params.get("$orderby")
        if order_by:
            parts = order_by.split()
            if len(parts) == 2:
                field_name, direction = parts
                all_groups_raw = sorted(
                    all_groups_raw,
                    key=lambda x: x.get(field_name, ""),
                    reverse=direction.lower() == "desc",
                )

        limit = params.get("$top")
        if limit:
            all_groups_raw = all_groups_raw[: int(limit)]

        select = params.get("$select")
        if select:
            select_fields = [f.strip() for f in select.split(",")]
            all_groups_raw = [
                {k: v for k, v in g.items() if k in select_fields}
                for g in all_groups_raw
            ]

        return MockResponse({"value": all_groups_raw}, 200)

    def _handle_group_members_request(self, path: str, params: dict) -> MockResponse:
        """Return group members for a specific group."""
        parts = path.strip("/").split("/")
        try:
            groups_idx = parts.index("groups")
            group_id = parts[groups_idx + 1]
            members = self.product.get_group_members_list(group_id)

            limit = params.get("$top")
            if limit:
                members = members[: int(limit)]

            return MockResponse({"value": members}, 200)
        except (ValueError, IndexError):
            return MockResponse({"value": []}, 200)

    def _handle_member_of_request(self, path: str, params: dict) -> MockResponse:
        """Check if a user is a member of a group (IsUserInGroup)."""
        parts = path.strip("/").split("/")
        try:
            users_idx = parts.index("users")
            upn = unquote(parts[users_idx + 1])

            # The filter looks like `id eq '<group_id>'`
            filter_str = params.get("$filter", "")
            match = re.search(r"id\s+eq\s+'([^']+)'", filter_str)
            if match:
                group_id = match.group(1)
                user_data = self.product.users.get(upn.lower())
                if user_data and self.product.is_user_in_group(
                    user_data.get("id", ""), group_id
                ):
                    return MockResponse({"value": [{"id": group_id}]}, 200)
            return MockResponse({"value": []}, 200)
        except (ValueError, IndexError):
            return MockResponse({"value": []}, 200)

    def _handle_manager_request(self, path, select, expand) -> MockResponse:
        """Helper to handle manager profile logic returning predefined responses."""
        parts = path.strip("/").split("/")
        try:
            user_upn = unquote(parts[parts.index("users") + 1])

            if not self.product.get_manager(user_upn):
                return MockResponse(
                    {"error": {"message": "Resource not found"}}, 404
                )

            if expand == "sponsors" and select == "displayName":
                return MockResponse(
                    self.raw_mock_data["manager_sponsors_response"],
                    200
                )

            if select == "displayName,mobilePhone,mail":
                return MockResponse(
                    self.raw_mock_data["manager_default_response"],
                    200
                )

            if select == "displayName,mobilePhone,mail,department":
                return MockResponse(
                    self.raw_mock_data["manager_custom_fields_response"],
                    200
                )

            manager_data = self.product.get_manager(user_upn) or copy.deepcopy(
                self.raw_mock_data["manager_full_profile_with_sponsors"]
            )
            return MockResponse(manager_data, 200)
        except (ValueError, IndexError, KeyError):
            return MockResponse({"error": "Bad Request"}, 400)

    def _handle_registration_details(self, params) -> MockResponse:
        """Helper to handle user registration details."""
        filter_str = params.get("$filter", "")
        match = re.search(
            r"userPrincipalName\s*eq\s*'([^']+)'", filter_str, re.IGNORECASE
        )

        if match:
            upn = match.group(1)
            details = self.product.get_user_registration_details(upn)
            if details:
                return MockResponse({"value": [details]})
            return MockResponse({"value": []})

        return MockResponse({"value": []})

    def _handle_devices_request(self, params: dict) -> MockResponse:
        """Return devices matching a displayName filter."""
        filter_str = params.get("$filter", "") if isinstance(params, dict) else params
        match = re.search(r"displayName\s*%20eq%20'([^']+)'", filter_str)
        if not match:
            match = re.search(r"displayName\s+eq\s+'([^']+)'", filter_str)
        if match:
            hostname = match.group(1)
            devices = self.product.get_devices_by_hostname(hostname)
            return MockResponse({"value": devices}, 200)
        return MockResponse({"value": []}, 200)

    def patch(self, url: str, **_kwargs: Any) -> MockResponse:
        """Handle PATCH requests (enable/disable user, force password update, reset password)."""
        if (fail := self._maybe_fail()) is not None:
            return fail
        return MockResponse({}, 204)

    def delete(self, url: str, **_kwargs: Any) -> MockResponse:
        """Handle DELETE requests (remove user from group)."""
        if (fail := self._maybe_fail()) is not None:
            return fail
        # 404 means user not in group
        if "/members/" in url:
            return MockResponse({}, 204)
        return MockResponse({"error": "Not Found"}, 404)

    def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        """Route request to the appropriate method."""
        method = method.upper()
        if method == "GET":
            return self.get(url, **kwargs)
        if method == "POST":
            return self.post(url, **kwargs)
        if method == "PATCH":
            return self.patch(url, **kwargs)
        if method == "DELETE":
            return self.delete(url, **kwargs)
        return MockResponse({"error": "Method not allowed"}, 405)
