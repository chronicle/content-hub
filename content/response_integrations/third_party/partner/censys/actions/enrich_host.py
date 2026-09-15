from __future__ import annotations

from datetime import datetime

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import (
    CensysException,
    FeatureNotEnabledException,
    ForbiddenErrorException,
    ItemNotFoundException,
    RateLimitException,
    UnauthorizedErrorException,
)
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    ENABLE_NEW_HOST_ENRICHMENT_PARAM,
    ENRICH_HOST_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    INTEGRATION_NAME,
    NEW_HOST_ENRICHMENT_DISABLED_MESSAGE,
    NO_ADDRESS_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import HostEnrichmentDatamodel
from ..core.utils import (
    filter_valid_ips,
    get_integration_params,
    get_ip_entities,
    remove_ip_enrichment,
)


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
        message_parts.append(
            f"Successfully enriched {len(successful)} host(s) from Censys."
        )

    if invalid:
        entities_str = ", ".join(invalid[:5])
        if len(invalid) > 5:
            entities_str += f" and {len(invalid) - 5} more"
        message_parts.append(
            f"{len(invalid)} IP(s) skipped due to invalid format: {entities_str}"
        )

    if not_found:
        entities_str = ", ".join(not_found[:5])
        if len(not_found) > 5:
            entities_str += f" and {len(not_found) - 5} more"
        message_parts.append(
            f"{len(not_found)} host(s) not found in Censys: {entities_str}"
        )

    if failed:
        entities_str = ", ".join(failed[:5])
        if len(failed) > 5:
            entities_str += f" and {len(failed) - 5} more"
        message_parts.append(
            f"{len(failed)} host(s) failed to process: {entities_str}"
        )

    if not message_parts:
        return "No hosts were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


def _build_account_level_error_message(
    error: Exception,
    successful: list[str],
    skipped: list[str],
) -> str:
    """
    Build the output message when an account-level Censys API error (no access,
    feature not enabled, or daily quota reached) stopped the loop early.

    Uses the same COMMON_ACTION_ERROR_MESSAGE template every other action in
    this integration uses for any CensysException, so the message reads the
    same way regardless of which action or error type produced it.

    Args:
        error: The account-level exception that stopped processing
        successful: Entity identifiers already enriched before the error occurred
        skipped: Entity identifiers never attempted because processing stopped

    Returns:
        Formatted output message string
    """
    message_parts = [
        COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_HOST_SCRIPT_NAME, error)
    ]

    if successful:
        message_parts.append(
            f"{len(successful)} host(s) were already enriched before this occurred."
        )

    if skipped:
        entities_str = ", ".join(skipped[:5])
        if len(skipped) > 5:
            entities_str += f" and {len(skipped) - 5} more"
        message_parts.append(
            f"{len(skipped)} host(s) were not attempted and were skipped: {entities_str}"
        )

    return "\n".join(message_parts)


