from __future__ import annotations

import sys
import json
from typing import Any, List

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    is_approaching_timeout,
)

from ..core.constants import (
    DEFAULT_TIMEOUT,
    FAILED_STATUS,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    PAYLOAD_CHUNK_SIZE,
    RATE_LIMIT_EXCEEDED,
    REJECTED_STATUS,
    RUNNING_STATUS,
    SUBMIT_URL_SCRIPT_NAME,
    SUCCESS_STATUS,
)
from ..core.TrendVisionOneExceptions import TrendVisionOneTimeoutException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import (
    get_entity_original_identifier,
    is_async_action_global_timeout_approaching,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]


def start_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    suitable_entities: List,
) -> tuple[str, bool, int]:
    """Submit URLs in first run.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        action_start_time (int): Action start time in milliseconds.
        suitable_entities (list): list of suitable entities for submitURL action.

    Returns:
        Tuple[str, bool, int]: output_message, is_success, result
    """
    result_data = {
        "result_urls": {},
        "json_results": {},
        "completed": [],
        "failed": [],
        "pending": [],
        "limit_exceeded": [],
    }

    for i in range(0, len(suitable_entities), PAYLOAD_CHUNK_SIZE):
        entity_list = suitable_entities[i : i + PAYLOAD_CHUNK_SIZE]
        entity_identifier_list = [
            get_entity_original_identifier(entity) for entity in entity_list
        ]
        siemplify.LOGGER.info(f"Started processing URLs: {entity_identifier_list}")
        current_url = None
        try:
            result, limit_exceed = manager.submit_urls(urls=entity_identifier_list)
            for entity_identifier in entity_identifier_list:
                current_url = entity_identifier
                if limit_exceed:
                    if (entity_identifier not in result_data["limit_exceeded"]) and len(
                        result
                    ) == 0:
                        result_data["limit_exceeded"].append(entity_identifier)
                for item in result:
                    if entity_identifier == item.url:
                        result_data["result_urls"][entity_identifier] = item.id
                        result_data["pending"].append(entity_identifier)
                    else:
                        if entity_identifier not in result_data["failed"]:
                            result_data["failed"].append(entity_identifier)
                        if limit_exceed:
                            if entity_identifier not in result_data["limit_exceeded"]:
                                result_data["limit_exceeded"].append(entity_identifier)
                        siemplify.LOGGER.info(
                            f"Submit URL task failed for : {entity_identifier}"
                        )
        except Exception as e:
            if RATE_LIMIT_EXCEEDED in str(e):
                result_data["limit_exceeded"].append(current_url)
            else:
                if current_url not in result_data["failed"]:
                    result_data["failed"].append(current_url)

            siemplify.LOGGER.error(f"An error occurred during submit URL {current_url}")
            siemplify.LOGGER.exception(e)
        siemplify.LOGGER.info(f"Finished processing URL: {current_url}")

    output_message, result_value, status = query_operation_status(
        siemplify, manager, result_data, action_start_time
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: dict,
    action_start_time: int,
) -> tuple[str, Any, int]:
    """Get operation details and results to update siemplify.end attributes.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (TrendVisionOneManager): TrendVisionOneManager manager object.
        result_data (Dict): Result data dictionary from submit URL.
        action_start_time (int): Action start time in milliseconds.

    Raises:
        TrendVisionOneTimeoutException: Exception to be raised if timeout
        approached.

    Returns:
        Tuple[str, Any, int]: output_message, is_success, result
    """
    results_urls = result_data["result_urls"]
    for url, task_id in results_urls.items():
        task_details = manager.get_task_detail(task_id=task_id)
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            raise TrendVisionOneTimeoutException(
                "action ran into a timeout during execution. "
                f'Pending URLs: {", ".join(result_data["pending"])}. '
                "Please increase the timeout in IDE."
            )

        json_data = task_details.to_json()
        if task_details.status == SUCCESS_STATUS:
            if url in result_data["pending"]:
                result_data["pending"].remove(url)
            task_result = manager.get_task_result(task_id=task_details.id)

            if task_result:
                siemplify.LOGGER.info(f"Successfully submitted url {url}")
                if url not in result_data["completed"]:
                    result_data["completed"].append(url)
                if url in result_data["failed"]:
                    result_data["failed"].remove(url)
                result_data["json_results"][url] = task_result
            else:
                if url not in result_data["failed"]:
                    result_data["failed"].append(url)
                if url in result_data["completed"]:
                    result_data["completed"].remove(url)
                result_data["json_results"][url] = json_data

            result_data["result_urls"][url] = None

        elif task_details.status == RUNNING_STATUS:
            result_data["json_results"][url] = json_data

        elif task_details.status in [FAILED_STATUS, REJECTED_STATUS]:
            result_data["result_urls"][url] = None
            result_data["json_results"][url] = json_data
            if url not in result_data["failed"]:
                result_data["failed"].append(url)
            if url in result_data["pending"]:
                result_data["pending"].remove(url)
            if url in result_data["completed"]:
                result_data["completed"].remove(url)

    result_data["result_urls"] = {
        k: v for k, v in result_data["result_urls"].items() if v
    }

    if result_data["pending"]:
        output_message = f'Pending url submissions: {", ".join(result_data["pending"])}'
        result_value = json.dumps(result_data)

        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    status = EXECUTION_STATE_COMPLETED
    if result_data["json_results"]:
        siemplify.LOGGER.info("adding json result")
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )
        siemplify.LOGGER.info("Json result added.")

    output_message, result_value = generate_output_message_and_result(result_data)

    return output_message, result_value, status


