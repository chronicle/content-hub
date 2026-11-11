from __future__ import annotations

from typing import Tuple, Any
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from TIPCommon.smp_time import is_approaching_timeout

from intezer.core.constants import (
    GET_FILE_REPORT_SCRIPT_NAME,
    INTEGRATION_NAME,
    API_URL,
    FileAnalysisInput,
    FileAnalysisStatus,
    FileAnalysisType,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
    FILE_HASH,
)
from intezer.core.exceptions import (
    IntezerManagerError,
    IntezerNotFoundError,
    IntezerTimeoutException,
    IntezerUnexpectedStatusException,
)
from intezer.core.IntezerManager import IntezerManager
from intezer.core.UtilsManager import remove_duplicate_dict_from_list, remove_pending_items


def build_result_data(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    result_data: dict,
    private_only: bool = False,
) -> dict:
    """Build the context data for an async action

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of the action.
        result_data: Context data between each iteration of the action.
        private_only: A flag to filter results by private analyses only.
    Returns:
        result_data: Context data between each iteration of the action
    """
    params = {}
    base_summary = {}

    pending_items = list(result_data["pending_items"].keys())

    for analysis_item in pending_items:
        if (
            siemplify.execution_deadline_unix_time_ms - action_start_time
            < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
            or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT)
        ):
            raise IntezerTimeoutException(
                "Action ran into a timeout during execution. "
                f"Pending items {result_data['pending_items'].keys()}"
            )
        siemplify.LOGGER.info(f"Started processing item: {analysis_item}")

        if result_data["analysis_type"] == FileAnalysisType.ANALYSIS_ID.value:
            params[FileAnalysisInput.ANALYSIS_ID.value] = analysis_item
            base_summary = {"analysis_id": analysis_item, "analysis_type": "file"}
        elif result_data["analysis_type"] == FileAnalysisType.FILE_HASH.value:
            params[FileAnalysisInput.FILE_HASH.value] = analysis_item
            params[FileAnalysisInput.PRIVATE_ONLY.value] = private_only
            base_summary = {"analysis_id": None, "analysis_type": "file"}

        try:
            file_analysis = manager.get_file_report(**params)
            if file_analysis:
                if file_analysis.status == FileAnalysisStatus.SUCCESS.value:
                    siemplify.LOGGER.info(
                        f"Successfully analysed the item: {analysis_item}"
                    )
                    result_details = {
                        **base_summary,
                        "analysis_status": file_analysis.status,
                        "analysis_content": file_analysis.analysis,
                    }
                    result_data["json_results"].append(result_details)
                    result_data["json_results"] = remove_pending_items(
                        data=result_data["json_results"],
                        in_progress_status=FileAnalysisStatus.IN_PROGRESS.value,
                        queued_status=FileAnalysisStatus.QUEUED.value,
                        status_key="analysis_status",
                    )
                    result_data["completed"].append(analysis_item)
                    del result_data["pending_items"][analysis_item]
                elif file_analysis.status in [
                    FileAnalysisStatus.IN_PROGRESS.value,
                    FileAnalysisStatus.QUEUED.value,
                ]:
                    result_details = {
                        **base_summary,
                        "analysis_status": file_analysis.status,
                    }
                    result_data["json_results"].append(result_details)
                    result_data["json_results"] = remove_duplicate_dict_from_list(
                        result_data["json_results"]
                    )
                    result_data["pending_items"][analysis_item] = file_analysis.status
                elif file_analysis.status in [
                    FileAnalysisStatus.FAILED.value,
                    FileAnalysisStatus.EXPIRED.value,
                ]:
                    result_data["failed"].append(analysis_item)
                    del result_data["pending_items"][analysis_item]
                else:
                    raise IntezerUnexpectedStatusException(
                        f"Unexpected status: {file_analysis.status}"
                    )
            else:
                raise IntezerNotFoundError(f"No result found for item: {analysis_item}")

        except IntezerManagerError as e:
            result_data["failed"].append(analysis_item)
            siemplify.LOGGER.error(
                f"An error occurred on item: {analysis_item} Reason: {e}"
            )
            del result_data["pending_items"][analysis_item]

        siemplify.LOGGER.info(f"Finished processing item: {analysis_item}")
    return result_data


