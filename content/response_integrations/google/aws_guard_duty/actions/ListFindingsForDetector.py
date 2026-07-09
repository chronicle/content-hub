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
from ..core.consts import ASC, DEFAULT_MAX_RESULTS, INTEGRATION_NAME
from ..core.utils import extract_integration_params

SCRIPT_NAME = "List Findings for a Detector"


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

    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Max Findings To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    sort_by = extract_action_param(siemplify, param_name="Sort By", is_mandatory=False, print_value=True)

    order_by = extract_action_param(
        siemplify,
        param_name="Order By",
        is_mandatory=False,
        print_value=True,
        default_value=ASC,
    )
    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    if max_results_to_return and max_results_to_return < 0:
        max_results_to_return = DEFAULT_MAX_RESULTS
        siemplify.LOGGER.info(
            f"Max Trusted IP Lists To Return parameter must be non-positive. Using default value of {DEFAULT_MAX_RESULTS}"
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_region,
            role_arn=role_arn,
            service_account_json=service_account_json,
            workload_identity_email=workload_identity_email,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

        siemplify.LOGGER.info(f"Fetching findings ids for detector {detector_id}")
        findings_ids = manager.get_findings_ids_for_detector(
            detector_id=detector_id,
            sort_by=sort_by,
            order_by=order_by,
            max_results=max_results_to_return,
        )
        siemplify.LOGGER.info(f"Successfully found {len(findings_ids)} findings ids")
        output_message = f"Successfully retrieved available findings IDs for detector {detector_id}."

        json_results["FindingIds"] = findings_ids

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
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
