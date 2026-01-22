from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    DEFAULT_SNAPSHOTS_SORT_TYPE,
    LIST_OBJECT_SNAPSHOTS_SCRIPT_NAME,
    MAX_SNAPSHOTS_LIMIT,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import ObjectSnapshotsDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    get_integration_params,
    is_valid_date,
    string_to_list,
    validate_integer_param,
    validate_required_string,
)


@output_handler
def main():
    """List snapshots for a specific object from Rubrik Security Cloud.

    This action retrieves a list of snapshots for a specified object with support for
    filtering by date range, snapshot type, and pagination. Results can be sorted
    and limited.

    Action Parameters:
        Object ID (str, required): The unique identifier of the object to list snapshots for
        Start Date (str, optional): Start date for snapshot range (ISO format)
        End Date (str, optional): End date for snapshot range (ISO format)
        Snapshot Type (str, optional): Comma-separated list of snapshot types to filter
        Limit (str, optional): Maximum number of snapshots to retrieve (default: 50)
        Next Page Token (str, optional): Token for pagination to retrieve next page
        Sort Order (str, optional): Sort order for results (default: from constants)

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
    siemplify.script_name = LIST_OBJECT_SNAPSHOTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    object_id = siemplify.extract_action_param(
        param_name="Object ID", input_type=str, is_mandatory=True
    )
    start_date = siemplify.extract_action_param(
        param_name="Start Date", input_type=str, is_mandatory=False, default_value=None
    )
    end_date = siemplify.extract_action_param(
        param_name="End Date", input_type=str, is_mandatory=False, default_value=None
    )
    snapshot_type = siemplify.extract_action_param(
        param_name="Snapshot Type",
        input_type=str,
        is_mandatory=False,
        default_value=None,
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
    sort_order = siemplify.extract_action_param(
        param_name="Sort Order",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_SNAPSHOTS_SORT_TYPE,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        object_id = validate_required_string(object_id, "Object ID")
        snapshot_types = string_to_list(snapshot_type)
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

        siemplify.LOGGER.info(f"Retrieving snapshots for Object ID: {object_id}")
        response = rubrik_manager.list_object_snapshots(
            object_id=object_id,
            start_date=start_date,
            end_date=end_date,
            snapshot_types=snapshot_types,
            limit=limit,
            next_page_token=next_page_token.strip() if next_page_token else None,
            sort_order=sort_order,
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        data = response.get("data", {})
        snapshots_connection = data.get("snapshotsListConnection", {})
        edges = snapshots_connection.get("edges", [])
        page_info = snapshots_connection.get("pageInfo", {})

        snapshot_count = len(edges)
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor", "")

        snapshots_data = ObjectSnapshotsDatamodel(edges, page_info)

        output_message = (
            f"Successfully retrieved {snapshot_count} snapshot(s) for Object ID: {object_id}"
            f"Showing up to {MAX_TABLE_RECORDS} records in table."
        )

        if has_next_page:
            output_message += f". More results available. Next page token: {end_cursor}"

        table_data = snapshots_data.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table(
                "Object Snapshots", construct_csv(consise_table_data), "RSC"
            )

    except (
        RubrikException,
        ValueError,
    ) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_OBJECT_SNAPSHOTS_SCRIPT_NAME, str(e)
        )
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
