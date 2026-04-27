from __future__ import annotations
import sys
import json

from typing import Any

from ..core.McAfeeESMManager import McAfeeESMManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    is_approaching_timeout,
)

from ..core.constants import (
    SEND_ADVANCED_QUERY_TO_ESM_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    DEFAULT_TIMEOUT,
)

SCRIPT_NAME = "McAfeeESM - Send Advanced Query To ESM"
INTEGRATION_NAME = "McAfeeESM"

QUERY_RESULTS_TABLE_NAME = "Query Results"


@output_handler
def main(is_first_run: bool) -> None:
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        remove_whitespaces=False,
        is_mandatory=True,
    )
    product_version = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Product Version",
        is_mandatory=True,
        print_value=True,
    )
    use_aes_encryption = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use AES Encryption",
        input_type=bool,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    query_payload = extract_action_param(
        siemplify, param_name="Query Payload", is_mandatory=True
    )

    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = McAfeeESMManager(
            api_root=api_root,
            username=username,
            password=password,
            product_version=product_version,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            siemplify_scope=siemplify,
            use_aes_encryption=use_aes_encryption,
        )
        if is_first_run:
            query = json.loads(query_payload)
            limit = query.get("limit", 200)
            if limit > 200:
                query["limit"] = 200  # set max limit to 200
            output_message, result_value, status = create_query(
                action_start_time=action_start_time,
                siemplify=siemplify,
                manager=manager,
                query=query,
            )
        else:
            output_message, result_value, status = execute_query(
                action_start_time=action_start_time,
                siemplify=siemplify,
                manager=manager,
                query_id=additional_data.get("query_id"),
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SEND_ADVANCED_QUERY_TO_ESM_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {SEND_ADVANCED_QUERY_TO_ESM_SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


def fetch_ready_results(siemplify, results: "AdvancedQueryResult") -> Any:
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    if results:
        json_results = [result.to_json() for result in results]
        output_message = f"Successfully retrieved data for the provided query in {INTEGRATION_DISPLAY_NAME}."
        siemplify.result.add_data_table(
            QUERY_RESULTS_TABLE_NAME,
            construct_csv([result.to_table() for result in results]),
        )
        siemplify.result.add_result_json(json_results)
    else:
        output_message = (
            f"No data was found for the provided query in {INTEGRATION_DISPLAY_NAME}."
        )
    return output_message, result_value, status


def create_query(
    action_start_time: Any, siemplify: Any, manager: "McAfeeESMManager", query: str
) -> Any:
    """
    Function creates query on McAfeeESM
    Args:
        siemplify: Siemplify instance
        manager: McAfeeESMManager
        query: query
    Returns:
        Output message, result_value, status
    """
    query_id = manager.create_advanced_query(query=query)
    # can happen when query created and run previously:
    if isinstance(query_id, list):
        return fetch_ready_results(siemplify, query_id)
    return execute_query(action_start_time, siemplify, manager, query_id=query_id)


def execute_query(
    action_start_time, siemplify: Any, manager: "McAfeeESMManager", query_id: str
):
    """
    Function executes query with provided ID on McAfeeESM
    Args:
        action_start_time: Action Start Time
        siemplify: Siemplify instance
        manager: McAfeeESMManager
        query_id: Query ID
    Returns:
        Output message, result_value, status
    """
    if (
        siemplify.execution_deadline_unix_time_ms - action_start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
        or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT)
    ):
        raise Exception(
            "action initiated the query but ran into a timeout during data "
            "retrieval. Please increase the timeout in the IDE and try again."
        )
    progress = manager.get_query_status(query_id)
    if progress == "complete":
        results = manager.execute_advanced_query(query_id)
        output_message, result_value, status = fetch_ready_results(siemplify, results)
    else:
        result_value = json.dumps({"query_id": query_id})
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for the query to finish."
    return output_message, result_value, status


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
