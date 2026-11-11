from __future__ import annotations

from typing import Tuple, Any
import copy
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
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.smp_time import is_approaching_timeout

from intezer.core.exceptions import (
    IntezerManagerError,
    IntezerTimeoutException,
    IntezerUnexpectedStatusException,
    IntezerNotFoundError,
)
from intezer.core.IntezerManager import IntezerManager
from intezer.core.UtilsManager import remove_duplicate_dict_from_list, remove_pending_items
from intezer.core.constants import (
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
    IndexStatusCode,
    IndexType,
    INTEGRATION_NAME,
    INDEX_FILE_SCRIPT_NAME,
    API_URL,
    FILE_HASH,
)


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
    pending_items = copy.deepcopy(result_data["pending_items"])
    for file_hash, index_id in pending_items.items():
        if (
            siemplify.execution_deadline_unix_time_ms - action_start_time
            < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
            or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT)
        ):
            raise IntezerTimeoutException(
                "Action ran into a timeout during execution. "
                f"Pending file hash {result_data['pending_items'].keys()}"
            )
        siemplify.LOGGER.info(f"Started processing file hash: {file_hash}")

        try:
            response = None
            if index_id:
                response = manager.index_file_hash_by_id(index_id=index_id)
            if response:
                if response.status == IndexStatusCode.SUCCESS.value:
                    siemplify.LOGGER.info(
                        f"Successfully indexed the file hash: {file_hash}"
                    )
                    result_data["json_results"].append(
                        {"index_id": index_id, "status": response.status}
                    )
                    result_data["json_results"] = remove_pending_items(
                        data=result_data["json_results"],
                        in_progress_status=IndexStatusCode.IN_PROGRESS.value,
                        queued_status=IndexStatusCode.QUEUED.value,
                        status_key="status",
                    )
                    result_data["completed"].append(file_hash)
                    del result_data["pending_items"][file_hash]
                elif response.status in [
                    IndexStatusCode.IN_PROGRESS.value,
                    IndexStatusCode.QUEUED.value,
                ]:
                    result_data["json_results"].append(
                        {"index_id": index_id, "status": response.status}
                    )
                    result_data["json_results"] = remove_duplicate_dict_from_list(
                        result_data["json_results"]
                    )
                elif (
                    response.status in [IndexStatusCode.FAILED.value]
                    or index_id is None
                ):
                    result_data["failed"].append(file_hash)
                    del result_data["pending_items"][file_hash]
                else:
                    raise IntezerUnexpectedStatusException(
                        f"Unexpected status: {response.status}"
                    )
            else:
                raise IntezerNotFoundError(
                    f"No result found for file hash: {file_hash}"
                )

        except IntezerManagerError as e:
            result_data["failed"].append(file_hash)
            siemplify.LOGGER.error(
                f"An error occurred on file hash: {file_hash} Reason: {e}"
            )
            del result_data["pending_items"][file_hash]
        siemplify.LOGGER.info(f"Finished processing file hash: {file_hash}")
    return result_data


def start_operation(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    sha256: list,
    index_as: IndexType,
    family_name: str,
) -> Tuple[str, Any, int]:
    """To start the operation for an analysis.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of the action.
        sha256: The sha256 of the file to index.
        index_as: The type of the index trusted or malicious.
        family_name: The family name to index as
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

    for item in sha256:
        response = manager.get_index_id_from_file_hash(
            index_as=index_as, sha256=item, family_name=family_name
        )
        if response:
            result_data["pending_items"][item] = response.id
        else:
            result_data["pending_items"][item] = None

    output_message, result_value, status = query_operation_status(
        siemplify=siemplify,
        manager=manager,
        action_start_time=action_start_time,
        result_data=result_data,
    )
    return output_message, result_value, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: IntezerManager,
    action_start_time: int,
    result_data: dict,
) -> Tuple[str, Any, int]:
    """Query the running operation of the action.

    Args:
        siemplify: SiemplifyAction object.
        manager: IntezerManager object.
        action_start_time: Start time of an action
        result_data: Context data between each iteration of the action.
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

    if result_data["pending_items"]:
        pending_sha256 = convert_list_to_comma_string(
            list(result_data["pending_items"].keys())
        )
        output_message = (
            f"Waiting for results for the following hashes: {pending_sha256}"
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
            "Successfully indexed the following file hashes: "
            f"{convert_list_to_comma_string(result_data['completed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    if result_data["failed"]:
        output_message += (
            "Action wasn't able to index the following file hashes: "
            f"{convert_list_to_comma_string(result_data['failed'])} "
            f"in {INTEGRATION_NAME}\n"
        )

    siemplify.result.add_result_json(result_data.get("json_results", {}))

    if not result_data["completed"]:
        output_message = "None of the file hash got indexed"
        result_value = False

    return output_message, result_value, status


@output_handler
def main(first_run) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = INDEX_FILE_SCRIPT_NAME
    action_start_time = unix_now()

    siemplify.LOGGER.info("----------------- Param Init ----------------")

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
        input_type=bool,
        print_value=True,
    )

    # Action Parameters
    index_as = extract_action_param(
        siemplify,
        param_name="Index As",
        print_value=True,
        is_mandatory=True,
        default_value="trusted",
    )
    sha256 = extract_action_param(
        siemplify, param_name="SHA256", print_value=True, is_mandatory=False
    )
    family_name = extract_action_param(
        siemplify, param_name="Family Name", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if index_as == IndexType.MALICIOUS and family_name is None:
            raise ValueError("Family_name is mandatory if the index type is malicious")

        sha256_from_entity = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type == FILE_HASH
        ]
        sha256 = list(set(sha256_from_entity + convert_comma_separated_to_list(sha256)))
        index_as = IndexType.from_str(index_as)

        manager = IntezerManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        if first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                sha256=sha256,
                index_as=index_as,
                family_name=family_name,
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
            )

    except IntezerManagerError as e:
        output_message = f"Error executing action {INDEX_FILE_SCRIPT_NAME}. Reason: {e}"
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
