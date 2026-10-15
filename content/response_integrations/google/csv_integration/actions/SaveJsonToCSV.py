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

from csv_integration.core.constants import SAVE_JSON_TO_CSV_SCRIPT_NAME

from csv_integration.core.CSVManager import CSVManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SAVE_JSON_TO_CSV_SCRIPT_NAME
    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    json_string = extract_action_param(
        siemplify, param_name="JSON Object", is_mandatory=True
    )
    overwrite_flag = extract_action_param(
        siemplify,
        param_name="Overwrite",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    file_path = extract_action_param(
        siemplify, param_name="File Path", print_value=True, is_mandatory=True
    )
    vertical_unpacking_flag = extract_action_param(
        siemplify,
        param_name="Advanced Nested JSON Handling",
        print_value=True,
        input_type=bool,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        manager = CSVManager(siemplify)
        siemplify.LOGGER.info("Processing JSON object to CSV file.")
        json_result = manager.save_json_to_csv(
            json_string=json_string,
            file_path=file_path,
            overwrite=overwrite_flag,
            vertical_unpacking=vertical_unpacking_flag,
        )
        siemplify.LOGGER.info("JSON object to CSV file conversion completed.")
        siemplify.result.add_result_json(json_result)
        output_message = (
            "Successfully transformed the JSON object and saved it to the "
            "provided file path."
        )

    except Exception as error:
        output_message = (
            f"Error executing action {SAVE_JSON_TO_CSV_SCRIPT_NAME}. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
