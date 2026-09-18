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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_script_param

from .constants import (
    ACCESS_ID_PARAM,
    ACCESS_KEY_PARAM,
    API_GATEWAY_URL_PARAM,
    DEFAULT_API_GATEWAY_URL,
    INTEGRATION_IDENTIFIER,
    VERIFY_SSL_PARAM,
)
from .datamodels import AkeylessClientConfig
from .exceptions import AkeylessError

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> AkeylessClientConfig:
    """Extract authentication parameters from the SOAR SDK object.

    Detects the SDK class type to determine where to read the
    integration configuration from, then returns a typed
    ``AkeylessClientConfig`` instance.

    Args:
        soar_sdk_object: A ChronicleSOAR SDK object (action, connector,
            or job).

    Returns:
        AkeylessClientConfig: The extracted integration configuration.

    Raises:
        AkeylessError: If the provided SDK object type is not
            supported.

    """
    sdk_class: str = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary: dict = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in {
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    }:
        input_dictionary = dict(soar_sdk_object.parameters or {})
        if (
            not input_dictionary.get(ACCESS_ID_PARAM)
            and hasattr(soar_sdk_object, "get_configuration_by_provider")
        ):
            fallback_config = soar_sdk_object.get_configuration_by_provider(
                INTEGRATION_IDENTIFIER,
            )
            if isinstance(fallback_config, dict):
                input_dictionary = {**fallback_config, **input_dictionary}
    else:
        msg = f"Provided SOAR instance is not supported! type: {sdk_class}."
        raise AkeylessError(
            msg,
        )

    access_id: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=ACCESS_ID_PARAM,
        is_mandatory=True,
        print_value=True,
    )
    access_key: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=ACCESS_KEY_PARAM,
        is_mandatory=True,
        print_value=False,
    )
    api_gateway_url: str = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=API_GATEWAY_URL_PARAM,
        is_mandatory=False,
        default_value=DEFAULT_API_GATEWAY_URL,
        print_value=True,
    )
    verify_ssl: bool = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name=VERIFY_SSL_PARAM,
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )

    return AkeylessClientConfig(
        access_id=access_id,
        access_key=access_key,
        api_gateway_url=api_gateway_url,
        verify_ssl=verify_ssl,
    )
