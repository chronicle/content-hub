from __future__ import annotations

from datetime import datetime
from typing import Any

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import (
    CensysException,
    ValidationException,
)
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    ENRICH_IPS_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    NO_ADDRESS_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import HostDatamodel
from ..core.utils import (
    filter_valid_ips,
    get_integration_params,
    get_ip_entities,
    remove_ip_enrichment,
    validate_rfc3339_timestamp,
)


def _extract_resources_from_response(
    response: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract resource list from API response.

    Args:
        response: API response dictionary

    Returns:
        List of resource items
    """
    if not isinstance(response, dict):
        return []

    result = response.get("result", [])
    return result if isinstance(result, list) else []


def _find_entity_resource(
    resources: list[dict[str, Any]], entity_identifier: str
) -> dict[str, Any] | None:
    """
    Find matching resource for an entity identifier.

    Args:
        resources: List of resource items from API
        entity_identifier: IP address to find

    Returns:
        Formatted entity result dict or None if not found
    """
    for resource_item in resources:
        result_item = resource_item.get("resource", {})
        if result_item.get("ip") == entity_identifier:
            return {"result": {"resource": result_item}}
    return None


def _build_output_message(
    successful: list[str],
    not_found: list[str],
    failed: list[str],
    invalid: list[str],
) -> str:
    """
    Build detailed output message with entity information.

    Args:
        successful: List of successfully enriched entity identifiers
        not_found: List of entity identifiers not found in Censys
        failed: List of entity identifiers that failed to process
        invalid: List of invalid IP addresses

    Returns:
        Formatted output message string
    """
    message_parts = []

    if successful:
        message_parts.append(f"Successfully enriched {len(successful)} IP(s) from Censys.")

    if invalid:
        entities_str = ", ".join(invalid[:5])
        if len(invalid) > 5:
            entities_str += f" and {len(invalid) - 5} more"
        message_parts.append(f"{len(invalid)} IP(s) skipped due to invalid format: {entities_str}")

    if not_found:
        entities_str = ", ".join(not_found[:5])
        if len(not_found) > 5:
            entities_str += f" and {len(not_found) - 5} more"
        message_parts.append(f"{len(not_found)} IP(s) not found in Censys: {entities_str}")

    if failed:
        entities_str = ", ".join(failed[:5])
        if len(failed) > 5:
            entities_str += f" and {len(failed) - 5} more"
        message_parts.append(f"{len(failed)} IP(s) failed to process: {entities_str}")

    if not message_parts:
        return "No IPs were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


@output_handler
def main():
    """
    Enrich IP entities with Censys host intelligence.

    This action retrieves comprehensive information about IP addresses
    using the Censys Platform API, including services, ports, protocols,
    certificates, vulnerabilities, and location data.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message: Status message with enrichment summary
            - result_value: True if any entities enriched, False otherwise
            - status: Execution state (COMPLETED or FAILED)
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IPS_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    at_time = siemplify.extract_action_param(
        param_name="At Time",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("================= Main - Started =================")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    output_message = ""

    # Entity tracking
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    invalid_entities = []
    json_results = []
    ip_addresses = []
    ip_entities = []
    valid_ips = []

    try:
        # Initialize API Manager
        censys_manager = APIManager(
            api_key=api_key,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # Get IP entities
        ip_entities = get_ip_entities(siemplify)

        if not ip_entities:
            output_message = NO_ADDRESS_ENTITIES_ERROR
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_TRUE, EXECUTION_STATE_COMPLETED)
            return

        siemplify.LOGGER.info(f"Found {len(ip_entities)} IP entities to process")

        # Extract and validate IP addresses
        ip_addresses = [entity.identifier for entity in ip_entities]
        valid_ips, invalid_ips = filter_valid_ips(ip_addresses)

        # Track invalid IPs
        if invalid_ips:
            invalid_entities.extend(invalid_ips)

            more_text = f" and {len(invalid_ips) - 5} more" if len(invalid_ips) > 5 else ""
            siemplify.LOGGER.info(
                f"Found {len(invalid_ips)} invalid IP(s): {', '.join(invalid_ips[:5])}{more_text}"
            )

        # Skip API call if no valid IPs
        if not valid_ips:
            output_message = (
                f"No valid IP addresses to process. All {len(invalid_ips)} IP(s) are invalid."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_FALSE, EXECUTION_STATE_FAILED)
            return

        siemplify.LOGGER.info(f"Processing {len(valid_ips)} valid IP(s)")

        # Validate at_time parameter if provided
        if at_time:
            at_time = validate_rfc3339_timestamp(at_time)
            siemplify.LOGGER.info(f"Using historical timestamp: {at_time}")

        # Call API with batch of valid IPs only
        response = censys_manager.enrich_hosts(valid_ips, at_time)
        resources = _extract_resources_from_response(response)

        siemplify.LOGGER.info(f"Received {len(resources)} resource(s) from Censys API")

        # Create set for O(1) lookup performance
        invalid_set = set(invalid_entities)

        # Process each entity
        for entity in ip_entities:
            entity_identifier = entity.identifier

            # Skip invalid IPs (already tracked)
            if entity_identifier in invalid_set:
                continue

            siemplify.LOGGER.info(f"Processing entity: {entity_identifier}")

            try:
                # Find matching resource for this IP
                entity_result = _find_entity_resource(resources, entity_identifier)

                if not entity_result:
                    siemplify.LOGGER.info(f"No data found for {entity_identifier}")
                    not_found_entities.append(entity_identifier)
                    continue

                # Create datamodel and get enrichment data
                host_model = HostDatamodel(entity_result)
                enrichment_data = host_model.get_enrichment_data()

                if not enrichment_data:
                    siemplify.LOGGER.info(f"No enrichment data available for {entity_identifier}")
                    not_found_entities.append(entity_identifier)
                    continue

                # Remove old Censys IP enrichment data
                remove_ip_enrichment(entity)
                siemplify.LOGGER.info(f"Removed old IP enrichment data for {entity_identifier}")

                # Add timestamp and enrich entity
                enrichment_data[f"{ENRICHMENT_PREFIX}last_enriched"] = (
                    datetime.utcnow().isoformat() + "Z"
                )

                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True

                # Store results
                successful_entities.append(entity_identifier)
                json_results.append({
                    "Entity": entity_identifier,
                    "EntityResult": host_model.to_json(),
                })

                siemplify.LOGGER.info(f"Successfully enriched: {entity_identifier}")

            except Exception as e:
                error_message = f"Failed to process {entity_identifier}: {e}"
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(e)
                failed_entities.append(entity_identifier)

    except ValueError as e:
        output_message = (
            f"Invalid parameter value: {str(e)}\nPlease verify your input parameters and try again."
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except ValidationException as e:
        error_detail = str(e)
        ip_list = ", ".join(ip_addresses[:10])
        more_text = f" and {len(ip_addresses) - 10} more" if len(ip_addresses) > 10 else ""

        output_message = (
            f"Validation error occurred while processing "
            f"{len(ip_entities)} IP entity(ies).\n"
            f"Input IPs: {ip_list}{more_text}.\n"
            f"Error details: {error_detail}\n"
            "Please check the error details above and verify your "
            "input parameters."
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_IPS_SCRIPT_NAME, e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    # Build output message if execution completed successfully
    if status == EXECUTION_STATE_COMPLETED:
        output_message = _build_output_message(
            successful_entities,
            not_found_entities,
            failed_entities,
            invalid_entities,
        )
        result_value = RESULT_VALUE_TRUE if successful_entities else RESULT_VALUE_FALSE

        # Update entities in Siemplify
        if successful_entities:
            siemplify.update_entities(ip_entities)

    # Add JSON results
    siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("================= Main - Finished =================")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
