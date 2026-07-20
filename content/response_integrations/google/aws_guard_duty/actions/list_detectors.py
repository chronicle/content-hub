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
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "List Detectors"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    max_detectors = extract_action_param(
        siemplify,
        param_name="Max Detectors To Return",
        input_type=int,
        is_mandatory=False,
        print_value=True,
        default_value=50,
    )

    json_results = {}

    siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
    manager.test_connectivity()
    siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service")

    siemplify.LOGGER.info("Fetching the detectors list")
    detector_ids = manager.list_detectors(max_results=max_detectors)
    siemplify.LOGGER.info("Successfully fetched the detectors")

    json_results = {"detectorIds": detector_ids}
    output_message = f"Successfully listed available detectors in AWS GuardDuty. Indicator ID: {detector_ids}"
    result_value = "true"
    siemplify.result.add_result_json(json_results)

    return result_value, output_message


@output_handler
def main() -> None:
    """List detectorIds of all the existing Amazon GuardDuty detector resources."""
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
