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
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.utils import extract_integration_params

SCRIPT_NAME = "Unarchive Findings"


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

    detector_id = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)
    findings_ids = extract_action_param(siemplify, param_name="Finding IDs", is_mandatory=True, print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    unarchived_findings = []
    output_message = ""
    result_value = "false"

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
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service")

        # Split the findings IDs
        findings_ids = utils.load_csv_to_list(findings_ids, "Finding IDs")

        siemplify.LOGGER.info(f"Un-archiving findings of detector {detector_id}")

        fetched_findings = manager.get_findings_by_ids(detector_id=detector_id, findings_ids=findings_ids)
        fetched_findings_ids = [finding.id for finding in fetched_findings]
        not_unarchived_findings = [id for id in findings_ids if id not in fetched_findings_ids]

        for finding in fetched_findings_ids:
            try:
                manager.unarchive_findings(detector_id=detector_id, finding_ids=[finding])
                siemplify.LOGGER.info(f"Successfully un-archiving finding with id {finding} of detector {detector_id}")
                unarchived_findings.append(finding)

            except Exception as error:
                siemplify.LOGGER.info(f"Action wasn’t able to un-archive Finding: {finding} Error {error}")
                siemplify.LOGGER.exception(f"Action wasn’t able to un-archive Finding {finding} Error {error}")

        if unarchived_findings:
            output_message += (
                "The following findings were successfully un-archived: " + ", ".join(unarchived_findings) + "\n"
            )
            result_value = "true"

        if not_unarchived_findings:
            output_message += "Could not un-archive the following findings: " + ", ".join(not_unarchived_findings)

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:  # action failed
        siemplify.LOGGER.exception(f"Error executing action '{SCRIPT_NAME}'. Reason: {error}")
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
