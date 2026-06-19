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
import datetime
from typing import Any, TYPE_CHECKING
import requests
from urllib.parse import urljoin

from .FireEyeETPConstants import (
    API_TIME_FORMAT,
    DEFAULT_FETCH_SIZE,
    ENDPOINTS,
    ETP_SCOPES,
    HEADERS,
    LEGACY_AUTH_HEADER,
    NEW_AUTH_HEADER,
    TOKEN_URL,
)
from .FireEyeETPParser import FireEyeETPParser
from .UtilsManager import validate_response

if TYPE_CHECKING:
    from .datamodels import Alert


class FireEyeETPManager:

    def __init__(
        self,
        api_root: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_key: str | None = None,
        verify_ssl: bool = False,
        siemplify_logger: Any = None,
    ) -> None:
        """Initializes the FireEye ETP Manager.

        Args:
            api_root: API Root of the FireEye ETP instance.
            client_id: Client ID of the Trellix IAM account.
            client_secret: Client Secret of the Trellix IAM account.
            api_key: API key of the FireEye ETP account (legacy).
            verify_ssl: If enabled, verify the SSL certificate for the connection to
              the FireEye ETP server is valid.
            siemplify_logger: Siemplify logger.

        Raises:
            ValueError: If neither Client ID/Secret nor API Key is provided.
        """
        self.api_root: str = api_root if api_root[-1:] == "/" else api_root + "/"
        self.client_id: str | None = client_id
        self.client_secret: str | None = client_secret
        self.api_key: str | None = api_key
        self.siemplify_logger: Any = siemplify_logger
        self.parser: FireEyeETPParser = FireEyeETPParser()
        self.session: requests.Session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS

        if self.client_id and self.client_secret:
            token: str = self._get_access_token()
            self.session.headers.update({NEW_AUTH_HEADER: f"Bearer {token}"})
        elif self.api_key:
            self.session.headers.update({LEGACY_AUTH_HEADER: self.api_key})
        else:
            raise ValueError("Either Client ID/Secret or API Key must be provided.")

    def _get_access_token(self) -> str:
        """Obtains an OAuth access token from Trellix IAM.

        Returns:
            The access token string.

        Raises:
            Exception: If token generation fails.
        """
        payload: dict[str, str] = {
            "grant_type": "client_credentials",
            "scope": ETP_SCOPES,
        }
        headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response: requests.Response = requests.post(
                TOKEN_URL,
                data=payload,
                headers=headers,
                auth=(self.client_id, self.client_secret),
                verify=self.session.verify,
            )
            response.raise_for_status()
            token: str = response.json().get("access_token")
            return token
        except Exception as e:
            if self.siemplify_logger:
                self.siemplify_logger.exception(
                    f"Failed to generate Trellix IAM access token: {e}"
                )
            raise

    def _get_full_url(self, url_id: str, **kwargs: Any) -> str:
        """Get full url from url identifier.

        Args:
            url_id: The id of url.
            **kwargs: Variables passed for string formatting.

        Returns:
            The full url.
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self) -> None:
        """Test connectivity to the FireEye ETP.

        Raises:
            Exception: If connection fails.
        """
        request_url: str = self._get_full_url("test_connectivity")
        payload: dict[str, int] = {"size": 1}
        response: requests.Response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to connect to FireEye ETP.")

    def get_alerts(
        self, start_time: datetime.datetime, timezone_offset: str
    ) -> list[Alert]:
        """Get alerts.

        Args:
            start_time: Specifies the start time of the search.
            timezone_offset: UTC timezone offset.

        Returns:
            List of found alerts.
        """
        request_url: str = self._get_full_url("get_alerts")
        start_time_str: str = self._convert_datetime_to_api_format(start_time)
        end_time_str: str = self._convert_datetime_to_api_format(
            datetime.datetime.utcnow()
        )
        payload: dict[str, Any] = {
            "date_range": {"from": start_time_str, "to": end_time_str},
            "size": DEFAULT_FETCH_SIZE,
        }
        response: requests.Response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to get alerts")
        alerts: list[Alert] = self.parser.build_alerts_array(
            raw_json=response.json(), timezone_offset=timezone_offset
        )
        return alerts

    def get_alert_details(self, alert_id: str, timezone_offset: str) -> Alert:
        """Get alert details by id.

        Args:
            alert_id: Id of the alert.
            timezone_offset: UTC timezone offset.

        Returns:
            Detailed alert.
        """
        request_url: str = self._get_full_url("get_alert_details", alert_id=alert_id)
        response: requests.Response = self.session.get(request_url)
        validate_response(response, "Unable to get alert details")
        alert: Alert = self.parser.build_first_alert(
            raw_data=response.json(), timezone_offset=timezone_offset
        )
        return alert

    @staticmethod
    def _convert_datetime_to_api_format(time: datetime.datetime) -> str:
        """Convert datetime object to the API time format of ETP.

        Args:
            time: The datetime object.

        Returns:
            The formatted time string.
        """
        base_time, miliseconds_zone = time.strftime(API_TIME_FORMAT).split(".")
        return f"{base_time}.{miliseconds_zone[:3]}Z"

