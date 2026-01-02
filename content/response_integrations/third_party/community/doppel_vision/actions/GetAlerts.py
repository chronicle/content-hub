from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DoppelManager import DoppelManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Get Alerts Action"

    # Extract configuration parameters
    api_key = siemplify.extract_configuration_param(
        provider_name="Doppel",
        param_name="API_Key",
    )

    # Extract optional action parameters
    search_key = siemplify.extract_action_param(
        param_name="Search Key",
        default_value=None,
    )
    queue_state = siemplify.extract_action_param(
        param_name="Queue State",
        default_value=None,
    )
    product = siemplify.extract_action_param(param_name="Product", default_value=None)
    created_before = siemplify.extract_action_param(
        param_name="Created Before",
        default_value=None,
    )
    created_after = siemplify.extract_action_param(
        param_name="Created After",
        default_value=None,
    )
    sort_type = siemplify.extract_action_param(
        param_name="Sort Type",
        default_value="date_sourced",
    )
    sort_order = siemplify.extract_action_param(
        param_name="Sort Order",
        default_value="desc",
    )
    page = siemplify.extract_action_param(
        param_name="Page",
        input_type=str,
        default_value=0,
    )
    tags = siemplify.extract_action_param(param_name="Tags", default_value=None)

    # Parse tags into a list if provided
    tags_list = tags.split(",") if tags else None

    # Build filters dictionary
    filters = {
        "search_key": search_key,
        "queue_state": queue_state,
        "product": product,
        "created_before": created_before,
        "created_after": created_after,
        "sort_type": sort_type,
        "sort_order": sort_order,
        "page": page,
        "tags": tags_list,
    }

    # Remove None values from filters
    filters = {key: value for key, value in filters.items() if value is not None}

    # Instantiate the manager
    manager = DoppelManager(api_key)

    # Initialize action result values
    status = EXECUTION_STATE_COMPLETED
    output_message = "Alerts retrieved successfully."
    result_value = True

    try:
        # Perform the get_alerts action
        siemplify.LOGGER.info(f"Fetching alerts with filters: {filters}")
        alerts = manager.get_alerts(filters=filters)

        if alerts:
            siemplify.result.add_result_json(
                alerts,
            )  # Store alerts in the action result JSON
            siemplify.LOGGER.info(f"Total alerts retrieved: {len(alerts)}")
        else:
            raise Exception("No alerts found or empty response received.")
    except Exception as e:
        output_message = f"Failed to retrieve alerts: {e!s}"
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)

    # Log results and complete the action
    siemplify.LOGGER.info(
        f"Action Completed: Status: {status}, Result Value: {result_value}, Output: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
