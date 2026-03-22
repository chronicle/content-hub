from __future__ import annotations

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import (
    CensysException,
    ValidationException,
)
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_PORTS,
    ENRICH_WEB_PROPERTIES_SCRIPT_NAME,
    NO_WEB_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import WebPropertyDatamodel
from ..core.utils import (
    get_integration_params,
    get_web_property_entities,
    remove_web_property_enrichment,
    validate_and_parse_ports,
    validate_rfc3339_timestamp,
    validate_web_property_entities,
)


def _extract_resources_from_response(
    response: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract resource list from API response.

    Args:
        response: API response dictionary

    Returns:
        List of resource dictionaries
    """
    if not response:
        return []

    result = response.get("result", [])
    if isinstance(result, list):
        return result

    return []


def _find_entity_resource(
    resources: list[dict[str, Any]], entity_identifier: str, port: int | None
) -> dict[str, Any] | None:
    """
    Find matching resource for entity and port.

    Args:
        resources: List of resource dictionaries
        entity_identifier: Hostname or IP to match
        port: Port number to match

    Returns:
        Matching resource dict or None
    """
    for resource in resources:
        resource_data = resource.get("resource", {})
        if resource_data.get("hostname") == entity_identifier and resource_data.get("port") == port:
            return resource

    return None


def _build_output_message(
    successful: list[str],
    not_found: list[str],
    failed: list[str],
    invalid: list[str],
) -> str:
    """
    Build detailed output message for action results.

    Args:
        successful: List of successfully enriched web property IDs
        not_found: List of web property IDs not found
        failed: List of web property IDs that failed
        invalid: List of invalid entities

    Returns:
        Formatted output message string
    """
    message_parts = []

    if successful:
        message_parts.append(
            f"Successfully enriched {len(successful)} web property(ies) from Censys."
        )

    if invalid:
        entities_str = ", ".join(invalid[:5])
        if len(invalid) > 5:
            entities_str += f" and {len(invalid) - 5} more"
        message_parts.append(
            f"{len(invalid)} entity(ies) skipped due to invalid format: {entities_str}"
        )

    if not_found:
        entities_str = ", ".join(not_found[:5])
        if len(not_found) > 5:
            entities_str += f" and {len(not_found) - 5} more"
        message_parts.append(
            f"{len(not_found)} web property(ies) not found in Censys: {entities_str}"
        )

    if failed:
        entities_str = ", ".join(failed[:5])
        if len(failed) > 5:
            entities_str += f" and {len(failed) - 5} more"
        message_parts.append(f"{len(failed)} web property(ies) failed to process: {entities_str}")

    if not message_parts:
        return "No web properties were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_WEB_PROPERTIES_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Started =================")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    ports_param = siemplify.extract_action_param(
        "Port", default_value=DEFAULT_PORTS, input_type=str
    )
    at_time = siemplify.extract_action_param("At Time", input_type=str, is_mandatory=False)

    successful_entities = []
    failed_entities = []
    not_found_entities = []
    invalid_entities = []
    json_results = []
    web_property_ids = []
    entities = []
    ports = []

    try:
        censys_manager = APIManager(
            api_key=api_key,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        entities = get_web_property_entities(siemplify)

        if not entities:
            output_message = NO_WEB_ENTITIES_ERROR
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_TRUE, EXECUTION_STATE_COMPLETED)
            return

        siemplify.LOGGER.info(f"Found {len(entities)} entity(ies) to process")

        entities, invalid_entities = validate_web_property_entities(entities, siemplify)

        if invalid_entities:
            siemplify.LOGGER.info(f"Skipping {len(invalid_entities)} invalid entity(ies)")

        if not entities:
            output_message = (
                f"All {len(invalid_entities)} entity(ies) are invalid. "
                "No valid entities to process."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_FALSE, EXECUTION_STATE_FAILED)
            return

        siemplify.LOGGER.info(f"Validated {len(entities)} entity(ies) for processing")

        ports = validate_and_parse_ports(ports_param)
        siemplify.LOGGER.info(f"Validated {len(ports)} port(s): {', '.join(map(str, ports))}")

        if at_time:
            at_time = validate_rfc3339_timestamp(at_time)
            siemplify.LOGGER.info(f"Using historical timestamp: {at_time}")

        for entity in entities:
            for port in ports:
                web_property_id = f"{entity.identifier}:{port}"
                web_property_ids.append(web_property_id)

        siemplify.LOGGER.info(f"Created {len(web_property_ids)} web property ID(s)")

        response = censys_manager.enrich_web_properties(web_property_ids, at_time)
        resources = _extract_resources_from_response(response)

        siemplify.LOGGER.info(f"Received {len(resources)} resource(s) from Censys API")

        for entity in entities:
            for port in ports:
                web_property_id = f"{entity.identifier}:{port}"

                siemplify.LOGGER.info(f"Processing: {web_property_id}")

                try:
                    entity_result = _find_entity_resource(resources, entity.identifier, port)

                    if not entity_result:
                        siemplify.LOGGER.info(f"No data found for {web_property_id}")
                        not_found_entities.append(web_property_id)
                        continue

                    web_model = WebPropertyDatamodel(entity_result, port)
                    enrichment_data = web_model.get_enrichment_data()

                    if enrichment_data:
                        # Remove old web property enrichment for this port
                        remove_web_property_enrichment(entity, port)
                        siemplify.LOGGER.info(f"Removed old enrichment for {web_property_id}")

                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True

                        successful_entities.append(web_property_id)
                        json_results.append({
                            "Entity": web_property_id,
                            "EntityResult": web_model.to_json(),
                        })

                        siemplify.LOGGER.info(f"Successfully enriched: {web_property_id}")
                    else:
                        siemplify.LOGGER.info(f"No enrichment data for {web_property_id}")
                        not_found_entities.append(web_property_id)

                except Exception as e:
                    error_message = f"Failed to process {web_property_id}: {e}"
                    siemplify.LOGGER.error(error_message)
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(web_property_id)

    except ValueError as e:
        output_message = (
            f"Invalid parameter value: {str(e)}\nPlease verify your input parameters and try again."
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except ValidationException as e:
        error_detail = str(e)
        wp_list = ", ".join(web_property_ids[:10])
        more_text = f" and {len(web_property_ids) - 10} more" if len(web_property_ids) > 10 else ""

        output_message = (
            f"Validation error occurred while processing "
            f"{len(web_property_ids)} web property(ies).\n"
            f"Input: {wp_list}{more_text}.\n"
            f"Error details: {error_detail}\n"
            "Please check the error details above and verify your "
            "input parameters."
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_WEB_PROPERTIES_SCRIPT_NAME, e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    if not output_message:
        output_message = _build_output_message(
            successful_entities, not_found_entities, failed_entities, invalid_entities
        )
        result_value = RESULT_VALUE_TRUE if successful_entities else RESULT_VALUE_FALSE

        if successful_entities:
            siemplify.update_entities(entities)

    siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("================= Main - Finished =================")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
