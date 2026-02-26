from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException, PartialDataException
from ..core.constants import (
    CENSYS_PLATFORM_BASE_URL,
    COMMON_ACTION_ERROR_MESSAGE,
    GET_RELATED_INFRASTRUCTURE_SCRIPT_NAME,
    MAX_RECORD_THRESHOLD,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.utils import get_integration_params


def build_table_row(index: int, hit: dict) -> dict:
    """Build a table row for a single hit.

    Args:
        index: Row number (1-indexed)
        hit: Hit data containing host_v1, webproperty_v1, or certificate_v1

    Returns:
        Dictionary representing a table row
    """
    if "host_v1" in hit:
        resource = hit["host_v1"]["resource"]
        return {
            "Primary ID": resource.get("ip", "N/A"),
        }
    elif "webproperty_v1" in hit:
        resource = hit["webproperty_v1"]["resource"]
        hostname = resource.get("hostname", "N/A")
        port = resource.get("port", "")
        primary_id = f"{hostname}:{port}" if port else hostname
        return {
            "Primary ID": primary_id,
        }
    elif "certificate_v1" in hit:
        resource = hit["certificate_v1"]["resource"]
        primary_id = resource.get("fingerprint_sha256", "N/A")

        return {
            "Primary ID": primary_id,
        }
    else:
        return {
            "Primary ID": "N/A",
        }


def validate_field_and_value(field: str, value: str) -> tuple[str, str]:
    """Validate field and value parameters.

    Args:
        field: The field name to search (e.g., 'services.port')
        value: The value to search for (e.g., '443')

    Returns:
        Tuple of (stripped_field, stripped_value)

    Raises:
        ValueError: If field or value is empty
    """
    if not field or not field.strip():
        raise ValueError("Field parameter cannot be empty")

    if not value or not value.strip():
        raise ValueError("Value parameter cannot be empty")

    return field.strip(), value.strip()


@output_handler
def main():
    """Retrieve related infrastructure based on a single field:value pair.

    This action searches for assets that match a specific field:value condition,
    enabling discovery of related infrastructure by identifying assets that share
    common attributes. This is similar to the CensEye functionality available in
    the Platform web UI.

    Max 1000 results will be returned. If more than 1000 results exist, the action
    will drop the results and provide a message with the search query to run manually.

    Action Parameters:
        Field (str, required): The field name to search (e.g., 'services.port')
        Value (str, required): The value to search for (e.g., '443')

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the results
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If Field or Value parameters are empty
        CensysException: If API calls to Censys fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_INFRASTRUCTURE_SCRIPT_NAME
    siemplify.LOGGER.info(
        "----------------- Main - Param Init -----------------"
    )

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    field = siemplify.extract_action_param(
        param_name="Field", input_type=str, is_mandatory=True
    )
    value = siemplify.extract_action_param(
        param_name="Value", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # Validate field and value parameters
        siemplify.LOGGER.info("Validating Field and Value parameters...")
        field, value = validate_field_and_value(field, value)
        siemplify.LOGGER.info(f"Field: '{field}', Value: '{value}'")

        # Initialize API Manager
        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # Build search query
        search_query = f"{field}:{value}"
        siemplify.LOGGER.info(f"Search query: {search_query}")

        # Fetch results with pagination (up to 1000 records)
        siemplify.LOGGER.info(
            f"Fetching related infrastructure (max {MAX_RECORD_THRESHOLD} records)..."
        )

        partial_data_warning = ""
        try:
            search_response = censys_manager.run_search_query_with_pagination(
                query=search_query,
                max_records=MAX_RECORD_THRESHOLD,
            )
        except PartialDataException as e:
            siemplify.LOGGER.info(f"Partial data collected: {str(e)}")

            search_response = {"result": e.collected_data}
            error_info = e.error_details

            partial_data_warning = (
                f"\n\nWARNING: Partial data collected. "
                f"Pagination stopped at page {error_info['page_number']} "
                f"due to {error_info['error_type']}: {error_info['error_message']}. "
                f"Retried {error_info['retries_attempted']} times."
            )

            search_response["result"]["error_info"] = error_info

        # Extract results
        result_data = search_response.get("result", {})
        all_hits = result_data.get("hits", [])
        total_available = result_data.get("total_available", 0)
        total_fetched = result_data.get("total_fetched", 0)
        pages_fetched = result_data.get("pages_fetched", 0)
        truncated = result_data.get("truncated", False)
        truncation_reason = result_data.get("truncation_reason")
        _ = result_data.get("partial_data", False)

        # Build table view
        table_rows = []
        host_count = 0
        web_count = 0
        cert_count = 0

        for idx, hit in enumerate(all_hits, start=1):
            table_row = build_table_row(idx, hit)
            table_rows.append(table_row)

            # Count by type
            if "host_v1" in hit:
                host_count += 1
            elif "webproperty_v1" in hit:
                web_count += 1
            elif "certificate_v1" in hit:
                cert_count += 1

        # Add table to SOAR
        if table_rows:
            siemplify.result.add_data_table(
                "Related Infrastructure Summary", construct_csv(table_rows)
            )
            siemplify.LOGGER.info(
                f"Added table with {len(table_rows)} rows "
                f"(Hosts: {host_count}, Web: {web_count}, Certs: {cert_count})"
            )

        # Prepare final result
        final_result = {
            "result": {
                "hits": all_hits,
                "total_available": total_available,
                "total_fetched": total_fetched,
                "pages_fetched": pages_fetched,
                "truncated": truncated,
                "summary": {
                    "host_count": host_count,
                    "web_property_count": web_count,
                    "certificate_count": cert_count,
                },
            }
        }

        # Build output message
        if total_fetched == 0:
            output_message = f"No related infrastructure found matching the query: {search_query}"
        else:
            # Build type breakdown
            type_breakdown = []
            if host_count > 0:
                type_breakdown.append(f"Hosts: {host_count}")
            if web_count > 0:
                type_breakdown.append(f"Web Properties: {web_count}")
            if cert_count > 0:
                type_breakdown.append(f"Certificates: {cert_count}")

            type_summary = (
                ", ".join(type_breakdown) if type_breakdown else "No results"
            )

            if truncated:
                if truncation_reason == "api_error":
                    output_message = (
                        f"Found {total_available:,} total matching assets for query:"
                        f" {search_query}\nSuccessfully retrieved {total_fetched} record(s)"
                        f" across {pages_fetched} page(s) (partial data).\nResult breakdown:"
                        f" {type_summary}\n\n"
                        f"Table view displays key information for all {total_fetched} results. "
                        "Full JSON data available in case wall."
                    )
                elif truncation_reason == "payload_limit":
                    output_message = (
                        f"Found {total_available:,} total matching assets for query:"
                        f" {search_query}\nSuccessfully retrieved {total_fetched} record(s) "
                        f" across {pages_fetched} page(s).\nResult breakdown: {type_summary}\n\n"
                        f"Results limited due to payload size constraint (28 MB). "
                        f"Table view displays key information for all {total_fetched} results. "
                        "For complete results, visit Censys Platform: "
                        f"{CENSYS_PLATFORM_BASE_URL}/search?q={search_query}"
                    )
                elif truncation_reason == "record_limit":
                    output_message = (
                        f"Found {total_available:,} total matching assets for query:"
                        f" {search_query}\nSuccessfully retrieved {total_fetched} record(s) "
                        f" across {pages_fetched} page(s).\nResult breakdown: {type_summary}\n\n"
                        f"There are more than {MAX_RECORD_THRESHOLD:,} related assets. "
                        f"Table view displays key information for the first {total_fetched} results"
                        ".\n\nFurther exploration should be conducted on the Censys platform: "
                        f"{CENSYS_PLATFORM_BASE_URL}/search?q={search_query}"
                    )
            else:
                output_message = (
                    f"Found {total_available:,} total matching assets for query: {search_query}\n"
                    f"Successfully retrieved all {total_fetched} record(s) across {pages_fetched} "
                    f"page(s).\nResult breakdown: {type_summary}\n\n"
                    "Table view displays key information for all results. "
                    "Full JSON data available in case wall."
                )

        # Add partial data warning if applicable
        output_message += partial_data_warning

        # Add JSON result
        siemplify.result.add_result_json(final_result)
        siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_RELATED_INFRASTRUCTURE_SCRIPT_NAME, str(e)
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
