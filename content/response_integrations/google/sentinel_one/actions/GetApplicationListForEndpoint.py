from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SentinelOneManager import SentinelOneManager, SentinelOneAgentNotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import flat_dict_to_csv

# Consts.
SENTINEL_ONE_PROVIDER = "SentinelOne"
SENTINEL_PREFIX = "SENO_"
ADDRESS = EntityTypes.ADDRESS
HOSTNAME = EntityTypes.HOSTNAME


@output_handler
def main():
    # Define Variables.
    entities_successed = []
    errors_dict = {}
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

    # Run on entities.
    for entity in scope_entities:
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

            applications_list = sentinel_one_manager.get_applications_from_endpoint(
                agent_id, csv_output=True
            )

            if applications_list:
                entities_successed.append(entity)
                result_value = True
                # Add entity table.
                siemplify.result.add_entity_table(entity.identifier, applications_list)
        except SentinelOneAgentNotFoundError as err:
            errors_dict[entity.identifier] = str(err)

    if entities_successed:
        output_message = f'Found applications for: {",".join([entity.identifier for entity in entities_successed])}'
    else:
        output_message = "No applications were found for target entities."

    # If were errors present them as a table.
    if errors_dict:
        # Produce error CSV.
        errors_csv = flat_dict_to_csv(errors_dict)
        # Draw table.
        siemplify.result.add_data_table("Unsuccessful Attempts", errors_csv)

    siemplify.update_entities(entities_successed)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
