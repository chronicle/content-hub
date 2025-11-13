"Enrich Entities action to enrich HOSTNAME and USER entities with data from XM Cyber platform."

from __future__ import annotations

from datetime import datetime

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
)

from ..core.ApiManager import ApiManager
from ..core.constants import (
    ENRICHMENT_PREFIX,
    ENTITY_ID_FIELD,
    INTEGRATION_NAME,
    PREFIX_PARAMETER_FOR_LABELS,
    SUPPORTED_ENTITY_TYPES,
)
from ..core.utils import get_integration_params
from ..core.XMCyberException import XMCyberException


def get_entities_from_the_event(events):
    """
    Extract entities from the given events.

    Args:
        events (list): The list of events.

    Returns:
        list: A list of tuples, where each tuple contains the entity ID and the event ID.
    """
    event_entities = []
    for event in events:
        event_properties = event.additional_properties
        # Get the entity ID for user and asset
        entity_id_map = {
            "asset": (
                event_properties.get(ENTITY_ID_FIELD.format("asset")),
                event_properties.get("event_principal_asset_hostname"),
            ),
            "user": (
                event_properties.get(ENTITY_ID_FIELD.format("user")),
                event_properties.get("event_principal_user_userid"),
            ),
        }

        # Iterate over the entity ID map and create the entity object
        for entity_type, (entity_id, soar_id) in entity_id_map.items():
            if entity_id is None:
                continue

            # Check if the entity is a XM Cyber entity
            is_xm_cyber_entity = event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(entity_type, "Entity Type")
            )
            if not is_xm_cyber_entity:
                continue

            # Only append if soar_id is not None and is a string
            if soar_id is not None and isinstance(soar_id, str):
                event_entities.append((soar_id, event.identifier))

    return event_entities


def get_not_found_entities(response, filtered_entities):
    """
    Get entities that are not found in the response.

    Args:
        response (dict): A dictionary with entity IDs as keys and their properties as values.
        filtered_entities (list): A list of entities to check if they are present in the response.

    Returns:
        list: A list of entity IDs that are not found in the response.
    """
    not_found_entities = []
    for entity in filtered_entities:
        if entity.identifier.lower() not in response.keys():
            not_found_entities.append(entity.identifier)
    return not_found_entities


def filter_entities(siemplify_action):
    """Filter entities by the following checks
        - Supported entity types by XMCyber
        - Entity already enriched and present in the event
        - Entity already enriched with in last 24 hours

    Args:
        siemplify_action (SiemplifyAction): The SiemplifyAction object containing the
                                            target entities and current alert.
    Returns:
        list: A list of entities that need to be enriched.
        str: A string with an error message if an entity doesn't match the criteria.
    """
    output_message = ""
    entities = siemplify_action.target_entities
    events = siemplify_action.current_alert.security_events
    logger = siemplify_action.LOGGER
    event_entities = get_entities_from_the_event(events)

    entities = [entity for entity in entities if entity.entity_type in SUPPORTED_ENTITY_TYPES]
    entities_to_skip = set()
    for entity, event_id in event_entities:
        for _entity in entities:
            if _entity.identifier.lower() == entity.lower():
                entities_to_skip.add(_entity)
                logger.info(
                    f"Entity {_entity.identifier} found in the event {event_id}. "
                    f"Skipping from the enrichment.\n"
                )
                output_message += (
                    f"Entity {_entity.identifier} found in the event {event_id}. "
                    f"Skipping from the enrichment.\n"
                )
    for _entity in entities_to_skip:
        if _entity in entities:
            entities.remove(_entity)

    entities_to_enrich = []
    for entity in entities:
        success, _output_message = is_entity_already_enriched(entity, logger)
        output_message += _output_message
        if success:
            logger.info(
                f"Entity {entity.identifier} was already enriched in the last 24 hours. "
                f"Skipping from the enrichment.\n"
            )
            output_message += (
                f"Entity {entity.identifier} was already enriched in the last 24 hours. "
                f"Skipping from the enrichment.\n"
            )

        else:
            entities_to_enrich.append(entity)
    return entities_to_enrich, output_message


