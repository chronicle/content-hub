from __future__ import annotations

import time

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.config import Config
from ..core.utils_manager import EntityValidator, GIBConnector

ev = EntityValidator()


@output_handler
def main():
    # Google Chronicle base class initialization
    siemplify = SiemplifyAction()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_SEARCH_SCRIPT_NAME

    # Get basic collection configuration
    mapping_parser_enabled = extract_action_param(
        siemplify, param_name="Enable mapping parser", print_value=True
    )

    # Get poller
    poller = GIBConnector(siemplify).init_action_poller()

    siemplify.LOGGER.info("──── GATHER ENTITIES")

    # Gather received entities and detect their type return [(entity.identifier, type), ...]
    received_entities = [
        ev.get_entity_type(entity.identifier) for entity in siemplify.target_entities
    ]

    siemplify.LOGGER.info("──── PARSE DATA")

    # Create result holder
    result_json = {}

    # Gather data
    for _entity, _entity_type in received_entities:
        siemplify.LOGGER.info("entity: {}, type: {}".format(_entity, _entity_type))

        if _entity:
            # if _entity == "jhon-ws@siemplify.local":
            #     _entity = "8.8.8.8"
            #     _entity_type = "ip"

            # Get collections which contains search results
            collections_containers = [
                response.get("apiPath") for response in poller.global_search(_entity)
            ]
            siemplify.LOGGER.info(collections_containers)

            # Sleep to keep API active
            time.sleep(1)

            # Extract data for each collection
            for collection_name in collections_containers:
                siemplify.LOGGER.info("Collection: {}".format(collection_name))

                # Data storage for each collection
                result_name = collection_name.replace("/", "_")
                result_json[result_name] = []

                # Create query params
                query = "{entity_type}:{entity}".format(entity_type=_entity_type, entity=_entity)

                # Create generator
                generator = poller.create_update_generator(
                    collection_name=collection_name, query=query, limit=3000
                )

                # Sleep to keep API active
                time.sleep(1)

                # Parse data
                for portion in generator:
                    if mapping_parser_enabled == "true":
                        # Extract data and parse it using mapping keys
                        parsed_portion = portion.parse_portion()
                    else:
                        # Extract data and collect raw dict items
                        parsed_portion = portion.raw_dict.get("items")

                    # Fill in result holder
                    result_json[result_name].extend(parsed_portion)

                    # Sleep to keep API active
                    time.sleep(1)

                    siemplify.LOGGER.info("Feeds added: {}".format(len(parsed_portion)))

    # Add result to Gogle Chronicle base class
    siemplify.result.add_result_json(result_json)

    siemplify.LOGGER.info("──── END THE TASK")

    # Prepare output message
    output_message = (
        "output message : All is done"  # human-readable message, showed in UI as the action result
    )
    result_value = True  # Set a simple result value, used for playbook if\else and placeholders.
    status = (
        EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    )

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )

    # End the playbook
    siemplify.end(output_message, result_value=result_value, execution_state=status)


if __name__ == "__main__":
    main()
