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

from typing import TYPE_CHECKING

import dataclasses
import time
import requests


from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param

from ..core.data_models import IntegrationParameters
from ..core.constants import (
    BASE_URL,
    FORM_URL_ENCODED_HEADERS,
    HEADERS,
    INVALID_CREDENTIALS_ERROR,
    LEGACY_AUTH_FAILED_ERROR,
    MISSING_CREDENTIALS_ERROR,
    OAUTH_AUDIENCE,
    OAUTH_AUTH_FAILED_ERROR,
    OAUTH_TOKEN_ENDPOINT,
)
from ..core.exceptions import ZscalerManagerError
from ..core.utils import Logger, validate_response

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import ChronicleSOAR, SingleJson


REQUEST_TIMEOUT: int = 30


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    login_id: str | None = None
    api_key: str | None = None
    password: str | None = None
    verify_ssl: bool = False
    client_id: str | None = None
    client_secret: str | None = None
    login_api_root: str | None = None


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract auth params for Auth manager"""
    sdk_class: str = type(soar_sdk_object).__name__
    input_dictionary: dict
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration("Zscaler")
    elif sdk_class in (SiemplifyConnectorExecution.__name__, SiemplifyJob.__name__):
        input_dictionary = soar_sdk_object.integration_config
    else:
        input_dictionary = {}

    return IntegrationParameters(
        api_root=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        ),
        login_id=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Login ID",
        ),
        api_key=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Api Key",
        ),
        password=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Password",
        ),
        verify_ssl=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
        ),
        client_id=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Client ID",
            remove_whitespaces=True,
        ),
        client_secret=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Client Secret",
            remove_whitespaces=True,
        ),
        login_api_root=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Login API Root",
        ),
    )


def _is_not_empty(value: str | None) -> bool:
    """Check if string has value."""
    return bool(value and str(value).strip())


class AuthenticatedSession(Authable):

    def __init__(self) -> None:
        """Initialize AuthenticatedSession."""
        self.session: requests.Session = CreateSession.create_session()
        self.api_root: str = ""
        self.use_oauth: bool = False
        self.use_legacy: bool = False
        self.access_token: str | None = None

    def _obfuscate_api_key(self, api_key: str, timestamp: int) -> str:
        """Obfuscate API key based on timestamp."""
        n: str = str(timestamp)[-6:]
        r: str = str(int(n) >> 1).zfill(6)
        api_key_str = str(api_key)

        key_chars: list[str] = []

        for digit in n:
            key_chars.append(api_key_str[int(digit) % len(api_key_str)])

        for digit in r:
            key_chars.append(api_key_str[(int(digit) + 2) % len(api_key_str)])

        return "".join(key_chars)

    def authenticate_session(
        self,
        params: SessionAuthenticationParameters,
        logger: ScriptLogger,
    ) -> None:
        """Authenticate session based on parameters."""
        auth_logger = Logger(logger)

        self.session.verify = params.verify_ssl
        self.session.headers = HEADERS.copy()

        self._reset_auth_state()

        self._check_auth_type(params)
        self.api_root = self._normalize_api_root(params.api_root)

        if self.use_oauth:
            self._authenticate_oauth(params, auth_logger)
            return

        if self.use_legacy:
            self._authenticate_legacy(params, auth_logger)
            return

        raise ZscalerManagerError(MISSING_CREDENTIALS_ERROR)

    def _reset_auth_state(self) -> None:
        """Reset authentication state."""
        self.api_root = ""
        self.use_oauth = False
        self.use_legacy = False
        self.access_token = None

    def _check_auth_type(self, params: SessionAuthenticationParameters) -> None:
        """Determine authentication method."""
        self.use_oauth = all(
            [
                _is_not_empty(params.client_id),
                _is_not_empty(params.client_secret),
                _is_not_empty(params.login_api_root),
            ]
        )

        self.use_legacy = all(
            [
                _is_not_empty(params.login_id),
                _is_not_empty(params.api_key),
                _is_not_empty(params.password),
            ]
        )

    def _normalize_api_root(self, api_root: str | None) -> str:
        """Normalize API root."""
        if not api_root:
            return ""

        api_root_str = str(api_root).strip().rstrip("/")

        if api_root_str.endswith("/api/v1"):
            return api_root_str

        if "zsapi" in api_root_str and not api_root_str.endswith("/zia"):
            return f"{api_root_str}/zia/api/v1"

        return BASE_URL.format(api_root_str)

    def _authenticate_oauth(
        self,
        params: SessionAuthenticationParameters,
        logger: Logger,
    ) -> None:
        """Authenticate using OAuth."""
        logger.info("Authenticating to Zscaler via OAuth 2.0 (OneAPI)...")

        token_url = OAUTH_TOKEN_ENDPOINT.format(str(params.login_api_root).rstrip("/"))

        payload: SingleJson = {
            "grant_type": "client_credentials",
            "client_id": params.client_id,
            "client_secret": params.client_secret,
            "audience": OAUTH_AUDIENCE,
        }

        try:
            response = self.session.post(
                token_url,
                data=payload,
                headers=FORM_URL_ENCODED_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

        except requests.exceptions.RequestException as error:
            raise ZscalerManagerError(INVALID_CREDENTIALS_ERROR) from error

        validate_response(response, OAUTH_AUTH_FAILED_ERROR)

        self.access_token = response.json().get("access_token")

        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

        logger.info("Successfully authenticated via OAuth 2.0.")

    def _authenticate_legacy(
        self,
        params: SessionAuthenticationParameters,
        logger: Logger,
    ) -> None:
        """Authenticate using legacy API."""
        logger.info("Authenticating to Zscaler via Legacy API Key...")

        now = int(time.time() * 1000)
        key = self._obfuscate_api_key(params.api_key, now)

        payload_legacy: SingleJson = {
            "apiKey": key,
            "username": params.login_id,
            "password": params.password,
            "timestamp": str(now),
        }

        response = self.session.post(
            f"{self.api_root}/authenticatedSession",
            json=payload_legacy,
            timeout=REQUEST_TIMEOUT,
        )

        validate_response(response, LEGACY_AUTH_FAILED_ERROR)

        logger.info("Successfully authenticated via Legacy API Key.")
