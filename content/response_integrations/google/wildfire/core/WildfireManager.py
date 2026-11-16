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

import pathlib
import re
import string
import time
from typing import Any

import requests
import xmltodict
from requests.auth import HTTPBasicAuth
from TIPCommon.extraction import extract_configuration_param

DEFAULT_API_ROOT: str = "https://wildfire.paloaltonetworks.com"
DEFAULT_TOKEN_URL: str = "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token"
CONNECTIVITY_TEST_HASH: str = "44d88612fea8a8f36de82e1278abb02f"


class WildfireManagerError(Exception):
    """General exception for Wildfire Manager."""


class WildfireNotFoundError(WildfireManagerError):
    """Raised when a sample or report is not found on WildFire."""


def validate_hash(hash_value: str) -> None:
    """Validate that the hash is 32 (MD5) or 64 (SHA256) hex characters.

    Args:
        hash_value: The hash string to validate.

    Raises:
        WildfireManagerError: If hash is invalid.

    """
    if not hash_value or len(hash_value) not in {32, 64} or not all(c in string.hexdigits for c in hash_value):
        msg = f"Invalid hash '{hash_value}'. Must be 32 (MD5) or 64 (SHA256) hex characters."
        raise WildfireManagerError(msg)


def extract_filename_from_response(response: requests.Response, default_name: str) -> str:
    """Extract filename from Content-Disposition header if available.

    Args:
        response: The HTTP response.
        default_name: Fallback filename.

    Returns:
        The extracted or default filename.

    """
    cd = response.headers.get("Content-Disposition")
    if cd:
        match = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
        if match:
            return match.group(1).strip()
    return default_name


