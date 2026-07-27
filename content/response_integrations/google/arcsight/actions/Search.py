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
from ..core.ArcsightManager import ArcsightManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME, SEARCH_SCRIPT_NAME, DEFAULT_LIMIT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=False,
    )

    search_query = extract_action_param(
        siemplify, param_name="Search Query", print_value=True, is_mandatory=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Items To Return",
        print_value=True,
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    results = []
    result_value = False
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        arcsight_manager = ArcsightManager(
            server_ip=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
        )
        arcsight_manager.login()
        search_result_object = arcsight_manager.search(query=search_query, limit=limit)
        results.extend(search_result_object)

        if results:
            siemplify.result.add_data_table(
                "Results", construct_csv([result.to_csv() for result in results])
            )
            siemplify.result.add_result_json([result.to_json() for result in results])
            result_value = True
            output_message = "Successfully retrieved available resources based on the provided search query."
        else:
            output_message = (
                "No resources were found that match the provided search query."
            )

        arcsight_manager.logout()
    except Exception as e:
        output_message = (
            f"Error executing action {SEARCH_SCRIPT_NAME}. Reason: {str(e)}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
