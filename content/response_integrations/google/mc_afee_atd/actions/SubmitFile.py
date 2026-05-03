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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeATDManager import McAfeeATDManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME, SUBMIT_FILE_SCRIPT_NAME
import json


TABLE_NAME = "Result Task IDs"
ZIP_FILE = -1


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_FILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    file_paths = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=True, print_value=True
    )
    analyzer_profile_id = extract_action_param(
        siemplify, param_name="Analyzer Profile ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Split string to list.
    file_paths_list = (
        [item.strip() for item in file_paths.split(",")] if file_paths else []
    )

    status = EXECUTION_STATE_COMPLETED
    results = []
    task_ids = []
    json_results = {}

    try:
        atd_manager = McAfeeATDManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        for file_path in file_paths_list:
            try:
                task_id = atd_manager.submit_file(
                    file_path.strip(), analyzer_profile_id
                )
                if task_id != ZIP_FILE:
                    json_results[file_path] = task_id
                    task_ids.append(str(task_id))
                results.append({"File": file_path, "Task ID": task_id})
            except Exception as err:
                error_message = f'Error submitting file "{file_path}", Error: {err}'
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(err)

        # Provide logout from McAfee ATD.
        atd_manager.logout()
        siemplify.result.add_result_json(json.dumps(json_results))

        if results:
            result_value = ",".join(task_ids)
            siemplify.result.add_data_table(TABLE_NAME, construct_csv(results))
            output_message = "Files was submitted. Note: taskId -1 is not supported"
        else:
            result_value = False
            output_message = "No file was submitted."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SUBMIT_FILE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{SUBMIT_FILE_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
