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

from ..core.aws_guard_duty_manager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_NAME
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "Ping"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
    manager.test_connectivity()
    output_message = "Successfully connected to the AWS GuardDuty server with the provided connection parameters!"
    result_value = "true"
    return result_value, output_message


@output_handler
def main() -> None:
    """Test connectivity to AWS GuardDuty."""
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
        output_message = f"Failed to connect to the AWS GuardDuty server. Error: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
