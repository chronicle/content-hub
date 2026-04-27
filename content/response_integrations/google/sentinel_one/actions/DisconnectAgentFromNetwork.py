from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SentinelOneManager import SentinelOneManager, SentinelOneAgentNotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import flat_dict_to_csv


# Consts.
SENTINEL_ONE_PROVIDER = "SentinelOne"
ADDRESS = EntityTypes.ADDRESS
HOSTNAME = EntityTypes.HOSTNAME


@output_handler
def main():
    # Define variables.
    errors_dict = {}
    entities_successed = []
    result_value = False
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(SENTINEL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    # Get scope entities.
    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == ADDRESS or entity.entity_type == HOSTNAME
    ]

    # Initiate full scan.
    for entity in scope_entities:
        action_status = False
        try:
            # Get endpoint agent id.
            if entity.entity_type == ADDRESS:
                agent_id = sentinel_one_manager.find_endpoint_agent_id(
                    entity.identifier, by_ip_address=True
                )
            else:
                agent_id = sentinel_one_manager.find_endpoint_agent_id(
                    entity.identifier
                )

            action_status = sentinel_one_manager.disconnect_agent_from_network(agent_id)
        except SentinelOneAgentNotFoundError as err:
            errors_dict[entity.identifier] = str(err)

        if action_status:
            result_value = True
            entities_successed.append(entity)

    # Form output message.
    if entities_successed:
        output_message = f'The following entities were disconnected from the network: {",".join([entity.identifier for entity in entities_successed])}'
    else:
        output_message = "No target entities were disconnected from the network."

    # If were errors present them as a table.
    if errors_dict:
        # Produce error CSV.
        errors_csv = flat_dict_to_csv(errors_dict)
        # Draw table.
        siemplify.result.add_data_table("Unsuccessful Attempts", errors_csv)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
