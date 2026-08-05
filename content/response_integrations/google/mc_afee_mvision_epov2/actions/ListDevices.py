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
from ..core.McAfeeMvisionEPOV2Manager import McAfeeMvisionEPOV2Manager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import LIST_DEVICES_SCRIPT_NAME, INTEGRATION_NAME, DEFAULT_LIMIT_DEVICES


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DEVICES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )

    iam_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IAM Root",
        is_mandatory=True,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    # Parameters
    max_devices_to_return = extract_action_param(
        siemplify,
        param_name="Max Devices to Return",
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_LIMIT_DEVICES,
    )

    if max_devices_to_return <= 0:
        siemplify.LOGGER.info(
            f"Max Devices to Return must be positive. Using default "
            f"value instead ({DEFAULT_LIMIT_DEVICES})."
        )
        max_devices_to_return = DEFAULT_LIMIT_DEVICES

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_results = []

    try:
        siemplify.LOGGER.info("Connecting to McAfee Mvision ePO V2.")
        manager = McAfeeMvisionEPOV2Manager(
            api_root,
            iam_root,
            client_id,
            client_secret,
            api_key,
            scopes,
            verify_ssl,
            siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Successfully connected to McAfee Mvision ePO V2.")

        siemplify.LOGGER.info("Fetching available devices.")
        devices = manager.get_devices(max_devices_to_return)

        if devices:
            siemplify.LOGGER.info(f"Found {len(devices)} devices.")
            csv_table = [device.to_table_data() for device in devices]
            json_results = [device.to_json() for device in devices]

            siemplify.result.add_data_table(
                title="Available Devices", data_table=construct_csv(csv_table)
            )
            output_message += (
                "Successfully listed available devices in McAfee Mvision ePO V2"
            )

        else:
            siemplify.LOGGER.info("No devices were found.")
            output_message += (
                "Action wasn’t able to list devices available in McAfee Mvision ePO V2"
            )
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_DEVICES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message += f"Error executing action List Devices. Reason: {e}"
        result_value = False

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
