from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    LIST_EVENTS_DEFAULT_SORT_BY,
    LIST_EVENTS_DEFAULT_SORT_ORDER,
    LIST_EVENTS_SCRIPT_NAME,
    MAX_SNAPSHOTS_LIMIT,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import ListEventsDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    get_integration_params,
    is_valid_date,
    string_to_list,
    validate_integer_param,
)


@output_handler
def main():
    """List events from Rubrik Security Cloud with filtering and pagination support.

    This action retrieves events/activities from Rubrik Security Cloud with support for
    various filters including activity status, type, severity, object details, cluster IDs,
    and date ranges. Results can be sorted and paginated.

    Action Parameters:
        Activity Status (str, optional): Comma-separated list of activity statuses to filter
        Activity Type (str, optional): Comma-separated list of activity types to filter
        Severity (str, optional): Comma-separated list of severity levels to filter
        Object Name (str, optional): Name of the object to filter events for
        Object Type (str, optional): Comma-separated list of object types to filter
        Cluster ID (str, optional): Comma-separated list of cluster IDs to filter
        Start Date (str, optional): Start date for event range (ISO format)
        End Date (str, optional): End date for event range (ISO format)
        Sort By (str, optional): Field to sort results by (default: from constants)
        Sort Order (str, optional): Sort order ASC/DESC (default: from constants)
        Limit (str, optional): Maximum number of events to retrieve (default: 50)
        Next Page Token (str, optional): Token for pagination to retrieve next page

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the retrieval results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails (e.g., invalid dates, start date after end date)
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_EVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    activity_status = siemplify.extract_action_param(
        param_name="Activity Status",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    activity_type = siemplify.extract_action_param(
        param_name="Activity Type",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    severity = siemplify.extract_action_param(
        param_name="Severity", input_type=str, is_mandatory=False, default_value=None
    )
    object_name = siemplify.extract_action_param(
        param_name="Object Name", input_type=str, is_mandatory=False, default_value=None
    )
    object_type = siemplify.extract_action_param(
        param_name="Object Type", input_type=str, is_mandatory=False, default_value=None
    )
    cluster_id = siemplify.extract_action_param(
        param_name="Cluster ID", input_type=str, is_mandatory=False, default_value=None
    )
    start_date = siemplify.extract_action_param(
        param_name="Start Date", input_type=str, is_mandatory=False, default_value=None
    )
    end_date = siemplify.extract_action_param(
        param_name="End Date", input_type=str, is_mandatory=False, default_value=None
    )
    sort_by = siemplify.extract_action_param(
        param_name="Sort By",
        input_type=str,
        is_mandatory=False,
        default_value=LIST_EVENTS_DEFAULT_SORT_BY,
    )
    sort_order = siemplify.extract_action_param(
        param_name="Sort Order",
        input_type=str,
        is_mandatory=False,
        default_value=LIST_EVENTS_DEFAULT_SORT_ORDER,
    )
    limit = siemplify.extract_action_param(
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )
    next_page_token = siemplify.extract_action_param(
        param_name="Next Page Token",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        activity_statuses = string_to_list(activity_status)
        activity_types = string_to_list(activity_type)
        severities = string_to_list(severity)
        object_types = string_to_list(object_type)
        cluster_ids = string_to_list(cluster_id)

        limit = validate_integer_param(
            limit,
            "Limit",
            zero_allowed=False,
            allow_negative=False,
            max_value=MAX_SNAPSHOTS_LIMIT,
            default_value=DEFAULT_LIMIT,
        )

        start_date = is_valid_date(start_date)

        end_date = is_valid_date(end_date)

        if start_date and end_date and (start_date > end_date):
            raise ValueError("Start Date must be before End Date")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Retrieving events")
        response = rubrik_manager.list_events(
            activity_statuses=activity_statuses,
            activity_types=activity_types,
            severities=severities,
            object_name=object_name.strip() if object_name else None,
            object_types=object_types,
            cluster_ids=cluster_ids,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            next_page_token=next_page_token.strip() if next_page_token else None,
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        data = response.get("data", {})
        activity_series_connection = data.get("activitySeriesConnection", {})
        edges = activity_series_connection.get("edges", [])
        page_info = activity_series_connection.get("pageInfo", {})

        event_count = len(edges)
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor", "")

        events_data = ListEventsDatamodel(edges, page_info)

        output_message = (
            f"Successfully retrieved {event_count} event(s)"
            f"Showing up to {MAX_TABLE_RECORDS} records in table."
        )
        if has_next_page:
            output_message += f". More results available. Next page Token: {end_cursor}"

        table_data = events_data.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table("Events", construct_csv(consise_table_data), "RSC")

    except (RubrikException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(LIST_EVENTS_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
