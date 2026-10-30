from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Sequence

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import Entity, SingleJson

from ..core.api_manager import APIManager
from ..core.censys_exceptions import (
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
)
from ..core.datamodels import HostEnrichmentDatamodel
from ..core.reputation import ReputationTables
from ..core.utils import (
    filter_valid_ips,
    get_integration_params,
    get_ip_entities,
    remove_ip_enrichment,
)

ACCOUNT_LEVEL_EXCEPTIONS: tuple[type[Exception], ...] = (
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
    """Build detailed output message with entity information.

    Args:
        summary: Entity identifiers grouped by outcome

    Returns:
        Formatted output message string
    """
    message_parts: list[str] = []

    if summary.successful:
        message_parts.append(f"Successfully enriched {len(summary.successful)} host(s) from Censys.")

    if summary.invalid:
        message_parts.append(
            f"{len(summary.invalid)} IP(s) skipped due to invalid format: {_format_entity_preview(summary.invalid)}"
        )

    if summary.not_found:
        message_parts.append(
            f"{len(summary.not_found)} host(s) not found in Censys: {_format_entity_preview(summary.not_found)}"
        )

    if summary.failed:
        message_parts.append(
            f"{len(summary.failed)} host(s) failed to process: {_format_entity_preview(summary.failed)}"
        )

    if not message_parts:
        return "No hosts were enriched. No matching data found in Censys."

    return "\n".join(message_parts)


def _build_account_level_error_message(
    error: Exception,
    summary: EnrichmentSummary,
) -> str:
    """Build the output message when an account-level Censys API error (no
    access, feature not enabled, or daily quota reached) stopped the loop early.

    Uses the same COMMON_ACTION_ERROR_MESSAGE template every other action in
    this integration uses for any CensysException, so the message reads the
    same way regardless of which action or error type produced it.

    Args:
        error: The account-level exception that stopped processing
        summary: Entity identifiers grouped by outcome

    Returns:
        Formatted output message string
    """
    message_parts: list[str] = [COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_HOST_SCRIPT_NAME, error)]

    if summary.successful:
        message_parts.append(f"{len(summary.successful)} host(s) were already enriched before this occurred.")

    if summary.skipped:
        message_parts.append(
            f"{len(summary.skipped)} host(s) were not attempted and were skipped: "
            f"{_format_entity_preview(summary.skipped)}"
        )

    return "\n".join(message_parts)


