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
from TIPCommon.extraction import extract_action_param

from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.utils import extract_integration_params

SCRIPT_NAME = "Update a Detector"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    (
        aws_access_key,
        aws_secret_key,
        aws_default_region,
        role_arn,
        service_account_json,
        workload_identity_email,
    ) = extract_integration_params(siemplify)

    detector_id = extract_action_param(
        siemplify,
        param_name="Detector ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    enable = extract_action_param(
        siemplify,
        param_name="Enable",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
            role_arn=role_arn,
            service_account_json=service_account_json,
            workload_identity_email=workload_identity_email,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()
        siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service")

        siemplify.LOGGER.info(f"Updating detector {detector_id}")
        manager.update_detector(detector_id=detector_id, enable=enable)
        siemplify.LOGGER.info(f"Successfully updated detector {detector_id}")

        status = EXECUTION_STATE_COMPLETED
        output_message = f"The detector {detector_id} has been updated."
        result_value = "true"

    except Exception as error:
        siemplify.LOGGER.exception(f"Error executing action {SCRIPT_NAME}. Reason: {error}")
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
