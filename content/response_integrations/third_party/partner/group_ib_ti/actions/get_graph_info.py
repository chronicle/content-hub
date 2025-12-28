from __future__ import annotations

import time

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.config import Config
from ..core.utils_manager import EntityValidator, GIBConnector

ev = EntityValidator()


@output_handler
def main():
    # Google Chronicle base class initialization
    siemplify = SiemplifyAction()

    # Google Chronicle base class set up
    siemplify.script_name = Config.GC_GRAPH_SCRIPT_NAME

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

    # Set allowed list for entity type
    allowed_list = ["ip", "domain"]

    # Gather data
    for _entity, _entity_type in received_entities:
        siemplify.LOGGER.info("entity: {}, type: {}".format(_entity, _entity_type))

        if _entity:
            # if _entity == "jhon-ws@siemplify.local":
            #     _entity = "google.com"
            #     _entity_type = "domain"

            if _entity_type not in allowed_list:
                siemplify.LOGGER.info(
                    "type: {} - is not allowed, skipping {}".format(_entity_type, _entity)
                )
                continue

            # Data storage
            result_name = _entity_type + "_results"
            result_json[result_name] = []

            # Create query params
            params = {_entity_type: str(_entity)}

            # Extract data
            res = poller.send_request(endpoint="utils/graph/{}".format(_entity_type), params=params)

            # Fill in result holder
            result_json[result_name].append(res)

            # Sleep to keep API active
            time.sleep(1)

    # Add result to Google Chronicle base class
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
