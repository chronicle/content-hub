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

from typing import NamedTuple

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_script_param
from TIPCommon.types import ChronicleSOAR

from .constants import (
    INTEGRATION_IDENTIFIER,
    ACCESS_ID_PARAM,
    ACCESS_KEY_PARAM,
    ACCESS_TYPE_PARAM,
    API_GATEWAY_URL_PARAM,
)
from .exceptions import AkeylessError


class IntegrationParameters(NamedTuple):
    access_id: str
    access_key: str | None
    access_type: str
    api_gateway_url: str


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract authentication parameters from the SOAR SDK object.

    Detects the SDK class type to determine where to read the
    integration configuration from, then returns a typed
    ``IntegrationParameters`` tuple.

    Args:
        soar_sdk_object: A ChronicleSOAR SDK object (action, connector,
            or job).

    Returns:
        IntegrationParameters: The extracted integration parameters.

    Raises:
        AkeylessError: If the provided SDK object type is not
            supported.

    """
    sdk_class: str = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary: dict = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    ):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise AkeylessError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    access_id: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=ACCESS_ID_PARAM,
        is_mandatory=True,
        print_value=True,
    )
    access_key: str | None = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=ACCESS_KEY_PARAM,
        is_mandatory=False,
        print_value=False,
    )
    access_type: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=ACCESS_TYPE_PARAM,
        is_mandatory=False,
        default_value="gcp",
        print_value=True,
    )
    api_gateway_url: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=API_GATEWAY_URL_PARAM,
        is_mandatory=False,
        default_value="https://api.akeyless.io",
        print_value=True,
    )

    return IntegrationParameters(
        access_id=access_id,
        access_key=access_key,
        access_type=access_type,
        api_gateway_url=api_gateway_url,
    )
