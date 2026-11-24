from __future__ import annotations
import sys
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from sentinel_one_v2.core.constants import DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from sentinel_one_v2.core.SentinelOneV2Manager import (
    DEEP_VISIBILITY_QUERY_FINISHED,
    DEEP_VISIBILITY_QUERY_RUNNING,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    GET_DEEP_VISIBILITY_QUERY_RESULT_SCRIPT_NAME,
    SENTINEL_ONE_EVENTS_TABLE_NAME,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory, API_VERSION_2_0


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DEEP_VISIBILITY_QUERY_RESULT_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
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

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    query_id = extract_action_param(
        siemplify, param_name="Query ID", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        print_value=True,
        input_type=int,
        default_value=DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT,
    )
    limit = limit if limit > 0 else DEEP_VISIBILITY_QUERY_EVENTS_DEFAULT_LIMIT

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        manager = SentinelOneV2ManagerFactory(API_VERSION_2_0).get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        siemplify.LOGGER.info(f"Getting query status for query id {query_id}")
        query_status = manager.get_deep_visibility_query_status(query_id=query_id)
        siemplify.LOGGER.info(f"Successfully got query status {query_status}")

        if query_status == DEEP_VISIBILITY_QUERY_FINISHED:
            siemplify.LOGGER.info(f"Fetching events for query id {query_id}")
            events = manager.get_deep_visibility_query_events(
                query_id=query_id, limit=limit
            )

            if events:
                siemplify.result.add_data_table(
                    SENTINEL_ONE_EVENTS_TABLE_NAME,
                    construct_csv([event.as_csv() for event in events]),
                )
                siemplify.result.add_result_json(
                    {"res_events": [event.to_base_json() for event in events]}
                )
                output_message = f"Successfully found events for query: {query_id}"
            else:
                result_value = False
                siemplify.result.add_result_json({"res_events": []})
                output_message = "No events were found"
        elif query_status == DEEP_VISIBILITY_QUERY_RUNNING:
            status = EXECUTION_STATE_INPROGRESS
            output_message = (
                f"Received query status {query_status}. Will check again later..."
            )
        else:
            raise Exception(
                f"status of the query - {query_status}. Please run action 'Initialize Deep Visibility Query' again."
            )

    except Exception as e:
        output_message = f"Error executing action '{GET_DEEP_VISIBILITY_QUERY_RESULT_SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
