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

"""ThreatConnect V3 authentication and session builder module."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any, NamedTuple
from urllib.parse import urlparse

import requests
from requests.auth import AuthBase
from requests.structures import CaseInsensitiveDict
from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param

from .constants import INTEGRATION_NAME
from .exceptions import ThreatConnectError

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


class SessionAuthenticationParameters(NamedTuple):
    """Parameters required to authenticate a session."""

    api_access_id: str
    api_secret_key: str
    verify_ssl: bool


class IntegrationParameters(NamedTuple):
    """Integration parameters parsed from configuration."""

    api_access_id: str
    api_secret_key: str
    api_root: str
    verify_ssl: bool


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract configuration parameters for ThreatConnect integration.

    Args:
        soar_sdk_object: ChronicleSOAR SDK object.

    Returns:
        Parsed integration parameters.

    Raises:
        ThreatConnectError: If the SOAR instance type is not supported.

    """
    sdk_class = type(soar_sdk_object).__name__
    if sdk_class == "SiemplifyAction":
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_NAME)
    elif sdk_class in ("SiemplifyConnectorExecution", "SiemplifyJob"):
        input_dictionary = soar_sdk_object.parameters
    else:
        msg = f"Provided SOAR instance is not supported! type: {sdk_class}."
        raise ThreatConnectError(msg)

    api_access_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Access ID",
        is_mandatory=True,
    )
    api_secret_key = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    return IntegrationParameters(
        api_access_id=api_access_id,
        api_secret_key=api_secret_key,
        api_root=api_root,
        verify_ssl=verify_ssl,
    )


class ThreatConnectAuth(AuthBase):
    """ThreatConnect V3 HMAC-SHA256 Request Authenticator."""

    def __init__(self, api_access_id: str, api_secret_key: str) -> None:
        self.api_access_id = api_access_id
        self.api_secret_key = api_secret_key

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Sign the outgoing PreparedRequest using custom ThreatConnect HMAC signature."""
        timestamp = str(int(time.time()))
        url_str = r.url.decode("utf-8") if isinstance(r.url, bytes) else (r.url or "")
        parsed_url = urlparse(url_str)
        path = parsed_url.path
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"

        method = (r.method or "GET").upper()
        signature_string = f"{path}:{method}:{timestamp}"

        hmac_obj = hmac.new(
            self.api_secret_key.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha256,
        )
        signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")

        if r.headers is None:
            r.headers = CaseInsensitiveDict()

        r.headers["Authorization"] = f"TC {self.api_access_id}:{signature}"
        r.headers["Timestamp"] = timestamp

        return r


class AuthenticatedSession(Authable):
    """ThreatConnect Authenticated Session implementing Authable interface."""

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate the session using custom ThreatConnect HMAC auth."""
        session = CreateSession.create_session()
        session.verify = params.verify_ssl
        session.auth = ThreatConnectAuth(params.api_access_id, params.api_secret_key)
        self.session = session

    def __getattr__(self, name: str) -> Any:
        """Delegate all missing attributes (e.g. get, post, request) to the underlying session."""
        if name == "session":
            msg = "session is not initialized"
            raise AttributeError(msg)
        return getattr(self.session, name)
