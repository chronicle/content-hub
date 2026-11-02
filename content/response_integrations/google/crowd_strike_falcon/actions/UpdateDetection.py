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
    INTEGRATION_NAME,
    PRODUCT_NAME,
    UPDATE_DETECTION_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    DetectionStatusEnum,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeParameterError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_DETECTION_SCRIPT_NAME

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
    customer_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True,
    )

    detection_id = extract_action_param(
        siemplify, param_name="Detection ID", is_mandatory=True
    )
    status_to_update = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True
    )
    assign_to = extract_action_param(siemplify, param_name="Assign Detection to")

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if status_to_update == DetectionStatusEnum.SELECT_ONE.value:
            if not assign_to:
                raise CrowdStrikeParameterError(
                    'Either "Status" or "Assign Detection To" should have a proper value.'
                )

            status_to_update = None

        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        uuid = manager.get_user_uuid_or_raise(assign_to) if assign_to else None

        manager.update_detection(uuid, [detection_id], status_to_update)

        output_message = (
            f"Successfully updated detection {detection_id} in {PRODUCT_NAME}."
        )
    except Exception as e:
        output_message = (
            f"Error executing action '{UPDATE_DETECTION_SCRIPT_NAME}'. Reason: {e}"
        )
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
