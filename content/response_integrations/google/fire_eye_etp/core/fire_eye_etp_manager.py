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


"""Manager class for FireEye ETP API interaction."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import requests

from .fire_eye_etp_constants import (
    AUTH_URL,
    DEFAULT_FETCH_SIZE,
    ENDPOINTS,
    ETP_SCOPES,
    HEADERS,
    LEGACY_AUTH_HEADER,
    NEW_AUTH_HEADER,
)
from .fire_eye_etp_exceptions import FireEyeETPError
from .fire_eye_etp_parser import FireEyeETPParser
from .utils_manager import validate_response

if TYPE_CHECKING:
    import logging

    from .datamodels import Alert


@dataclass
class FireEyeETPConfig:
    """Configuration for FireEye ETP Manager."""

    api_root: str
    client_id: str | None = None
    client_secret: str | None = None
    api_key: str | None = None
    verify_ssl: bool = False


class FireEyeETPManager:
    """Manager for FireEye ETP API."""

    def __init__(
        self,
        config: FireEyeETPConfig,
        siemplify_logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the FireEye ETP Manager.

        Args:
            config: The configuration object.
            siemplify_logger: The Siemplify logger object.

        Raises:
            FireEyeETPError: If neither client ID/secret nor API key is provided,
                or if token generation fails.

        """
        self.api_root: str = config.api_root
        self.client_id: str | None = config.client_id
        self.client_secret: str | None = config.client_secret
        self.api_key: str | None = config.api_key
        self.siemplify_logger: logging.Logger | None = siemplify_logger
        self.parser: FireEyeETPParser = FireEyeETPParser()
        self.session: requests.Session = requests.session()
        self.session.verify = config.verify_ssl
        self.session.headers = HEADERS

        if self.client_id and self.client_secret:
            token: str = self._get_access_token()
            self.session.headers.update({NEW_AUTH_HEADER: f"Bearer {token}"})
        elif self.api_key:
            self.session.headers.update({LEGACY_AUTH_HEADER: self.api_key})
        else:
            msg = "Either Client ID/Secret or API Key must be provided."
            raise FireEyeETPError(msg)

    def _get_access_token(self) -> str:
        """Obtain an OAuth access token from Trellix IAM.

        Returns:
            The OAuth access token string.

        Raises:
            FireEyeETPError: If token generation fails or token is missing.

        """
        payload: dict[str, str] = {
            "grant_type": "client_credentials",
            "scope": ETP_SCOPES,
        }
        headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response: requests.Response = requests.post(
                AUTH_URL,
                data=payload,
                headers=headers,
                auth=(self.client_id, self.client_secret),
                verify=self.session.verify,
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            if self.siemplify_logger:
                self.siemplify_logger.exception("Failed to generate Trellix IAM access token.")
            msg = f"Failed to generate access token: {e}"
            raise FireEyeETPError(msg) from e

        token: str | None = response.json().get("access_token")
        if not token:
            msg = "Access token is missing in the response."
            raise FireEyeETPError(msg)
        return token

    def _get_full_url(self, url_id: str, **kwargs: object) -> str:
        """Get full URL from URL identifier.

        Args:
            url_id: The URL identifier from ENDPOINTS.
            **kwargs: Format parameters for the URL.

        Returns:
            The full URL string.

        """
        return f"{self.api_root}{ENDPOINTS[url_id].format(**kwargs)}"

    def test_connectivity(self) -> None:
        """Test connectivity to the FireEye ETP API."""
        request_url: str = self._get_full_url("test_connectivity")
        payload: dict[str, Any] = {
            "date_range": {
                "from": "2026-01-01T00:00:00.000Z",
                "to": "2026-01-01T00:01:00.000Z",
            },
            "size": 1,
        }
        response: requests.Response = self.session.post(request_url, json=payload, timeout=30)
        validate_response(response, "Connectivity test failed")

    def get_alerts(self, start_time: datetime.datetime, timezone_offset: str) -> list[Any]:
        """Get alerts from FireEye ETP.

        Args:
            start_time: Specifies the start time of the search.
            timezone_offset: UTC timezone offset.

        Returns:
            List of found alerts.

        """
        request_url: str = self._get_full_url("get_alerts")
        start_time_str: str = self._convert_datetime_to_api_format(start_time)
        end_time_str: str = self._convert_datetime_to_api_format(datetime.datetime.now(datetime.UTC))
        payload: dict[str, Any] = {
            "date_range": {"from": start_time_str, "to": end_time_str},
            "size": DEFAULT_FETCH_SIZE,
        }
        response: requests.Response = self.session.post(request_url, json=payload, timeout=30)
        validate_response(response, "Unable to get alerts")
        alerts: list[Any] = self.parser.build_alerts_array(raw_json=response.json(), timezone_offset=timezone_offset)
        return alerts

    def get_alert_details(self, alert_id: str, timezone_offset: str) -> Alert:
        """Get alert details by ID.

        Args:
            alert_id: The alert ID.
            timezone_offset: UTC timezone offset.

        Returns:
            The parsed Alert object.

        """
        request_url: str = self._get_full_url("get_alert_details", alert_id=alert_id)
        response: requests.Response = self.session.get(request_url, timeout=30)
        validate_response(response, f"Unable to get alert details for {alert_id}")
        return self.parser.build_siemplify_alert_obj(
            alert_data=response.json().get("data", {}),
            timezone_offset=timezone_offset,
        )

    @staticmethod
    def _convert_datetime_to_api_format(date_time: datetime.datetime) -> str:
        """Convert datetime object to API format string.

        Args:
            date_time: The datetime object to convert.

        Returns:
            The API formatted string.

        """
        return f"{date_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
