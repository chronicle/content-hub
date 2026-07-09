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
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core import utils
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_NAME
from ..core.utils import extract_integration_params

SCRIPT_NAME = "Get Threat Intelligence Set Details"


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
    ti_sets_ids = extract_action_param(
        siemplify,
        param_name="Threat Intelligence Set IDs",
        is_mandatory=True,
        print_value=True,
    )
    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    # Split the ti sets IDs
    ti_sets_ids = utils.load_csv_to_list(ti_sets_ids, "Threat Intelligence Set IDs")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_ids = []
    failed_ids = []

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

        manager.get_detector(detector_id=detector_id)  # Validate that the detector exists

        found_ti_sets = []

        for ti_set_id in ti_sets_ids:
            try:
                siemplify.LOGGER.info(f"Fetching Threat Intelligence set {ti_set_id} details (detector {detector_id})")
                ti_set = manager.get_threat_intel_set_by_id(detector_id=detector_id, threat_intel_set_id=ti_set_id)
                found_ti_sets.append(ti_set)
                successful_ids.append(ti_set_id)
                json_results[ti_set_id] = ti_set.raw_data

            except Exception as e:
                failed_ids.append(ti_set_id)
                siemplify.LOGGER.exception(f"An error occurred on Threat Intelligence set {ti_set_id}")
                siemplify.LOGGER.exception(e)

        if found_ti_sets:
            siemplify.LOGGER.info(f"Found {len(found_ti_sets)} Threat Intelligence sets details.")
            siemplify.result.add_data_table(
                "Threat Intelligence Set Details",
                construct_csv([ti_set.as_csv() for ti_set in found_ti_sets]),
            )

            if successful_ids:
                output_message += "Successfully retrieved details about the following Threat Intelligence Sets from AWS GuardDuty:\n{}\n\n".format(
                    "\n".join(successful_ids)
                )

            if failed_ids:
                output_message += "Action wasn't able to  retrieve details about the following Threat Intelligence Sets from AWS GuardDuty:\n{}".format(
                    "\n".join(failed_ids)
                )

        else:
            siemplify.LOGGER.info("No details were retrieved about the provided Threat Intelligence Sets.")
            output_message += "No details were retrieved about the provided Threat Intelligence Sets."
            result_value = "false"

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
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
