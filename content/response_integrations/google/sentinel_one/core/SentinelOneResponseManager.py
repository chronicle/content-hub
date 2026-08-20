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
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

from .datamodels import Agent
from .exceptions import (
    SentinelOneConnectivityError,
    SentinelOneException,
    SentinelOneNotFoundError,
    SentinelOneTimeoutException,
)

API_VERSION = "2.1"
LOGIN_URL = "web/api/v1.6/users/login"

NETWORK_STATUS_TO_CONTAINMENT_MAP = {
    "disconnected": "contained",
    "disconnecting": "containment_requested",
    "connecting": "uncontainment_requested",
    "connected": "uncontained",
}


class SentinelOneResponseManager:
    """
    SentinelOne v2.1 Response Actions Manager.

    Handles communication with SentinelOne Management Console API v2.1 for
    incident response actions: containment, uncontainment, status checking,
    and file acquisition.
    """

    def __init__(
        self,
        api_root: str,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        self.api_root = api_root.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl

        token = api_token
        if not token and username and password:
            token = self._fetch_token(username, password)
        elif not token and password and not username:
            token = password

        auth_header = ""
        if token:
            if token.startswith("ApiToken ") or token.startswith("Token "):
                auth_header = token
            else:
                auth_header = f"ApiToken {token}"

        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header

        self.session.headers.update(headers)

    def _fetch_token(self, username: str, password: str) -> str:
        """
        Authenticate with username and password to retrieve API token.

        :param username: Username
        :param password: Password
        :return: Token string
        """
        request_url = f"{self.api_root}/{LOGIN_URL.lstrip('/')}"
        payload = {"username": username, "password": password}
        try:
            response = self.session.post(request_url, json=payload)
            self.validate_response(response)
            return response.json().get("token", "")
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to authenticate with SentinelOne: {e}"
            ) from e

    def get_full_url(self, endpoint_path: str) -> str:
        """
        Construct the full API URL for a given endpoint path.

        :param endpoint_path: Relative endpoint path (e.g. 'agents' or '/activities')
        :return: Full URL string
        """
        clean_path = endpoint_path.lstrip("/")
        return f"{self.api_root}/web/api/v{API_VERSION}/{clean_path}"

    def validate_response(self, response: requests.Response) -> None:
        """
        Validate HTTP response from SentinelOne API.

        :param response: requests.Response object
        :raises SentinelOneNotFoundError: If HTTP status is 404
        :raises SentinelOneConnectivityError: If HTTP status is non-2xx
        """
        if 200 <= response.status_code < 300:
            return

        error_message = ""
        try:
            resp_json = response.json()
            if isinstance(resp_json, dict):
                if "errors" in resp_json and resp_json["errors"]:
                    details = []
                    for err in resp_json["errors"]:
                        if isinstance(err, dict):
                            detail = err.get("detail") or err.get("title") or str(err)
                            details.append(detail)
                        else:
                            details.append(str(err))
                    error_message = "; ".join(details)
                elif "message" in resp_json:
                    error_message = str(resp_json["message"])
                elif "detail" in resp_json:
                    error_message = str(resp_json["detail"])
        except Exception:
            pass

        if not error_message:
            error_message = response.text or f"HTTP status {response.status_code}"

        if response.status_code == 404:
            raise SentinelOneNotFoundError(
                f"Resource not found (404): {error_message}"
            )

        raise SentinelOneConnectivityError(
            f"SentinelOne API error (HTTP {response.status_code}): {error_message}"
        )

    def disconnect_agent_from_network(self, agent_id: str) -> bool:
        """
        Disconnect (contain) an agent from the network.

        :param agent_id: S1 agent ID (integer or numeric string)
        :return: True on success
        :raises SentinelOneNotFoundError: If agent is not found
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        url = self.get_full_url(f"agents/{agent_id}/actions/disconnect")
        try:
            response = self.session.post(url, json={"data": {}})
            self.validate_response(response)
            return True
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to disconnect agent {agent_id}: {e}"
            ) from e

    def connect_agent_to_network(self, agent_id: str) -> bool:
        """
        Connect (uncontain) an agent back to the network.

        :param agent_id: S1 agent ID (integer or numeric string)
        :return: True on success
        :raises SentinelOneNotFoundError: If agent is not found
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        url = self.get_full_url(f"agents/{agent_id}/actions/connect")
        try:
            response = self.session.post(url, json={"data": {}})
            self.validate_response(response)
            return True
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to connect agent {agent_id}: {e}"
            ) from e

    def get_agent_by_uuid(self, agent_uuid: str) -> Agent:
        """
        Retrieve agent details by UUID.

        :param agent_uuid: Agent UUID string
        :return: Agent dataclass instance
        :raises SentinelOneNotFoundError: If agent is not found
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        url = self.get_full_url("agents")
        params = {"uuids": agent_uuid, "limit": 2, "tenant": "true"}
        try:
            response = self.session.get(url, params=params)
            self.validate_response(response)
            resp_json = response.json()
            data = resp_json.get("data", [])
            if not data or len(data) == 0:
                raise SentinelOneNotFoundError(
                    f"Agent with UUID '{agent_uuid}' was not found in SentinelOne."
                )
            return Agent.from_dict(data[0])
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to retrieve agent by UUID '{agent_uuid}': {e}"
            ) from e

    def get_containment_status(self, network_status: Optional[str]) -> str:
        """
        Map SentinelOne network status to standardized containment status:
        - disconnected -> contained
        - disconnecting -> containment_requested
        - connecting -> uncontainment_requested
        - connected -> uncontained
        - fallback -> raw network_status (or 'unknown' if empty/None)

        :param network_status: Raw network status from S1 API
        :return: Normalized containment status string
        """
        if not network_status:
            return "unknown"
        return NETWORK_STATUS_TO_CONTAINMENT_MAP.get(network_status, network_status)

    def initiate_fetch_files(
        self, agent_id: str, file_path: str, password: str
    ) -> Dict[str, Any]:
        """
        Initiate file acquisition on an agent.

        :param agent_id: S1 agent ID
        :param file_path: Absolute path to the file on target machine
        :param password: Password to encrypt the archive package
        :return: Response data dict containing task/activity info
        :raises SentinelOneNotFoundError: If agent is not found
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        url = self.get_full_url(f"agents/{agent_id}/actions/fetch-files")
        payload = {"data": {"files": [file_path], "password": password}}
        try:
            response = self.session.post(url, json=payload)
            self.validate_response(response)
            resp_json = response.json()
            return resp_json.get("data", {})
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to initiate fetch files for agent {agent_id}: {e}"
            ) from e

    def get_file_upload_activities(
        self, agent_id: str, created_at_gte: str
    ) -> List[Dict[str, Any]]:
        """
        Query file upload activities (Activity Type 80).

        :param agent_id: S1 agent ID
        :param created_at_gte: ISO 8601 timestamp string (UTC) for start boundary
        :return: List of activity dictionaries
        :raises SentinelOneNotFoundError: If endpoint not found
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        url = self.get_full_url("activities")
        params = {
            "createdAt__gte": created_at_gte,
            "agent_ids": agent_id,
            "activity_types": 80,
            "sortBy": "createdAt",
            "sortOrder": "desc",
        }
        try:
            response = self.session.get(url, params=params)
            self.validate_response(response)
            resp_json = response.json()
            return resp_json.get("data", [])
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to query file upload activities for agent {agent_id}: {e}"
            ) from e

    def download_file(self, download_url: str) -> requests.Response:
        """
        Download file package with stream=True.

        :param download_url: Download URL (absolute or relative to API root)
        :return: requests.Response object with stream=True
        :raises SentinelOneNotFoundError: If download URL returns 404
        :raises SentinelOneConnectivityError: On API/connectivity failure
        """
        if not download_url.startswith("http://") and not download_url.startswith(
            "https://"
        ):
            url = self.get_full_url(download_url)
        else:
            url = download_url

        try:
            response = self.session.get(url, stream=True)
            self.validate_response(response)
            return response
        except SentinelOneException:
            raise
        except Exception as e:
            raise SentinelOneConnectivityError(
                f"Failed to download file from '{download_url}': {e}"
            ) from e


# Backward compatibility alias
SentinelOneV2ResponseManager = SentinelOneResponseManager
