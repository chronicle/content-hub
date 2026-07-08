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

from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..constants import REQUEST_TIMEOUT, SEVERITIES
from ..data_models import AlertNote, AlertUpdateResult, SentinelOneAlertDetails
from ..exceptions import (
    SentinelOneSingularityOperationsCenterError,
    UserNotFoundError,
)
from .api_utils import get_full_url, validate_response
from .queries import (
    ADD_ALERT_NOTE_MUTATION,
    GET_ALERT_DETAILS_QUERY,
    GET_UNIFIED_ALERTS_QUERY,
    TEST_CONNECTIVITY_QUERY,
    UPDATE_ALERT_MUTATION,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger


class ApiParameters(NamedTuple):
    api_root: str


class SentinelOneSingularityOperationsCenterApiClient(Apiable):
    PAGE_SIZE = 100

    def __init__(
        self,
        authenticated_session: Session,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,  # type: ignore # noqa: PGH003
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root

    def test_connectivity(self) -> None:
        """Test connectivity to SentinelOne Singularity Operations Center."""
        url: str = get_full_url(self.api_root, "graphql_unified_alerts")

        # Payload to list 1 alert with limited fields as per specification
        payload = {
            "query": TEST_CONNECTIVITY_QUERY,
            "variables": {
                "first": 1,
                "viewType": "ALL",
            },
        }

        response: Response = self.session.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        validate_response(
            response,
            error_msg="Failed to connect to the SentinelOne Singularity Operations Center server",
        )

    @staticmethod
    def _get_nested_value(data: dict, path: list[str]) -> dict | list:
        """Safely traverse a nested dictionary using a list of keys.

        Args:
            data (dict): The dictionary to traverse.
            path (list[str]): The path of keys.

        Returns:
            dict | list: The value at the end of the path, or an empty dict if not found.

        """
        val = data
        for key in path:
            if not isinstance(val, dict):
                return {}
            val = val.get(key)
            if val is None:
                return {}
        return val

    @staticmethod
    def _extract_node(edge: dict) -> dict | None:
        """Safely extract the node dictionary from a GraphQL edge.

        Args:
            edge (dict): The edge dictionary.

        Returns:
            dict, optional: The node dictionary if available, otherwise None.

        """
        return edge.get("node") if edge else None

    @staticmethod
    def build_unified_alerts_or_filter(
        start_timestamp_ms: int | None = None,
        lowest_severity: str | None = None,
    ) -> dict | None:
        """Build GraphQL OrFilterSelectionInput from parameters.

        Args:
            start_timestamp_ms (int, optional): The start timestamp in milliseconds.
            lowest_severity (str, optional): The lowest severity to fetch.

        Returns:
            dict, optional: A dictionary representing the OrFilterSelectionInput payload,
                            or None if no filters are applicable.

        """
        common_filters = []
        if lowest_severity:
            lowest_severity_upper = lowest_severity.upper()
            if lowest_severity_upper in SEVERITIES:
                idx = SEVERITIES.index(lowest_severity_upper)
                if idx > 0:
                    target_severities = SEVERITIES[idx:]
                    common_filters.append(
                        {
                            "fieldId": "severity",
                            "stringIn": {"values": target_severities},
                        }
                    )

        if start_timestamp_ms is None:
            if not common_filters:
                return None
            return {"or": [{"and": common_filters}]}

        branch_created = {
            "and": [
                {
                    "fieldId": "createdAt",
                    "dateTimeRange": {"start": start_timestamp_ms, "end": None},
                },
                *common_filters,
            ]
        }
        branch_updated = {
            "and": [
                {
                    "fieldId": "updatedAt",
                    "dateTimeRange": {"start": start_timestamp_ms, "end": None},
                },
                *common_filters,
            ]
        }

        return {"or": [branch_created, branch_updated]}

    def _fetch_pages(
        self,
        url: str,
        query: str,
        variables: dict,
        data_path: list[str],
        error_msg: str = "Failed to fetch paginated data",
    ) -> Generator[tuple[list[dict], dict], None, None]:
        """Fetch pages sequentially from a GraphQL connection endpoint.

        Args:
            url (str): The GraphQL endpoint URL.
            query (str): The GraphQL query string.
            variables (dict): The query variables.
            data_path (list[str]): The path of keys to reach the connection object in the response.
            error_msg (str): Error message to display on failure.

        Yields:
            tuple[list[dict], dict]: A tuple of (edges list, page_info dict) for each page.

        """
        cursor: str | None = None
        has_next_page = True

        while has_next_page:
            payload = {
                "query": query,
                "variables": {**variables, "after": cursor},
            }

            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            validate_response(response, error_msg=error_msg)

            response_json = response.json()
            connection = self._get_nested_value(response_json, data_path) or {}

            edges = connection.get("edges") or []
            page_info = connection.get("pageInfo") or {}

            yield edges, page_info

            cursor = page_info.get("endCursor")
            has_next_page = bool(page_info.get("hasNextPage", False)) and bool(cursor)

    def yield_unified_alerts(
        self,
        limit: int | None = None,
        start_timestamp_ms: int | None = None,
        lowest_severity: str | None = None,
    ) -> Generator[dict, None, None]:
        """Stream unified alerts one-by-one from SentinelOne.

        Args:
            limit (int, optional): The maximum number of alerts to yield.
            start_timestamp_ms (int, optional): The start timestamp in milliseconds.
            lowest_severity (str, optional): The lowest severity to fetch.

        Yields:
            dict: An individual raw alert dictionary.

        """
        url = get_full_url(self.api_root, "graphql_unified_alerts")
        or_filter = self.build_unified_alerts_or_filter(
            start_timestamp_ms=start_timestamp_ms,
            lowest_severity=lowest_severity,
        )
        variables = {
            "first": self.PAGE_SIZE,
            "viewType": "ALL",
            "orFilter": or_filter,
            "sorts": [{"by": "createdAt", "order": "ASC"}],
        }

        pages_gen = self._fetch_pages(
            url=url,
            query=GET_UNIFIED_ALERTS_QUERY,
            variables=variables,
            data_path=["data", "alerts"],
            error_msg="Failed to fetch unified alerts from SentinelOne",
        )

        nodes_gen = (
            self._extract_node(edge) for edges, _ in pages_gen for edge in edges
        )

        for count, node in enumerate((n for n in nodes_gen if n), start=1):
            yield node

            if limit is not None and count >= limit:
                break

    def get_alert_details(self, alert_id: str) -> SentinelOneAlertDetails:
        """Get full details of an alert by ID.

        Args:
            alert_id (str): The ID of the alert to fetch.

        Returns:
            SentinelOneAlertDetails: The alert details object.

        """
        url: str = get_full_url(self.api_root, "graphql_unified_alerts")
        payload = {"query": GET_ALERT_DETAILS_QUERY, "variables": {"id": alert_id}}
        response: Response = self.session.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        validate_response(
            response,
            error_msg=f"Failed to fetch alert details for ID {alert_id}",
        )
        response_json = response.json()
        data = response_json.get("data", {}) or {}
        return SentinelOneAlertDetails(data.get("alert") or {})

    def update_alert(
        self,
        alert_id: str,
        status: str | None = None,
        analyst_verdict: str | None = None,
        assignee_id: int | bool | None = False,  # noqa: FBT001, FBT002
    ) -> AlertUpdateResult:
        """Update a SentinelOne alert's status, analyst verdict, and/or assignee.

        Args:
            alert_id (str): The ID of the alert to update.
            status (str, optional): The target SentinelOne Status enum (NEW, IN_PROGRESS, RESOLVED).
            analyst_verdict (str, optional): The target SentinelOne AnalystVerdict enum.
            assignee_id (int | None | bool, optional): The ID of the user to assign,
                None to unassign, or False if not provided.

        Returns:
            AlertUpdateResult: The structured result of the update.

        """
        # Build the actions payload list based on provided arguments
        actions_payload = []

        if status:
            actions_payload.append(
                {
                    "id": "S1/alert/statusUpdate",
                    "payload": {"status": {"value": status}},
                }
            )

        if analyst_verdict:
            actions_payload.append(
                {
                    "id": "S1/alert/analystVerdictUpdate",
                    "payload": {"analystVerdict": {"value": analyst_verdict}},
                }
            )

        if assignee_id is not False:
            actions_payload.append(
                {
                    "id": "S1/alert/assignUser",
                    "payload": {"assignUser": {"value": assignee_id}},
                }
            )

        payload = {
            "query": UPDATE_ALERT_MUTATION,
            "variables": {
                "actions": actions_payload,
                "filter": {
                    "or": [
                        {"and": [{"fieldId": "id", "stringEqual": {"value": alert_id}}]}
                    ]
                },
                "viewType": "ALL",
            },
        }

        response = self.session.post(
            get_full_url(self.api_root, "graphql_unified_alerts"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        validate_response(
            response,
            error_msg=f"Failed to execute Update Alert action for alert {alert_id}",
        )

        return AlertUpdateResult.from_api_response(
            response_data=response.json(),
            alert_id=alert_id,
        )

    def get_user_id_by_email(self, email: str) -> int:
        """Resolve a SentinelOne User ID from their email address.

        Args:
            email (str): The email address of the user to resolve.

        Returns:
            int: The numerical User ID.

        Raises:
            UserNotFoundError: If no matching user is found in SentinelOne.

        """
        url = get_full_url(self.api_root, "users")
        response = self.session.get(
            url,
            params={"email": email},
            timeout=REQUEST_TIMEOUT,
        )

        validate_response(
            response,
            error_msg=f"Failed to search for user email '{email}' in SentinelOne",
        )

        data = response.json().get("data") or []
        if not data:
            msg = f"User with email '{email}' was not found in SentinelOne."
            raise UserNotFoundError(msg)

        # Extract the ID of the matching user safely
        first_user = data[0]
        if not isinstance(first_user, dict) or "id" not in first_user:
            msg = f"User data for '{email}' is malformed or missing 'id'."
            raise SentinelOneSingularityOperationsCenterError(msg)
        try:
            return int(first_user["id"])
        except (ValueError, TypeError) as e:
            msg = f"Failed to parse user ID '{first_user.get('id')}' as integer: {e}"
            raise SentinelOneSingularityOperationsCenterError(msg) from e

    def add_alert_comment(
        self,
        alert_id: str,
        comment: str,
        comment_type: str | None = None,
    ) -> AlertNote:
        """Add a comment/note to a SentinelOne alert.

        Args:
            alert_id (str): The ID of the alert to add the comment to.
            comment (str): The text of the comment.
            comment_type (str, optional): The content type (HTML, MARKDOWN, PLAIN_TEXT).

        Returns:
            AlertNote: The created alert note.

        """
        url = get_full_url(self.api_root, "graphql_unified_alerts")

        variables: dict[str, str] = {
            "alertId": alert_id,
            "text": comment,
        }
        if comment_type:
            variables["type"] = comment_type
        if not comment_type or comment_type == "PLAIN_TEXT":
            variables["plainText"] = comment

        payload = {
            "query": ADD_ALERT_NOTE_MUTATION,
            "variables": variables,
        }

        response = self.session.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        validate_response(
            response,
            error_msg=f"Failed to execute Add Alert Comment action for alert {alert_id}",
        )

        response_json = response.json()
        data = response_json.get("data") or {}
        result = data.get("addAlertNote") or {}
        note_data = result.get("data") or {}
        if isinstance(note_data, list):
            note_data = note_data[0] if note_data else {}
        return AlertNote(note_data)
