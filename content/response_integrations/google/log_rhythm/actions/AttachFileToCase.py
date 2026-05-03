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
import sys
import json
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, ATTACH_FILE_TO_CASE_SCRIPT_NAME
from ..core.utils import (
    string_to_multi_value,
    validate_files,
    is_async_action_global_timeout_approaching,
)
from ..core.exceptions import LogRhythmManagerNotFoundError, LogRhythmManagerBadRequestError
from ..core.LogRhythmParser import LogRhythmParser


COMPLETED_STATUSES = ["completed"]
IN_PROGRESS_STATUSES = ["pending"]


def start_operation(siemplify, manager, files, case_id):
    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    note = extract_action_param(siemplify, param_name="Note", print_value=True)

    failed_files, successful_files = [], []
    result_value = {"in_progress": {}, "completed": {}, "failed": []}

    for file in files:
        try:
            file_evidence = manager.attach_file(case_id=case_id, file=file, note=note)
            if file_evidence.status in COMPLETED_STATUSES:
                # Add evidence in completed
                result_value["completed"][file] = file_evidence
                continue
            result_value["in_progress"][file] = file_evidence.id
            successful_files.append(file)
        except Exception as err:
            if isinstance(err, LogRhythmManagerNotFoundError) or isinstance(
                err, LogRhythmManagerBadRequestError
            ):
                raise
            failed_files.append(file)
            result_value["failed"].append(file)
            siemplify.LOGGER.error(
                f"An error occurred when uploading file {file}: Reason {err}"
            )
            siemplify.LOGGER.exception(err)

    if successful_files:
        result_value = json.dumps(result_value)
        output_message = (f"Successfully added the files to the case with ID "
                          f"{case_id} in {INTEGRATION_NAME}")
    else:
        output_message = (
            f"No files were added to the case with ID {case_id} in {INTEGRATION_NAME}."
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, files, result_data, case_id
):
    failed_files, completed_files = [], {}
    timeout_approaching = False

    for file, evidence_id in result_data["in_progress"].items():
        if is_async_action_global_timeout_approaching(siemplify, action_start_time):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
            break

        siemplify.LOGGER.info(
            f"Checking status for {file} with evidence id {evidence_id}."
        )

        try:
            file_evidence = manager.get_evidence(
                case_id=case_id, evidence_id=evidence_id
            )
            if file_evidence.status in IN_PROGRESS_STATUSES:
                continue

            completed_files[file] = file_evidence.raw_data
        except Exception as err:
            failed_files.append(file)
            result_data["failed"].append(file)
            siemplify.LOGGER.error(
                f"An error occurred when getting data about evidence {evidence_id}"
            )
            siemplify.LOGGER.exception(err)

    for key in completed_files.keys():
        result_data["in_progress"].pop(key)
    # Update completed files with completed_files dict including json_result
    result_data["completed"].update(completed_files)

    for file in failed_files:
        if file in result_data["in_progress"].keys():
            result_data["in_progress"].pop(file)

    if result_data["in_progress"] and not timeout_approaching:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = (
            f"Waiting for the following files to be uploaded: "
            f"{', '.join(result_data['in_progress'].keys())}"
        )
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            files=files,
            case_id=case_id,
            result_data=result_data,
            timeout_approaching=timeout_approaching,
        )

    return output_message, result_value, status


def finish_operation(siemplify, files, case_id, result_data, timeout_approaching):
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    failed_files = result_data["failed"]
    not_finished, successful_files, json_result = [], [], []
    parser = LogRhythmParser()

    for file in files:
        if file in result_data["completed"].keys():
            case_evidence = parser.build_case_evidence_obj(
                result_data["completed"][file]
            )
            json_result.append(case_evidence.as_json())
            successful_files.append(file)
        if file in result_data["in_progress"].keys():
            not_finished.append(file)

    if successful_files:
        output_message += (
            f"Successfully added the following files to the case with ID {case_id} in "
            f"{INTEGRATION_NAME}: {', '.join(successful_files)}\n"
        )
    if failed_files:
        output_message += (
            f"Action wasn't able to add the following files to the case with ID "
            f"{case_id} in {INTEGRATION_NAME}: {', '.join(failed_files)} \n"
        )
    if timeout_approaching and not_finished:
        raise Exception(
            f"action ran into a timeout. The following files are still processing: "
            f"{','.join(not_finished)}. Please increase the timeout in IDE. Note: "
            f"adding the same file will create a separate entry in {INTEGRATION_NAME}."
            + "\n"
            + output_message
        )
    elif failed_files and not successful_files:
        output_message = (
            f"No files were added to the case with ID {case_id} in {INTEGRATION_NAME}."
        )
        result_value = False

    if json_result:
        siemplify.result.add_result_json(json_result)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = ATTACH_FILE_TO_CASE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    case_id = extract_action_param(
        siemplify, param_name="Case ID", is_mandatory=True, print_value=True
    )
    files = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="File Paths", is_mandatory=True, print_value=True
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    output_message = ""

    try:
        validate_files(files)

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager=manager, files=files, case_id=case_id
            )

        if status == EXECUTION_STATE_INPROGRESS:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                files=files,
                result_data=json.loads(result_data),
                case_id=case_id,
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{ATTACH_FILE_TO_CASE_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