class EnrichHost(Action):
    """Enrich IP entities using the Censys get host enrichment endpoint.

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
    always set to false on the FAILED path, so the condition's existing
    "result equals false" check still correctly routes to the Enrich Host -
    Get Host API fallback.

    On a normal COMPLETED run, result_value is true when at least one host was
    enriched, or when nothing was enriched but nothing failed either (every IP
    was simply not found in Censys). It is false only when the run produced
    per-IP failures and no enrichment. A not-found host is therefore never a
    reason to fall back, which avoids a second, redundant API call per IP.
    """

    def __init__(self) -> None:
        super().__init__(ENRICH_HOST_SCRIPT_NAME)
        self.error_output_message: str = f"Error while executing action {ENRICH_HOST_SCRIPT_NAME}."
        # The base class only sends the JSON result when it is non-empty, so
        # the disabled-toggle / no-entities / all-invalid paths send none. This
        # is intentional: the fallback condition in the Censys - Host Enrichment
        # Block routes on ScriptResult, never on this action's JsonResult.
        self.json_results: list[SingleJson] = []
        self.summary: EnrichmentSummary = EnrichmentSummary()
        self.reputation_tables: ReputationTables = ReputationTables()
        self.ip_entities: list[Entity] = []
        self.account_level_error: Exception | None = None

    def _extract_action_parameters(self) -> None:
        # Per-instance rollout toggle for the new host enrichment API. Resolved
        # from whichever Censys instance the platform picked (dynamic/named/
        # fallback), so each instance can independently opt in/out without
        # playbook changes.
        self.params.enable_new_api = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name=ENABLE_NEW_HOST_ENRICHMENT_PARAM,
            input_type=bool,
            is_mandatory=False,
            default_value=False,
            print_value=True,
        )

    def _init_api_clients(self) -> APIManager | None:
        if not self.params.enable_new_api:
            return None

        api_key, organization_id, verify_ssl = get_integration_params(self.soar_action)
        return APIManager(
            api_key=api_key,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
            siemplify=self.soar_action,
        )

    def _perform_action(self, _: Entity | None = None) -> None:
        if not self.params.enable_new_api:
            self.logger.info(NEW_HOST_ENRICHMENT_DISABLED_MESSAGE)
            self.output_message = NEW_HOST_ENRICHMENT_DISABLED_MESSAGE
            self.result_value = False
            return

        self.ip_entities = get_ip_entities(self.soar_action)
        if not self.ip_entities:
            self.output_message = NO_ADDRESS_ENTITIES_ERROR
            self.result_value = True
            return

        self.logger.info(f"Found {len(self.ip_entities)} IP entities to process")

        if not self._validate_and_filter_ips():
            self._fail_all_invalid()
            return

        self._process_ip_entities()
        self._set_final_result()

    def _validate_and_filter_ips(self) -> list[str]:
        """Split IP entities into valid/invalid and record invalid ones.

        Returns:
            The list of valid IP addresses
        """
        ip_addresses: list[str] = [e.identifier for e in self.ip_entities]
        valid_ips, invalid_ips = filter_valid_ips(ip_addresses)

        if invalid_ips:
            self.summary.invalid.extend(invalid_ips)
            self.logger.info(f"Found {len(invalid_ips)} invalid IP(s): {_format_entity_preview(invalid_ips)}")

        return valid_ips

    def _fail_all_invalid(self) -> None:
        """Fail the action when none of the IP entities has a valid format."""
        self.output_message = f"No valid IP addresses to process. All {len(self.summary.invalid)} IP(s) are invalid."
        self.logger.error(self.output_message)
        self.result_value = False
        self.execution_state = ExecutionState.FAILED

    def _process_ip_entities(self) -> None:
        """Enrich each valid IP entity against the per-IP enrichment endpoint.

        Stops at the first account-level error, since every remaining IP
        would fail the exact same way, and records the untouched IPs as
        skipped.
        """
        invalid_set = set(self.summary.invalid)

        for entity in self.ip_entities:
            if entity.identifier in invalid_set:
                continue

            self.account_level_error = self._enrich_single_entity(entity)
            if self.account_level_error is not None:
                self._record_skipped_entities()
                break

    def _record_skipped_entities(self) -> None:
        """Record entities never attempted after an account-level error."""
        handled = (
            set(self.summary.successful)
            | set(self.summary.not_found)
            | set(self.summary.failed)
            | set(self.summary.invalid)
        )
        self.summary.skipped.extend(
            entity.identifier for entity in self.ip_entities if entity.identifier not in handled
        )

    def _enrich_single_entity(self, entity: Entity) -> Exception | None:
        """Enrich a single IP entity and record its outcome on the summary.

        Args:
            entity: The IP entity to enrich

        Returns:
            The account-level exception if one occurred, otherwise None
        """
        identifier: str = entity.identifier
        self.logger.info(f"Processing entity: {identifier}")

        try:
            response = self._api_client.get_host_enrichment(identifier)
            host_model = HostEnrichmentDatamodel(response)

            if not host_model.is_found():
                self.logger.info(f"No data found for {identifier}")
                self.summary.not_found.append(identifier)
                return None

            self._apply_enrichment(entity, host_model)

        except ItemNotFoundException:
            self.logger.info(f"No data found for {identifier}")
            self.summary.not_found.append(identifier)

        except ACCOUNT_LEVEL_EXCEPTIONS as e:
            # Account-level error: every remaining IP would fail the exact
            # same way, so stop attempting the rest instead of hammering the
            # API with calls that can't succeed. This fails the action -
            # matching every other action in this integration - since it
            # signals a real access/credentials/quota problem. The playbook
            # step is configured with AutoSkipOnFailure, and result_value
            # stays false on this path, so the fallback condition to
            # Enrich Host - Get Host API still fires.
            self.logger.error(f"Account-level Censys API error on {identifier}: {e}")
            return e

        except Exception as e:
            self.logger.error(f"Failed to process {identifier}: {e}")
            self.summary.failed.append(identifier)

        return None

    def _apply_enrichment(self, entity: Entity, host_model: HostEnrichmentDatamodel) -> None:
        """Apply enrichment data to an entity and record the outcome.

        Args:
            entity: The IP entity to enrich
            host_model: Parsed enrichment response for this entity
        """
        identifier: str = entity.identifier
        enrichment_data: SingleJson = host_model.get_enrichment_data()
        if not enrichment_data:
            self.logger.info(f"No enrichment data available for {identifier}")
            self.summary.not_found.append(identifier)
            return

        remove_ip_enrichment(entity)
        enrichment_data[f"{ENRICHMENT_PREFIX}last_enriched"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        entity.additional_properties.update(enrichment_data)
        entity.is_enriched = True

        self.summary.successful.append(identifier)
        self.json_results.append({
            "Entity": identifier,
            "EntityResult": host_model.to_json(),
        })
        self.reputation_tables.add(identifier, host_model.host_data.get("reputation"))
        self.logger.info(f"Successfully enriched: {identifier}")

    def _set_final_result(self) -> None:
        """Set the output message, result value and execution state."""
        if self.account_level_error is not None:
            self.output_message = _build_account_level_error_message(self.account_level_error, self.summary)
            self.execution_state = ExecutionState.FAILED
            self.result_value = False
        else:
            self.output_message = _build_output_message(self.summary)
            # The result value tells the playbook whether to fall back to
            # Enrich Host - Get Host API. A routine "not found" (404 or empty
            # resource) is a valid answer, not a reason to fall back: the
            # fallback would hit the same data and spend a second API call per
            # IP. Only per-IP failures with nothing enriched may be transient,
            # so those keep the result false and still reach the fallback.
            self.result_value = bool(self.summary.successful) or not self.summary.failed

        # Update entities in Siemplify - any entity enriched before an
        # account-level error occurred should still have its data persisted,
        # even though the action itself ends FAILED.
        if self.summary.successful:
            self.soar_action.update_entities(self.ip_entities)

    def _finalize(self) -> None:
        self.reputation_tables.add_to_case_wall(self.soar_action)


def main() -> None:
    EnrichHost().run()


if __name__ == "__main__":
    main()
