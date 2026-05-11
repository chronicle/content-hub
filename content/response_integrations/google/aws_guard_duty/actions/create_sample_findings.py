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
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.aws_guard_duty_manager import aws_guard_duty_manager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME
from ..core import utils
from ..core import exceptions

SCRIPT_NAME = "Create Sample Findings"


@output_handler
def main():
    """
    Create sample findings
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    detector_id = extract_action_param(
        siemplify, param_name="Detector ID", is_mandatory=True, print_value=True
    )
    findings_types = extract_action_param(
        siemplify, param_name="Finding Types", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"

    try:
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        manager = aws_guard_duty_manager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service"
        )

        # Split the findings types
        findings_types = (
            utils.load_csv_to_list(findings_types, "Finding Types")
            if findings_types
            else []
        )

        if findings_types:
            siemplify.LOGGER.info(
                f"Creating sample findings for detector {detector_id}"
            )
            manager.create_sample_findings(
                detector_id=detector_id, finding_types=findings_types
            )
            siemplify.LOGGER.info(
                f"Successfully created sample findings for detector {detector_id}"
            )
            result_value = "true"

        output_message = (
            "Successfully created sample findings"
            if findings_types
            else "No samples was created, findings types list is empty"
        )
        status = EXECUTION_STATE_COMPLETED

    except exceptions.AWSGuardDutyNotFoundException as error:
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Action wasn’t able to create sample findings because an invalid value was found as Finding "
            f"Types parameter.Error: {error}"
        )

    except Exception as error:
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
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