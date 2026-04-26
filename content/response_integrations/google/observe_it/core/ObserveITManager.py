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
import requests

from .ObserveITEndpoints import ObserveITEndpoints
from .ObserveITPayload import ObserveITPayload
from .ObserveITBuilder import ObserveITBuilder
from .ObserveITExceptions import (
    ObserveITException,
    ObserveITAuthorizationException,
    ObserveITConnectivityException,
    ObserveITAlertsException,
)
from .ObserveITConstants import ALERTS_LIMIT, SEVERITIES


class ObserveITManager:
    def __init__(self, api_root, client_id, client_secret, verify_ssl=False):
        self.api_root = api_root
        self.builder = ObserveITBuilder()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self._get_authorization_token(client_id, client_secret)}"
            }
        )

    def _get_authorization_token(self, client_id, client_secret):
        # type: (str or unicode, str or unicode) -> str or unicode
        """
        Get Authorization token
        @param client_id: Client ID to authorize with
        @param client_secret: Client Secret to authorize with
        @return: Access token
        """
        method, url = ObserveITEndpoints.get_authorization_endpoint(self.api_root)
        payload = ObserveITPayload.get_authorization_payload(client_id, client_secret)

        response = self.session.request(method, url, **payload)
        self._validate_response(response, ObserveITAuthorizationException)

        return response.json().get("access_token")

    def test_connectivity(self):
        # type: () -> bool
        """
        Test connectivity
        @return: Is connected successfully or not
        """
        method, url = ObserveITEndpoints.get_test_connectivity_endpoint(self.api_root)
        payload = ObserveITPayload.get_test_connectivity_payload()

        response = self.session.request(method, url, **payload)
        self._validate_response(response, ObserveITConnectivityException)

        return response.json().get("_status", {}).get("status") == 200

    def get_alerts(self, severity, timestamp, limit=ALERTS_LIMIT):
        # type: (str or unicode, int, int) -> [Alert]
        """
        Get alerts with filtering.
        @param severity: Lowest severity to start from
        @param timestamp: Timestamp to start from
        @param limit: How many alerts to take
        @return: List of Alerts
        """
        method, url = ObserveITEndpoints.get_alerts_endpoint(self.api_root)
        severities = self._get_severities_from(severity)
        payload = ObserveITPayload.get_alerts_payload(
            severities, timestamp, max(limit, ALERTS_LIMIT)
        )

        response = self.session.request(method, url, **payload)
        self._validate_response(response, ObserveITAlertsException)

        alerts_data = response.json().get("data", [])

        return [self.builder.build_alert(alert_data) for alert_data in alerts_data]

    @staticmethod
    def _get_severities_from(lowest_severity):
        # type: (str or unicode) -> list
        """
        Get the highest severities started from the lowest.
        Ex. Low -> [Low, Medium, High, Critical]
        Ex. High -> [High, Critical]
        Ex. Unknown -> []
        @param lowest_severity: Lowest severity to start from
        @return: List of the highest severities
        """
        return (
            SEVERITIES[SEVERITIES.index(lowest_severity) :]
            if lowest_severity in SEVERITIES
            else []
        )

    @staticmethod
    def _validate_response(response, custom_exception=ObserveITException):
        # type: (requests.Response, type(ObserveITException)) -> None or ObserveITException
        """
        Validate Response
        @param response: Response
        @param custom_exception: Exception with which to raise
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            response_json = response.json()
            raise custom_exception(
                f'{response_json.get("_status", {}).get("message")}. \n{e}'
            )