def generate_output_message_and_result(result_data: dict) -> tuple(str, bool):
    """Update output message and result based on the status for submit URL.

    Args:
        result_data (Dict): Result data dictionary from submit URL.

    Returns:
        Tuple(str, bool): output_message, is_success
    """
    result_value = True
    pending_urls = ", ".join(result_data["limit_exceeded"])
    limit_message = (
        "Action wasn't able to submit all URLs as the daily quota was "
        f"reached during the execution. Pending URLs: {pending_urls}"
    )

    if result_data["limit_exceeded"]:
        if not result_data["completed"]:
            result_value = False
            output_message = limit_message.format(pending_urls=pending_urls)

        if result_data["completed"]:
            result_value = True
            completed_submit_urls = ", ".join(
                [entity for entity in result_data["completed"]]
            )
            output_message = (
                "Successfully submitted the following URLs in "
                f"{INTEGRATION_DISPLAY_NAME}: {completed_submit_urls}\n"
            )
            output_message += limit_message.format(pending_urls=pending_urls)

        return output_message, result_value

    if result_data["completed"]:
        completed_submit_urls = ", ".join(
            [entity for entity in result_data["completed"]]
        )
        output_message = (
            "Successfully submitted the following URLs in "
            f"{INTEGRATION_DISPLAY_NAME}: {completed_submit_urls}\n"
        )

        if result_data["failed"]:
            result_value = False
            failed_submission = ", ".join([entity for entity in result_data["failed"]])
            output_message += (
                "Action wasn't able to submit the following "
                f"URLs in {INTEGRATION_DISPLAY_NAME}: {failed_submission}\n"
            )

        if result_data["limit_exceeded"]:
            output_message += limit_message.format(pending_urls=pending_urls)
            result_value = True

    else:
        if result_data["limit_exceeded"]:
            output_message = limit_message.format(pending_urls=pending_urls)
            result_value = False
        else:
            output_message = "No results were found for the submitted URLs."
            result_value = False

    return output_message, result_value


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SUBMIT_URL_SCRIPT_NAME

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
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

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    result_value = False
    result_data = {}
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        if not suitable_entities:
            output_message = "No suitable entities found in the scope"
        else:
            manager = TrendVisionOneManager(
                api_root=api_root,
                api_token=api_token,
                verify_ssl=verify_ssl,
                siemplify=siemplify,
            )
            manager.test_connectivity()

            if is_first_run:
                output_message, result_value, status = start_operation(
                    siemplify=siemplify,
                    manager=manager,
                    action_start_time=action_start_time,
                    suitable_entities=suitable_entities,
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
                    result_data=result_data,
                    action_start_time=action_start_time,
                )

    except TrendVisionOneTimeoutException as e:
        output_message = (
            f"Error executing action {SUBMIT_URL_SCRIPT_NAME}. " f"Reason: {e}\n"
        )
        status = EXECUTION_STATE_FAILED

        if result_data:
            json_results = result_data.get("json_results", {})
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            output_message_for_finished, _ = generate_output_message_and_result(
                result_data
            )
            output_message += output_message_for_finished

        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = (
            f"Error executing action {SUBMIT_URL_SCRIPT_NAME}. " f"Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