def is_entity_already_enriched(entity, logger):
    """Check if an entity was already enriched in the last 24 hours.

    Args:
        entity (Entity): The entity to check.
        logger: Logger instance to log messages.

    Returns:
        tuple: A tuple containing a boolean indicating if the entity was already enriched,
               and a string with an output message.
    """
    output_message = ""
    last_enrichment_time = entity.additional_properties.get(f"{ENRICHMENT_PREFIX}_last_enriched")
    if last_enrichment_time:
        # Try multiple datetime formats to handle timezone offset with/without colon
        datetime_formats = [
            "%Y-%m-%d %H:%M:%S.%f%z",  # Format without colon in timezone (e.g., +0000)
            "%Y-%m-%d %H:%M:%S%z",     # Format without microseconds
        ]
        
        parsed_time = None
        for fmt in datetime_formats:
            try:
                # Handle timezone offset with colon by removing it before parsing
                time_str = last_enrichment_time
                if '+' in time_str or time_str.count('-') > 2:  # Has timezone
                    # Remove colon from timezone offset (e.g., +05:30 -> +0530)
                    import re
                    time_str = re.sub(r'([+-]\d{2}):(\d{2})$', r'\1\2', time_str)
                
                parsed_time = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        
        if parsed_time is None:
            logger.info(
                f"The value of {ENRICHMENT_PREFIX}_last_enriched' field: {last_enrichment_time} "
                f"could not be parsed with any expected format. Hence, enriching the "
                f"entity: {entity.identifier} again...\n"
            )
            output_message = (
                f"The value of {ENRICHMENT_PREFIX}_last_enriched' field: {last_enrichment_time} "
                f"could not be parsed with any expected format. Hence, enriching the "
                f"entity: {entity.identifier} again...\n"
            )
            return False, output_message
        
        last_enrichment_time = parsed_time

        current_time = convert_unixtime_to_datetime(unix_now())
        logger.info(f"Current time: {current_time}, Last enrichment time: {last_enrichment_time}")
        delta = current_time - last_enrichment_time

        # Entity already enriched
        if delta.total_seconds() < 24 * 60 * 60:
            return True, output_message

    return False, output_message


@output_handler
def main():
    """
    Enrich Entities action is used to enrich the HOSTNAME and USER Entities from the
    information available in XM Cyber platform.
    """
    siemplify = SiemplifyAction()
    auth_type, base_url, api_key = get_integration_params(siemplify)

    result_value = False
    is_success = False
    output_message = ""
    status = EXECUTION_STATE_FAILED

    try:
        api_manager = ApiManager(auth_type, base_url, api_key, siemplify.LOGGER)
        if api_manager.error:
            raise Exception(api_manager.error)

        successful_entities, failed_entities = [], []
        status = EXECUTION_STATE_COMPLETED

        filtered_entities, output_message = filter_entities(siemplify)
        if not filtered_entities:
            is_success = True
            output_message += (
                "No entities of supported types (HOSTNAME/USER) were found in the alert to be "
                "enriched.\n"
            )
        else:
            entities_names = [entity.identifier for entity in filtered_entities]
            is_success, enrichment_data_response = api_manager.enrich_entities(entities_names)
            if not is_success:
                raise XMCyberException(output_message + enrichment_data_response)

            not_found_entities = get_not_found_entities(enrichment_data_response, filtered_entities)
            for entity in filtered_entities:
                try:
                    if entity.identifier in not_found_entities:
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} not found in XMCyber. Skipping enrichment."
                        )
                        output_message += (
                            f"Entity {entity.identifier} not found in XMCyber. "
                            f"Skipping enrichment.\n"
                        )
                        failed_entities.append(entity)
                        continue

                    enrichment_data = enrichment_data_response.get(entity.identifier.lower(), {})
                    enrichment_data["last_enriched"] = str(convert_unixtime_to_datetime(unix_now()))
                    enrichment_data = add_prefix_to_dict(enrichment_data, ENRICHMENT_PREFIX)

                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    successful_entities.append(entity)
                    siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}\n\tResponse: {str(e)}\n"
                    )
                    siemplify.LOGGER.exception(e)
                    output_message += (
                        f"An error occurred on entity {entity.identifier}\n\tResponse: {str(e)}\n"
                    )
                    failed_entities.append(entity)

            if successful_entities:
                entities_names = ", ".join([entity.identifier for entity in successful_entities])
                output_message += f"\nSuccessfully processed entities: {entities_names}"
                siemplify.update_entities(successful_entities)

            if failed_entities:
                entities_names = ", ".join([entity.identifier for entity in failed_entities])
                output_message += f"\nFailed processing entities: {entities_names}"

            status = EXECUTION_STATE_COMPLETED
            result_value = True

        result_value = is_success
    except XMCyberException as e:
        error_message = str(e)
        output_message = error_message
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        error_message = str(e)
        output_message = (
            f"Failed to enrich entities to the {INTEGRATION_NAME} server!\n\tError: {error_message}"
        )
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
