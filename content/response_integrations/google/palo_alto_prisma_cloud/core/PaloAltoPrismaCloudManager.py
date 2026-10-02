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

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.types import SingleJson
from . import api_utils
from . import constants
from . import datamodels
from . import PaloAltoPrismaCloudParser as parser


@dataclass
class ApiParameters:
    api_root: str
    access_key_id: str
    secret_access_key: str
    verify_ssl: bool


class ApiManager:
    """ApiManager Manager for handling
    action's core functionalities
    """

    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        logger: SiemplifyLogger,
    ):
        """The method is used to init an object of Manager class

        Args:
            session (requests.Session): The session object for making HTTP requests.
            api_parameters (ApiParameters): Object containing API parameters such as
                api_root, access_key_id, secret_access_key, and verify_ssl.
            logger (SiemplifyLogger): Logger instance to log data in the console.
        """
        self.api_root = (
            api_parameters.api_root[:-1]
            if api_parameters.api_root.endswith("/")
            else api_parameters.api_root
        )
        self.session = session
        self.access_key_id = api_parameters.access_key_id
        self.secret_access_key = api_parameters.secret_access_key
        self.session.verify = api_parameters.verify_ssl
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test the connectivity"""

        data = {
            "limit": 1,
            "sortBy": ["alerttime:asc"],
            "timeRange": {"type": "relative", "value": {"amount": 1, "unit": "hour"}},
        }

        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint_id="ping", endpoints=constants.ENDPOINTS
        )
        response = self.session.post(url, json=data)
        api_utils.validate_response(response=response)

    def get_alerts(
        self,
        fallback_severity: str,
        max_alerts_to_fetch: int,
        max_hours_backwards: int,
        last_alert_time: datetime | None = None,
    ) -> datamodels.AlertResponse:
        """Fetch alerts from Prisma Cloud.

        Args:
            fallback_severity (str): The severity level to use if no severity is
                provided for an alert.
            max_alerts_to_fetch (int): The maximum number of alerts to fetch.
            max_hours_backwards (int): The maximum number of hours to look back
                for alerts.
            last_alert_time (datetime, optional): The timestamp of the last
                fetched alert.Defaults to None.

        Returns:
            AlertResponse: The list of datamodels.AlertResponse object.
        """
        filters = ApiManager.create_filters(fallback_severity=fallback_severity)

        time_range = ApiManager.create_alert_time_filter(
            max_hours_backwards=max_hours_backwards, last_success_time=last_alert_time
        )

        body = {
            "detailed": True,
            "limit": constants.PAGESIZE,
            "filters": filters,
            "sortBy": ["alerttime:asc"],
            "timeRange": time_range,
        }

        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint_id="ping", endpoints=constants.ENDPOINTS
        )
        response = self.paginate_results(
            url=url, method="POST", json=body, limit=max_alerts_to_fetch
        )
        return parser.build_alert_response(raw_data=response)

    @staticmethod
    def create_filters(fallback_severity: str) -> list:
        """Create filters for fetching alerts based on the provided severity level.

        Args:
            fallback_severity (str): The severity level to use if no severity is
                provided for an alert. Must be one of the levels defined in
                `constants.SEVERITY_LEVELS`.

        Returns:
            list: A list of filter dictionaries to be used in the alert fetching query.

        Raises:
            ValueError: If the provided `fallback_severity` is not valid.
        """
        filters = [{"operator": "=", "name": "alert.status", "value": "open"}]

        if fallback_severity:
            fallback_severity = fallback_severity.lower()
            if fallback_severity in constants.SEVERITY_LEVELS:
                fallback_index = constants.SEVERITY_LEVELS.index(fallback_severity)
                for severity in constants.SEVERITY_LEVELS[: fallback_index + 1]:
                    filters.append(
                        {"operator": "=", "name": "policy.severity", "value": severity}
                    )
            else:
                raise ValueError('Invalid "Lowest Severity To Fetch" level provided.')

        return filters

    @staticmethod
    def create_alert_time_filter(
        max_hours_backwards: int, last_success_time: int
    ) -> int:
        """Create time filter for provided time filter.

        Args:
            time_filter (int): time filter in minutes.

        Returns:
            str: datetime time filter string.
        """
        time_range = {
            "type": "relative",
            "value": {"amount": max_hours_backwards, "unit": "hour"},
        }

        if last_success_time:
            current_timestamp = int(datetime.now().timestamp())
            time_value = (
                current_timestamp - last_success_time / constants.SEC_IN_MS
            ) / constants.HOUR_IN_SEC + 1
            time_range["value"]["amount"] = int(time_value)

        return time_range

    def enrich_assets(self, asset: str) -> datamodels.Asset:
        """Enrich asset information.

        Args:
            asset (str): The asset ID.

        Returns:
            datamodels.Asset: The enriched asset information.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id="enrich_assets",
            endpoints=constants.ENDPOINTS,
        )

        payload = {"assetId": f"{asset}"}
        response = self.session.post(url, json=payload)
        api_utils.validate_response(response)
        return parser.build_asset(response.json().get("data", {}).get("asset", {}))

    def verify_alert(self, alert_id: str, error_message: str) -> datamodels.Asset:
        """Verify the alert with the given ID.

        Parameters:
            alert_id (str): The ID of the alert to verify.
            error_message (str): The error message to be raised if verification fails.

        Returns:
            datamodels.Asset: The verified asset.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root, endpoint_id="alert", endpoints=constants.ENDPOINTS
        )
        url += f"{alert_id}"

        response = self.session.get(url)
        api_utils.validate_response(response, error_message)
        return parser.build_alert(response.json())

    def build_alert_body(
        self, alert_id: str, response_type: str, dismissal_note: str, snooze_time: str
    ) -> dict:
        """Build the request body for the alert API call.

        Parameters:
            alert_id (str): The ID of the alert.
            response_type (str): The type of response
                ('Dismiss', 'Snooze', 'Remediate', or 'Reopen').
            dismissal_note (str): The dismissal note for the alert.
            snooze_time (str): The snooze time for the alert.

        Returns:
            dict: The request body for the alert API call.
        """
        body = {"alerts": [alert_id]}
        if response_type == "Remediate":
            return None
        if response_type == "Dismiss":
            body["dismissalNote"] = dismissal_note
            body["filter"] = {"timeRange": None, "filters": None}
        if response_type == "Snooze":
            body["dismissalNote"] = dismissal_note
            body["dismissalTimeRange"] = {
                "type": "relative",
                "value": {"amount": snooze_time, "unit": "hour"},
            }
            body["filter"] = {"timeRange": {"type": "to_now", "value": "epoch"}}
        if response_type == "Reopen":
            body["filter"] = {"timeRange": None, "filters": None}
        return body

    def respond_to_alert(
        self,
        alert_id: str,
        response_type: str,
        dismissal_note: str,
        snooze_time: str,
        error_message: str,
    ) -> dict:
        """Respond to the alert with the given ID.

        Parameters:
            alert_id (str): The ID of the alert to respond to.
            response_type (str): The type of response
                ('Dismiss', 'Snooze', 'Remediate', or 'Reopen').
            dismissal_note (str): The dismissal note for the alert.
            snooze_time (str): The snooze time for the alert.
            error_message (str): The error message to be raised if responding to
                the alert fails.

        Returns:
            dict: The response from the API.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            endpoint_id=response_type,
            endpoints=constants.ENDPOINTS,
        )
        url += f"{alert_id}" if response_type == "Remediate" else ""

        body = self.build_alert_body(
            alert_id, response_type, dismissal_note, snooze_time
        )

        if response_type == "Remediate":
            status = self.session.patch(url)
            response = {"response_status": "Remediated"}
        elif response_type in ("Dismiss", "Snooze"):
            status = self.session.post(url, json=body)
            response = {
                "response_status": (
                    "Dismissed" if response_type == "Dismiss" else "Snoozed"
                )
            }
        elif response_type == "Reopen":
            status = self.session.post(url, json=body)
            response = {"response_status": "Reopened"}
        else:
            status = self.session.get(url, json=body)
            response = {"response_status": "No Remediation Applied."}
        api_utils.validate_response(status, err_msg=error_message)
        return response

    def paginate_results(
        self,
        url: str,
        method: str,
        json: dict[str, Any],
        params: dict | None = None,
        limit: int | None = None,
    ) -> list[SingleJson]:
        """
        Paginate through API results.

        Args:
            url (str): The URL for the request.
            method (str): The HTTP method for the request (e.g., 'GET', 'POST').
            json (dict): The JSON body for the request.
            params (dict, optional): The parameters for the request.
                Defaults to None.
            limit (int, optional): The maximum number of results to fetch.
                Defaults to None.

        Returns:
            list[SingleJson]: A list of parsed results.
        """
        results = []
        while url:
            if limit and len(results) >= limit:
                break

            response = self.session.request(method, url, params=params, json=json)
            api_utils.validate_response(response)

            current_items = response.json().get("items", [])
            results.extend(current_items)

            page_token = response.json().get("nextPageToken")
            if not page_token:
                break

            json["pageToken"] = page_token

        return results[:limit] if limit else results
