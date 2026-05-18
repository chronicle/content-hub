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
from ..core.AttivoManager import AttivoManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_SERVICE_THREATPATHS_SCRIPT_NAME,
)
from TIPCommon import construct_csv
from ..core.UtilsManager import convert_comma_separated_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SERVICE_THREATPATHS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    services = extract_action_param(
        siemplify, param_name="Services", print_value=True, is_mandatory=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max ThreatPaths To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    successful_services, failed_services, json_results = [], [], []

    try:
        services = convert_comma_separated_to_list(services)
        if limit is not None:
            if limit < 1:
                raise Exception(
                    f'Invalid value was provided for "Max ThreatPaths to Return": {limit}. '
                    f"Positive number should be provided"
                )

        manager = AttivoManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for service in services:
            threatpaths = manager.get_service_threatpaths(service, limit)
            if threatpaths:
                successful_services.append(service)
                siemplify.result.add_data_table(
                    service, construct_csv([path.to_csv() for path in threatpaths])
                )
                json_results.append(
                    {
                        "service": service,
                        "paths": [path.to_json() for path in threatpaths],
                    }
                )
            else:
                failed_services.append(service)

        if successful_services:
            output_message = (
                f"Successfully retrieved ThreatPaths for the following services in  "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f'{", ".join(successful_services)}\n'
            )
            siemplify.result.add_result_json(json_results)

            if failed_services:
                output_message += (
                    f"No ThreatPaths were found for the following services in "
                    f'{INTEGRATION_DISPLAY_NAME}: {", ".join(failed_services)}\n'
                )
        else:
            output_message = f"No ThreatPaths were found for the provided services in {INTEGRATION_DISPLAY_NAME}."
            result = False

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_SERVICE_THREATPATHS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_SERVICE_THREATPATHS_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
