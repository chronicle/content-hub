from __future__ import annotations

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
    ENRICH_CERTIFICATES_SCRIPT_NAME,
    NO_FILEHASH_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import CertificateDatamodel
from ..core.utils import (
    filter_valid_certificate_ids,
    get_filehash_entities,
    get_integration_params,
    remove_certificate_enrichment,
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
        entity_identifier: Certificate SHA-256 fingerprint to find

    Returns:
        Formatted entity result dict or None if not found
    """
    entity_lower = entity_identifier.lower()
    for resource_item in resources:
        result_item = resource_item.get("resource", {})
        cert_sha256 = result_item.get("fingerprint_sha256", "")
        if cert_sha256.lower() == entity_lower:
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
        invalid: List of entity identifiers with invalid format

    Returns:
        Formatted output message string
    """
    message_parts = []

    if successful:
        message_parts.append(f"Successfully enriched {len(successful)} certificate(s) from Censys.")

    if not_found:
        entities_str = ", ".join(not_found[:5])
        if len(not_found) > 5:
            entities_str += f" and {len(not_found) - 5} more"
        message_parts.append(f"{len(not_found)} certificate(s) not found in Censys: {entities_str}")

    if failed:
        entities_str = ", ".join(failed[:5])
        if len(failed) > 5:
            entities_str += f" and {len(failed) - 5} more"
        message_parts.append(f"{len(failed)} certificate(s) failed to process: {entities_str}")

    if invalid:
        entities_str = ", ".join(invalid[:5])
        if len(invalid) > 5:
            entities_str += f" and {len(invalid) - 5} more"
        message_parts.append(
            f"{len(invalid)} certificate(s) have invalid format "
            f"(must be 64 hex characters): {entities_str}"
        )

    if not message_parts:
        return "No certificates were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


@output_handler
def main():
    """
    Enrich FILEHASH entities with Censys certificate intelligence.

    This action retrieves comprehensive information about SSL/TLS
    certificates using the Censys Platform API, including issuer,
    subject, validity periods, SANs, and certificate chains.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message: Status message with enrichment summary
            - result_value: True if any entities enriched, False otherwise
            - status: Execution state (COMPLETED or FAILED)
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_CERTIFICATES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

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
    certificate_ids = []
    cert_entities = []
    valid_cert_ids = []

    try:
        # Initialize API Manager
        censys_manager = APIManager(
            api_key=api_key,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # Get FILEHASH entities
        cert_entities = get_filehash_entities(siemplify)

        if not cert_entities:
            output_message = NO_FILEHASH_ENTITIES_ERROR
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_TRUE, EXECUTION_STATE_COMPLETED)
            return

        siemplify.LOGGER.info(f"Found {len(cert_entities)} certificate entities to process")

        # Extract and validate certificate IDs
        certificate_ids = [entity.identifier for entity in cert_entities]
        valid_cert_ids, invalid_cert_ids = filter_valid_certificate_ids(certificate_ids)

        # Track invalid certificate IDs
        if invalid_cert_ids:
            more_str = ""
            if len(invalid_cert_ids) > 5:
                more_str = f" and {len(invalid_cert_ids) - 5} more"
            invalid_entities.extend(invalid_cert_ids)
            siemplify.LOGGER.info(
                f"Found {len(invalid_cert_ids)} invalid certificate ID(s): "
                f"{', '.join(invalid_cert_ids[:5])}"
                f"{more_str if len(invalid_cert_ids) > 5 else ''}"
            )

        # Skip API call if no valid certificate IDs
        if not valid_cert_ids:
            output_message = (
                f"No valid certificate IDs to process. "
                f"All {len(invalid_cert_ids)} certificate ID(s) are invalid."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_FALSE, EXECUTION_STATE_FAILED)
            return

        siemplify.LOGGER.info(f"Processing {len(valid_cert_ids)} valid certificate(s)")

        # Call API with batch of valid certificate IDs only
        response = censys_manager.enrich_certificates(valid_cert_ids)
        resources = _extract_resources_from_response(response)

        siemplify.LOGGER.info(f"Received {len(resources)} resource(s) from Censys API")

        # Create set for O(1) lookup performance
        invalid_set = set(invalid_entities)

        # Process each entity
        for entity in cert_entities:
            entity_identifier = entity.identifier

            # Skip invalid certificate IDs (already tracked)
            if entity_identifier in invalid_set:
                continue

            siemplify.LOGGER.info(f"Processing entity: {entity_identifier}")

            try:
                # Find matching resource for this certificate
                entity_result = _find_entity_resource(resources, entity_identifier)

                if not entity_result:
                    siemplify.LOGGER.info(f"No data found for {entity_identifier}")
                    not_found_entities.append(entity_identifier)
                    continue

                # Create datamodel and get enrichment data
                cert_model = CertificateDatamodel(entity_result)
                enrichment_data = cert_model.get_enrichment_data()

                if not enrichment_data:
                    siemplify.LOGGER.info(f"No enrichment data available for {entity_identifier}")
                    not_found_entities.append(entity_identifier)
                    continue

                # Remove old certificate enrichment data
                remove_certificate_enrichment(entity)
                siemplify.LOGGER.info(f"Removed old certificate enrichment for {entity_identifier}")

                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True

                # Store results
                successful_entities.append(entity_identifier)
                json_results.append({
                    "Entity": entity_identifier,
                    "EntityResult": cert_model.to_json(),
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
        cert_list = ", ".join(certificate_ids[:10])
        more_text = f" and {len(certificate_ids) - 10} more" if len(certificate_ids) > 10 else ""

        output_message = (
            f"Validation error occurred while processing "
            f"{len(cert_entities)} certificate entity(ies).\n"
            f"Input certificates: {cert_list}{more_text}.\n"
            f"Error details: {error_detail}\n"
            "Please check the error details above and verify your "
            "input parameters."
        )
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_CERTIFICATES_SCRIPT_NAME, e)
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
            siemplify.update_entities(cert_entities)

    # Add JSON results
    siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("================= Main - Finished =================")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
