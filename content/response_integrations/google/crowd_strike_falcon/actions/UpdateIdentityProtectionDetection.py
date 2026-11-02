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

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    DETECTION_STATUS_MAPPING,
    INTEGRATION_NAME,
    UPDATE_IDENTITY_PROTECTION_DETECTION_SCRIPT_NAME,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeNotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_IDENTITY_PROTECTION_DETECTION_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client API ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client API Secret",
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
    customer_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True,
    )

    # action parameters
    detection_id = extract_action_param(
        siemplify, param_name="Detection ID", is_mandatory=True, print_value=True
    )
    detection_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    assign_to = extract_action_param(
        siemplify, param_name="Assign To", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if not DETECTION_STATUS_MAPPING.get(detection_status) and not assign_to:
            raise Exception(
                'at least one of the "Status" or "Assign To" parameters should have a value'
            )

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=verify_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        try:
            manager.get_alerts_details([detection_id])[0]
        except CrowdStrikeNotFoundError:
            raise Exception(
                f"identity protection detection with ID {detection_id} wasn't found in {INTEGRATION_NAME}. "
                f"Please check the spelling."
            )

        manager.update_alert(
            alert_id=detection_id,
            status=detection_status,
            assign_to=assign_to,
        )
        updated_alert = manager.get_alerts_details([detection_id])[0]
        siemplify.result.add_result_json(updated_alert.to_json())
        output_message = (
            f"Successfully updated identity protection detection with ID {detection_id} in "
            f"{INTEGRATION_NAME}."
        )

    except Exception as e:
        output_message = f'Error executing action "{UPDATE_IDENTITY_PROTECTION_DETECTION_SCRIPT_NAME}". Reason: {e}'
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
