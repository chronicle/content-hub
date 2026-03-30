from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DOMAIN_MONITOR_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.cyjax_exceptions import CyjaxException
from ..core.datamodels import DomainMonitorResult
from ..core.utils import get_integration_params, parse_date


@output_handler
def main():
    """Execute Domain Monitor action for Cyjax.

    This action retrieves information for the Domain Monitor feature. The feature tracks
    your brands against newly registered global domains and the certificate transparency logs (CTL).

    Args:
        Query: A query string to search for a domain or part of it.
        Since: The start date time in ISO8601 format.
        Until: The end date time in ISO8601 format.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the results
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        CyjaxException: If API calls to Cyjax fail.
        ValueError: If the 'Since' date is after the 'Until' date.
        Exception: For any other unexpected errors during execution.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = DOMAIN_MONITOR_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_token, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    query = siemplify.extract_action_param("Query", print_value=True, default_value="")
    since = siemplify.extract_action_param("Since", print_value=True, default_value="")
    until = siemplify.extract_action_param("Until", print_value=True, default_value="")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE
    json_results = []

    try:
        query_param = query.strip() if query else None
        parse_date(since)
        parse_date(until)
        if since and until and (since > until):
            raise ValueError("Since date cannot be greater than Until date")

        siemplify.LOGGER.info("Initializing Cyjax API client")
        cyjax_manager = APIManager(siemplify=siemplify, api_token=api_token, verify_ssl=verify_ssl)

        siemplify.LOGGER.info("Starting Domain Monitor query with automatic pagination")
        result_data = cyjax_manager.process_domain_monitor(
            query=query_param,
            since=since,
            until=until,
        )

        results = result_data["results"]
        total_fetched = result_data["total_fetched"]
        limit_reached = result_data["limit_reached"]
        partial_error = result_data.get("partial_error")

        domain_results = [DomainMonitorResult(item) for item in results]
        csv_output = [domain_result.to_csv() for domain_result in domain_results]

        if results:
            json_results = results
            if limit_reached:
                output_message = f"Successfully retrieved {total_fetched} domain monitor results."\
                " Note: Only the first 1000 records from the API have been retrieved."
            else:
                output_message = f"Successfully retrieved {total_fetched} domain monitor results."

            if partial_error:
                output_message += (
                    f" Note: Pagination stopped early due to an error: {partial_error}"
                )

            if csv_output:
                siemplify.result.add_data_table(
                    "Domain Monitor Results",
                    construct_csv(csv_output),
                    "Cyjax",
                )

        else:
            output_message = "No domain monitor results found."

    except (CyjaxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(DOMAIN_MONITOR_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json.dumps(json_results, indent=4))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
