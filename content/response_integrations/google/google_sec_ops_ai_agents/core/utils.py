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
from typing import TYPE_CHECKING
from google_sec_ops_ai_agents.core import consts
from google_sec_ops_ai_agents.core.data_models import IntegrationParameters
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.utils import BASE_1P_SDK_CONTROLLER_VERSION

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def get_google_secops_api_uri(soar_sdk_object: ChronicleSOAR) -> str:
    return soar_sdk_object.sdk_config.one_platform_api_root_uri_format.format(BASE_1P_SDK_CONTROLLER_VERSION)


def build_integration_params(
    soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Build integration parameters from the SOAR SDK object.

      Args:
          soar_sdk_object: The SOAR SDK object.

      Returns:
          The integration parameters.
      """

    # TODO: use get_sdk_api_uri when featSdkDataplane is 100% true
    api_root = get_google_secops_api_uri(soar_sdk_object)
    verify_ssl: bool = extract_configuration_param(
        soar_sdk_object,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    return IntegrationParameters(
        api_root=api_root,
        verify_ssl=verify_ssl,
    )
