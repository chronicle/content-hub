from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Sequence

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

ACCOUNT_LEVEL_EXCEPTIONS = (
    UnauthorizedErrorException,
    ForbiddenErrorException,
    FeatureNotEnabledException,
    RateLimitException,
)


@dataclasses.dataclass(slots=True)
class EnrichmentSummary:
    """Tracks entity identifiers by outcome across the per-IP enrichment loop."""

    successful: list[str] = dataclasses.field(default_factory=list)
    not_found: list[str] = dataclasses.field(default_factory=list)
    failed: list[str] = dataclasses.field(default_factory=list)
    invalid: list[str] = dataclasses.field(default_factory=list)
    skipped: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(slots=True)
class EnrichmentContext:
    """Bundles the collaborators needed to enrich entities, to keep helper
    function signatures within the repo's 3-argument guideline."""

    censys_manager: APIManager
    siemplify: SiemplifyAction
    summary: EnrichmentSummary


def _format_entity_preview(entities: Sequence[str], max_items: int = 5) -> str:
    """Format entity identifiers as a comma-separated preview, truncated with a count.

    Args:
        entities: Entity identifiers to format
        max_items: Maximum number of identifiers to include before truncating

    Returns:
        Comma-separated preview string, e.g. "a, b, c and 2 more"
    """
    preview = ", ".join(entities[:max_items])
    if len(entities) > max_items:
        preview += f" and {len(entities) - max_items} more"
    return preview


def _build_output_message(summary: EnrichmentSummary) -> str:
    """
    Build detailed output message with entity information.

    Args:
        summary: Entity identifiers grouped by outcome

    Returns:
        Formatted output message string
    """
    message_parts = []

    if summary.successful:
        message_parts.append(
            f"Successfully enriched {len(summary.successful)} host(s) from Censys."
        )

    if summary.invalid:
        message_parts.append(
            f"{len(summary.invalid)} IP(s) skipped due to invalid format: "
            f"{_format_entity_preview(summary.invalid)}"
        )

    if summary.not_found:
        message_parts.append(
            f"{len(summary.not_found)} host(s) not found in Censys: "
            f"{_format_entity_preview(summary.not_found)}"
        )

    if summary.failed:
        message_parts.append(
            f"{len(summary.failed)} host(s) failed to process: "
            f"{_format_entity_preview(summary.failed)}"
        )

    if not message_parts:
        return "No hosts were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


def _build_account_level_error_message(
    error: Exception,
    summary: EnrichmentSummary,
) -> str:
    """
    Build the output message when an account-level Censys API error (no access,
    feature not enabled, or daily quota reached) stopped the loop early.

    Uses the same COMMON_ACTION_ERROR_MESSAGE template every other action in
    this integration uses for any CensysException, so the message reads the
    same way regardless of which action or error type produced it.

    Args:
        error: The account-level exception that stopped processing
        summary: Entity identifiers grouped by outcome

    Returns:
        Formatted output message string
    """
    message_parts = [
        COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_HOST_SCRIPT_NAME, error)
    ]

    if summary.successful:
        message_parts.append(
            f"{len(summary.successful)} host(s) were already enriched before this "
            "occurred."
        )

    if summary.skipped:
        message_parts.append(
            f"{len(summary.skipped)} host(s) were not attempted and were skipped: "
            f"{_format_entity_preview(summary.skipped)}"
        )

    return "\n".join(message_parts)


