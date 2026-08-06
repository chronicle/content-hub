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

from ..core.aws_guard_duty_manager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_NAME
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "Update Threat Intelligence Set"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    detector_id = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)
    threat_intel_set_id = extract_action_param(siemplify, param_name="ID", is_mandatory=True, print_value=True)
    name = extract_action_param(siemplify, param_name="Name", is_mandatory=False, print_value=True)
    file_location = extract_action_param(siemplify, param_name="File Location", is_mandatory=False, print_value=True)
    activate = extract_action_param(
        siemplify,
        param_name="Active",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
    manager.test_connectivity()  # this validates the credentials
    siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

    siemplify.LOGGER.info(f"Updating Threat Intelligence set {threat_intel_set_id} (detector {detector_id}).")
    manager.update_threat_intel_set(
        detector_id=detector_id,
        threat_intel_set_id=threat_intel_set_id,
        name=name,
        file_location=file_location,
        activate=activate,
    )

    output_message = f"Successfully updated the Threat Intelligence Set '{threat_intel_set_id}' in AWS GuardDuty."
    siemplify.LOGGER.info(output_message)
    result_value = "true"
    return result_value, output_message


@output_handler
def main() -> None:
    """Update a threat intelligence set in AWS GuardDuty."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    config = extract_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        result_value, output_message = _run_action(siemplify, config)
        status = EXECUTION_STATE_COMPLETED
    except Exception as error:
        siemplify.LOGGER.exception("Error executing action.")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