def start_operation(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    analysis_id: str = None,
    file_hash: str = None,
    private_only: bool = False,
    wait_for_completion: bool = False,
) -> Tuple[str, Any, int]:
    """To start the operation for an analysis.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of the action.
        analysis_id: The analysis ID of the file to retrieve analysis for.
        file_hash: The hash of the file to retrieve analysis for.
        private_only: A flag to filter results by private analyses only.
        wait_for_completion: Flag to wait for operation to finish.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    result_data = {
        "analysis_type": None,
        "pending_items": {},
        "completed": [],
        "failed": [],
        "json_results": [],
    }
    if not file_hash:
        result_data["analysis_type"] = FileAnalysisType.ANALYSIS_ID.value
        analysis_ids = list(set(convert_comma_separated_to_list(analysis_id)))
        for item in analysis_ids:
            result_data["pending_items"][item] = FileAnalysisStatus.PENDING.value
    else:
        result_data["analysis_type"] = FileAnalysisType.FILE_HASH.value
        file_hash_from_entity = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type == FILE_HASH
        ]
        file_hashes = list(
            set(file_hash_from_entity + convert_comma_separated_to_list(file_hash))
        )

        for item in file_hashes:
            result_data["pending_items"][item] = FileAnalysisStatus.PENDING.value

    output_message, result_value, status = query_operation_status(
        siemplify,
        manager,
        action_start_time,
        result_data,
        private_only,
        wait_for_completion,
    )
    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    result_data: dict,
    private_only: bool = None,
    wait_for_completion: bool = False,
) -> Tuple[str, Any, int]:
    """Query the running operation of the action.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of an action
        result_data: Context data between each iteration of the action.
        private_only: A flag to filter results by private analyses only.
        wait_for_completion: Flag to wait for operation to finish.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """

    result_data = build_result_data(
        siemplify=siemplify,
        manager=manager,
        action_start_time=action_start_time,
        result_data=result_data,
        private_only=private_only,
    )

    if not wait_for_completion:
        output_message, result_value, status = finish_operation(
            siemplify, result_data=result_data
        )
        return output_message, result_value, status

    if result_data["pending_items"]:
        pending_ids = convert_list_to_comma_string(
            list(result_data["pending_items"].keys())
        )
        output_message = f"Waiting for results for the following items: {pending_ids}"
        result_value = json.dumps(result_data)
        status = EXECUTION_STATE_INPROGRESS
        return output_message, result_value, status

    output_message, result_value, status = finish_operation(
        siemplify, result_data=result_data
    )
    return output_message, result_value, status


def finish_operation(
    siemplify: SiemplifyAction, result_data: dict
) -> Tuple[str, bool, int]:
    """Finish the operation of an action.

    Args:
        siemplify: SiemplifyAction object.
        result_data: Context data between each iteration of the action.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    if result_data["completed"]:
        output_message = (
            "Successfully fetched the file analysis for the following items: "
            f"{convert_list_to_comma_string(result_data['completed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    if result_data["pending_items"]:
        pending_ids = convert_list_to_comma_string(
            list(result_data["pending_items"].keys())
        )
        output_message += (
            f"Waiting for results for the following items: {pending_ids}\n"
        )

    if result_data["failed"]:
        output_message += (
            "Action wasn't able to fetch the file analysis "
            f"for the following items: "
            f"{convert_list_to_comma_string(result_data['failed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    siemplify.result.add_result_json(result_data.get("json_results", []))

    if not result_data["completed"] and not result_data["pending_items"]:
        output_message = "No file analysis were found for the provided items"
        result_value = False

    return output_message, result_value, status


@output_handler
def main(first_run) -> None:
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = GET_FILE_REPORT_SCRIPT_NAME

    siemplify.LOGGER.info("------------------ Param Init --------------------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_URL,
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API key",
        is_mandatory=True,
        print_value=False,
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

    # Action Parameters
    analysis_id = extract_action_param(
        siemplify, param_name="Analysis ID", is_mandatory=False, print_value=True
    )
    file_hash = extract_action_param(
        siemplify, param_name="File Hash", is_mandatory=False, print_value=True
    )
    private_only = extract_action_param(
        siemplify,
        param_name="Private Only",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    wait_for_completion = extract_action_param(
        siemplify,
        param_name="Wait For Completion",
        print_value=True,
        input_type=bool,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started ------------------------")

    try:
        if not analysis_id and not file_hash:
            raise IntezerNotFoundError("Must provide either analysis id or file hash")

        manager = IntezerManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                action_start_time=action_start_time,
                analysis_id=analysis_id,
                file_hash=file_hash,
                private_only=private_only,
                wait_for_completion=wait_for_completion,
            )
        else:
            result_data = json.loads(
                extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data=result_data,
                private_only=private_only,
                wait_for_completion=wait_for_completion,
            )

    except IntezerManagerError as e:
        output_message = (
            f"Error executing action {GET_FILE_REPORT_SCRIPT_NAME}. Reason: {e}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