def _apply_enrichment(entity, host_model: HostEnrichmentDatamodel) -> dict | None:
    """Apply enrichment data to an entity if the model produced any.

    Args:
        entity: The IP entity to enrich
        host_model: Parsed enrichment response for this entity

    Returns:
        A JSON result entry if enrichment data was applied, otherwise None
    """
    enrichment_data = host_model.get_enrichment_data()
    if not enrichment_data:
        return None

    remove_ip_enrichment(entity)

    enrichment_data[f"{ENRICHMENT_PREFIX}last_enriched"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    entity.additional_properties.update(enrichment_data)
    entity.is_enriched = True

    return {"Entity": entity.identifier, "EntityResult": host_model.to_json()}


def _enrich_single_entity(
    entity,
    ctx: EnrichmentContext,
    json_results: list[dict],
) -> Exception | None:
    """Enrich a single IP entity and record its outcome on the summary.

    Args:
        entity: The IP entity to enrich
        ctx: Shared enrichment collaborators (API manager, logger, summary)
        json_results: Accumulated per-entity JSON results, updated in place

    Returns:
        The account-level exception if one occurred, otherwise None
    """
    entity_identifier = entity.identifier
    ctx.siemplify.LOGGER.info(f"Processing entity: {entity_identifier}")

    try:
        response = ctx.censys_manager.get_host_enrichment(entity_identifier)
        host_model = HostEnrichmentDatamodel(response)

        if not host_model.is_found():
            ctx.siemplify.LOGGER.info(f"No data found for {entity_identifier}")
            ctx.summary.not_found.append(entity_identifier)
            return None

        result = _apply_enrichment(entity, host_model)
        if result is None:
            ctx.siemplify.LOGGER.info(
                f"No enrichment data available for {entity_identifier}"
            )
            ctx.summary.not_found.append(entity_identifier)
            return None

        ctx.summary.successful.append(entity_identifier)
        json_results.append(result)
        ctx.siemplify.LOGGER.info(f"Successfully enriched: {entity_identifier}")
        return None

    except ItemNotFoundException:
        ctx.siemplify.LOGGER.info(f"No data found for {entity_identifier}")
        ctx.summary.not_found.append(entity_identifier)
        return None

    except ACCOUNT_LEVEL_EXCEPTIONS as e:
        # Account-level error: every remaining IP would fail the exact
        # same way, so stop attempting the rest instead of hammering the
        # API with calls that can't succeed. This fails the action -
        # matching every other action in this integration - since it
        # signals a real access/credentials/quota problem. The
        # playbook step is configured with AutoSkipOnFailure, and
        # result_value stays false on this path, so the fallback
        # condition to Enrich Host - Get Host API still fires.
        ctx.siemplify.LOGGER.error(
            f"Account-level Censys API error on {entity_identifier}: {e}"
        )
        return e

    except Exception as e:
        ctx.siemplify.LOGGER.error(f"Failed to process {entity_identifier}: {e}")
        ctx.siemplify.LOGGER.exception(e)
        ctx.summary.failed.append(entity_identifier)
        return None


def _record_skipped_entities(ip_entities: list, ctx: EnrichmentContext) -> None:
    """Record entities never attempted after an account-level error stopped the loop.

    Args:
        ip_entities: All IP entities in scope
        ctx: Shared enrichment collaborators (API manager, logger, summary)
    """
    handled_entities = (
        set(ctx.summary.successful)
        | set(ctx.summary.not_found)
        | set(ctx.summary.failed)
        | set(ctx.summary.invalid)
    )
    ctx.summary.skipped.extend(
        entity.identifier
        for entity in ip_entities
        if entity.identifier not in handled_entities
    )


def _process_ip_entities(
    ip_entities: list,
    ctx: EnrichmentContext,
) -> tuple[list[dict], Exception | None]:
    """Process each IP entity individually against the per-IP enrichment endpoint.

    Args:
        ip_entities: All IP entities in scope (including already-tracked invalid ones)
        ctx: Shared enrichment collaborators (API manager, logger, summary)

    Returns:
        Tuple of (accumulated JSON results, account-level exception or None)
    """
    json_results: list[dict] = []
    invalid_set = set(ctx.summary.invalid)
    account_level_error: Exception | None = None

    for entity in ip_entities:
        if entity.identifier in invalid_set:
            continue

        account_level_error = _enrich_single_entity(entity, ctx, json_results)
        if account_level_error is not None:
            break

    if account_level_error is not None:
        _record_skipped_entities(ip_entities, ctx)

    return json_results, account_level_error


def _finalize_action(
    ctx: EnrichmentContext,
    ip_entities: list,
    account_level_error: Exception | None,
) -> tuple[str, bool, str]:
    """Build the final output message, result value, and execution state.

    Args:
        ctx: Shared enrichment collaborators (API manager, logger, summary)
        ip_entities: All IP entities in scope, used to push updates back to SOAR
        account_level_error: The account-level exception that stopped processing,
            if any

    Returns:
        Tuple of (output_message, result_value, status)
    """
    summary = ctx.summary
    if account_level_error is not None:
        output_message = _build_account_level_error_message(
            account_level_error, summary
        )
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
    else:
        output_message = _build_output_message(summary)
        status = EXECUTION_STATE_COMPLETED
        result_value = (
            RESULT_VALUE_TRUE if summary.successful else RESULT_VALUE_FALSE
        )

    # Update entities in Siemplify - any entity enriched before an
    # account-level error occurred should still have its data persisted,
    # even though the action itself ends FAILED.
    if summary.successful:
        ctx.siemplify.update_entities(ip_entities)

    return output_message, result_value, status


def _init_siemplify_action() -> tuple[SiemplifyAction, bool]:
    """Create the SiemplifyAction instance and resolve the rollout toggle.

    Returns:
        Tuple of (siemplify action instance, whether the new API is enabled)
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_HOST_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
    return siemplify, enable_new_api


def _validate_and_filter_ips(
    ip_entities: list, summary: EnrichmentSummary, siemplify: SiemplifyAction
) -> list[str]:
    """Split IP entities into valid/invalid and record invalid ones on the summary.

    Args:
        ip_entities: All IP entities in scope
        summary: Entity identifiers grouped by outcome, updated in place
        siemplify: Siemplify action instance for logging

    Returns:
        The list of valid IP addresses
    """
    ip_addresses = [entity.identifier for entity in ip_entities]
    valid_ips, invalid_ips = filter_valid_ips(ip_addresses)

    if invalid_ips:
        summary.invalid.extend(invalid_ips)
        siemplify.LOGGER.info(
            f"Found {len(invalid_ips)} invalid IP(s): "
            f"{_format_entity_preview(invalid_ips)}"
        )

    return valid_ips


def _run_enrichment(
    siemplify: SiemplifyAction, censys_manager: APIManager
) -> tuple[str, bool, str, list[dict]]:
    """Validate IP entities and run the per-IP enrichment loop.

    Args:
        siemplify: Siemplify action instance for logging and entity access
        censys_manager: Initialized Censys API manager

    Returns:
        Tuple of (output_message, result_value, status, json_results).
    """
    ip_entities = get_ip_entities(siemplify)
    if not ip_entities:
        return (
            NO_ADDRESS_ENTITIES_ERROR,
            RESULT_VALUE_TRUE,
            EXECUTION_STATE_COMPLETED,
            [],
        )

    siemplify.LOGGER.info(f"Found {len(ip_entities)} IP entities to process")

    summary = EnrichmentSummary()
    valid_ips = _validate_and_filter_ips(ip_entities, summary, siemplify)

    if not valid_ips:
        output_message = (
            f"No valid IP addresses to process. All {len(summary.invalid)} "
            "IP(s) are invalid."
        )
        siemplify.LOGGER.error(output_message)
        return output_message, RESULT_VALUE_FALSE, EXECUTION_STATE_FAILED, []

    siemplify.LOGGER.info(f"Processing {len(valid_ips)} valid IP(s)")

    ctx = EnrichmentContext(censys_manager, siemplify, summary)
    json_results, account_level_error = _process_ip_entities(ip_entities, ctx)

    output_message, result_value, status = _finalize_action(
        ctx, ip_entities, account_level_error
    )
    return output_message, result_value, status, json_results


@output_handler
def main() -> None:
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
    """
    siemplify, enable_new_api = _init_siemplify_action()

    if not enable_new_api:
        siemplify.LOGGER.info(NEW_HOST_ENRICHMENT_DISABLED_MESSAGE)
        siemplify.result.add_result_json([])
        siemplify.end(
            NEW_HOST_ENRICHMENT_DISABLED_MESSAGE,
            RESULT_VALUE_FALSE,
            EXECUTION_STATE_COMPLETED,
        )
        return

    api_key, organization_id, verify_ssl = get_integration_params(siemplify)
    json_results: list[dict] = []

    try:
        censys_manager = APIManager(
            api_key=api_key,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        output_message, result_value, status, json_results = _run_enrichment(
            siemplify, censys_manager
        )

    except ValueError as e:
        output_message = (
            f"Invalid parameter value: {e}\n"
            "Please verify your input parameters and try again."
        )
        siemplify.LOGGER.error(output_message)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_HOST_SCRIPT_NAME, e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED

    siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("================= Main - Finished =================")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
