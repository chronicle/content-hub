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

import json
from typing import TYPE_CHECKING, Any
import requests

from . import consts, exceptions
from .data_models import ApiParameters
from .utils import get_parent_resource_name

if TYPE_CHECKING:
    from google.auth.transport.requests import AuthorizedSession
    from TIPCommon.base.interfaces.logger import ScriptLogger
    import TIPCommon.types


MAX_PAGE_SIZE = 1000


class ChronicleInvestigationApiClient:
    """Chronicle Investigation API client."""

    def __init__(
        self,
        api_params: ApiParameters,
        logger: ScriptLogger,
        authenticated_session: AuthorizedSession,
    ) -> None:
        """Initialize a new ChronicleInvestigationApiClient.

        Args:
            api_params: The API parameters.
            logger: The logger.
            authenticated_session: The authenticated session.
        """
        self.api_params = api_params
        self.logger = logger
        self.session = authenticated_session

    def test_connectivity(self) -> None:
        """Test connectivity to the Chronicle API."""
        try:
            self.list_investigations(
                alert_id="siemplify-connectivity-test",
                page_size=1,
            )
        except exceptions.ChronicleInvestigationManagerError as e:
            raise exceptions.ChronicleInvestigationManagerError(
                exceptions.UNABLE_TO_CONNECT_ERROR % e,
            ) from e

    def trigger_investigation(self, alert_id: str) -> TIPCommon.types.SingleJson:
        """Trigger an investigation.

        Args:
            alert_id: The alert ID.

        Returns:
            The investigation data.
        """
        url = f"{self.api_params.api_root}/investigations:trigger"
        payload = {"alertId": alert_id}
        self.logger.info(f"Triggering investigation at: {url}")
        response = self.session.post(url, json=payload)
        validate_response(response, "Failed to trigger investigation")
        return response.json()

    def get_investigation_status(self, investigation_name: str) -> TIPCommon.types.SingleJson:
        """Get the status of an investigation.

        Args:
            investigation_name: The investigation name.

        Returns:
            The investigation status.
        """
        if "/v1alpha" in self.api_params.api_root:
            base_url = self.api_params.api_root.split("/v1alpha")[0] + "/v1alpha"
        else:
            base_url = self.api_params.api_root.rstrip("/")
        url = f"{base_url}/{investigation_name}"
        self.logger.info(f"Checking status for: {url}")
        response = self.session.get(url)
        validate_response(response, "Failed to get investigation status")
        return response.json()

    def list_investigations(
        self,
        alert_id: str,
        page_size: int = MAX_PAGE_SIZE,
    ) -> TIPCommon.types.SingleJson:
        """List investigations.

        Args:
            alert_id: The alert ID.
            page_size: The page size.

        Returns:
            The list of investigations.
        """
        url = f"{self.api_params.api_root}/investigations"
        params = {"pageSize": page_size, "filter": f"alert_id='{alert_id}'"}
        self.logger.info(f"Listing investigations from: {url}")
        response = self.session.get(url, params=params)
        validate_response(response, "Failed to list investigations")
        return response.json().get("investigations", [])

    def paginate(
        self,
        url: str,
        results_key: str,
        params: dict[str, Any] | None = None,
        page_size: int | None = None,
        limit: int | None = None,
        page_token_param_name: str = "pageToken",
        next_page_token_key: str = "nextPageToken",
        total_size_key: str = "totalSize",
        error_msg: str = "Failed to fetch paginated results",
    ) -> list[dict[str, Any]]:
        """A reusable method to handle token-based paginated API requests.

        Args:
            url: The API endpoint URL.
            results_key: The key in the JSON response containing the list of items.
            params: Initial query parameters for the request.
            page_size: Optional number of items per page ('page_size' parameter).
            limit: Maximum number of total items to retrieve across pages.
            page_token_param_name: The query parameter name for the page token ('page_token').
            next_page_token_key: The key in JSON response containing the next page token ('next_page_token').
            total_size_key: The key in JSON response containing the total size ('total_size').
            error_msg: Error message for validation on failure.

        Returns:
            List of raw dictionaries for the items.
        """
        current_params = dict(params) if params else {}
        if page_size is not None:
            current_params["pageSize"] = page_size

        results: list[dict[str, Any]] = []
        next_token: str | None = None

        while True:
            if next_token:
                current_params[page_token_param_name] = next_token

            response = self.session.get(url, params=current_params)
            validate_response(response, error_msg)
            res_json = response.json()

            page_items = res_json.get(results_key, [])
            results.extend(page_items)

            if limit is not None and len(results) >= limit:
                results = results[:limit]
                break

            total_size = res_json.get(total_size_key)
            if total_size is not None and len(results) >= total_size:
                break

            next_token = res_json.get(next_page_token_key)
            if not next_token:
                break

        return results

    def list_remediation_plans(
        self,
        alert_id: str | None = None,
        filter: str | None = None,
        order_by: str | None = None,
        expand: str | None = None,
        page_size: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List remediation plans for a SIEM alert with pagination support.

        Args:
            alert_id: The SIEM alert ID to filter by.
            filter: Explicit filter expression (used if alert_id is not provided).
            order_by: Order by expression (e.g. 'create_time desc').
            expand: Related sub-resources to expand (e.g. 'actions, latest_execution').
            page_size: The number of items to return per page.
            limit: Maximum total plans to retrieve.

        Returns:
            List of remediation plans as raw dictionaries.
        """
        url = f"{self.api_params.api_root}/remediationPlans"
        params: dict[str, Any] = {}

        if alert_id:
            params["filter"] = f'(siemAlertId="{alert_id}")'
        elif filter:
            params["filter"] = filter

        if order_by:
            params["orderBy"] = order_by

        if expand:
            params["expand"] = expand

        self.logger.info(
            f"Listing remediation plans from: {url} with filter: {params.get('filter')}"
        )

        return self.paginate(
            url=url,
            results_key="remediationPlans",
            params=params,
            page_size=page_size,
            limit=limit,
            error_msg="Failed to list remediation plans",
        )

    def generate_remediation_plan(self, alert_id: str) -> dict[str, Any]:
        """Trigger generation of a new remediation plan for a SIEM alert.

        Args:
            alert_id: The SIEM alert ID.

        Returns:
            The created remediation plan data.
        """
        url = f"{self.api_params.api_root}/remediationPlans:generate"
        payload: dict[str, Any] = {
            "parent": get_parent_resource_name(),
            "siemAlertId": alert_id,
        }

        self.logger.info(f"Generating remediation plan at: {url}")

        response = self.session.post(url, json=payload)
        validate_response(response, "Failed to generate remediation plan")

        return response.json()

    def get_remediation_plan(self, plan_id: int) -> dict[str, Any]:
        """Get details of a remediation plan.

        Args:
            plan_id: Remediation plan identifier.

        Returns:
            The remediation plan data.
        """
        url = f"{self.api_params.api_root}/remediationPlans/{plan_id}"

        self.logger.info(f"Getting remediation plan from: {url}")

        response = self.session.get(url)
        validate_response(response, "Failed to get remediation plan details")

        return response.json()

    def list_remediation_action_executions(
        self,
        plan_id: int | str,
        filter: str | None = None,
        order_by: str | None = None,
        include_all_executions: bool | None = None,
        page_size: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List execution records for actions within a remediation plan with pagination support.

        Args:
            plan_id: Remediation plan identifier.
            filter: Optional filter string for filtering action executions.
            order_by: Optional order by expression for sorting action executions.
            include_all_executions: Optional flag to include all historical executions or just the latest.
            page_size: Optional page size for pagination.
            limit: Optional maximum number of action executions to fetch in total.

        Returns:
            List of remediation action execution records as raw dictionaries.
        """
        url = (
            f"{self.api_params.api_root}/remediationPlans/{plan_id}/"
            "remediationActions/-/remediationActionExecutions"
        )
        params: dict[str, Any] = {}
        if filter:
            params["filter"] = filter
        if order_by:
            params["orderBy"] = order_by
        if include_all_executions is not None:
            params["includeAllExecutions"] = include_all_executions

        self.logger.info(
            f"Listing remediation action executions from: {url} with params: {params}"
        )

        return self.paginate(
            url=url,
            results_key="remediationActionExecutions",
            params=params,
            page_size=page_size,
            limit=limit,
            error_msg="Failed to list remediation action executions",
        )


def validate_response(response: requests.Response, error_msg: str = "An error occurred") -> None:
    """Validate a response.

    Args:
        response: The response.
        error_msg: The error message.
    """
    try:
        if response.status_code == consts.API_LIMIT_ERROR:
            raise exceptions.GoogleChronicleAPILimitError(
                exceptions.API_LIMIT_ERROR_MESSAGE,
            )
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
            error_content = (
                response.json().get("error", {}).get("message", response.content)
            )
            error_message = f"{error_msg}: {error} {error_content}"
            raise exceptions.ChronicleInvestigationManagerError(
                error_message,
            ) from error
        except json.JSONDecodeError as e:
            error_message = f"{error_msg}: {error} {response.content}"
            raise exceptions.ChronicleInvestigationManagerError(
                error_message,
            ) from e
