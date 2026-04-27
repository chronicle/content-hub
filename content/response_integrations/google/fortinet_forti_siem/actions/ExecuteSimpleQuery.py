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
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.FortiSIEMManager import FortiSIEMManager
from ..core.UtilsManager import convert_comma_separated_to_list, get_timestamps
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SIMPLE_QUERY_SCRIPT_NAME,
    QUERY_STATUS,
)
from TIPCommon import construct_csv


TABLE_NAME = "Simple Query Results"


def start_query(siemplify, manager, xml_payload, limit, original_query, conditions):
    """
    Start event query
    :param siemplify: SiemplifyAction object
    :param manager: FortiSIEMManager object
    :param xml_payload: {str} xml payload for query
    :param limit: {int} limit for results
    :param original_query: {str} Original Query
    :param conditions: {str} Conditions
    :return: {tuple} output messages, result value, status
    """
    query_id = manager.start_event_query(xml_payload)
    # get query progress right after query started
    return check_query_progress_and_get_results(
        siemplify, manager, query_id, limit, original_query, conditions
    )


def check_query_progress_and_get_results(
    siemplify, manager, query_id, limit, original_query, conditions
):
    """
    Check query progress and get results
    :param siemplify: SiemplifyAction object
    :param manager: FortiSIEMManager object
    :param original_query: {str} Original Query
    :param query_id: {str} query id
    :param limit: {int} limit for results
    :param conditions: {str} Conditions
    :return: {tuple} output messages, result value, status
    """
    query_progress = manager.get_event_query_progress(query_id)
    result_value = True
    if query_progress == QUERY_STATUS.get("completed"):
        results = manager.get_event_query_results(query_id, limit)

        if results:
            siemplify.result.add_result_json([result.to_json() for result in results])
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([result.to_table() for result in results])
            )
            status = EXECUTION_STATE_COMPLETED
            output_message = (
                f"Successfully retrieved results for the constructed query {conditions} "
                f"in {INTEGRATION_DISPLAY_NAME}."
            )
        else:
            status = EXECUTION_STATE_COMPLETED
            output_message = f"No results were found for the constructed query {conditions} in {INTEGRATION_DISPLAY_NAME}"
    else:
        result_value = json.dumps({"query_id": query_id})
        status = EXECUTION_STATE_INPROGRESS
        output_message = f"Submitted Query. Waiting for results."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SIMPLE_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
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
        print_value=True,
    )

    # Action parameters
    minimum_severity_to_fetch = extract_action_param(
        siemplify,
        param_name="Minimum Severity to Fetch",
        input_type=int,
        is_mandatory=False,
        print_value=True,
    )
    event_types = extract_action_param(
        siemplify, param_name="Event Types", is_mandatory=False, print_value=True
    )
    event_types = convert_comma_separated_to_list(event_types)
    ph_event_categories = extract_action_param(
        siemplify, param_name="Event Category", is_mandatory=False, print_value=True
    )
    ph_event_categories = convert_comma_separated_to_list(ph_event_categories)
    event_ids = extract_action_param(
        siemplify, param_name="Event IDs", is_mandatory=False, print_value=True
    )
    event_ids = convert_comma_separated_to_list(event_ids)
    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )
    time_frame = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )
    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", is_mandatory=False, print_value=True
    )
    sort_field = extract_action_param(
        siemplify, param_name="Sort Field", is_mandatory=False, print_value=True
    )
    sort_order = extract_action_param(
        siemplify,
        param_name="Sort Order",
        is_mandatory=False,
        print_value=True,
        default_value="DESC",
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

        if minimum_severity_to_fetch is not None and minimum_severity_to_fetch < 1:
            raise Exception(
                f'Invalid value was provided for "Minimum Severity to Fetch": {limit}. Positive number '
                f"should be provided."
            )

        start_time, end_time = get_timestamps(
            range_string=time_frame,
            start_time_string=start_time,
            end_time_string=end_time,
        )

        manager = FortiSIEMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        xml_payload, conditions = manager.build_query_payload(
            fields_to_return=fields_to_return,
            sort_field=sort_field,
            sort_order=sort_order,
            start_time_seconds=start_time,
            end_time_seconds=end_time,
            event_types=event_types,
            ph_event_categories=ph_event_categories,
            minimum_severity_to_fetch=minimum_severity_to_fetch,
            event_ids=event_ids,
        )

        if is_first_run:
            output_message, result_value, status = start_query(
                siemplify, manager, xml_payload, limit, xml_payload, conditions
            )
        else:
            output_message, result_value, status = check_query_progress_and_get_results(
                siemplify,
                manager,
                additional_data.get("query_id"),
                limit,
                xml_payload,
                conditions,
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SIMPLE_QUERY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {SIMPLE_QUERY_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
