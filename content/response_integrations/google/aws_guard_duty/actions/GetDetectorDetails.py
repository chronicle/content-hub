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
from TIPCommon.extraction import extract_action_param
from ..core.utils import extract_integration_params
from TIPCommon.transformation import construct_csv
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME
from ..core.exceptions import AWSGuardDutyNotFoundException
from ..core import utils


SCRIPT_NAME = "Get Detector Details"


@output_handler
def main():
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

    detector_ids = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    csv_list = []
    not_found_detectors_id = []
    found_detectors = []
    not_founds_message = ""

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

        # Split the detectors IDs
        detector_ids = utils.load_csv_to_list(detector_ids, "Detector ID")

        siemplify.LOGGER.info("Fetching Detectors details by id")

        for detector_id in detector_ids:
            try:
                detector_obj = manager.get_detector_details(detector_id)
                csv_list.append(detector_obj.to_csv())
                json_results[detector_id] = detector_obj.to_json()
                found_detectors.append(detector_obj)

            except Exception as e:
                siemplify.LOGGER.error(f"An error occurred when tried to fetch {detector_id}")
                siemplify.LOGGER.exception(e)
                not_found_detectors_id.append(detector_id)

        if not found_detectors:
            raise AWSGuardDutyNotFoundException(f"Invalid detector details.")

        siemplify.LOGGER.info("Done Fetching Detectors details by id")

        if not_found_detectors_id:
            not_founds_message = f"Action wasn’t able to get {[_id for _id in not_found_detectors_id]} detectors."

        # If at least one of the api calls returns a detector valid details
        if csv_list and json_results:
            siemplify.LOGGER.info("Processing Detectors")
            founds_ids = json_results.keys()
            json_results = convert_dict_to_json_result_dict(json_results)
            siemplify.result.add_data_table("Detectors Details", construct_csv(csv_list))
            founds_message = f"Successfully retrieved information about {[detectorId for detectorId in founds_ids]}"
            result_value = "true"
            output_message = f"{founds_message} \n {not_founds_message}"
            siemplify.LOGGER.info("Done Processing Detectors")

        # If none of the api calls returns a valid detector details
        else:
            siemplify.LOGGER.info("No detectors were found according to the ids given")
            result_value = "false"
            output_message = not_founds_message

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:  # action failed
        siemplify.LOGGER.error(f"Error executing action '{SCRIPT_NAME}'. Reason: {error}")
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
