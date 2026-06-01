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

from http import HTTPStatus
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_configuration_param

from . import consts
from .datamodels import IntegrationParameters
from .exceptions import (
    GoogleCloudIdentityApiEntityNotFoundException,
    GoogleCloudIdentityApiException,
)

if TYPE_CHECKING:
    import requests
    from TIPCommon.types import ChronicleSOAR


def get_integration_parameters(chronicle_soar: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for CloudIdentity auth and api manager.

    Args:
        chronicle_soar (ChronicleSOAR): ChronicleSOAR object.

    Returns:
        IntegrationParameters: IntegrationParameters object.

    """
    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Service Account JSON File Content",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        chronicle_soar,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Workload Identity Email",
        is_mandatory=False,
        print_value=True,
    )
    delegated_email = extract_configuration_param(
        chronicle_soar,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Delegated Email",
        is_mandatory=True,
        print_value=True,
    )
    return IntegrationParameters(
        service_account_json=service_account_json,
        verify_ssl=verify_ssl,
        workload_identity_email=workload_identity_email,
        delegated_email=delegated_email,
        siemplify_logger=chronicle_soar.LOGGER,
    )


def validate_response(response: requests.Response, api_name: str) -> None:
    """Validate a response from the Google Cloud Identity API.

    Args:
        response: The response to validate.
        api_name: The name of the API that was called.

    Raises:
        GoogleCloudIdentityApiEntityNotFoundException: If the entity was not found.
        GoogleCloudIdentityApiException: For other API errors.

    """
    response_json = response.json()
    if response.status_code == HTTPStatus.NOT_FOUND:
        msg = f"{api_name} entity not found: {response_json}"
        raise GoogleCloudIdentityApiEntityNotFoundException(msg)
    try:
        response.raise_for_status()
    except Exception as e:
        msg = f"{api_name} failed reason: {e}, {response_json}"
        raise GoogleCloudIdentityApiException(msg) from e

    # Validation for modification calls results
    if response_json.get("done") is False:
        msg = f"{api_name} did not finish request: {response_json}"
        raise GoogleCloudIdentityApiException(msg)
