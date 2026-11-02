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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator

from crowd_strike_falcon.core.constants import (
    CID_ERROR,
    INTEGRATION_NAME,
    LIST_HOSTS_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    HOSTS_TABLE_NAME,
    MIN_HOSTS_TO_FETCH,
    MAX_HOSTS_TO_FETCH
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


MAX_HOSTS_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_HOSTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    integration_cid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True
    )
    action_cid = extract_action_param(
        siemplify,
        param_name="Customer ID",
        print_value=True,
    )
    customer_id = action_cid or integration_cid

    limit = extract_action_param(
        siemplify,
        param_name="Max Hosts To Return",
        input_type=int,
        print_value=True,
        default_value=MAX_HOSTS_LIMIT,
    )

    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = "No hosts were found for the provided criteria."

    try:
        validator = ParameterValidator(siemplify)
        limit = validator.validate_range(
            param_name="Max Hosts To Return",
            value=limit,
            min_limit=MIN_HOSTS_TO_FETCH,
            max_limit=MAX_HOSTS_TO_FETCH,
        )

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        devices = manager.get_devices_by_hostname(
            hostname=filter_value,
            filter_strategy=filter_logic,
            cid=customer_id,
            limit=limit,
            page_size=MAX_HOSTS_TO_FETCH
        )

        # Construct output json (empty if no devices where found)
        siemplify.result.add_result_json([device.to_json() for device in devices])

        if devices:
            siemplify.result.add_data_table(
                HOSTS_TABLE_NAME, construct_csv([device.to_csv() for device in devices])
            )
            output_message = (
                "Successfully retrieved available hosts based on the provided criteria."
            )
            result_value = True

    except Exception as e:
        error_message = f"Error executing action {LIST_HOSTS_SCRIPT_NAME}."
        output_message = f"{error_message} Reason: {e}"
        if CID_ERROR in str(e).lower():
            output_message = f"{error_message} Reason: Incorrect Customer ID specified."

        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