@output_handler
def main():
    """
    Enrich IP entities using the Censys get host enrichment endpoint.

    This action retrieves focused enrichment data for IP addresses using the
    Censys get host enrichment API, including reputation, GreyNoise
    classification, and privacy (TOR/VPN/proxy) signals, in addition to the
    standard host intelligence fields. Unlike Enrich Host - Get Host API, this
    action calls the API once per IP address since the underlying endpoint
    does not support batch requests.

    The instance-level "Enable Get Host Enrichment API" config toggle gates
    whether this API is used at all. When disabled, the action ends COMPLETED
    with a false result value so a playbook's Previous Actions Condition can
    branch on that result and fall back to Enrich Host - Get Host API without
    treating it as a crash - this is an expected, routine state, not an error.
    Any account-level API error (401 Unauthorized, 403 Forbidden, 409 Feature
    Not Enabled, 429 Rate Limit) or unrecognized top-level error ends the
    action FAILED, matching every other action in this integration - these
    indicate a real access/credentials/quota problem or an unanticipated bug,
    not a routine bypass condition. The playbook step running this action is
    configured with AutoSkipOnFailure so a FAILED run doesn't block the
    downstream Previous Actions Condition from evaluating, and result_value is
    always set to false on the FAILED path (see below), so the condition's
    existing "result equals false" check still correctly routes to the
    Enrich Host - Get Host API fallback.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message: Status message with enrichment summary
            - result_value: True if any entities enriched, False otherwise
            - status: Execution state (COMPLETED or FAILED)
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_HOST_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Per-instance rollout toggle for the new host enrichment API. Resolved from
    # whichever Censys instance the platform picked (dynamic/named/fallback), so
    # each instance can independently opt in/out without playbook changes.
    enable_new_api = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        ENABLE_NEW_HOST_ENRICHMENT_PARAM,
        input_type=bool,
        is_mandatory=False,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("================= Main - Started =================")

    if not enable_new_api:
        siemplify.LOGGER.info(NEW_HOST_ENRICHMENT_DISABLED_MESSAGE)
        siemplify.result.add_result_json([])
        siemplify.end(
            NEW_HOST_ENRICHMENT_DISABLED_MESSAGE,
            RESULT_VALUE_FALSE,
            EXECUTION_STATE_COMPLETED,
        )
        return

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    output_message = ""
    top_level_error_occurred = False

    # Entity tracking
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    invalid_entities = []
    skipped_entities = []
    json_results = []
    ip_entities = []
    account_level_error = None

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

            more_text = (
                f" and {len(invalid_ips) - 5} more" if len(invalid_ips) > 5 else ""
            )
            siemplify.LOGGER.info(
                f"Found {len(invalid_ips)} invalid IP(s): {', '.join(invalid_ips[:5])}{more_text}"
            )

        # Skip processing if no valid IPs
        if not valid_ips:
            output_message = "No valid IP addresses to process." \
                 f" All {len(invalid_ips)} IP(s) are invalid."
            siemplify.LOGGER.error(output_message)
            siemplify.result.add_result_json([])
            siemplify.end(output_message, RESULT_VALUE_FALSE, EXECUTION_STATE_FAILED)
            return

        siemplify.LOGGER.info(f"Processing {len(valid_ips)} valid IP(s)")

        # Create set for O(1) lookup performance
        invalid_set = set(invalid_entities)

        # Process each entity individually - the enrichment endpoint is per-IP only
        for entity in ip_entities:
            entity_identifier = entity.identifier

            # Skip invalid IPs (already tracked)
            if entity_identifier in invalid_set:
                continue

            siemplify.LOGGER.info(f"Processing entity: {entity_identifier}")

            try:
                response = censys_manager.get_host_enrichment(entity_identifier)
                host_model = HostEnrichmentDatamodel(response)

                if not host_model.is_found():
                    siemplify.LOGGER.info(f"No data found for {entity_identifier}")
                    not_found_entities.append(entity_identifier)
                    continue

                enrichment_data = host_model.get_enrichment_data()

                if not enrichment_data:
                    siemplify.LOGGER.info(
                        f"No enrichment data available for {entity_identifier}"
                    )
                    not_found_entities.append(entity_identifier)
                    continue

                # Remove old Censys IP enrichment data
                remove_ip_enrichment(entity)
                siemplify.LOGGER.info(
                    f"Removed old IP enrichment data for {entity_identifier}"
                )

                # Add timestamp and enrich entity
                enrichment_data[f"{ENRICHMENT_PREFIX}last_enriched"] = (
                    datetime.utcnow().isoformat() + "Z"
                )

                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True

                # Store results
                successful_entities.append(entity_identifier)
                json_results.append(
                    {
                        "Entity": entity_identifier,
                        "EntityResult": host_model.to_json(),
                    }
                )

                siemplify.LOGGER.info(f"Successfully enriched: {entity_identifier}")

            except ItemNotFoundException:
                siemplify.LOGGER.info(f"No data found for {entity_identifier}")
                not_found_entities.append(entity_identifier)

            except (
                UnauthorizedErrorException,
                ForbiddenErrorException,
                FeatureNotEnabledException,
                RateLimitException,
            ) as e:
                # Account-level error: every remaining IP would fail the exact
                # same way, so stop attempting the rest instead of hammering the
                # API with calls that can't succeed. This fails the action -
                # matching every other action in this integration - since it
                # signals a real access/credentials/quota problem. The
                # playbook step is configured with AutoSkipOnFailure, and
                # result_value stays false on this path, so the fallback
                # condition to Enrich Host - Get Host API still fires.
                siemplify.LOGGER.error(
                    f"Account-level Censys API error on {entity_identifier}: {e}"
                )
                account_level_error = e
                break

            except Exception as e:
                error_message = f"Failed to process {entity_identifier}: {e}"
                siemplify.LOGGER.error(error_message)
                siemplify.LOGGER.exception(e)
                failed_entities.append(entity_identifier)

        if account_level_error is not None:
            handled_entities = (
                set(successful_entities)
                | set(not_found_entities)
                | set(failed_entities)
                | invalid_set
            )
            skipped_entities.extend(
                entity.identifier
                for entity in ip_entities
                if entity.identifier not in handled_entities
            )

    except ValueError as e:
        output_message = f"Invalid parameter value: {str(e)}\nPlease verify your input " \
            "parameters and try again."
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_HOST_SCRIPT_NAME, e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        top_level_error_occurred = True

    # Build output message if execution completed successfully (not via the
    # error path above, which already set its own output_message/result_value)
    if status == EXECUTION_STATE_COMPLETED and not top_level_error_occurred:
        if account_level_error is not None:
            output_message = _build_account_level_error_message(
                account_level_error,
                successful_entities,
                skipped_entities,
            )
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE
        else:
            output_message = _build_output_message(
                successful_entities,
                not_found_entities,
                failed_entities,
                invalid_entities,
            )
            result_value = RESULT_VALUE_TRUE if successful_entities else RESULT_VALUE_FALSE

        # Update entities in Siemplify - any entity enriched before an
        # account-level error occurred should still have its data persisted,
        # even though the action itself ends FAILED.
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
