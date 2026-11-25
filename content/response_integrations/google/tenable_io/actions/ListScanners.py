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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.TenableIOManager import TenableIOManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_SCANNERS_SCRIPT_NAME,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    DEFAULT_POLICIES_LIMIT,
    MAX_POLICIES_LIMIT,
)

TABLE_NAME = "Available Scanners"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SCANNERS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
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

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Scanners To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_POLICIES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Scanners To Return" must be greater than 0.')
        elif limit > MAX_POLICIES_LIMIT:
            siemplify.LOGGER.info(
                f'"Max Scanners To Return" exceeded the maximum limit of '
                f"{MAX_POLICIES_LIMIT}. The default value {DEFAULT_POLICIES_LIMIT} "
                f"will be used"
            )
            limit = MAX_POLICIES_LIMIT

        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Retrieving information about available scanners...")
        scanners = manager.list_scanners()
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                scanners = [
                    scanner for scanner in scanners if scanner.name == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                scanners = [
                    scanner for scanner in scanners if filter_value in scanner.name
                ]

        scanners = scanners[:limit] if limit else scanners

        if scanners:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([scanner.to_csv() for scanner in scanners])
            )
            siemplify.result.add_result_json(
                [scanner.to_json() for scanner in scanners]
            )
            output_message = (
                f"Successfully found scanners for the provided criteria in"
                f" {INTEGRATION_NAME}."
            )
        else:
            result_value = False
            output_message = f"No scanners were found for the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_SCANNERS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
