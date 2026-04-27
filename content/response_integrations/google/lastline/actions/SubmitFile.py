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

import json
import sys
from typing import TYPE_CHECKING

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.consts import INTEGRATION_NAME, SUBMIT_FILE
from ..core.exceptions import (
    LastlineAuthenticationException,
    LastlineInvalidParamException,
    LastlineManyRequestsException,
    LastlinePermissionException,
)
from ..core.LastlineManager import LastlineManager

if TYPE_CHECKING:
    from ..core.datamodels import SubmissionTask


def start_operation(siemplify, manager, file_path: str, wait_for_report: bool):
    """If the action runs for the first time, this function will be called and will create a submission task.
    :param siemplify: {SiemplifyAction} Siemplify service
    :param manager: {LastlineManager} Lastline manager
    :param file_path: {str} The file_path of the file to analyze
    :param wait_for_report: {bool} Decide if should wait to submission reports or not
    :return: (output_message, result_value, status)
    """
    status = EXECUTION_STATE_INPROGRESS

    siemplify.LOGGER.info(f"Submitting file to {INTEGRATION_NAME}: {file_path}")
    submission_task = manager.submit_file(file_path=file_path)
    siemplify.LOGGER.info(f"Successfully submitted file: {file_path}")

    if (
        wait_for_report and submission_task.data.raw_data.get("reports")
    ) or not wait_for_report:
        return finish_operation(
            siemplify=siemplify,
            submission_task=submission_task,
            file_path=file_path,
            wait_for_report=wait_for_report,
        )

    result_value = json.dumps(
        {"task_uuid": submission_task.data.task_uuid, "file_path": file_path}
    )
    output_message = f"Waiting for the analysis results for the file: {file_path}"

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, task_uuid: str, file_path: str, wait_for_report: bool
):
    """Starting from the second time that the action will run, this function will be called and check if the submission
    task completed create a submission task.
    :param siemplify: {SiemplifyAction} Siemplify service
    :param manager: {LastlineManager} Lastline manager
    :param task_uuid: {str} Task identifier
    :param file_path: {str} The file path of the file to analyze
    :param wait_for_report: {bool} Decide if should wait to submission reports or not
    :return: (output_message, result_value, status)
    """
    siemplify.LOGGER.info("Checking the status of analysis task.")
    submission_task = manager.get_progress(uuid=task_uuid)
    siemplify.LOGGER.info("Successfully checked  the status of analysis task.")

    if submission_task.data.completed:
        completed_submission_task = manager.get_result(uuid=task_uuid)
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            submission_task=completed_submission_task,
            file_path=file_path,
            wait_for_report=wait_for_report,
        )

    else:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps({"task_uuid": task_uuid, "file_path": file_path})
        output_message = f"Waiting for the analysis results for the file: {file_path}"

    return output_message, result_value, status


def finish_operation(
    siemplify, submission_task: SubmissionTask, file_path: str, wait_for_report: bool
):
    """Finalizing results
    :param siemplify: {SiemplifyAction} Siemplify service
    :param submission_task: {SubmissionTask} Submission Task data model
    :param file_path: {str} file path of the analyzed file
    :param wait_for_report: {bool} Decide if should wait to submission reports or not
    :return: (output_message, result_value, status)
    """
    siemplify.LOGGER.info(f"Finalizing submission results for: {file_path}")

    # JSON
    json_results = submission_task.as_json()
    siemplify.result.add_result_json(json_results)

    # CSV output message and attachment
    if wait_for_report:
        # CSV
        csv_table = [submission_task.as_csv()]
        csv_table_name = f"{file_path} Analysis Results"
        siemplify.result.add_data_table(csv_table_name, construct_csv(csv_table))

        output_message = (
            f"Successfully fetched the analysis results for the file {file_path}"
        )

    else:
        output_message = f"Successfully created analysis task for the file {file_path}"

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SUBMIT_FILE}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
        print_value=True,
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
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )

    file_path = extract_action_param(
        siemplify, param_name="File Path", is_mandatory=False, print_value=True
    )

    wait_for_report = extract_action_param(
        siemplify,
        param_name="Wait for the report?",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    mode = "Main" if is_first_run else {SUBMIT_FILE}
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = LastlineManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                file_path=file_path,
                wait_for_report=wait_for_report,
            )

        else:
            task_uuid = json.loads(
                siemplify.extract_action_param("additional_data")
            ).get("task_uuid")
            file_path = json.loads(
                siemplify.extract_action_param("additional_data")
            ).get("file_path")
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                task_uuid=task_uuid,
                file_path=file_path,
                wait_for_report=wait_for_report,
            )

    except FileNotFoundError as error:
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Failed to create analysis task because the provided file path {file_path} is incorrect."
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(error)

    except LastlineInvalidParamException as error:
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Failed to create analysis task because the provided file path {file_path} is incorrect."
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(error)

    except (LastlinePermissionException, LastlineManyRequestsException) as error:
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Failed to create analysis task for the provided file path {file_path}. Error is: {error}"
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(error)

    except LastlineAuthenticationException as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} service with the provided account. Please "
            f"check your configuration. Error is: {error}"
        )
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to create analysis task for the provided file path"
            f"{(' ' + file_path) if file_path else ''}. Error is: {error}"
        )
        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
