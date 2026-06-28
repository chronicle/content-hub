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

from datetime import datetime, timezone
from urllib.parse import urljoin
import json
import requests

from google.auth.transport.requests import AuthorizedSession

from TIPCommon.base.interfaces import Apiable
from TIPCommon.types import SingleJson
from TIPCommon.rest.gcp import validate_impersonation

from cloud_logging.core.consts import (
    ENDPOINTS,
    API_URL,
    INTEGRATION_DISPLAY_NAME,
    TIME_INTERVALS,
    CUSTOM_TIME,
)
from cloud_logging.core.datamodels import ApiManagerParams
from cloud_logging.core.exceptions import CloudLoggingManagerError, CloudAuthenticationError


class CloudLoggingApiManager(Apiable):
    """
    Google Cloud Logging API Manager
    """

    def __init__(self, session: AuthorizedSession, params: ApiManagerParams) -> None:
        self.session: AuthorizedSession = session
        self.api_root = params.api_root
        self.project_id = params.project_id
        self.organization_id = params.organization_id

    def _get_full_url(self, url_key: str, **kwargs) -> str:
        """
        Get full url from url key.

        Args:
            url_id: {str} The key of url
            kwargs: {dict} Key value arguments passed for string formatting

        Returns:
            {str} The full url
        """
        url = ENDPOINTS[url_key].format(**kwargs)
        full_url = urljoin(self.api_root, url)

        return full_url

    def validate_response(
        self, response: requests.Response, error_msg="An error occurred"
    ) -> None:
        """Validate a response.

        Args:
            response: The response
            error_msg: Error message prefix

        Raises:
            ImpersonationUnauthorizedError: if impersonation fails.
            GoogleCloudAuthenticationError: if there is a problem with permisions.
            GoogleCloudLoggingManagerError: if any other unknown HTTPError occurs.
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response_json = response.json()

            except json.JSONDecodeError as e:
                raise CloudLoggingManagerError(
                    f"{error_msg}: {error} {response.text}"
                ) from e

            validate_impersonation(response_json)
            json_err_message = response_json.get("error", {}).get("message", "")

            if response.status_code in (401, 403):
                raise CloudAuthenticationError(
                    f"Authentication error - {error} "
                    f"{json_err_message or response.text}"
                ) from error

            raise CloudLoggingManagerError(
                f"{error_msg}: {error} {json_err_message or response.text}"
            ) from error

    def test_connectivity(self) -> None:
        """Test conectivity."""

        if not self.project_id and not self.organization_id:
            raise CloudLoggingManagerError(
                "Project id or organization id must be specified"
            )

        request_url = self._get_full_url("execute_query")

        resources = self._prepare_resources()
        payload = {"resourceNames": resources, "pageSize": 1}
        response = self.session.post(request_url, data=payload)

        self.validate_response(
            response, f"Unable to connect to {INTEGRATION_DISPLAY_NAME}"
        )

    def execute_query(
        self,
        query: str,
        project_id: str | None,
        organization_id: str | None,
        time_frame: str | None,
        start_time: str | None,
        end_time: str | None,
        max_results: int | None,
    ) -> tuple[list[SingleJson], str]:
        """
        Executes query to obtain log entries.

        Args:
            query: query value that is used for filtering log entries.
            project_id: id of a project that you want to query.
            organization_id: id of organization that you want to query.
            time_frame: parameter that sets the time range that
                will be applied during obtaining logs.
            start_time: if the time_frame is set to 'Custom' than
                this is the beginning of the user defined range.
            end_time: if the time_frame is set to 'Custom' than
                this is the end of the user defined range.
            max_results: Maximum number of logs that will be returned.

        Returns:
            list of logs that were returned from the query execution.
        """
        request_url = self._get_full_url("execute_query")
        resources = self._prepare_resources(project_id, organization_id)

        payload = {"resourceNames": resources}

        if time_frame == CUSTOM_TIME:
            finish_time = (
                end_time if end_time else datetime.now(timezone.utc).isoformat()
            )
            query += (
                f' AND timestamp >= "{start_time}" AND timestamp <= "{finish_time}"'
            )
        else:
            query += self._prepare_timestamp_filter(time_frame)
        payload["filter"] = query

        if max_results:
            payload["pageSize"] = max_results

        results = self._paginate_results(
            "POST", request_url, "entries", body=payload, limit=max_results
        )

        return results, query

    def _prepare_timestamp_filter(self, time_frame: str) -> str:
        """
        Prepares timestamp filter for the query.

        Args:
            time_frame: time frame that will be used for filtering.

        Returns:
            timestamp filter that will be used in the query.
        """
        now = datetime.now(timezone.utc)
        start_time = now - TIME_INTERVALS[time_frame]
        return (
            f' AND timestamp >= "{start_time.isoformat()}"'
            f' AND timestamp <= "{now.isoformat()}"'
        )

    def _prepare_resources(
        self, project_id: str | None = None, organization_id: str | None = None
    ) -> list[str]:
        """
        Prepares resources for the query.

        Args:
            project_id: id of a project that you want to query.
            organization_id: id of organization that you want to query.

        Returns:
            list of resources that will be used for the query.
        """
        resources = []

        if organization_id:
            resources.append(f"organizations/{organization_id}")
        elif project_id:
            resources.append(f"projects/{project_id}")
        elif self.organization_id:
            resources.append(f"organizations/{self.organization_id}")
        elif self.project_id:
            resources.append(f"projects/{self.project_id}")
        else:
            raise CloudLoggingManagerError(
                "Either project_id or organization_id must be provided"
            )
        return resources

    def _paginate_results(
        self,
        method,
        url: str,
        results_key: str,
        body=None,
        limit=None,
        error_msg="Unable to paginate results",
    ) -> list:
        """
        Paginate results

        Args:
            method (str): The method of the request (GET, POST, PUT, DELETE, PATCH)
            url (str): The request url to send request to
            results_key (str): The name of the key where the results are
            body (dict): Body that will be attached to the request
            limit (int): Max number of results to fetch
            error_msg (str): Error message to display on failure

        Returns:
            list: List of found results
        """
        response = self.session.request(method=method, url=url, json=body)
        self.validate_response(response, error_msg)
        results = response.json().get(results_key, [])

        while response.json().get("nextPageToken"):
            if limit and len(results) >= limit:
                break
            body["pageToken"] = response.json()["nextPageToken"]
            response = self.session.request(method=method, url=url, json=body)
            self.validate_response(response, error_msg)
            results.extend(response.json().get(results_key, []))

        return results[:limit] if limit else results
