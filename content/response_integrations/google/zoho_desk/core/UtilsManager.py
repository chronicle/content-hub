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
from urllib.parse import urlparse

import requests

from zoho_desk.core.AccessToken import AccessTokenComponents, get_access_token
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR
from zoho_desk.core.ZohoDeskExceptions import ZohoDeskException
from zoho_desk.core.constants import INTEGRATION_NAME
from zoho_desk.core.datamodels import IntegrationParameters


def get_integration_parameters(siemplify: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for ZohoDesk's manager"""
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    region = extract_region_from_api_root(api_root)
    token_parameters = get_access_token_components(siemplify, region)
    access_token = get_access_token(siemplify, token_parameters)
    return IntegrationParameters(
        api_root=api_root,
        oauth_token=access_token,
        verify_ssl=verify_ssl,
        siemplify_logger=siemplify.LOGGER,
    )


def get_access_token_components(
    siemplify: ChronicleSOAR, region: str
) -> AccessTokenComponents:
    """Get the components for creating access token"""
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        remove_whitespaces=False,
    )
    return AccessTokenComponents(region, client_id, client_secret, refresh_token)


def extract_region_from_api_root(api_root: str) -> str:
    parsed_uri = urlparse(api_root)
    return parsed_uri.netloc.split(".")[-1]


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response_json = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ZohoDeskException(
                f"{error_msg}: {error} {error.response.content}"
            ) from e

        if response_json.get("message"):
            errors = response_json.get("errors", [])
            if errors:
                errors_message = "\n".join([err.get("errorMessage") for err in errors])
                raise ZohoDeskException(
                    f"{response_json.get('message')}: {errors_message}"
                ) from error

            raise ZohoDeskException(f"{response_json.get('message')}") from error

        raise ZohoDeskException(f"{error_msg}: {error} {response.content}") from error
