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
    GET_URL_REPORT_SCRIPT_NAME,
    INTEGRATION_NAME,
    API_URL,
    UrlAnalysisStatus,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
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
) -> dict:
    """Build the context data for an async action

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of the action.
        result_data: Context data between each iteration of the action.
    Returns:
        result_data: Context data between each iteration of the action
    """
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

        base_summary = {"analysis_id": analysis_item, "analysis_type": "url"}

        try:
            url_analysis = manager.get_url_report(analysis_id=analysis_item)
            if url_analysis:
                if url_analysis.status == UrlAnalysisStatus.SUCCESS.value:
                    siemplify.LOGGER.info(
                        f"Successfully analysed the item: {analysis_item}"
                    )
                    result_details = {
                        **base_summary,
                        "analysis_status": url_analysis.status,
                        "analysis_content": {"analysis": url_analysis.to_json()},
                    }
                    result_data["json_results"].append(result_details)
                    result_data["json_results"] = remove_pending_items(
                        data=result_data["json_results"],
                        in_progress_status=UrlAnalysisStatus.IN_PROGRESS.value,
                        queued_status=UrlAnalysisStatus.QUEUED.value,
                        status_key="analysis_status",
                    )
                    result_data["completed"].append(analysis_item)
                    del result_data["pending_items"][analysis_item]
                elif url_analysis.status in [
                    UrlAnalysisStatus.IN_PROGRESS.value,
                    UrlAnalysisStatus.QUEUED.value,
                ]:
                    result_details = {
                        **base_summary,
                        "analysis_status": url_analysis.status,
                    }
                    result_data["json_results"].append(result_details)
                    result_data["json_results"] = remove_duplicate_dict_from_list(
                        result_data["json_results"]
                    )
                    result_data["pending_items"][analysis_item] = url_analysis.status
                elif url_analysis.status in [
                    UrlAnalysisStatus.FAILED.value,
                    UrlAnalysisStatus.EXPIRED.value,
                ]:
                    result_data["failed"].append(analysis_item)
                    del result_data["pending_items"][analysis_item]
                else:
                    raise IntezerUnexpectedStatusException(
                        f"Unexpected status: {url_analysis.status}"
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
    wait_for_completion: bool = False,
) -> Tuple[str, Any, int]:
    """To start the operation for an analysis.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of the action.
        analysis_id: The analysis ID of the file to retrieve analysis for.
        wait_for_completion: Flag to wait for operation to finish.
    Returns:
        output_message: Output message to be displayed on UI.
        result_value: Result of the action.
        status: Execution state of the action.
    """
    result_data = {
        "pending_items": {},
        "completed": [],
        "failed": [],
        "json_results": [],
    }

    analysis_ids = list(set(convert_comma_separated_to_list(analysis_id)))
    for item in analysis_ids:
        result_data["pending_items"][item] = UrlAnalysisStatus.PENDING.value

    output_message, result_value, status = query_operation_status(
        siemplify=siemplify,
        manager=manager,
        action_start_time=action_start_time,
        result_data=result_data,
        wait_for_completion=wait_for_completion,
    )
    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    result_data: dict,
    wait_for_completion: bool = False,
) -> Tuple[str, Any, int]:
    """Query the running operation of the action.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of an action
        result_data: Context data between each iteration of the action.
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
        output_message = (
            f"Waiting for results for the following analysis ids: {pending_ids}"
        )
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
            "Successfully fetched the url analysis for the following analysis ids: "
            f"{convert_list_to_comma_string(result_data['completed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    if result_data["pending_items"]:
        pending_ids = convert_list_to_comma_string(
            list(result_data["pending_items"].keys())
        )
        output_message += (
            f"Waiting for results for the following analysis ids: {pending_ids}\n"
        )

    if result_data["failed"]:
        output_message += (
            "Action wasn't able to fetch the url analysis "
            f"for the following analysis ids: "
            f"{convert_list_to_comma_string(result_data['failed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    siemplify.result.add_result_json(result_data.get("json_results", []))

    if not result_data["completed"] and not result_data["pending_items"]:
        output_message = "No url analysis were found for the provided analysis ids"
        result_value = False

    return output_message, result_value, status


@output_handler
def main(first_run) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_URL_REPORT_SCRIPT_NAME
    action_start_time = unix_now()

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
        default_value=False,
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action Parameters
    analysis_id = extract_action_param(
        siemplify, param_name="Analysis ID", is_mandatory=False, print_value=True
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
                wait_for_completion=wait_for_completion,
            )

    except IntezerManagerError as e:
        output_message = (
            f"Error executing action {GET_URL_REPORT_SCRIPT_NAME}. Reason: {e}"
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
