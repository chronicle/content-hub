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
from ..core.consts import INTEGRATION_NAME
from ..core.datamodels import FILE_FORMATS, TISet
from ..core.utils import AWSGuardDutyConfig, extract_integration_params

SCRIPT_NAME = "Create Threat Intelligence Set"


def _run_action(siemplify: SiemplifyAction, config: AWSGuardDutyConfig) -> tuple[str, str]:

    detector_id = extract_action_param(siemplify, param_name="Detector ID", is_mandatory=True, print_value=True)
    name = extract_action_param(siemplify, param_name="Name", is_mandatory=True, print_value=True)
    file_format = extract_action_param(siemplify, param_name="File Format", is_mandatory=True, print_value=True)
    file_location = extract_action_param(siemplify, param_name="File Location", is_mandatory=True, print_value=True)
    activate = extract_action_param(
        siemplify,
        param_name="Active",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    tags = extract_action_param(siemplify, param_name="Tags", is_mandatory=False, print_value=True)

    file_format = FILE_FORMATS[file_format]

    json_results = {}

    tags = utils.load_kv_csv_to_dict(tags, "Tags") if tags else {}

    siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
    manager = AWSGuardDutyManager(config=config, siemplify_logger=siemplify.LOGGER)
    manager.test_connectivity()  # this validates the credentials
    siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

    siemplify.LOGGER.info(f"Creating Threat Intelligence set {name}.")
    ti_set = TISet(
        raw_data={
            "Name": name,
            "Format": file_format,
            "Location": file_location,
            "Tags": tags,
        }
    )
    threat_intel_set_id = manager.create_threat_intel_set(
        detector_id=detector_id,
        ti_set=ti_set,
        activate=activate,
    )
    siemplify.LOGGER.info(f"Successfully created the Threat Intelligence Set {threat_intel_set_id}.")
    json_results["ThreatIntelSetId"] = threat_intel_set_id

    output_message = f"Successfully created the Threat Intelligence Set '{name}' in AWS GuardDuty."
    result_value = "true"
    siemplify.result.add_result_json(json_results)

    return result_value, output_message


@output_handler
def main() -> None:
    """Create a threat intelligence set in AWS GuardDuty."""
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
