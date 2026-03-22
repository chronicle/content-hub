from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException, PartialDataException
from ..core.constants import (
    CENSYS_PLATFORM_BASE_URL,
    COMMON_ACTION_ERROR_MESSAGE,
    GET_HOST_HISTORY_SCRIPT_NAME,
    MAX_RECORD_THRESHOLD,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import HostHistoryEventModel
from ..core.utils import get_integration_params, validate_ip_address, validate_rfc3339_timestamp


@output_handler
def main():
    """Retrieve the event history for a host (IP address).

    This action retrieves the event history for a host, allowing users to view historical
    scan data, track infrastructure changes over time, and identify when services were
    added, removed, or modified.

    Action Parameters:
        Host ID (str, required): The IP address of a host
        Start Time (str, required): Start time of the host timeline (RFC3339 format)
        End Time (str, required): End time of the host timeline (RFC3339 format)

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the results
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        CensysException: If API calls to Censys fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_HOST_HISTORY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    host_id = siemplify.extract_action_param(
        param_name="Host ID", input_type=str, is_mandatory=True
    )
    start_time = siemplify.extract_action_param(
        param_name="Start Time", input_type=str, is_mandatory=True
    )
    end_time = siemplify.extract_action_param(
        param_name="End Time", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # Validate Host ID (IP address)
        host_id = validate_ip_address(host_id, "Host ID")

        # Validate Start Time and End Time (RFC3339 format)
        start_time = validate_rfc3339_timestamp(start_time, "Start Time")
        end_time = validate_rfc3339_timestamp(end_time, "End Time")

        # Initialize API Manager
        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving host history for Host ID: {host_id}")

        partial_data_warning = ""
        try:
            response = censys_manager.get_host_history(host_id, start_time, end_time)
        except PartialDataException as e:
            siemplify.LOGGER.info(f"Partial data collected: {str(e)}")

            response = {"result": e.collected_data}
            error_info = e.error_details

            partial_data_warning = (
                f"\n\nWARNING: Partial data collected. "
                f"Pagination stopped at page {error_info['page_number']} "
                f"due to {error_info['error_type']}: {error_info['error_message']}. "
                f"Retried {error_info['retries_attempted']} times."
            )

            response["result"]["error_info"] = error_info

        # Add JSON result
        siemplify.result.add_result_json(response)

        # Extract events from response
        result = response.get("result", {})
        events = result.get("events", [])
        total_events = result.get("total_events", len(events))
        is_partial = result.get("partial_data", False)
        pagination_info = result.get("pagination_info", {})

        if not events:
            output_message = (
                f"No historical data found for host {host_id} within the specified time range."
            )
            siemplify.LOGGER.info(output_message)
        else:
            # Build table data using datamodels (limit to MAX_TABLE_RECORDS for display)
            table_results = []
            events_for_table = events[:MAX_TABLE_RECORDS]

            for idx, event in enumerate(events_for_table, start=1):
                model = HostHistoryEventModel(event, idx, host_id, organization_id)
                table_results.append(model.to_csv())

            # Add table to results
            if table_results:
                siemplify.result.add_data_table(
                    "Host History Events", construct_csv(table_results), "Censys"
                )

            # Build output message
            if is_partial:
                pages_fetched = pagination_info.get("pages_fetched", 0)
                output_message = (
                    f"Successfully retrieved {total_events} event(s) for host {host_id} "
                    f"(partial data - {pages_fetched} page(s) fetched)."
                )
            else:
                output_message = (
                    f"Successfully retrieved {total_events} event(s) for host {host_id}."
                )

            # Add table limit info if we have more events than table can show
            if total_events > MAX_TABLE_RECORDS:
                output_message += (
                    f"\nDisplaying {MAX_TABLE_RECORDS} events in table view. "
                    f"Full results ({total_events} events) available in JSON output."
                )

            # Add info about MAX_RECORD_THRESHOLD record limit and Censys Platform link
            if total_events >= MAX_RECORD_THRESHOLD and not is_partial:
                output_message += (
                    f"\nThere are more than {MAX_RECORD_THRESHOLD} host history "
                    "records available for this host.\n"
                    f"The first {MAX_RECORD_THRESHOLD} records are displayed.\n"
                    f"Further exploration should be conducted on the Censys platform: "
                    f"{CENSYS_PLATFORM_BASE_URL}/hosts/{host_id}"
                )

            # Add partial data warning if applicable
            output_message += partial_data_warning

            siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_HOST_HISTORY_SCRIPT_NAME, str(e))
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