class WildfireManager:
    """Responsible for all Wildfire operations functionality."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        tsg_id: str | None = None,
        api_root: str | None = None,
        token_url: str | None = None,
        verify_ssl: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.tsg_id = tsg_id
        self.api_root = (api_root or DEFAULT_API_ROOT).rstrip("/")
        self.token_url = token_url or DEFAULT_TOKEN_URL
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()
        self.session.verify = self.verify_ssl

        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self.is_scm: bool = bool(self.client_id and self.client_secret and self.tsg_id)

        if not self.is_scm and not self.api_key:
            msg = (
                "Either 'Api Key' or ('Client ID', 'Client Secret', and 'TSG ID') "
                "must be provided for WildFire authentication."
            )
            raise WildfireManagerError(msg)

    @classmethod
    def from_siemplify(cls, siemplify: Any) -> WildfireManager:
        """Create a WildfireManager instance from the Siemplify execution context."""
        api_key = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="Api Key",
            is_mandatory=False,
        )
        client_id = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="Client ID",
            is_mandatory=False,
        )
        client_secret = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="Client Secret",
            is_mandatory=False,
        )
        tsg_id = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="TSG ID",
            is_mandatory=False,
        )
        api_root = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="API Root",
            is_mandatory=False,
            default_value=DEFAULT_API_ROOT,
        )
        verify_ssl = extract_configuration_param(
            siemplify,
            provider_name="Wildfire",
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=False,
            default_value=True,
        )

        return cls(
            api_key=api_key,
            client_id=client_id,
            client_secret=client_secret,
            tsg_id=tsg_id,
            api_root=api_root,
            verify_ssl=verify_ssl,
        )

    def get_token(self) -> str:
        """Fetch or return cached OAuth2 access token for Strata Cloud Manager."""
        if not self.is_scm:
            msg = "SCM credentials are not configured on this instance."
            raise WildfireManagerError(msg)

        if self._token and time.time() < (self._token_expires_at - 60):
            return self._token

        data = {
            "grant_type": "client_credentials",
            "scope": f"tsg_id:{self.tsg_id}",
        }

        try:
            response = self.session.post(
                self.token_url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
        except Exception as e:
            msg = f"Failed to connect to authentication server ({self.token_url}): {e}"
            raise WildfireManagerError(msg) from e

        if not response.ok:
            msg = f"Authentication failed: HTTP {response.status_code} - {response.text}"
            raise WildfireManagerError(msg)

        try:
            token_json = response.json()
            access_token = token_json["access_token"]
            expires_in = int(token_json.get("expires_in", 3600))
        except (KeyError, ValueError) as err:
            msg = f"Unexpected token response from auth server: {response.text}"
            raise WildfireManagerError(msg) from err

        self._token = access_token
        self._token_expires_at = time.time() + expires_in
        return self._token

    def _build_url(self, endpoint: str) -> str:
        clean_endpoint = endpoint.lstrip("/")
        if self.api_root.endswith("/publicapi"):
            return f"{self.api_root}/{clean_endpoint}"
        return f"{self.api_root}/publicapi/{clean_endpoint}"

    def _apply_auth(
        self,
        method: str,
        params: dict[str, Any],
        data: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        if self.is_scm:
            headers["Authorization"] = f"Bearer {self.get_token()}"
        elif method.upper() == "GET":
            params["apikey"] = self.api_key
        else:
            data["apikey"] = self.api_key

    def _make_request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """Execute an authenticated HTTP request to WildFire."""
        url = self._build_url(endpoint)
        req_headers = headers.copy() if headers else {}
        req_data = data.copy() if data else {}
        req_params = params.copy() if params else {}

        self._apply_auth(method, req_params, req_data, req_headers)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=req_params,
                data=req_data,
                files=files,
                headers=req_headers,
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            msg = f"Request to {url} failed: {e}"
            raise WildfireManagerError(msg) from e

        if response.status_code == 404:
            msg = f"Requested resource not found on Wildfire ({endpoint})"
            raise WildfireNotFoundError(msg)

        if not response.ok:
            error_message = response.text
            try:
                parsed = xmltodict.parse(response.content)
                if "wildfire" in parsed and "error" in parsed["wildfire"]:
                    error_message = parsed["wildfire"]["error"].get("error-message", response.text)
            except Exception:
                pass
            msg = f"Wildfire request failed with status code {response.status_code}: {error_message}"
            raise WildfireManagerError(msg)

        return response

    def get_sample(self, hash_value: str) -> dict[str, Any]:
        """Download binary sample file for a given file hash."""
        validate_hash(hash_value)
        try:
            response = self._make_request("get/sample", method="POST", data={"hash": hash_value})
        except WildfireNotFoundError as error:
            msg = f"Sample is not available for {hash_value}"
            raise WildfireNotFoundError(msg) from error
        except Exception as e:
            msg = f"Unable to get sample of {hash_value}:\n{e}"
            raise WildfireManagerError(msg) from e

        filename = extract_filename_from_response(response, f"{hash_value}.tar")
        return {
            "filename": filename,
            "content": response.content,
        }

    def get_report(self, hash_value: str) -> dict[str, Any]:
        """Fetch XML detonation report and return parsed dictionary."""
        validate_hash(hash_value)
        try:
            response = self._make_request(
                "get/report",
                method="POST",
                data={"hash": hash_value, "format": "xml"},
            )
            parsed = xmltodict.parse(response.content)
            return dict(parsed.get("wildfire", {}))
        except WildfireNotFoundError as error:
            msg = f"Report is not available for {hash_value}"
            raise WildfireNotFoundError(msg) from error
        except Exception as e:
            msg = f"Unable to get report for {hash_value}:\n{e}"
            raise WildfireManagerError(msg) from e

    def get_pdf_report(self, hash_value: str) -> dict[str, Any]:
        """Fetch PDF detonation report."""
        validate_hash(hash_value)
        try:
            response = self._make_request(
                "get/report",
                method="POST",
                data={"hash": hash_value, "format": "pdf"},
            )
        except WildfireNotFoundError as error:
            msg = f"PDF report is not available for {hash_value}"
            raise WildfireNotFoundError(msg) from error
        except Exception as e:
            msg = f"Unable to get report for {hash_value}:\n{e}"
            raise WildfireManagerError(msg) from e

        filename = extract_filename_from_response(response, f"{hash_value}.pdf")
        return {
            "filename": filename,
            "content": response.content,
        }

    def get_pcap(self, hash_value: str) -> dict[str, Any]:
        """Retrieve PCAP file for a previously submitted file sample."""
        validate_hash(hash_value)
        try:
            response = self._make_request("get/pcap", method="POST", data={"hash": hash_value})
        except WildfireNotFoundError as error:
            msg = f"PCAP is not available for {hash_value}"
            raise WildfireNotFoundError(msg) from error
        except Exception as e:
            msg = f"Unable to get PCAP for {hash_value}:\n{e}"
            raise WildfireManagerError(msg) from e

        filename = extract_filename_from_response(response, f"{hash_value}.pcap")
        return {
            "filename": filename,
            "content": response.content,
        }

    def submit_file(self, file_path: str) -> dict[str, Any]:
        """Submit a file sample to WildFire for analysis."""
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists():
            msg = f"File not found: {file_path}"
            raise WildfireManagerError(msg)

        filename = path_obj.name
        try:
            with path_obj.open("rb") as f:
                response = self._make_request(
                    "submit/file",
                    method="POST",
                    files={"file": (filename, f)},
                )
            parsed = xmltodict.parse(response.content)
            return dict(parsed["wildfire"]["upload-file-info"])
        except Exception as e:
            msg = f"Unable to submit file {file_path}:\n{e}"
            raise WildfireManagerError(msg) from e

    def test_connectivity(self) -> bool:
        """Validate connectivity and authentication against WildFire."""
        if self.is_scm:
            self.get_token()

        self._make_request("get/verdict", method="POST", data={"hash": CONNECTIVITY_TEST_HASH})
        return True
