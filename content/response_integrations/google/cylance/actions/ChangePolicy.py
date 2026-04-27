from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CylanceManager import CylanceManager

SCRIPT_NAME = "Cylance - ChangePolicy"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Cylance")

    server_address = conf["Server Address"]
    application_secret = conf["Application Secret"]
    application_id = conf["Application ID"]
    tenant_identifier = conf["Tenant Identifier"]

    cm = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    policy_name = siemplify.parameters.get("Policy Name")

    affected_entities = []

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                device_id = cm.get_device_by_name(entity.identifier, is_address=True)
                cm.change_device_policy(device_id, policy_name)

                affected_entities.append(entity)

            elif entity.entity_type == EntityTypes.HOSTNAME:
                device_id = cm.get_device_by_name(entity.identifier)
                cm.change_device_policy(device_id, policy_name)

                affected_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]

        output_message = f"Policy {policy_name} was changed for:\n" + "\n".join(
            entities_names
        )

    else:
        output_message = "No entities were affected."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
