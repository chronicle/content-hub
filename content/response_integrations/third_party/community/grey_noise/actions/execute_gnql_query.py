from __future__ import annotations

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.api_manager import APIManager
from ..core.constants import (
    EXECUTE_GNQL_QUERY_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    GNQL_PAGE_SIZE,
    MAX_RESULT_SIZE,
)
from ..core.utils import get_integration_params, validate_integer_param
from ..core.greynoise_exceptions import InvalidIntegerException


def process_gnql_query(greynoise_manager, query, max_results, exclude_raw, quick, siemplify, all_data):
    """
    Process GNQL query and return results, automatically paginating
    through all pages.

    Args:
        greynoise_manager (APIManager): APIManager instance.
        query (str): GNQL query string.
        max_results (int): Maximum number of results to fetch.
        exclude_raw (bool): Whether to exclude raw scan data.
        quick (bool): If true, only return IP and classification/trust level.
        siemplify (SiemplifyAction): SiemplifyAction instance.
        all_data (list): Reference to list that will be populated with results.

    Returns:
        str: Output message describing the results.
    """
    siemplify.LOGGER.info(f"Executing GNQL query: {query}.")

    scroll_token = None
    total_count = 0
    complete = False
    is_first_call = True

    page_size = max_results if max_results < GNQL_PAGE_SIZE else GNQL_PAGE_SIZE

    siemplify.LOGGER.info(f"Page size: {page_size}.")

    # Loop through all pages until complete
    while not complete:
        result = greynoise_manager.execute_gnql_query(
            query=query, size=page_size, exclude_raw=exclude_raw, quick=quick, scroll=scroll_token
        )

        data = result.get("data", [])
        request_metadata = result.get("request_metadata", {})
        total_count = request_metadata.get("count", 0)
        complete = request_metadata.get("complete", True)
        scroll_token = request_metadata.get("scroll", "")

        if is_first_call:
            siemplify.LOGGER.info(f"Total available results for provided query are: {total_count}.")
            is_first_call = False

        all_data.extend(data)
        siemplify.LOGGER.info(f"Fetched records from GreyNoise: {len(data)}.")

        # Break if max results reached
        if len(all_data) >= max_results:
            siemplify.LOGGER.info(
                f"Reached max results limit of {max_results}, stopping pagination."
            )
            break

        # Break if no more data or complete
        if complete or not scroll_token or len(data) == 0:
            break

    # Trim to max_results if we collected more
    if len(all_data) > max_results:
        del all_data[max_results:]

    returned_count = len(all_data)
    if returned_count == 0:
        output_message = f"No IP addresses match the query criteria: {query}."
    else:
        output_message = (
            f"Successfully executed GNQL query: {query}. Total fetched records: {returned_count}."
        )

    siemplify.LOGGER.info(f"Processed {returned_count} IP results from GNQL query.")

    return output_message


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_GNQL_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key = get_integration_params(siemplify)

    # Action Parameters
    gnql_query = siemplify.extract_action_param(
        param_name="GNQL Query", is_mandatory=True, print_value=True, input_type=str
    )

    max_results = siemplify.extract_action_param(
        param_name="Max Results",
        default_value=str(MAX_RESULT_SIZE),
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    quick = siemplify.extract_action_param(
        param_name="Quick",
        default_value=False,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    exclude_raw = siemplify.extract_action_param(
        param_name="Exclude Raw",
        default_value=True,
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    all_data = []  # Initialize data collection list

    try:
        # Validate max results parameter
        max_results = validate_integer_param(
            max_results, "Max Results", zero_allowed=False, allow_negative=False
        )

        greynoise_manager = APIManager(api_key, siemplify=siemplify)
        siemplify.LOGGER.info(
            f"Connection to API established, performing action {EXECUTE_GNQL_QUERY_SCRIPT_NAME}."
        )

        if not gnql_query or not gnql_query.strip():
            output_message = "GNQL Query parameter is required."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
        else:
            output_message = process_gnql_query(
                greynoise_manager, gnql_query, max_results, exclude_raw, quick, siemplify, all_data
            )

    except RateLimitError as e:
        output_message = f"Rate limit reached: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RequestFailure as e:
        output_message = f"Failed to connect to the GreyNoise server: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except InvalidIntegerException as e:
        output_message = f"Invalid parameter value: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except ValueError as e:
        output_message = f"Invalid parameter value: {e}."
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(EXECUTE_GNQL_QUERY_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json({"data": all_data})

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
