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
from ..core.aws_guard_duty_manager import AWSGuardDutyManager
from ..core.consts import INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.exceptions import AWSGuardDutyNotFoundError
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "Get Detector Details"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    detector_ids = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)

    json_results = {}
    csv_list = []
    not_found_detectors_id = []
    found_detectors = []
    not_founds_message = ""

    siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
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

        except Exception:
            siemplify.LOGGER.exception(f"An error occurred when tried to fetch {detector_id}")
            not_found_detectors_id.append(detector_id)

    if not found_detectors:
        msg = "Invalid detector details."
        raise AWSGuardDutyNotFoundError(msg)

    siemplify.LOGGER.info("Done Fetching Detectors details by id")

    if not_found_detectors_id:
        not_founds_message = f"Action wasn't able to get {list(not_found_detectors_id)} detectors."

    # If at least one of the api calls returns a detector valid details
    if csv_list and json_results:
        siemplify.LOGGER.info("Processing Detectors")
        founds_ids = json_results.keys()
        json_results = convert_dict_to_json_result_dict(json_results)
        siemplify.result.add_data_table("Detectors Details", construct_csv(csv_list))
        founds_message = f"Successfully retrieved information about {list(founds_ids)}"
        result_value = "true"
        output_message = f"{founds_message} \n {not_founds_message}"
        siemplify.LOGGER.info("Done Processing Detectors")

    # If none of the api calls returns a valid detector details
    else:
        siemplify.LOGGER.info("No detectors were found according to the ids given")
        result_value = "false"
        output_message = not_founds_message

    siemplify.result.add_result_json(json_results)

    return result_value, output_message


@output_handler
def main() -> None:
    """Retrieve an Amazon GuardDuty detector specified by the detector ID."""
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
