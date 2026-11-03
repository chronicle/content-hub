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

import collections
import re
import urllib.parse

import requests
from requests.structures import CaseInsensitiveDict

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from . import constants
from . import AuthenticationManager as auth_manager
from . import MandiantDTMManager as api_manager
from .exceptions import MandiantDTMException


IntegrationParams = collections.namedtuple(
    "IntegrationParams", ["auth_params", "api_params"]
)


def get_integration_params(soar_action: SiemplifyAction) -> IntegrationParams:
    """Get Mandiant DTM IntegrationParams object for auth params and api params

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object

    Returns:
        IntegrationParams: Named tuple IntegrationParams
    """
    api_root = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        soar_action,
        param_name="Client ID",
        provider_name=constants.PROVIDER_NAME,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        soar_action,
        param_name="Client Secret",
        provider_name=constants.PROVIDER_NAME,
        remove_whitespaces=False,
    )
    gti_api_key = extract_configuration_param(
        soar_action,
        param_name="GTI API Key",
        provider_name=constants.PROVIDER_NAME,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    auth_params = auth_manager.SessionAuthenticationParameters(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        gti_api_key=gti_api_key,
        verify_ssl=verify_ssl,
    )
    api_params = api_manager.ApiParameters(api_root=api_root)
    integration_params = IntegrationParams(
        auth_params=auth_params, api_params=api_params
    )

    return integration_params


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        MandiantDTMException: If there is any error in the response
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if constants.UNAUTHORIZED_ERROR_MESSAGE in str(error):
            output_message = (
                "Invalid Credentials or Wrong API Key. Please verify the 'Client ID,' "
                "'Client Secret,' or 'GTI API Key'."
            )
        else:
            output_message = f"{error}"

        raise MandiantDTMException(f"{error_msg}: {output_message}") from error


def get_full_url(api_root: str, endpoint: str, **kwargs) -> str:
    """Construct the full URL using a URL identifier and optional variables

    Args:
        api_root (str): api root
        endpoint (str): endpoint path
        kwargs (dict): variables passed for string formatting

    Returns:
        str: constructed full URL
    """
    return urllib.parse.urljoin(api_root, endpoint.format(**kwargs))


def get_next_page_url(headers: CaseInsensitiveDict[str]) -> str:
    """Get next page url from response headers

    Args:
        headers (CaseInsensitiveDict[str]): response headers

    Returns:
        str: next page url
    """
    # extract next page url from response link header
    matches = re.findall(r"<(.*?)>", headers.get("link", ""))
    return matches[0] if matches else None
