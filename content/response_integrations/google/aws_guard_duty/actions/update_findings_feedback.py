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

from ..core import utils
from ..core.aws_guard_duty_manager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME, NOT_USEFUL, USEFUL
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "Update Findings Feedback"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    detector_id = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)

    is_useful = extract_action_param(
        siemplify,
        param_name="Useful",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    finding_ids = extract_action_param(siemplify, param_name="Findings IDs", is_mandatory=True, print_value=True)

    comment = extract_action_param(siemplify, param_name="Comment", is_mandatory=False, print_value=True)

    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=config.aws_default_region,
    )

    not_updated_finding = []
    output_message = ""
    updated_findings = ""
    failed_to_update_findings = ""

    siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
    if aws_region:
        config.aws_default_region = aws_region

    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
    manager.test_connectivity()  # this validates the credentials
    siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service")

    # Split the findings IDs
    finding_ids = utils.load_csv_to_list(finding_ids, "Findings IDs")
    useful = USEFUL if is_useful else NOT_USEFUL

    # Get finding by id's to see if exist
    findings_found = manager.get_findings_by_ids(detector_id=detector_id, findings_ids=finding_ids)

    fetched_findings = [find.id for find in findings_found]
    for finding_id in finding_ids:
        if finding_id not in fetched_findings:
            not_updated_finding.append(finding_id)
            failed_to_update_findings += f"{finding_id} "
        else:
            updated_findings += f"{finding_id} "

    siemplify.LOGGER.info(f"Update Findings Feedback for {fetched_findings}")
    manager.update_findings_feedback(
        detector_id=detector_id,
        useful=useful,
        finding_ids=fetched_findings,
        comment=comment,
    )
    siemplify.LOGGER.info(f"Successfully Updated Findings Feedback for {fetched_findings}")

    output_message += f"Findings feedback was updated for finding: {updated_findings}" if fetched_findings else ""

    output_message += f"Unable to update feedback findings: {failed_to_update_findings}" if not_updated_finding else ""

    result_value = "true" if fetched_findings else "false"
    return result_value, output_message


@output_handler
def main() -> None:
    """Mark the specified Amazon GuardDuty findings as useful or not useful."""
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
