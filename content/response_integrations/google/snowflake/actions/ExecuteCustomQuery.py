from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.SnowflakeManager import SnowflakeManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    EXECUTE_CUSTOM_QUERY_SCRIPT_NAME,
    EXECUTION_FINISHED,
)

TABLE_NAME = "Results"


def start_query(siemplify, manager, database, schema, limit, original_query):
    """
    Start query
    :param siemplify: SiemplifyAction object
    :param manager: Snowflake Manager object
    :param database: {str} Database to use
    :param schema: {str} Schema to use
    :param limit: {int} Limit for results
    :param original_query: {str} Original Query
    :return: {tuple} output messages, result value, status
    """
    query_id = manager.submit_query(
        query=original_query, database=database, schema=schema, limit=limit
    )
    # get query progress right after query started
    return check_query_progress_and_get_results(
        siemplify, manager, query_id, original_query
    )


def check_query_progress_and_get_results(siemplify, manager, query_id, original_query):
    """
    Check query progress and get results
    :param siemplify: SiemplifyAction object
    :param manager: Snowflake Manager object
    :param original_query: {str} Original Query
    :param query_id: {str} query id
    :return: {tuple} output messages, result value, status
    """
    query_results, query_progress = manager.get_data(query_id)
    result_value = True

    if query_progress == EXECUTION_FINISHED:

        if query_results:
            siemplify.result.add_data_table(TABLE_NAME, construct_csv(query_results))
            siemplify.result.add_result_json(query_results)

            status = EXECUTION_STATE_COMPLETED
            output_message = f'Successfully executed query "{original_query}" in {INTEGRATION_DISPLAY_NAME}.'
        else:
            status = EXECUTION_STATE_COMPLETED
            output_message = f'No results were found for the query "{original_query}" in {INTEGRATION_DISPLAY_NAME}.'
    else:
        result_value = json.dumps({"query_id": query_id})
        status = EXECUTION_STATE_INPROGRESS
        output_message = f"Submitted Query. Waiting for results."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    account = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account",
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
    private_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Private Key",
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

    # Action parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    database = extract_action_param(
        siemplify, param_name="Database", is_mandatory=True, print_value=True
    )
    schema = extract_action_param(
        siemplify, param_name="Schema", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Results To Return": {limit}. Positive number '
                f"should be provided."
            )

        manager = SnowflakeManager(
            api_root=api_root,
            account=account,
            username=username,
            private_key_file=private_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_query(
                siemplify, manager, database, schema, limit, query
            )
        else:
            output_message, result_value, status = check_query_progress_and_get_results(
                siemplify, manager, additional_data.get("query_id"), query
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_CUSTOM_QUERY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {EXECUTE_CUSTOM_QUERY_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
