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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from TIPCommon import dict_to_flat, construct_csv, extract_configuration_param

INTEGRATION_NAME = "CiscoISE"
TABLE_HEADER = "Endpoints Data"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_GetEndpoints"

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    cim = CiscoISEManager(api_root, username, password, verify_ssl)

    # Variables.
    result_value = False

    endpoints_objects_list = cim.get_endpoints()
    if endpoints_objects_list:
        endpoints_objects_list = list(map(dict_to_flat, endpoints_objects_list))
        csv_result = construct_csv(endpoints_objects_list)

        siemplify.result.add_data_table(TABLE_HEADER, csv_result)
        result_value = True
        output_message = f'Found "{len(endpoints_objects_list)}" endpoints.'
    else:
        output_message = "No Endpoints found."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
