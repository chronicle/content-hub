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

import os
import re
import string
import time
from typing import Any, Dict, Optional

import requests
from requests.auth import HTTPBasicAuth
from TIPCommon.extraction import extract_configuration_param
import xmltodict

# =====================================
#              CONSTS                 #
# =====================================

DEFAULT_API_ROOT = "https://wildfire.paloaltonetworks.com"
DEFAULT_TOKEN_URL = "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token"


# =====================================
#              CLASSES                #
# =====================================


class WildfireManagerError(Exception):
    """General exception for Wildfire Manager."""

    pass


class WildfireNotFoundError(WildfireManagerError):
    """Raised when a sample or report is not found on WildFire."""

    pass


class WildfireManager:
    """Responsible for all Wildfire operations functionality.

    Supports both legacy API Key authentication (standalone WildFire portal)
    and modern OAuth2 token-based authentication via Strata Cloud Manager (SCM).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tsg_id: Optional[str] = None,
        api_root: Optional[str] = None,
        token_url: Optional[str] = None,
        verify_ssl: bool = True,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.tsg_id = tsg_id
        self.api_root = (api_root or DEFAULT_API_ROOT).rstrip("/")
        self.token_url = token_url or DEFAULT_TOKEN_URL
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()
        self.session.verify = self.verify_ssl

        # Token caching for SCM OAuth2
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

        self.is_scm = bool(self.client_id and self.client_secret and self.tsg_id)

        if not self.is_scm and not self.api_key:
            raise WildfireManagerError(
                "Either 'Api Key' or ('Client ID', 'Client Secret', and 'TSG ID') "
                "must be provided for WildFire authentication."
            )

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

    # -------------------------------------------------------------
    # SCM OAuth2 Token Management
    # -------------------------------------------------------------
    def get_token(self) -> str:
        """Fetch or return cached OAuth2 access token for Strata Cloud Manager."""
        if not self.is_scm:
            raise WildfireManagerError("SCM credentials are not configured on this instance.")

        # Return cached token if valid (with 60-second buffer)
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
            raise WildfireManagerError(f"Failed to connect to authentication server ({self.token_url}): {e}") from e

        if not response.ok:
            raise WildfireManagerError(
                f"Authentication failed: HTTP {response.status_code} - {response.text}"
            )

        try:
            token_json = response.json()
            access_token = token_json["access_token"]
            expires_in = int(token_json.get("expires_in", 3600))
        except (KeyError, ValueError) as err:
            raise WildfireManagerError(f"Unexpected token response from auth server: {response.text}") from err

        self._token = access_token
        self._token_expires_at = time.time() + expires_in
        return self._token

    # -------------------------------------------------------------
    # HTTP Request Dispatcher
    # -------------------------------------------------------------
    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Execute an authenticated HTTP request to WildFire."""
        endpoint = endpoint.lstrip("/")
        # If api_root doesn't include /publicapi, append it unless already included
        base_url = self.api_root
        if not base_url.endswith("/publicapi"):
            url = f"{base_url}/publicapi/{endpoint}"
        else:
            url = f"{base_url}/{endpoint}"

        headers = headers or {}
        data = data.copy() if data else {}
        params = params.copy() if params else {}

        if self.is_scm:
            token = self.get_token()
            headers["Authorization"] = f"Bearer {token}"
            headers["X-PAN-KEY"] = token
        else:
            # Legacy API key authentication
            if method.upper() == "GET":
                params["apikey"] = self.api_key
            else:
                data["apikey"] = self.api_key

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                files=files,
                headers=headers,
                timeout=60,
            )
        except requests.exceptions.RequestException as e:
            raise WildfireManagerError(f"Request to {url} failed: {e}") from e

        if response.status_code == 404:
            raise WildfireNotFoundError(f"Requested resource not found on Wildfire ({endpoint})")

        if not response.ok:
            # Try to extract error message from WildFire XML error response
            error_message = response.text
            try:
                parsed = xmltodict.parse(response.content)
                if "wildfire" in parsed and "error" in parsed["wildfire"]:
                    error_message = parsed["wildfire"]["error"].get("error-message", response.text)
            except Exception:
                pass
            raise WildfireManagerError(
                f"Wildfire request failed with status code {response.status_code}: {error_message}"
            )

        return response

    # -------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------
    @staticmethod
    def _validate_hash(hash_value: str) -> None:
        if not hash_value or not (
            (len(hash_value) == 32 and all(c in string.hexdigits for c in hash_value))
            or (len(hash_value) == 64 and all(c in string.hexdigits for c in hash_value))
        ):
            raise WildfireManagerError(f"Invalid hash '{hash_value}'. Must be 32 (MD5) or 64 (SHA256) hex characters.")

    @staticmethod
    def _extract_filename(response: requests.Response, default_name: str) -> str:
        cd = response.headers.get("Content-Disposition") or response.headers.get("content-disposition", "")
        if cd:
            match = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
            if match:
                return match.group(1).strip()
        return default_name

    # -------------------------------------------------------------
    # Public Operations
    # -------------------------------------------------------------
    def get_sample(self, hash_value: str) -> Dict[str, Any]:
        """Download binary sample file for a given file hash.

        :param hash_value: MD5 or SHA-256 hash string
        :return: Dict containing 'filename' and 'content' (bytes)
        """
        self._validate_hash(hash_value)
        try:
            response = self._make_request("get/sample", method="POST", data={"hash": hash_value})
        except WildfireNotFoundError:
            raise WildfireManagerError(f"Sample is not available for {hash_value}")
        except Exception as e:
            raise WildfireManagerError(f"Unable to get sample of {hash_value}:\n{e}") from e

        filename = self._extract_filename(response, f"{hash_value}.tar")
        return {
            "filename": filename,
            "content": response.content,
        }

    def get_report(self, hash_value: str) -> Dict[str, Any]:
        """Fetch XML detonation report and return parsed dictionary.

        :param hash_value: MD5 or SHA-256 hash string
        :return: Dict of report details
        """
        self._validate_hash(hash_value)
        try:
            response = self._make_request(
                "get/report",
                method="POST",
                data={"hash": hash_value, "format": "xml"},
            )
            parsed = xmltodict.parse(response.content)
            return dict(parsed.get("wildfire", {}))
        except WildfireNotFoundError:
            raise WildfireManagerError(f"Report is not available for {hash_value}")
        except Exception as e:
            raise WildfireManagerError(f"Unable to get report for {hash_value}:\n{e}") from e

    def get_pdf_report(self, hash_value: str) -> Dict[str, Any]:
        """Fetch PDF detonation report.

        :param hash_value: MD5 or SHA-256 hash string
        :return: Dict containing 'filename' and 'content' (bytes)
        """
        self._validate_hash(hash_value)
        try:
            response = self._make_request(
                "get/report",
                method="POST",
                data={"hash": hash_value, "format": "pdf"},
            )
        except WildfireNotFoundError:
            raise WildfireManagerError(f"PDF report is not available for {hash_value}")
        except Exception as e:
            raise WildfireManagerError(f"Unable to get report for {hash_value}:\n{e}") from e

        filename = self._extract_filename(response, f"{hash_value}.pdf")
        return {
            "filename": filename,
            "content": response.content,
        }

    def get_pcap(self, hash_value: str) -> Dict[str, Any]:
        """Retrieve PCAP file for a previously submitted file sample.

        :param hash_value: MD5 or SHA-256 hash string
        :return: Dict containing 'filename' and 'content' (bytes)
        """
        self._validate_hash(hash_value)
        try:
            response = self._make_request("get/pcap", method="POST", data={"hash": hash_value})
        except WildfireNotFoundError:
            raise WildfireManagerError(f"PCAP is not available for {hash_value}")
        except Exception as e:
            raise WildfireManagerError(f"Unable to get PCAP for {hash_value}:\n{e}") from e

        filename = self._extract_filename(response, f"{hash_value}.pcap")
        return {
            "filename": filename,
            "content": response.content,
        }

    def submit_file(self, file_path: str) -> Dict[str, Any]:
        """Submit a file sample to WildFire for analysis.

        :param file_path: Path to file to submit
        :return: Dict with upload file info
        """
        if not os.path.exists(file_path):
            raise WildfireManagerError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        try:
            with open(file_path, "rb") as f:
                response = self._make_request(
                    "submit/file",
                    method="POST",
                    files={"file": (filename, f)},
                )
            parsed = xmltodict.parse(response.content)
            return dict(parsed["wildfire"]["upload-file-info"])
        except Exception as e:
            raise WildfireManagerError(f"Unable to submit file {file_path}:\n{e}") from e

    def test_connectivity(self) -> bool:
        """Validate connectivity and authentication against WildFire.

        For SCM, validates token generation and queries the verdicts endpoint.
        For legacy API Key, queries the verdicts endpoint.
        :return: True if successful
        """
        if self.is_scm:
            # Ensure SCM token generation succeeds
            self.get_token()

        # Query verdicts endpoint for a dummy benign hash to verify API credentials
        test_hash = "44d88612fea8a8f36de82e1278abb02f"  # standard test hash
        self._make_request("get/verdicts", method="POST", data={"hash": test_hash})
        return True
