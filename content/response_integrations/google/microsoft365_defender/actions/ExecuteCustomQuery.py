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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    EXECUTE_CUSTOM_QUERY_SCRIPT_NAME,
    DEFAULT_RESULTS_LIMIT,
    LOGIN_API_ROOT_DEFAULT,
    GRAPH_API_ROOT_DEFAULT,
    EMPTY_DROPDOWN_VALUE,
)
from ..core.Microsoft365DefenderManager import Microsoft365DefenderManager
from ..core.UtilsManager import get_timestamps

TABLE_NAME = "Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        default_value=LOGIN_API_ROOT_DEFAULT,
        print_value=True,
    )
    graph_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Graph API Root",
        is_mandatory=True,
        default_value=GRAPH_API_ROOT_DEFAULT,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
        remove_whitespaces=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        remove_whitespaces=False,
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
    custom_query = extract_action_param(
        siemplify, param_name="Query", print_value=True, is_mandatory=True
    )
    timeframe: str | None = extract_action_param(siemplify, param_name="Time Frame", print_value=True)
    start_time_string: str | None = extract_action_param(siemplify, param_name="Start Time", print_value=True)
    end_time_string: str | None = extract_action_param(siemplify, param_name="End Time", print_value=True)

    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_RESULTS_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = False
    status = EXECUTION_STATE_COMPLETED

    try:
        if limit < 1:
            raise Exception('"Max Results To Return" must be greater than 0.')

        start_time: str | None = None
        end_time: str | None = None
        if (
            (timeframe and timeframe != EMPTY_DROPDOWN_VALUE)
            or start_time_string
            or end_time_string
        ):
            start_time, end_time = get_timestamps(timeframe, start_time_string, end_time_string)

        manager = Microsoft365DefenderManager(
            api_root=api_root,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            microsoft_graph_url=graph_api_root,
            siemplify=siemplify,
            login_api_root=login_api_root,
        )
        devices, query_string = manager.search_for_devices(
            custom_query=custom_query,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        if devices:
            result = True
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([device.to_csv() for device in devices])
            )
            siemplify.result.add_result_json([device.to_json() for device in devices])
            output_message = (
                f'Successfully executed query "{query_string}" in {INTEGRATION_DISPLAY_NAME}'
                if query_string
                else f"Successfully executed query in {INTEGRATION_DISPLAY_NAME}"
            )
        else:
            output_message = (
                f'No data was found for the query "{query_string}" in {INTEGRATION_DISPLAY_NAME}'
                if query_string
                else f"No data was found for the query in {INTEGRATION_DISPLAY_NAME}"
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_CUSTOM_QUERY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{EXECUTE_CUSTOM_QUERY_SCRIPT_NAME}" Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
