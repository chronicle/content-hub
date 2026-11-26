from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import DEVICE_ENTITY_TYPES, create_manager, find_devices_for_entity
from ..core.constants import (
    DEFAULT_MAX_PAGES,
    ENRICHMENT_PREFIX,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
)
from ..core.portnox_manager import PortnoxAuthError, PortnoxError, flatten_device_for_enrichment

SCRIPT_NAME = "Enrich Entities"
BLOCKED_FIELD = f"{ENRICHMENT_PREFIX}_IsBlockedByAdmin"


def build_insight(enrichment: dict[str, object]) -> str:
    """Build the entity insight text for one enriched device.

    Args:
        enrichment: The flattened enrichment fields.

    Returns:
        The insight text.
    """
    return (
        f"Portnox Cloud device {enrichment.get(f'{ENRICHMENT_PREFIX}_DeviceId', 'n/a')}\n"
        f"Account: {enrichment.get(f'{ENRICHMENT_PREFIX}_AccountName', 'n/a')}\n"
        f"MACs: {enrichment.get(f'{ENRICHMENT_PREFIX}_MacAddresses', 'n/a')}\n"
        f"IPs: {enrichment.get(f'{ENRICHMENT_PREFIX}_IpAddresses', 'n/a')}\n"
        f"Blocked: {enrichment.get(BLOCKED_FIELD, False)}"
    )


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        input_type=bool,
        default_value=True,
        print_value=True,
    )

    enriched: list[str] = []
    failed: list[str] = []
    json_results: dict[str, object] = {}
    updated_entities = []

    try:
        max_pages = extract_action_param(
            siemplify,
            param_name="Max Pages To Scan",
            input_type=int,
            default_value=DEFAULT_MAX_PAGES,
            print_value=True,
        )
        if max_pages < 1:
            raise ValueError("Max Pages To Scan must be a positive number.")

        manager = create_manager(siemplify)

        for entity in (e for e in siemplify.target_entities if e.entity_type in DEVICE_ENTITY_TYPES):
            siemplify.LOGGER.info(f"Looking up {entity.identifier}")
            try:
                devices = find_devices_for_entity(manager, entity, max_pages)
            except PortnoxAuthError:
                raise
            except PortnoxError as entity_error:
                siemplify.LOGGER.error(f"Failed to look up {entity.identifier}: {entity_error}")
                failed.append(entity.identifier)
                continue

            if not devices:
                siemplify.LOGGER.info(f"No Portnox Cloud device matches {entity.identifier}")
                failed.append(entity.identifier)
                continue

            device = devices[0]
            json_results[entity.identifier] = device

            enrichment = flatten_device_for_enrichment(device)
            entity.additional_properties.update(enrichment)
            entity.is_enriched = True
            if enrichment.get(BLOCKED_FIELD) in (True, "True", "true"):
                entity.is_suspicious = True
            if create_insight:
                siemplify.add_entity_insight(entity, build_insight(enrichment), triggered_by=INTEGRATION_DISPLAY_NAME)

            updated_entities.append(entity)
            enriched.append(entity.identifier)

        if updated_entities:
            siemplify.update_entities(updated_entities)
        if json_results:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

        messages = []
        if enriched:
            messages.append(
                f"Successfully enriched the following entities using {INTEGRATION_DISPLAY_NAME}: {', '.join(enriched)}"
            )
        if failed:
            messages.append(
                f"Action wasn't able to enrich the following entities using {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(failed)}"
            )
        if not messages:
            messages.append("No MAC address, IP address or hostname entities to enrich.")

        status = EXECUTION_STATE_COMPLETED
        result_value = bool(enriched)
        output_message = "\n".join(messages)

    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
