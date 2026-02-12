from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.NSMManager import NsmManager

# Consts
# Provider Sign.
NSM_PROVIDER = "McAfeeNSM"
ADDRESS = EntityTypes.ADDRESS


@output_handler
def main():
    # Define Variables.
    blocked_entitites = []
    unblocked_entities = []
    result_value = False
    # configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )

    # Fetch scope entities.
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == ADDRESS
    ]

    # Run on entities.
    for entity in scope_entities:
        # Check if address blocked.
        block_status = nsm_manager.is_ip_blocked(entity.identifier)
        if block_status:
            blocked_entitites.append(entity)
            result_value = True
        else:
            unblocked_entities.append(entity)

    # Logout from NSM.
    nsm_manager.logout()

    # Form output message.
    if scope_entities:
        output_message = (
            f"Blocked Entities: {','.join(map(str, blocked_entitites))} \n Unblocked"
            f" Entities: {','.join(map(str, unblocked_entities))}"
        )
    else:
        output_message = "No entities with type address at the case."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
