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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from ..core.TrendMicroDDANExceptions import TrendMicroDDANInProgressException
from ..core.TrendMicroDDANManager import TrendMicroDDANManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SUBMIT_FILE_SCRIPT_NAME,
    LINE_BREAK,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    SAMPLE_TYPE,
)
from ..core.TrendMicroDDANParser import TrendMicroDDANParser
from ..core.UtilsManager import validate_positive_integer, get_file_sha1, get_opened_file


def start_operation(siemplify, manager, file_paths, resubmit_file):
    """
    Submit file path or check if submission already exists
    Args:
        siemplify (SiemplifyAction): SiemplifyAction object
        manager: (TrendMicroDDANManager): TrendMicroDDANManager object
        file_paths: ([str]): list of file paths
        resubmit_file: (bool): specifies if file path should be resubmitted
    Returns:
        (tuple) output_message, result, status
    """
    submitted_file_paths, duplicated_file_paths, failed_file_paths = [], [], []

    for file_path in file_paths:
        siemplify.LOGGER.info(f"\nStarted processing file path: {file_path}")
        is_submitted = None

        try:
            sha1_hash = get_file_sha1(file_path)
            file = get_opened_file(file_path)

            if not resubmit_file:
                # check if submission already exists
                is_submitted = manager.check_duplicate(sha1_hash)

                if is_submitted:
                    duplicated_file_paths.append(file_path)
                    siemplify.LOGGER.info(
                        f"Found already existing submission for {file_path}"
                    )

            if not is_submitted:
                manager.submit_sample(sha1_hash, SAMPLE_TYPE.get("file"), file)
                file.close()
                submitted_file_paths.append(file_path)
                siemplify.LOGGER.info(f"Successfully submitted file path {file_path}")

        except Exception as e:
            failed_file_paths.append(file_path)
            siemplify.LOGGER.info(f"An error occurred on file path: {file_path}")
            siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Finish processing file path: {file_path}\n")

    result = json.dumps(
        {
            "data": {},
            "in_progress": list(set(file_paths) - set(failed_file_paths)),
            "failed": failed_file_paths,
        }
    )

    status = EXECUTION_STATE_INPROGRESS
    output_message = (
        f"{f'Successfully submitted following file paths {convert_list_to_comma_string(submitted_file_paths)}{LINE_BREAK}' if submitted_file_paths else ''}"
        f"{f'Duplicates found for following file paths {convert_list_to_comma_string(duplicated_file_paths)}{LINE_BREAK}' if duplicated_file_paths else ''}"
        f"Waiting for analyzes to complete..."
    )

    return output_message, result, status


def check_progress(
    siemplify,
    manager,
    file_paths_results,
    fetch_event_log,
    fetch_suspicious_objects,
    fetch_sandbox_screenshot,
):
    """
    Check progress
    Args:
        siemplify (SiemplifyAction): SiemplifyAction object
        manager: (TrendMicroDDANManager): TrendMicroDDANManager object
        file_paths_results: (dist): dict of file paths results
        fetch_event_log: (bool): specifies if event logs should be fetched
        fetch_suspicious_objects: (bool): specifies if suspicious objects should be fetched
        fetch_sandbox_screenshot: (bool): specifies if sandbox screenshot should be fetched
    Returns:
        (tuple) output_message, result, status
    """
    in_progress_file_paths = []

    for file_path in file_paths_results.get("in_progress", []):
        siemplify.LOGGER.info(f"\nStarted processing file path: {file_path}")

        try:
            sha1_hash = get_file_sha1(file_path)
            report = manager.get_report(sha1_hash)
            file_paths_results.get("data")[file_path] = report.to_json()
            siemplify.LOGGER.info(f"Successfully got report for file path: {file_path}")

        except TrendMicroDDANInProgressException:
            in_progress_file_paths.append(file_path)
            siemplify.LOGGER.info(f"Analyzes not completed for file path: {file_path}")

        except Exception as e:
            file_paths_results.get("failed").append(file_path)
            siemplify.LOGGER.info(f"An error occurred on file path: {file_path}")
            siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Finish processing file path: {file_path}\n")

    if (
        not in_progress_file_paths
        and not fetch_event_log
        and not fetch_suspicious_objects
        and not fetch_sandbox_screenshot
    ):
        return prepare_outputs(
            siemplify,
            {
                "data": {
                    key: TrendMicroDDANParser.build_report_object(raw_data=value)
                    for key, value in file_paths_results.get("data").items()
                },
                "in_progress": in_progress_file_paths,
                "failed": file_paths_results.get("failed"),
            },
        )
    else:
        result = json.dumps(
            {
                "data": file_paths_results.get("data"),
                "in_progress": in_progress_file_paths,
                "failed": file_paths_results.get("failed"),
            }
        )
        output_message = "Waiting for analyzes to complete..."
        status = EXECUTION_STATE_INPROGRESS

    return output_message, result, status


