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

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from crowd_strike_falcon.core.constants import (
    ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    INTEGRATION_NAME,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_SCRIPT_NAME

    siemplify.LOGGER.info("--------------- Main - Param Init ----------------")

    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
        default_value=API_ROOT_DEFAULT,
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
        remove_whitespaces=False,
    )
    use_ssl = extract_configuration_param(
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
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )

        manager.update_alert_detail(comment, detection_id)

        output_message = (
            "Successfully added comment to the identity "
            "protection detection with "
            f"ID {detection_id} in CrowdStrike."
        )

    except Exception as e:
        output_message = (
            "Error executing action "
            f'"{ADD_IDENTITY_PROTECTION_DETECTION_COMMENT_SCRIPT_NAME}". '
            f"Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, result_value, status)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")


if __name__ == "__main__":
    main()
