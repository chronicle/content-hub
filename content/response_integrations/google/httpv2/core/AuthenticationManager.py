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

import dataclasses

import json
import requests

from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import ChronicleSOAR
from . import api_utils
from . import constants
from .UtilsManager import save_certificate_file
from .exceptions import HTTPV2AuthException


@dataclasses.dataclass
class SessionAuthenticationParameters:
    test_url: str
    basic_auth_username: str
    basic_auth_password: str
    api_key_field_name: str
    api_key_secret: str
    auth_api_request_method: str
    auth_api_request_url: str
    auth_api_request_headers: str | dict
    auth_api_request_body: str
    auth_api_request_token_field_name: str
    restrict_domain: bool
    verify_ssl: bool
    ca_certificate: str


def get_authenticated_session(
    chronicle_soar: ChronicleSOAR,
    auth_method: str,
    auth_params: SessionAuthenticationParameters,
) -> (requests.Session, str):
    """Get authenticated session based on auth method and auth params

    Args:
        chronicle_soar (ChronicleSOAR): Chronicle SOAR SDK object
        auth_method (str): auth method
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        (requests.Session, str) requests.Session object, access token
    """
    session = requests.Session()
    session.verify = get_verify_value(
        chronicle_soar, auth_params.verify_ssl, auth_params.ca_certificate
    )
    access_token = None

    if auth_method == constants.AUTH_METHOD.get("ACCESS_TOKEN"):
        session.headers.update(auth_params.auth_api_request_headers)
        access_token = generate_access_token(session, auth_params)

        if not access_token:
            raise HTTPV2AuthException(
                f"Couldn't retrieve the access token from response, as the key "
                f"{auth_params.auth_api_request_token_field_name} wasn't found in "
                f"the response. Please check the spelling."
            )

    elif auth_method == constants.AUTH_METHOD.get("BASIC"):
        session.auth = (
            auth_params.basic_auth_username,
            auth_params.basic_auth_password,
        )
    elif auth_method == constants.AUTH_METHOD.get("API_KEY"):
        session.headers.update(
            {auth_params.api_key_field_name: auth_params.api_key_secret}
        )

    return session, access_token


def generate_access_token(
    session: requests.Session, auth_params: SessionAuthenticationParameters
) -> str:
    """Generate access token for authentication

    Args:
        session (requests.Session): requests.Session object
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        str: access token
    """
    response = session.request(
        method=auth_params.auth_api_request_method,
        url=auth_params.auth_api_request_url,
        data=auth_params.auth_api_request_body,
    )

    api_utils.validate_response(response)

    return get_access_token(response, auth_params.auth_api_request_token_field_name)


def get_access_token(response: requests.Response, access_token_field_name: str) -> str:
    """Get access token from the request response by access token field name

    Args:
        response (requests.Response): request response
        access_token_field_name: access token field name to retrieve access token

    Returns:
        str: access token
    """
    try:
        # try to get json from the response
        response_data = response.json()
    except json.JSONDecodeError:
        # response is not in json format
        return ""

    return dict_to_flat(response_data).get(access_token_field_name)


def get_verify_value(
    chronicle_soar: ChronicleSOAR, verify_ssl: bool = True, ca_certificate: str = None
) -> str | bool:
    """Get verify value

    Args:
        chronicle_soar (ChronicleSOAR): Chronicle SOAR SDK object
        verify_ssl (bool): specifies if certificate should be validated
        ca_certificate (str): certificate to use for validation

    Returns:
        str | bool: verify value
    """
    if verify_ssl and ca_certificate is not None:
        return save_certificate_file(chronicle_soar, ca_certificate)

    return verify_ssl