def get_additional_results(
    siemplify,
    manager,
    file_paths_results,
    fetch_event_log,
    fetch_suspicious_objects,
    fetch_sandbox_screenshot,
    event_logs_limit,
    suspicious_objects_limit,
):
    """
    Get additional results
    Args:
        siemplify (SiemplifyAction): SiemplifyAction object
        manager: (TrendMicroDDANManager): TrendMicroDDANManager object
        file_paths_results: (dict): dict of file paths results
        fetch_event_log: (bool): specifies if event logs should be fetched
        fetch_suspicious_objects: (bool): specifies if suspicious objects should be fetched
        fetch_sandbox_screenshot: (bool): specifies if sandbox screenshot should be fetched
        event_logs_limit: (int): limit for event logs
        suspicious_objects_limit: (int): limit for suspicious objects
    Returns:
        (tuple) output_message, result, status
    """
    for key, value in file_paths_results.get("data", {}).items():
        report = TrendMicroDDANParser.build_report_object(raw_data=value)
        siemplify.LOGGER.info(f"\nStarted processing file path: {key}")

        try:
            sha1_hash = get_file_sha1(key)
            if fetch_event_log:
                report.event_logs = manager.get_event_logs(sha1_hash, event_logs_limit)

            if fetch_suspicious_objects:
                try:
                    report.suspicious_objects = manager.get_suspicious_objects(
                        sha1_hash, suspicious_objects_limit
                    )
                except Exception as e:
                    siemplify.LOGGER.info(
                        f"An error occurred while fetching suspicious objects for file path: {key}"
                    )
                    siemplify.LOGGER.exception(e)

            if fetch_sandbox_screenshot:
                try:
                    report.screenshot = manager.get_screenshot(sha1_hash)
                except Exception as e:
                    siemplify.LOGGER.info(
                        f"An error occurred while fetching screenshot for file path: {key}"
                    )
                    siemplify.LOGGER.exception(e)

            file_paths_results.get("data", {})[key] = report

        except Exception as e:
            file_paths_results.get("failed", []).append(key)
            siemplify.LOGGER.info(f"An error occurred on file path: {key}")
            siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Finish processing file path: {key}\n")

    return prepare_outputs(siemplify, file_paths_results)


def prepare_outputs(siemplify, file_paths_results):
    """
    Prepare outputs
    Args:
        siemplify (SiemplifyAction): SiemplifyAction object
        file_paths_results: (dict): dict of file paths results
    Returns:
        (tuple) output_message, result, status
    """
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result = True

    if file_paths_results.get("data"):
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(
                {
                    key: value.to_json()
                    for key, value in file_paths_results.get("data").items()
                }
            )
        )
        output_message += (
            f"Successfully analyzed the following paths in {INTEGRATION_DISPLAY_NAME}: "
            f"{convert_list_to_comma_string(list(file_paths_results.get('data').keys()))}\n"
        )

    if file_paths_results.get("failed"):
        output_message += (
            f"Action wasn't able to return results for the following paths in {INTEGRATION_DISPLAY_NAME}: "
            f"{convert_list_to_comma_string(file_paths_results.get('failed'))}\n"
        )

    if not file_paths_results.get("data"):
        output_message = "No results for the provided paths."
        result = False

    return output_message, result, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_FILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # action parameters
    file_paths = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=True, print_value=True
    )
    fetch_event_log = extract_action_param(
        siemplify, param_name="Fetch Event Log", input_type=bool, print_value=True
    )
    fetch_suspicious_objects = extract_action_param(
        siemplify,
        param_name="Fetch Suspicious Objects",
        input_type=bool,
        print_value=True,
    )
    fetch_sandbox_screenshot = extract_action_param(
        siemplify,
        param_name="Fetch Sandbox Screenshot",
        input_type=bool,
        print_value=True,
    )
    resubmit_file = extract_action_param(
        siemplify, param_name="Resubmit File", input_type=bool, print_value=True
    )
    event_logs_limit = extract_action_param(
        siemplify,
        param_name="Max Event Logs To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    suspicious_objects_limit = extract_action_param(
        siemplify,
        param_name="Max Suspicious Objects To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )

    additional_data = json.loads(
        extract_action_param(
            siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    file_paths = convert_comma_separated_to_list(file_paths)
    status = EXECUTION_STATE_INPROGRESS
    result = True
    output_message = ""
    manager = None
    is_registered = False

    try:
        validate_positive_integer(
            number=event_logs_limit,
            err_msg="Max Event Logs To Return parameter should be positive",
        )
        validate_positive_integer(
            number=suspicious_objects_limit,
            err_msg="Max Suspicious Objects To Return parameter should be positive",
        )

        if event_logs_limit > MAX_LIMIT:
            raise Exception(
                f"Max Event Logs To Return exceeded the maximum limit of {MAX_LIMIT}."
            )

        if suspicious_objects_limit > MAX_LIMIT:
            raise Exception(
                f"Max Suspicious Objects To Return exceeded the maximum limit of {MAX_LIMIT}."
            )

        manager = TrendMicroDDANManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        is_registered = manager.register()

        if is_first_run:
            output_message, result, status = start_operation(
                siemplify, manager, file_paths, resubmit_file
            )
        else:
            if additional_data.get("in_progress"):
                output_message, result, status = check_progress(
                    siemplify,
                    manager,
                    additional_data,
                    fetch_event_log,
                    fetch_suspicious_objects,
                    fetch_sandbox_screenshot,
                )

            else:
                output_message, result, status = get_additional_results(
                    siemplify,
                    manager,
                    additional_data,
                    fetch_event_log,
                    fetch_suspicious_objects,
                    fetch_sandbox_screenshot,
                    event_logs_limit,
                    suspicious_objects_limit,
                )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SUBMIT_FILE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {SUBMIT_FILE_SCRIPT_NAME}. Reason: {e}"
        )
    finally:
        try:
            if is_registered:
                manager.unregister()
        except Exception as e:
            siemplify.LOGGER.error(
                f"Unregistering failed performing action {SUBMIT_FILE_SCRIPT_NAME}"
            )
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
