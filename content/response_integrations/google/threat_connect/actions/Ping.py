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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

from ..core.constants import INTEGRATION_NAME
from ..core.ThreatConnectManager import ThreatconnectAPI


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    # Integration params
    api_access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiAccessId",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiSecretKey",
        is_mandatory=True,
    )
    api_default_org = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiDefaultOrg",
        is_mandatory=True,
        print_value=True,
    )
    api_base_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiBaseUrl",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    threat_connect = ThreatconnectAPI(
        api_access_id, api_secret_key, api_default_org, api_base_url
    )
    threat_connect.owner = api_default_org

    r = threat_connect.test_connectivity()

    if r:
        output_message = "Connection Established"
        result_value = "true"
    else:
        output_message = "Connection Failed"
        result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
