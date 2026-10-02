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

import urllib.parse

from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param

import requests
from . import constants
from . import exceptions
from . import AuthenticationManager as auth_manager
from . import PaloAltoPrismaCloudManager as api_manager


IntegrationParams = collections.namedtuple(
    "IntegrationParams", ["auth_params", "api_params"]
)


def get_integration_params(soar_action: SiemplifyAction) -> IntegrationParams:
    """Get Palo Alto Prisma Cloud IntegrationParams object for session auth params and
    api params.

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object.

    Returns:
        IntegrationParams: Named tuple IntegrationParams.
    """
    api_root = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    access_key_id = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Access Key ID",
        is_mandatory=True,
        print_value=True,
    )
    secret_access_key = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Secret Access Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    auth_params = auth_manager.SessionAuthenticationParameters(
        api_root=api_root,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        verify_ssl=verify_ssl,
    )
    api_params = api_manager.ApiParameters(
        api_root=api_root,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        verify_ssl=verify_ssl,
    )
    integration_params = IntegrationParams(
        auth_params=auth_params, api_params=api_params
    )

    return integration_params


def get_full_url(
    api_root: str, endpoint_id: str, endpoints: dict[str, str], **kwargs
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root (str): The root of the API endpoint.
        endpoint_id (str): The identifier for the specific URL.
        endpoints (dict[str, str]): endpoints dictionary object.
        kwargs (dict): Variables passed for string formatting.

    Returns:
        str: The full URL constructed by combining the API root, URL identifier, and
            variables.
    """
    return urllib.parse.urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response, err_msg: str = "An error is occurred"
) -> None:
    """Validate response.

    Args:
        response: The response info
        err_msg: Default message to display on error
    Raises:
        PaloAltoPrismaCloudError: if there is any error
    """
    try:
        if response.status_code in (
            constants.API_BAD_REQUEST,
            constants.ITEM_NOT_FOUND,
            constants.METHOD_NOT_ALLOWED,
        ):
            raise exceptions.PaloAltoPrismaCloudError(err_msg)
        response.raise_for_status()

    except requests.HTTPError as error:
        raise exceptions.PaloAltoPrismaCloudError(f"{error} {err_msg}")
