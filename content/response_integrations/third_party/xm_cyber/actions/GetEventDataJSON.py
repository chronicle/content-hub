"""Get Event Data JSON Action."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    ENRICHED_ENTITY_ID_FIELD,
    ENRICHED_PARAMETERS,
    ENRICHMENT_PREFIX,
    ENTITY_ID_FIELD,
    PREFIX_PARAMETER_FOR_ENTITY_ID,
    PREFIX_PARAMETER_FOR_LABELS,
    SUPPORTED_ENTITY_TYPES,
)
from ..core.utils import convert_string, get_integration_params


def get_entity_data(data, entity_type=None):
    """Create entity object from data.

    Args:
        data (dict): Data of the event or entity.
        entity_type (str): The type of field to look. Can be "user" or "asset".
            None for enriched entities.

    Returns:
        dict: The object containing mapping between entity ID and its properties
    """
    PARAMETERS = {*ENRICHED_PARAMETERS, "Entity Type"}
    entity_data = {}
    for parameter in PARAMETERS:
        key = f"{ENRICHMENT_PREFIX}_{parameter}"
        if entity_type is not None:
            key = PREFIX_PARAMETER_FOR_LABELS.format(entity_type, parameter)

        value = data.get(key, "") or ""
        converted_value = convert_string(value)

        if isinstance(converted_value, str) and converted_value == "":
            continue

        entity_data[parameter] = converted_value

    return entity_data


def get_event_entity_data(events, base_url):
    """
    Create entity object from events.

    This function iterates over the security events and extracts the entity data
    from each event. The entity data contains the mapping between entity ID and its
    properties. The function also adds a URL to the entity overview page in XM Cyber
    instance for each entity.

    Args:
        events (SiemplifyAlert): The alert object containing security events.
        base_url (str): The base URL of the XM Cyber instance.

    Returns:
        dict: The object containing mapping between entity ID and its properties
    """
    entity_json = {}

    for event in events:
        event_properties = event.additional_properties

        # Get the entity ID for user and asset
        entity_id_map = {
            "asset": event_properties.get(ENTITY_ID_FIELD.format("asset")),
            "user": event_properties.get(ENTITY_ID_FIELD.format("user")),
        }

        # Iterate over the entity ID map and create the entity object
        for entity_type, entity_id in entity_id_map.items():
            if entity_id is None:
                continue

            # Check if the entity is a XM Cyber entity
            is_xm_cyber_entity = event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(entity_type, "Entity Type")
            )

            if not is_xm_cyber_entity:
                continue
            # Create the entity object
            entity_json[entity_id] = get_entity_data(event_properties, entity_type)

            # Add URL to the entity overview page in XM Cyber instance
            entity_json[entity_id]["url"] = f"{base_url}/#/report/entity/{entity_id}"
    return entity_json


def get_enriched_entity_data(entities, base_url):
    """Create entity object from enriched entities."""
    entity_json = {}

    entities = [entity for entity in entities if entity.entity_type in SUPPORTED_ENTITY_TYPES]

    for entity in entities:
        xm_cyber_identifier = entity.additional_properties.get(ENRICHED_ENTITY_ID_FIELD)
        is_xm_cyber_entity = entity.additional_properties.get(
            PREFIX_PARAMETER_FOR_ENTITY_ID.format("Entity Type")
        )

        if not xm_cyber_identifier or not is_xm_cyber_entity:
            continue

        # enriched_data["Entity ID"] = entity.identifier
        entity_json[xm_cyber_identifier] = get_entity_data(entity.additional_properties)
        entity_json[xm_cyber_identifier]["SecOps Entity ID"] = entity.identifier
        entity_json[xm_cyber_identifier]["url"] = (
            f"{base_url}/#/report/entity/{xm_cyber_identifier}"
        )

    return entity_json


@output_handler
def main():
    """Generate a JSON object mapping between entity ID and its details."""
    result_value = False
    entity_json = {}
    output_message = ""
    status = EXECUTION_STATE_FAILED

    siemplify = SiemplifyAction()
    events = siemplify.current_alert.security_events
    entities = siemplify.target_entities
    _, base_url, _ = get_integration_params(siemplify)

    try:
        event_entities = get_event_entity_data(events, base_url)
        entity_json.update(event_entities)
        enriched_entities = get_enriched_entity_data(entities, base_url)
        entity_json.update(enriched_entities)

        siemplify.result.add_result_json(entity_json)
        if not entity_json:
            output_message = "No XM Cyber entity details found in the alert events/entities."
        else:
            output_message = (
                f"Successfully created entity data object for the following entities: "
                f"{list(entity_json.keys())}"
            )

        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as e:
        error_message = str(e)
        output_message = (
            f"Failed to create JSON object for the entities found in events/entities! "
            f"Error: {error_message}"
        )
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
